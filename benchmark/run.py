#!/usr/bin/env python3
"""
PI Benchmark — GitHub Models API Runner

Compares AI investigation quality across different skill conditions (PI, PUA, etc.).
Uses GitHub Models API (OpenAI-compatible) for unified multi-model access.

Usage:
    # Run full benchmark (all models, all scenarios, 2 runs)
    python run.py

    # Single model
    python run.py --models gpt-4o

    # Specific scenario
    python run.py --scenario 3

    # Custom conditions (default: pi,pua)
    python run.py --conditions pi pua baseline

    # Generate prompt files for manual Copilot Chat testing
    python run.py --prompts

    # Dry run
    python run.py --dry-run

    # Run + generate report
    python run.py --report
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent

# Self-contained test data directory (benchmark/data/)
DATA_DIR = SCRIPT_DIR / "data"
CODEBASE_PATH = DATA_DIR / "test-project"
SCENARIOS_PATH = DATA_DIR / "scenarios.json"

# Skill / prompt files for each condition.
# Paths are configurable via CLI (--pi-skill, --pua-skill, --nopua-skill).
# NOTE: GitHub Models API has an 8K token limit per request (~32KB text).
#       Use the progressive/compact variant for PI to fit within limits.
SKILL_PATHS = {
    "pi": SCRIPT_DIR.parent / "skills" / "pi-progressive" / "SKILL.md",
    "pi-lite": SCRIPT_DIR.parent / "skills" / "pi-progressive" / "SKILL_LITE.md",
    "pua": DATA_DIR / "pua_prompt.txt",
    "nopua": SCRIPT_DIR.parent / "nopua" / "SKILL.md",
    # "baseline" has no file — handled specially in build_system_prompt()
}

# GitHub Models API (OpenAI-compatible endpoint)
# Auth: GITHUB_TOKEN env var (from `gh auth token` or PAT with models:read)
GITHUB_MODELS_URL = "https://models.inference.ai.azure.com"

# Model aliases → actual model IDs on GitHub Models
# Adjust if GitHub Models catalog changes
MODELS = {
    "gpt-4.1": "gpt-4.1",
    "gpt-4o": "gpt-4o",
    # gpt-5-mini: 4K token limit + 12 calls/day + no temp control = unusable for benchmark
    # "gpt-5-mini": "gpt-5-mini",
}

# GitHub Models free-tier token limits (input tokens).
# These limits constrain prompt size; we reserve ~20% for output.
# NOTE: These are INPUT limits from GitHub Models error messages.
MODEL_TOKEN_LIMITS = {
    "gpt-4.1": 8000,
    "gpt-5-mini": 4000,
    "gpt-4o": 8000,
}
DEFAULT_TOKEN_LIMIT = 8000

# Models that don't support temperature=0 (only default=1).
# gpt-5-mini on GitHub Models free tier only supports temperature=1.
MODELS_NO_TEMP_CONTROL = {"gpt-5-mini"}

# Default: PI vs PI-lite vs PUA vs NoPUA four-way comparison
CONDITIONS = ["pi", "pua", "nopua"]
DEFAULT_RUNS = 2

# Extraction model (free-tier, fast, 50 calls/day on GitHub Models)
EXTRACTION_MODEL = "gpt-4.1"

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@dataclass
class Result:
    scenario_id: int
    scenario_name: str
    condition: str
    model: str
    run_number: int
    timestamp: str = ""
    # Extracted metrics
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
    # Raw data
    raw_response: str = ""
    duration_seconds: float = 0.0
    error: str = ""


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Any:
    # Use utf-8-sig to handle optional BOM (byte-order mark)
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def read_source_files(scenario: dict) -> str:
    """Pre-read source files referenced in the scenario task."""
    task = scenario["task"]
    # Extract file paths from task description
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
        # Guard against path traversal (e.g. ../../etc/passwd)
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
        # Guard against path traversal
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


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: CJK chars ~1 tok, other chars ~0.25 tok."""
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3000' <= c <= '\u303f')
    return cjk + (len(text) - cjk) // 4


