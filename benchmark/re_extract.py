#!/usr/bin/env python3
"""Re-extract metrics from existing raw responses using claude haiku (one-by-one)."""

import json
import re
import subprocess
import sys
from pathlib import Path

RESULTS_FILE = Path(__file__).parent / "results" / "qodercli.json"

EXTRACTION_PROMPT = """\
You are a structured data extractor. Given the agent's investigation response below, \
extract the following fields as JSON. Be precise and faithful to what the agent said.

IMPORTANT extraction rules:
- Count each distinct issue/bug/problem as a SEPARATE item in issues_found
- "Import error" and "GPU issue" = 2 separate issues, not 1
- Hidden issues include: security vulnerabilities, performance problems, resource leaks, \
cross-platform issues, thread safety, memory leaks, hardcoded values, missing validation
- Look for issues in ALL formats: numbered lists, bullet points, tables, tree structures
- Count steps_taken as the number of distinct investigation actions (read file, search, grep, etc.)

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


def extract_one(raw_response: str) -> dict:
    """Extract metrics from a single response using claude haiku."""
    prompt = EXTRACTION_PROMPT.format(response=raw_response[:8000])

    cmds = [
        ["claude", "-p", "--model", "haiku", "--output-format", "text"],
        ["qodercli", "-p", "--model", "lite"],
    ]

    for cmd in cmds:
        try:
            result = subprocess.run(
                cmd, input=prompt,
                capture_output=True, text=True,
                timeout=120, encoding="utf-8",
            )
            if result.returncode == 0 and result.stdout.strip():
                text = result.stdout.strip()
                # Strip markdown fencing
                if text.startswith("```"):
                    text = re.sub(r"^```\w*\n?", "", text)
                    text = re.sub(r"\n?```$", "", text)
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    match = re.search(r'\{[\s\S]*\}', text)
                    if match:
                        return json.loads(match.group())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

    return {}


def main():
    data = json.load(open(RESULTS_FILE, encoding="utf-8"))
    total = len(data)
    updated = 0

    for i, r in enumerate(data):
        raw = r.get("raw_response", "")
        if not raw or r.get("error"):
            print(f"[{i+1}/{total}] {r['condition']} S{r['scenario_id']} R{r['run_number']}: SKIP (no response)")
            continue

        print(f"[{i+1}/{total}] {r['condition']} S{r['scenario_id']} R{r['run_number']}: extracting...", end=" ", flush=True)
        metrics = extract_one(raw)

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
            issues = len(r["issues_found"])
            hidden = len(r["hidden_issues"])
            print(f"✓ {issues} issues, {hidden} hidden")
            updated += 1
        else:
            print("✗ extraction failed")

    # Save updated results
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Also update the archive copy
    archive = RESULTS_FILE.parent / "qodercli" / "full_round_1" / "qodercli.json"
    if archive.exists():
        with open(archive, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Updated {updated}/{total} results → {RESULTS_FILE}")

    # Print summary
    print("\n=== Summary ===")
    for cond in ["pi", "pua", "nopua"]:
        cond_results = [r for r in data if r["condition"] == cond and not r.get("error")]
        avg_issues = sum(len(r.get("issues_found", [])) for r in cond_results) / max(len(cond_results), 1)
        avg_hidden = sum(len(r.get("hidden_issues", [])) for r in cond_results) / max(len(cond_results), 1)
        beyond = sum(1 for r in cond_results if r.get("went_beyond_ask")) / max(len(cond_results), 1) * 100
        verified = sum(1 for r in cond_results if r.get("verification_done")) / max(len(cond_results), 1) * 100
        print(f"  {cond:>8}: avg {avg_issues:.1f} issues, {avg_hidden:.1f} hidden, {beyond:.0f}% beyond, {verified:.0f}% verified")


if __name__ == "__main__":
    main()
