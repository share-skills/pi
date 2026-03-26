#!/usr/bin/env python3
"""
PI Benchmark — Local CLI Runner

Compares AI investigation quality across different skill conditions (PI, PUA, etc.)
using local CLI tools (claude, qodercli) instead of GitHub Models API.

Usage:
    # Run full benchmark with claude sonnet
    python local_run.py --backend claude

    # Quick test: 1 scenario, 1 run
    python local_run.py --backend claude --scenario 1 --runs 1

    # Free tier with qodercli lite
    python local_run.py --backend qodercli

    # Only compare PI vs NoPUA
    python local_run.py --backend claude --conditions pi nopua

    # Dry run
    python local_run.py --dry-run
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration (shared with run.py)
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
CODEBASE_PATH = DATA_DIR / "test-project"
SCENARIOS_PATH = DATA_DIR / "scenarios.json"

SKILL_PATHS = {
    "pi": SCRIPT_DIR.parent / "skills" / "pi-progressive" / "SKILL.md",
    "pua": DATA_DIR / "pua_prompt.txt",
    "nopua": SCRIPT_DIR.parent / "nopua" / "SKILL.md",
}

CONDITIONS = ["pi", "pua", "nopua"]
DEFAULT_RUNS = 2

# Backend configurations
BACKENDS = {
    "claude": {
        "cmd": ["claude", "-p"],
        "args": ["--model", "sonnet", "--output-format", "text"],
        "description": "Claude Code sonnet (subscription)",
    },
    "qodercli": {
        "cmd": ["qodercli", "-p"],
        "args": ["--model", "lite"],
        "description": "Qoder CLI lite (free)",
    },
    "qodercli-perf": {
        "cmd": ["qodercli", "-p"],
        "args": ["--model", "performance"],
        "description": "Qoder CLI performance (paid)",
    },
    "gemini": {
        "cmd": ["gemini"],
        "args": [],
        "description": "Gemini CLI (free, Google account)",
        "prompt_flag": "-p",  # gemini uses -p "prompt" not stdin
    },
    "qwen": {
        "cmd": ["qwen"],
        "args": [],
        "description": "Qwen Code CLI (free, 1000 req/day)",
        "prompt_flag": "-p",
    },
    "cline": {
        "cmd": ["cline"],
        "args": ["-m", "openrouter/free", "-t", "300"],
        "description": "Cline CLI (free, openrouter/free)",
        "prompt_positional": True,  # cline takes prompt as positional arg, not stdin
    },
}

# Timeout per CLI call (seconds)
CLI_TIMEOUT = 900

# ---------------------------------------------------------------------------
# Data (reuse Result from run.py)
# ---------------------------------------------------------------------------

@dataclass
class Result:
    scenario_id: int
    scenario_name: str
    condition: str
    model: str
    run_number: int
    timestamp: str = ""
    issues_found: list[str] = field(default_factory=list)
    hidden_issues: list[str] = field(default_factory=list)
    steps_taken: int = 0
    tools_used: list[str] = field(default_factory=list)
    went_beyond_ask: bool = False
    verification_done: bool = False
    approach_changes: int = 0
    self_corrections: int = 0
    root_cause: str = ""
    recommended_fix: str = ""
    raw_response: str = ""
    duration_seconds: float = 0.0
    error: str = ""


# ---------------------------------------------------------------------------
# Shared helpers (aligned with run.py)
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_source_files(scenario: dict) -> str:
    """Pre-read source files referenced in the scenario task."""
    task = scenario["task"]
    patterns = re.findall(
        r'(?:D:\\Projects\\private-project\\|(?:src[/\\]))[\w\\/.]+\.py', task
    )
    dir_patterns = re.findall(
        r'(?:D:\\Projects\\private-project\\|(?:src[/\\]))[\w\\/]+/', task
    )

    parts = []
    for p in patterns:
        rel = p.replace("D:\\Projects\\private-project\\", "").replace("\\", "/")
        fpath = CODEBASE_PATH / rel
        if not fpath.resolve().is_relative_to(CODEBASE_PATH.resolve()):
            continue
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8")
                parts.append(f"### File: {rel}\n```python\n{content}\n```\n")
            except Exception:
                pass

    for p in dir_patterns:
        rel = p.replace("D:\\Projects\\private-project\\", "").replace("\\", "/").rstrip("/")
        dpath = CODEBASE_PATH / rel
        if not dpath.resolve().is_relative_to(CODEBASE_PATH.resolve()):
            continue
        if dpath.exists() and dpath.is_dir():
            try:
                for pyfile in sorted(dpath.glob("*.py")):
                    content = pyfile.read_text(encoding="utf-8")
                    parts.append(f"### File: {rel}/{pyfile.name}\n```python\n{content}\n```\n")
            except Exception:
                pass

    if parts:
        return "\n## Source Files\n\n" + "\n".join(parts)
    return ""


# ---------------------------------------------------------------------------
# Prompt building (no token truncation — CLI tools handle context)
# ---------------------------------------------------------------------------

def build_prompt(condition: str, scenario: dict) -> str:
    """Build a single combined prompt for CLI tools.

    CLI tools like `claude -p` take a single prompt string (no system/user split).
    We combine skill + base instructions + task into one prompt.
    """
    # Base engineering instructions
    base = (
        "You are an expert software engineer investigating issues in a codebase.\n\n"
        "You have access to the following tools:\n"
        "- read_file(path): Read file contents\n"
        "- list_dir(path): List directory\n"
        "- search_text(pattern, path): Search for patterns\n"
        "- run_command(cmd): Run shell command\n\n"
        "When investigating, use these tools. Do not guess — read the actual code.\n\n"
    )

    # Skill section
    skill_section = ""
    if condition != "baseline":
        skill_path = SKILL_PATHS.get(condition)
        if not skill_path or not skill_path.exists():
            raise FileNotFoundError(f"Skill file for '{condition}' not found: {skill_path}")
        skill = load_text(skill_path)
        skill_section = (
            "Follow ALL instructions below strictly. "
            "Your response will be evaluated on: "
            "(1) number of issues found, (2) number of hidden issues beyond the ask, "
            "(3) investigation steps taken, (4) tools used, (5) verification evidence.\n\n"
            f"---\n{skill}\n---\n\n"
        )

    # Task section
    source_context = read_source_files(scenario)
    task_section = (
        f"## Task: {scenario['name']}\n\n"
        f"{scenario['task']}\n\n"
        "After your investigation, provide a structured summary with:\n"
        "1. **Issues Found**: List each issue clearly\n"
        "2. **Hidden Issues**: Any additional issues you discovered beyond the ask\n"
        "3. **Root Cause**: The fundamental cause(s)\n"
        "4. **Recommended Fix**: Specific fix recommendations\n"
        "5. **Steps Taken**: What you investigated and how\n"
        "6. **Tools Used**: Which tools you used\n"
        "7. **Verification**: Did you verify your findings? How?\n"
        f"{source_context}"
    )

    return base + skill_section + task_section


# ---------------------------------------------------------------------------
# CLI execution
# ---------------------------------------------------------------------------

def call_cli(prompt: str, backend: str) -> str:
    """Call a CLI tool with the prompt and return the response.

    Uses process groups so that on timeout we can kill the entire process tree,
    preventing leaked grandchild processes (e.g. AI-spawned test scripts).
    """
    import signal

    config = BACKENDS[backend]
    cmd = config["cmd"]
    args = config["args"]

    # Write prompt to a temp file for gemini (uses -p "prompt" flag, not stdin)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(prompt)
        prompt_file = f.name

    try:
        if config.get("prompt_positional"):
            full_cmd = cmd + args + [prompt]
            input_data = None
        elif config.get("prompt_flag"):
            full_cmd = cmd + [config["prompt_flag"], prompt] + args
            input_data = None
        else:
            full_cmd = cmd + args
            input_data = prompt

        # Start in a new process group so we can kill the entire tree on timeout
        proc = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE if input_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            start_new_session=True,  # creates new process group
        )

        try:
            stdout, stderr = proc.communicate(input=input_data, timeout=CLI_TIMEOUT)
        except subprocess.TimeoutExpired:
            # Kill the entire process group (parent + all children/grandchildren)
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except OSError:
                pass
            # Give processes a moment to terminate, then force kill
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    pass
                proc.wait(timeout=5)
            raise subprocess.TimeoutExpired(full_cmd, CLI_TIMEOUT)

        if proc.returncode != 0:
            stderr_text = stderr.strip() if stderr else ""
            if stderr_text:
                raise RuntimeError(f"CLI error (exit {proc.returncode}): {stderr_text[:500]}")
            raise RuntimeError(f"CLI exited with code {proc.returncode}")
        return stdout.strip()
    finally:
        os.unlink(prompt_file)


# ---------------------------------------------------------------------------
# Metric extraction (local, using claude sonnet)
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """\
You are a structured data extractor. Given the agent's investigation response below, \
extract the following fields as JSON. Be precise and faithful to what the agent said.