def _truncate_to_tokens(text: str, max_tokens: int, label: str = "content") -> str:
    """Truncate text to fit within estimated token budget."""
    if _estimate_tokens(text) <= max_tokens:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _estimate_tokens(text[:mid]) <= max_tokens:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo] + f"\n\n[... {label} truncated to ~{max_tokens} tokens ...]"


def build_system_prompt(condition: str, model: str = "") -> str:
    """Build system prompt for a condition.

    - 'baseline' → no skill, just the base engineering prompt.
    - 'pua'      → fear-driven PUA prompt loaded from pua_prompt.txt.
    - 'pi'/'nopua' → wisdom-driven skill loaded from SKILL.md.

    Token budget is model-aware: smaller models get more aggressive truncation.
    """
    base = (
        "You are an expert software engineer investigating issues in a codebase.\n\n"
        "You have access to the following tools:\n"
        "- read_file(path): Read file contents\n"
        "- list_dir(path): List directory\n"
        "- search_text(pattern, path): Search for patterns\n"
        "- run_command(cmd): Run shell command\n\n"
        "When investigating, use these tools. Do not guess — read the actual code.\n\n"
    )
    # Baseline: no skill loaded, pure model capability.
    if condition == "baseline":
        return base

    skill_path = SKILL_PATHS.get(condition)
    if not skill_path or not skill_path.exists():
        raise FileNotFoundError(f"Skill file for '{condition}' not found: {skill_path}")

    skill = load_text(skill_path)

    # Model-aware token budget: allocate 60% of model limit to skill text,
    # reserving the rest for base prompt + user prompt + output.
    token_limit = MODEL_TOKEN_LIMITS.get(model, DEFAULT_TOKEN_LIMIT)
    max_skill_tokens = int(token_limit * 0.6)
    skill = _truncate_to_tokens(skill, max_skill_tokens, "skill")

    return base + (
        "The following skill guides your approach:\n\n"
        f"---\n{skill}\n---\n\n"
        "Apply this skill's principles as you investigate the issue below."
    )