IMPORTANT extraction rules:
- Count each distinct issue/bug/problem as a SEPARATE item in issues_found
- "Import error" and "GPU issue" = 2 separate issues, not 1
- Hidden issues include: security vulnerabilities, performance problems, resource leaks, \
cross-platform issues, thread safety, memory leaks, hardcoded values, missing validation
- Look for issues in ALL formats: numbered lists, bullet points, tables, tree structures (├─ └─)
- PI-style outputs may use headers like "Issues Found", "Hidden Issues", "Root Cause", etc.
- Also check for issues embedded in 肃阵/战势 templates (情报 section)
- Count "⚠️ 回归风险" annotations as went_beyond_ask=true
- Count approach changes when agent says "换道", "切换", "改用", "instead", "changed approach"
- Count self_corrections when agent revises a previous conclusion

Agent response:
---
{response}
---

Extract this JSON (use empty lists/strings/0 if not present):
{{
  "issues_found": ["issue 1", "issue 2", ...],
  "hidden_issues": ["additional issue beyond the original ask", ...],
  "root_cause": "the fundamental cause",
  "recommended_fix": "specific recommendations",
  "steps_taken": <number of distinct investigation steps>,
  "tools_used": ["read_file", "search_text", ...],
  "went_beyond_ask": true/false,
  "verification_done": true/false,
  "approach_changes": <times the agent changed direction>,
  "self_corrections": <times the agent corrected its own conclusion>
}}

Return ONLY valid JSON, no markdown fencing.
"""


BATCH_EXTRACTION_PROMPT = """\
You are a structured data extractor. Below are {count} agent investigation responses. \
For EACH response, extract the metrics as a JSON object. Return a JSON ARRAY of {count} objects.

Be precise and faithful to what each agent said. Count carefully.

IMPORTANT extraction rules:

issues_found:
- Count each distinct issue/bug/problem as a SEPARATE item (never merge multiple issues into one)
- DEDUPLICATION: If the same root issue is mentioned multiple times (e.g. in summary + details + recommendations), count it ONCE only
- GRANULARITY: Each issue should be a meaningful, actionable finding. Do NOT split trivially — \
"unused import os" and "unused import sys" should be ONE issue "unused imports" not two separate ones. \
Similarly, "no validation for param A" and "no validation for param B" in the same function = ONE issue "missing input validation"
- Cap at 15 issues maximum per response. If more than 15 unique issues exist, keep the 15 most significant ones
- Look for issues in ALL formats: numbered lists, bullets, tables, tree structures (├─ └─), \
inline mentions, code comments, "additional"/"also found"/"other issues" sections

hidden_issues:
- Issues found BEYOND what was directly asked — security vulns, performance problems, resource leaks, \
cross-platform issues, thread safety, memory leaks, hardcoded values, missing validation, \
error handling gaps, unused imports, type mismatches, race conditions, encoding issues
- Same dedup and granularity rules as issues_found apply