def build_user_prompt(scenario: dict, model: str = "") -> str:
    """Build user prompt from scenario + source files."""
    task_prompt = (
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
    )
    source_context = read_source_files(scenario)
    # Model-aware: allocate 25% of token limit to source context
    token_limit = MODEL_TOKEN_LIMITS.get(model, DEFAULT_TOKEN_LIMIT)
    max_source_tokens = int(token_limit * 0.25)
    source_context = _truncate_to_tokens(source_context, max_source_tokens, "source")
    return task_prompt + source_context


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def call_model(system_prompt: str, user_prompt: str, model_id: str) -> str:
    """Call a model via GitHub Models API (OpenAI-compatible)."""
    from openai import OpenAI

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN not set. Run: export GITHUB_TOKEN=$(gh auth token)"
        )

    # Newer models (gpt-5-mini etc.) require 'max_completion_tokens' instead of 'max_tokens'.
    # Some models also don't support temperature=0 (only default=1).
    client = OpenAI(base_url=GITHUB_MODELS_URL, api_key=token)
    kwargs = dict(
        model=model_id,
        max_completion_tokens=8192,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    if model_id not in MODELS_NO_TEMP_CONTROL:
        kwargs["temperature"] = 0
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """\
You are a structured data extractor. Given the agent's investigation response below, \
extract the following fields as JSON. Be precise and faithful to what the agent said.

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


def extract_metrics(response: str) -> dict:
    """Extract structured metrics from agent response."""
    from openai import OpenAI

    token = os.environ.get("GITHUB_TOKEN")
    client = OpenAI(base_url=GITHUB_MODELS_URL, api_key=token)

    prompt = EXTRACTION_PROMPT.format(response=response[:8000])
    resp = client.chat.completions.create(
        model=EXTRACTION_MODEL,
        max_completion_tokens=2000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.choices[0].message.content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# Prompt file generation (for manual Copilot Chat)
# ---------------------------------------------------------------------------

def generate_prompt_files(scenarios: list[dict], output_dir: Path,
                          conditions: list[str] | None = None):
    """Generate markdown prompt files for manual testing in Copilot Chat."""
    conds = conditions or CONDITIONS
    prompts_dir = output_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    for scenario in scenarios:
        for condition in conds:
            fname = f"s{scenario['id']:02d}_{condition}.md"
            system = build_system_prompt(condition, model="gpt-4.1")
            user = build_user_prompt(scenario, model="gpt-4.1")

            content = (
                f"# Scenario {scenario['id']}: {scenario['name']} [{condition.upper()}]\n\n"
                f"## System Prompt\n\n"
                f"Paste the following as system context (or prepend to your message):\n\n"
                f"---\n\n{system}\n\n---\n\n"
                f"## User Prompt\n\n"
                f"Then send this as your message:\n\n"
                f"---\n\n{user}\n\n---\n\n"
                f"## Scoring\n\n"
                f"After getting the response, count:\n"
                f"- Issues Found: explicit bugs/problems identified\n"
                f"- Hidden Issues: problems found beyond what was asked\n"
                f"- Steps Taken: distinct investigation steps\n"
                f"- Went Beyond Ask: yes/no\n"
                f"- Verification Done: yes/no\n"
                f"- Approach Changes: direction changes\n"
                f"- Self-Corrections: corrected own earlier conclusion\n"
            )
            (prompts_dir / fname).write_text(content, encoding="utf-8")

    count = len(scenarios) * len(conds)
    print(f"Generated {count} prompt files in {prompts_dir}/")
    print(f"Use these in Copilot Chat: paste system + user prompt, record response.")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_benchmark(
    scenarios: list[dict],
    models: list[str],
    num_runs: int,
    output_dir: Path,
    scenario_filter: int | None = None,
    conditions: list[str] | None = None,
):
    """Run the full benchmark."""
    conds = conditions or CONDITIONS

    if scenario_filter is not None:
        scenarios = [s for s in scenarios if s["id"] == scenario_filter]
        if not scenarios:
            print(f"Error: Scenario {scenario_filter} not found")
            sys.exit(1)

    total = len(scenarios) * len(conds) * len(models) * num_runs
    print(f"Running {total} benchmark calls")
    print(f"  Scenarios: {len(scenarios)}")
    print(f"  Conditions: {conds}")
    print(f"  Models: {models}")
    print(f"  Runs: {num_runs}")
    print()

    output_dir.mkdir(parents=True, exist_ok=True)
    done = 0

    for model_name in models:
        model_id = MODELS.get(model_name, model_name)
        all_results = []

        for condition in conds:
            system_prompt = build_system_prompt(condition, model=model_id)

            for scenario in scenarios:
                user_prompt = build_user_prompt(scenario, model=model_id)

                for run_num in range(1, num_runs + 1):
                    done += 1
                    tag = f"[{done}/{total}] {model_name} | {condition} | S{scenario['id']} | R{run_num}"
                    print(f"{tag} ...", end=" ", flush=True)

                    result = Result(
                        scenario_id=scenario["id"],
                        scenario_name=scenario["name"],
                        condition=condition,
                        model=model_name,
                        run_number=run_num,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )

                    start = time.monotonic()
                    try:
                        response = call_model(system_prompt, user_prompt, model_id)
                        result.raw_response = response
                        result.duration_seconds = round(time.monotonic() - start, 2)

                        # Extract metrics
                        metrics = extract_metrics(response)
                        if metrics:
                            result.issues_found = metrics.get("issues_found", [])
                            result.hidden_issues = metrics.get("hidden_issues", [])
                            result.steps_taken = metrics.get("steps_taken", 0)
                            result.tools_used = metrics.get("tools_used", [])
                            result.went_beyond_ask = metrics.get("went_beyond_ask", False)
                            result.verification_done = metrics.get("verification_done", False)
                            result.approach_changes = metrics.get("approach_changes", 0)
                            result.self_corrections = metrics.get("self_corrections", 0)
                            result.root_cause = metrics.get("root_cause", "")
                            result.recommended_fix = metrics.get("recommended_fix", "")

                        issues = len(result.issues_found)
                        hidden = len(result.hidden_issues)
                        print(f"✓ {issues} issues, {hidden} hidden, {result.duration_seconds}s")

                    except Exception as e:
                        result.error = f"{type(e).__name__}: {e}"
                        result.duration_seconds = round(time.monotonic() - start, 2)
                        print(f"✗ {result.error}")

                    all_results.append(asdict(result))

                    # Rate limit courtesy
                    time.sleep(1)

        # Save per-model results
        outfile = output_dir / f"{model_name}.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(all_results)} results → {outfile}\n")


def main():
    parser = argparse.ArgumentParser(
        description="PI Benchmark (GitHub Models API)",
    )
    parser.add_argument(
        "--models", nargs="+", default=list(MODELS.keys()),
        help=f"Models to test (default: {list(MODELS.keys())})",
    )
    parser.add_argument(
        "--conditions", nargs="+", default=None,
        help=f"Conditions to compare (default: {CONDITIONS}). "
             f"Available: pi, pua, nopua, baseline",
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
        "--output-dir", type=str, default=str(SCRIPT_DIR / "results"),
        help="Output directory",
    )
    parser.add_argument(
        "--prompts", action="store_true",
        help="Generate prompt files for manual Copilot Chat testing (no API calls)",
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Generate HTML report after benchmark completes",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print plan without executing",
    )
    args = parser.parse_args()

    # Resolve conditions
    conditions = args.conditions or CONDITIONS

    # Validate paths
    if not SCENARIOS_PATH.exists():
        print(f"Error: scenarios.json not found at {SCENARIOS_PATH}")
        print("Make sure nopua/benchmark/ is present.")
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

    # Apply scenario filter early (shared by --prompts, --dry-run, and full run)
    filtered = scenarios
    if args.scenario is not None:
        filtered = [s for s in scenarios if s["id"] == args.scenario]
        if not filtered:
            print(f"Error: scenario {args.scenario} not found. "
                  f"Available: {[s['id'] for s in scenarios]}")
            sys.exit(1)

    # Generate prompt files mode
    if args.prompts:
        generate_prompt_files(filtered, output_dir, conditions=conditions)
        return

    # Dry run (no token needed)
    total = len(filtered) * len(conditions) * len(args.models) * args.runs

    if args.dry_run:
        print(f"DRY RUN: {total} API calls")
        print(f"  Models: {args.models}")
        print(f"  Conditions: {conditions}")
        print(f"  Scenarios: {[s['id'] for s in filtered]}")
        print(f"  Runs: {args.runs}")
        est_cost = total * 0.12  # rough estimate per call
        print(f"  Est. cost: ~${est_cost:.0f}")
        return

    # Validate GitHub token (only needed for actual API calls)
    if not os.environ.get("GITHUB_TOKEN"):
        print("Error: GITHUB_TOKEN not set.")
        print("Run: export GITHUB_TOKEN=$(gh auth token)")
        print("Or use --prompts to generate files for manual testing.")
        sys.exit(1)

    run_benchmark(scenarios, args.models, args.runs, output_dir, args.scenario,
                  conditions=conditions)

    # Generate report if requested
    if args.report:
        try:
            from report import generate_report
            report_path = output_dir / "report.html"
            generate_report(output_dir, report_path)
            print(f"\n📊 Report generated: {report_path}")
            # Try to open in browser
            import webbrowser
            webbrowser.open(f"file://{report_path.resolve()}")
        except ImportError:
            print("\nWarning: report.py not found. Run separately:")
            print(f"  python report.py --input-dir {output_dir}")

    print("Done! Run: python analyze.py --input-dir results/")
    print("       or: python report.py --input-dir results/")


if __name__ == "__main__":
    main()