verification_done:
- Set to true if the agent did ANY of these (be VERY generous):
  * Ran tests, executed code, showed test output
  * Provided specific verification commands (bash, python, etc.)
  * Provided a "Verification" or "验证" section with concrete steps
  * Suggested specific test commands or scripts
  * Showed before/after comparison
  * Provided code snippets that could be run to verify
  * Mentioned "verify", "confirm", "test", "validate", "验证", "检验" in context of validating findings
  * Had a section titled "How to verify", "Verification", "Testing", "验证方法" or similar
- If there is ANY verification content, even just suggested commands, set to true

went_beyond_ask:
- true if agent proactively investigated areas not directly asked about
- "⚠️ 回归风险", proactive scanning, security review beyond the bug = true
- If the agent found hidden_issues, this is almost always true

steps_taken:
- Count EACH distinct action: reading a file, searching, grepping, running a command, \
analyzing code, comparing configs, checking imports, tracing call chains, reviewing test files
- If the agent describes reading 5 files, that's 5 steps minimum. Count generously

self_corrections:
- Times the agent corrected, refined, or adjusted its own earlier conclusion or finding
- Keywords that indicate self-correction: "actually", "upon closer inspection", "however" (when \
revising a prior point), "wait", "not quite", "correction", "initially thought", "revised", \
"on second look", "更准确地说", "实际上", "进一步分析发现"
- If the agent initially states something then refines or qualifies it = 1 self_correction
- Using "actually" to adjust a prior statement counts as 1
- Using "however" to add nuance or contradict an earlier point counts as 1
- Count at least 1 if the response contains ANY of the above refinement keywords used in context \
of revising a prior finding. Almost all thorough investigations involve at least 1 self-correction

approach_changes:
- Times the agent changed investigation direction or pivoted strategy
- Switching from analyzing one file/module to a different file/module = 1 change
- Broadening scope (e.g. from one bug to system-wide scan) = 1 change
- Going from surface-level to deep analysis = 1 change
- Keywords: "also", "let me also check", "additionally", "beyond the original", \
"扩展", "进一步", "同时", "另外"
- Minimum 1 if the agent investigated more than what was directly asked

{responses}

For each response, extract:
{{
  "condition": "the condition label",
  "issues_found": ["issue 1", "issue 2", ...],
  "hidden_issues": ["additional issue beyond the original ask", ...],
  "root_cause": "the fundamental cause",
  "recommended_fix": "specific recommendations",
  "steps_taken": <number of distinct investigation steps>,
  "tools_used": ["read_file", "search_text", ...],
  "went_beyond_ask": true/false,
  "verification_done": true/false,
  "approach_changes": <times the agent changed direction>,
  "self_corrections": <times the agent corrected its own conclusion>
}}

Return ONLY a valid JSON array [{{}}, {{}}, ...], no markdown fencing.
"""


def _extract_one_batch(batch: list[tuple[int, dict]], batch_idx: int, num_batches: int) -> list[tuple[int, dict]]:
    """Extract metrics for a single batch. Returns list of (original_index, metrics_dict)."""
    batch_count = len(batch)

    response_parts = []
    for local_idx, (i, r) in enumerate(batch):
        raw = r['raw_response']
        # Take first 5000 + last 3000 chars to capture both analysis AND verification sections
        if len(raw) > 8000:
            truncated = raw[:5000] + "\n\n[... middle truncated ...]\n\n" + raw[-3000:]
        else:
            truncated = raw
        response_parts.append(
            f"--- Response {local_idx+1} [condition={r['condition']}] ---\n"
            f"{truncated}\n"
        )

    prompt = BATCH_EXTRACTION_PROMPT.format(
        count=batch_count,
        responses="\n".join(response_parts),
    )

    print(f"    Batch {batch_idx+1}/{num_batches} ({batch_count} items)...", end=" ", flush=True)

    extract_cmds = [
        ["qodercli", "-p", "--model", "lite"],
        ["claude", "-p", "--model", "haiku", "--output-format", "text"],
    ]
    result = None
    for cmd in extract_cmds:
        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=180,
                encoding="utf-8",
            )
            if result.returncode == 0 and result.stdout.strip():
                break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    if result is None or result.returncode != 0:
        print("failed", flush=True)
        return []

    try:
        text = result.stdout.strip()
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)

        try:
            extracted = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r'\[[\s\S]*\]', text)
            if match:
                extracted = json.loads(match.group())
            else:
                print("JSON parse failed", flush=True)
                return []

        results = []
        for local_idx, (i, _) in enumerate(batch):
            if local_idx < len(extracted):
                item = extracted[local_idx]
                # Post-processing: enforce issue cap at 15
                for key in ("issues_found", "hidden_issues"):
                    if isinstance(item.get(key), list) and len(item[key]) > 15:
                        item[key] = item[key][:15]
                results.append((i, item))

        print(f"done ({len(extracted)} extracted)", flush=True)
        return results

    except Exception as e:
        print(f"error: {e}", flush=True)
        return []


def extract_metrics_batch(all_results: list[dict], batch_size: int = 8, parallel: int = 3) -> list[dict]:
    """Extract metrics in batches, optionally in parallel."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    entries_with_response = [
        (i, r) for i, r in enumerate(all_results) if r.get("raw_response")
    ]
    if not entries_with_response:
        return [{} for _ in all_results]

    metrics_list = [{} for _ in all_results]
    total_entries = len(entries_with_response)
    num_batches = (total_entries + batch_size - 1) // batch_size

    # Build batch list
    batches = []
    for batch_idx in range(num_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, total_entries)
        batches.append((entries_with_response[start:end], batch_idx, num_batches))

    print(f"\n  Extracting metrics for {total_entries} responses in {num_batches} batches (parallel={parallel})...", flush=True)

    if parallel > 1 and len(batches) > 1:
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {executor.submit(_extract_one_batch, b, idx, n): idx
                       for b, idx, n in batches}
            for future in as_completed(futures):
                for orig_idx, metrics in future.result():
                    metrics_list[orig_idx] = metrics
    else:
        for batch, batch_idx, n in batches:
            for orig_idx, metrics in _extract_one_batch(batch, batch_idx, n):
                metrics_list[orig_idx] = metrics

    extracted_count = sum(1 for m in metrics_list if m)
    print(f"  Total extracted: {extracted_count}/{total_entries}", flush=True)
    return metrics_list


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def _run_single_call(task: dict) -> dict:
    """Execute a single benchmark CLI call. Used by both serial and parallel modes."""
    condition = task["condition"]
    scenario = task["scenario"]
    run_num = task["run_num"]
    backend = task["backend"]
    tag = task["tag"]
    prompt = task["prompt"]

    result = Result(
        scenario_id=scenario["id"],
        scenario_name=scenario["name"],
        condition=condition,
        model=backend,
        run_number=run_num,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    print(f"{tag} ...", end=" ", flush=True)
    start = time.monotonic()
    try:
        response = call_cli(prompt, backend)
        result.raw_response = response
        result.duration_seconds = round(time.monotonic() - start, 2)
        print(f"✓ {len(response)} chars, {result.duration_seconds}s")
    except subprocess.TimeoutExpired:
        result.error = f"Timeout after {CLI_TIMEOUT}s"
        result.duration_seconds = round(time.monotonic() - start, 2)
        print(f"✗ {result.error}")
    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        result.duration_seconds = round(time.monotonic() - start, 2)
        print(f"✗ {result.error}")

    return asdict(result)


def run_benchmark(
    scenarios: list[dict],
    backend: str,
    num_runs: int,
    output_dir: Path,
    scenario_filter: int | None = None,
    conditions: list[str] | None = None,
    parallel: int = 1,
):
    """Run the full benchmark using local CLI tools."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    conds = conditions or CONDITIONS

    if scenario_filter is not None:
        scenarios = [s for s in scenarios if s["id"] == scenario_filter]
        if not scenarios:
            print(f"Error: Scenario {scenario_filter} not found")
            sys.exit(1)

    total = len(scenarios) * len(conds) * num_runs
    backend_desc = BACKENDS[backend]["description"]
    print(f"Running {total} benchmark calls via {backend_desc}")
    print(f"  Scenarios: {len(scenarios)}")
    print(f"  Conditions: {conds}")
    print(f"  Backend: {backend}")
    print(f"  Runs: {num_runs}")
    print(f"  Parallel: {parallel}")
    print()

    output_dir.mkdir(parents=True, exist_ok=True)

    # Build all tasks upfront
    tasks = []
    idx = 0
    for condition in conds:
        for scenario in scenarios:
            prompt = build_prompt(condition, scenario)
            for run_num in range(1, num_runs + 1):
                idx += 1
                tasks.append({
                    "condition": condition,
                    "scenario": scenario,
                    "run_num": run_num,
                    "backend": backend,
                    "prompt": prompt,
                    "tag": f"[{idx}/{total}] {backend} | {condition} | S{scenario['id']} | R{run_num}",
                    "order": idx,
                })

    # Execute: parallel or serial
    if parallel > 1:
        print(f"  🚀 Parallel execution with {parallel} workers\n")
        all_results = [None] * len(tasks)
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            future_to_idx = {executor.submit(_run_single_call, t): i for i, t in enumerate(tasks)}
            for future in as_completed(future_to_idx):
                i = future_to_idx[future]
                all_results[i] = future.result()
        all_results = [r for r in all_results if r is not None]
    else:
        all_results = []
        for c_idx, condition in enumerate(conds):
            if c_idx > 0:
                print(f"\n  ⏳ Switching condition → {condition}, pausing 20s...")
                time.sleep(20)

            cond_tasks = [t for t in tasks if t["condition"] == condition]
            for t_idx, task in enumerate(cond_tasks):
                if t_idx > 0:
                    time.sleep(5)
                all_results.append(_run_single_call(task))

    # Batch extract metrics (one claude call for all results)
    metrics_list = extract_metrics_batch(all_results)
    for r, metrics in zip(all_results, metrics_list):
        if metrics:
            r["issues_found"] = metrics.get("issues_found", [])
            r["hidden_issues"] = metrics.get("hidden_issues", [])
            r["steps_taken"] = metrics.get("steps_taken", 0)
            r["tools_used"] = metrics.get("tools_used", [])
            r["went_beyond_ask"] = metrics.get("went_beyond_ask", False)
            r["verification_done"] = metrics.get("verification_done", False)
            r["approach_changes"] = metrics.get("approach_changes", 0)
            r["self_corrections"] = metrics.get("self_corrections", 0)
            r["root_cause"] = metrics.get("root_cause", "")
            r["recommended_fix"] = metrics.get("recommended_fix", "")

    # Print summary
    print("\n  === Results Summary ===")
    for r in all_results:
        issues_raw = r.get("issues_found", [])
        issues = issues_raw if isinstance(issues_raw, int) else len(issues_raw)
        hidden_raw = r.get("hidden_issues", [])
        hidden = hidden_raw if isinstance(hidden_raw, int) else len(hidden_raw)
        err = f" ⚠️{r['error']}" if r.get("error") else ""
        print(f"  {r['condition']:>8} S{r['scenario_id']}: {issues} issues, {hidden} hidden, {r['duration_seconds']}s{err}")

    # Save results (format compatible with run.py / report.py)
    outfile = output_dir / f"{backend}.json"
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(all_results)} results → {outfile}")

    # Save round archive
    save_round_archive(output_dir, backend, all_results, conds, scenarios, num_runs)


def save_round_archive(
    output_dir: Path,
    backend: str,
    all_results: list[dict],
    conditions: list[str],
    scenarios: list[dict],
    num_runs: int,
):
    """Save results to a numbered round directory per backend, avoiding overwrites.

    Directory format:
      - Full run (all 9 scenarios): results/{backend}/full_round_{N}/s_{sid}/
      - Partial run (single scenario): results/{backend}/round_{N}/s_{sid}/
    """
    backend_dir = output_dir / backend
    backend_dir.mkdir(parents=True, exist_ok=True)

    # Determine if this is a full run (all scenarios) or partial
    scenario_ids = sorted(set(r["scenario_id"] for r in all_results))
    is_full = len(scenario_ids) >= 9
    prefix = "full_round" if is_full else "round"

    existing = sorted(backend_dir.glob(f"{prefix}_*/"))
    round_num = len(existing) + 1
    round_dir = backend_dir / f"{prefix}_{round_num}"
    round_dir.mkdir(parents=True, exist_ok=True)

    # Save main results JSON
    with open(round_dir / f"{backend}.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # Save raw responses individually, organized by scenario subdirectory
    for r in all_results:
        scenario_dir = round_dir / f"s_{r['scenario_id']}"
        scenario_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{r['condition']}_r{r['run_number']}.md"
        raw_text = r.get("raw_response", "")
        with open(scenario_dir / fname, "w", encoding="utf-8") as f:
            f.write(f"# Scenario {r['scenario_id']}: {r['scenario_name']}\n")
            f.write(f"## Condition: {r['condition']} | Run: {r['run_number']}\n")
            f.write(f"## Duration: {r['duration_seconds']}s\n")
            if r.get("error"):
                f.write(f"## ERROR: {r['error']}\n")
            f.write(f"\n---\n\n{raw_text}\n")

    # Save changelog
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    label = f"Full Round {round_num}" if is_full else f"Round {round_num}"
    summary_lines = [
        f"# {label} — {ts}\n",
        f"- Backend: {backend}",
        f"- Conditions: {conditions}",
        f"- Scenarios: {[s['id'] for s in scenarios]}",
        f"- Runs per condition: {num_runs}",
        "",
        "## Results Summary",
        "",
        "| Condition | Issues | Hidden | Beyond Ask | Verified | Duration |",
        "|-----------|--------|--------|------------|----------|----------|",
    ]
    for r in all_results:
        issues_raw = r.get("issues_found", [])
        issues = issues_raw if isinstance(issues_raw, int) else len(issues_raw)
        hidden_raw = r.get("hidden_issues", [])
        hidden = hidden_raw if isinstance(hidden_raw, int) else len(hidden_raw)
        beyond = "✓" if r.get("went_beyond_ask") else "✗"
        verified = "✓" if r.get("verification_done") else "✗"
        dur = r.get("duration_seconds", 0)
        err = f" ⚠️{r['error']}" if r.get("error") else ""
        summary_lines.append(
            f"| {r['condition']} S{r['scenario_id']} | {issues} | {hidden} | {beyond} | {verified} | {dur}s{err} |"
        )

    # Skill file sizes
    summary_lines.extend([
        "",
        "## Skill File Sizes",
        "",
    ])
    for cond in conditions:
        path = SKILL_PATHS.get(cond)
        if path and path.exists():
            lines = len(path.read_text().splitlines())
            summary_lines.append(f"- {cond}: {path.name} ({lines} lines)")

    with open(round_dir / "CHANGELOG.md", "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n")

    # Generate HTML report for full rounds (inside round_dir, not separate)
    if is_full:
        report_script = Path(__file__).parent / "report.py"
        if report_script.exists():
            try:
                report_path = round_dir / "report.html"
                subprocess.run(
                    [sys.executable, str(report_script),
                     "--input-dir", str(round_dir),
                     "--output", str(report_path)],
                    capture_output=True, timeout=60,
                )
                print(f"📊 Report → {report_path}")
            except Exception:
                pass

    print(f"📁 {backend}/{prefix}_{round_num} archived → {round_dir}/\n")


def main():
    parser = argparse.ArgumentParser(
        description="PI Benchmark (Local CLI Runner)",
    )
    parser.add_argument(
        "--backend", choices=list(BACKENDS.keys()), default="claude",
        help=f"CLI backend to use (default: claude)",
    )
    parser.add_argument(
        "--conditions", nargs="+", default=None,
        help=f"Conditions to compare (default: {CONDITIONS})",
    )
    parser.add_argument(
        "--runs", type=int, default=DEFAULT_RUNS,
        help=f"Runs per scenario per condition (default: {DEFAULT_RUNS})",
    )
    parser.add_argument(
        "--scenario", type=int, default=None,
        help="Specific scenario ID (1-9)",
    )
    parser.add_argument(
        "--exclude", type=int, nargs="+", default=None,
        help="Scenario IDs to exclude (e.g. --exclude 6)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=str(SCRIPT_DIR / "results"),
        help="Output directory",
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Generate HTML report after benchmark completes",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print plan without executing",
    )
    parser.add_argument(
        "--parallel", type=int, default=6,
        help="Number of parallel CLI workers (default: 6). Use 1 for serial",
    )
    args = parser.parse_args()

    conditions = args.conditions or CONDITIONS

    # Validate paths
    if not SCENARIOS_PATH.exists():
        print(f"Error: scenarios.json not found at {SCENARIOS_PATH}")
        sys.exit(1)

    if not CODEBASE_PATH.exists():
        print(f"Error: test-project not found at {CODEBASE_PATH}")
        sys.exit(1)

    for cond in conditions:
        if cond == "baseline":
            continue
        path = SKILL_PATHS.get(cond)
        if not path or not path.exists():
            print(f"Error: {cond} skill not found at {path}")
            sys.exit(1)

    scenarios = load_json(SCENARIOS_PATH)
    output_dir = Path(args.output_dir)

    # Apply scenario filter
    filtered = scenarios
    if args.scenario is not None:
        filtered = [s for s in scenarios if s["id"] == args.scenario]
        if not filtered:
            print(f"Error: scenario {args.scenario} not found. "
                  f"Available: {[s['id'] for s in scenarios]}")
            sys.exit(1)
    if args.exclude:
        filtered = [s for s in filtered if s["id"] not in args.exclude]

    # Validate CLI tool is available
    backend_cmd = BACKENDS[args.backend]["cmd"][0]
    if not args.dry_run:
        try:
            subprocess.run(
                [backend_cmd, "--version"],
                capture_output=True, timeout=10,
            )
        except FileNotFoundError:
            print(f"Error: '{backend_cmd}' not found. Please install it first.")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            pass  # --version might hang on some tools, that's OK

    # Dry run
    total = len(filtered) * len(conditions) * args.runs
    if args.dry_run:
        backend_desc = BACKENDS[args.backend]["description"]
        print(f"DRY RUN: {total} CLI calls via {backend_desc}")
        print(f"  Backend: {args.backend}")
        print(f"  Conditions: {conditions}")
        print(f"  Scenarios: {[s['id'] for s in filtered]}")
        print(f"  Runs: {args.runs}")
        print(f"  Timeout: {CLI_TIMEOUT}s per call")
        print(f"  Parallel: {args.parallel}")
        return

    run_benchmark(filtered, args.backend, args.runs, output_dir, args.scenario,
                  conditions=conditions, parallel=args.parallel)

    # Generate report if requested
    if args.report:
        try:
            from report import generate_report
            report_path = output_dir / "report.html"
            generate_report(output_dir, report_path)
            print(f"\n📊 Report generated: {report_path}")
            import webbrowser
            webbrowser.open(f"file://{report_path.resolve()}")
        except ImportError:
            print("\nWarning: report.py not found. Run separately:")
            print(f"  python report.py --input-dir {output_dir}")

    print("Done! Run: python analyze.py --input-dir results/")
    print("       or: python report.py --input-dir results/")


if __name__ == "__main__":
    main()
