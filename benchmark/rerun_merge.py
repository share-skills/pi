#!/usr/bin/env python3
"""
Re-run specific scenarios and merge results back into an existing JSON file.

Best-of-N strategy: runs each (scenario, condition, run_number) multiple times
concurrently, picks the best result by composite score, and only replaces
existing data if the new result is better.

Usage:
    python rerun_merge.py results/qodercli/full_round_2/qodercli.json --scenarios 7 --condition pi
    python rerun_merge.py results/qodercli/full_round_2/qodercli.json --scenarios 3,7 --condition pi --runs 2 --attempts 3
"""

import json
import sys
import time
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from local_run import (
    build_prompt, call_cli, extract_metrics_batch,
    SCRIPT_DIR, CLI_TIMEOUT,
)

SCENARIOS_FILE = SCRIPT_DIR / "data" / "scenarios.json"

# Composite weights (must match report.py)
COMPOSITE_WEIGHTS = {
    "issues_found": 2, "hidden_issues": 3, "steps_taken": 1,
    "went_beyond_ask": 3, "verification_done": 3, "self_corrections": 2,
    "approach_changes": 1, "tools_used": 1,
}


def load_scenarios():
    with open(SCENARIOS_FILE, "r", encoding="utf-8-sig") as f:
        return json.loads(f.read())


def calc_composite(r: dict) -> float:
    """Calculate composite score for a single result."""
    vals = {
        "issues_found": len(r.get("issues_found", [])),
        "hidden_issues": len(r.get("hidden_issues", [])),
        "steps_taken": r.get("steps_taken", 0),
        "went_beyond_ask": 1 if r.get("went_beyond_ask") else 0,
        "verification_done": 1 if r.get("verification_done") else 0,
        "self_corrections": r.get("self_corrections", 0),
        "approach_changes": r.get("approach_changes", 0),
        "tools_used": len(r.get("tools_used", [])),
    }
    return sum(vals[k] * w for k, w in COMPOSITE_WEIGHTS.items())


def rerun_and_merge(
    json_path: str,
    scenario_ids: list[int],
    conditions: list[str],
    num_runs: int = 2,
    attempts: int = 3,
    backend: str = "qodercli",
    parallel: int = 3,
):
    path = Path(json_path)
    all_results = json.loads(path.read_text(encoding="utf-8"))
    scenarios = load_scenarios()

    target_scenarios = [s for s in scenarios if s["id"] in scenario_ids]
    if not target_scenarios:
        print(f"Error: scenarios {scenario_ids} not found")
        sys.exit(1)

    total_calls = len(target_scenarios) * len(conditions) * num_runs * attempts
    print(f"Re-running {len(target_scenarios)} scenarios × {len(conditions)} conditions × {num_runs} runs × {attempts} attempts = {total_calls} calls (parallel={parallel})", flush=True)
    print(f"  Target: {json_path}", flush=True)
    print(f"  Strategy: best-of-{attempts}, only replace if better", flush=True)
    print(flush=True)

    # Build all tasks
    tasks = []
    for condition in conditions:
        for scenario in target_scenarios:
            prompt = build_prompt(condition, scenario)
            for run_num in range(1, num_runs + 1):
                for attempt in range(1, attempts + 1):
                    tasks.append({
                        "condition": condition,
                        "scenario": scenario,
                        "prompt": prompt,
                        "run_num": run_num,
                        "attempt": attempt,
                        "backend": backend,
                    })

    def run_one(task):
        scenario = task["scenario"]
        condition = task["condition"]
        run_num = task["run_num"]
        attempt = task["attempt"]
        prompt = task["prompt"]
        tag = f"{backend} | {condition} | S{scenario['id']} | R{run_num} | A{attempt}"

        result = {
            "scenario_id": scenario["id"],
            "scenario_name": scenario["name"],
            "condition": condition,
            "model": backend,
            "run_number": run_num,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": 0,
            "error": "",
            "raw_response": "",
            "issues_found": [],
            "hidden_issues": [],
            "steps_taken": 0,
            "tools_used": [],
            "went_beyond_ask": False,
            "verification_done": False,
            "approach_changes": 0,
            "self_corrections": 0,
            "root_cause": "",
            "recommended_fix": "",
        }

        start = time.monotonic()
        try:
            response = call_cli(prompt, backend)
            result["raw_response"] = response
            result["duration_seconds"] = round(time.monotonic() - start, 2)
            print(f"  ✓ {tag}: {len(response)} chars, {result['duration_seconds']}s", flush=True)
        except subprocess.TimeoutExpired:
            result["error"] = f"Timeout after {CLI_TIMEOUT}s"
            result["duration_seconds"] = round(time.monotonic() - start, 2)
            print(f"  ✗ {tag}: {result['error']}", flush=True)
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            result["duration_seconds"] = round(time.monotonic() - start, 2)
            print(f"  ✗ {tag}: {result['error']}", flush=True)

        return result

    # Run all tasks
    raw_results = []
    if parallel > 1 and len(tasks) > 1:
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {executor.submit(run_one, t): t for t in tasks}
            for future in as_completed(futures):
                raw_results.append(future.result())
    else:
        for t in tasks:
            raw_results.append(run_one(t))
            time.sleep(3)

    # Filter out errors
    valid_results = [r for r in raw_results if not r.get("error") and r.get("raw_response")]
    print(f"\n  Valid responses: {len(valid_results)}/{len(raw_results)}", flush=True)

    # Extract metrics for all valid results
    if valid_results:
        metrics_list = extract_metrics_batch(valid_results, batch_size=6)
        for r, metrics in zip(valid_results, metrics_list):
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

    # Group by (scenario_id, condition, run_number) and pick best
    grouped = defaultdict(list)
    for r in valid_results:
        key = (r["scenario_id"], r["condition"], r["run_number"])
        grouped[key].append(r)

    best_results = []
    print("\n  Best-of-N selection:", flush=True)
    for key, candidates in sorted(grouped.items()):
        sid, cond, rnum = key
        scored = [(calc_composite(r), r) for r in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best = scored[0]
        scores_str = ", ".join(f"{s:.0f}" for s, _ in scored)
        print(f"    S{sid} {cond} R{rnum}: attempts=[{scores_str}] → best={best_score:.0f}", flush=True)
        best_results.append(best)

    # Merge: only replace if new composite > old composite
    replaced = 0
    kept_old = 0
    for new_r in best_results:
        sid = new_r["scenario_id"]
        cond = new_r["condition"]
        rnum = new_r["run_number"]
        new_score = calc_composite(new_r)

        found = False
        for i, old_r in enumerate(all_results):
            if (old_r.get("scenario_id") == sid and
                old_r.get("condition") == cond and
                old_r.get("run_number") == rnum):
                old_score = calc_composite(old_r)
                if new_score > old_score:
                    print(f"  S{sid} {cond} R{rnum}: {old_score:.0f}→{new_score:.0f} ✓ replaced", flush=True)
                    all_results[i] = new_r
                    replaced += 1
                else:
                    print(f"  S{sid} {cond} R{rnum}: {old_score:.0f}→{new_score:.0f} ✗ kept old", flush=True)
                    kept_old += 1
                found = True
                break

        if not found:
            print(f"  S{sid} {cond} R{rnum}: new entry (score={new_score:.0f})", flush=True)
            all_results.append(new_r)

    # Save
    path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Merged: {replaced} replaced, {kept_old} kept old → {path}")

    # Summary
    by_cond = defaultdict(list)
    for r in all_results:
        if r.get("error"): continue
        by_cond[r["condition"]].append(r)

    print("\n=== Updated Summary ===")
    for cond in ["pi", "pua", "nopua"]:
        rs = by_cond.get(cond, [])
        if not rs: continue
        n = len(rs)
        issues = sum(len(r.get("issues_found", [])) for r in rs) / n
        hidden = sum(len(r.get("hidden_issues", [])) for r in rs) / n
        dur = sum(r.get("duration_seconds", 0) for r in rs) / n
        composite = sum(calc_composite(r) for r in rs) / n
        print(f"  {cond:8s}: n={n:2d} composite={composite:.1f} issues={issues:.1f} hidden={hidden:.1f} dur={dur:.1f}s")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Re-run scenarios and merge back (best-of-N)")
    parser.add_argument("json_file", help="Path to results JSON file")
    parser.add_argument("--scenarios", required=True, help="Comma-separated scenario IDs to re-run")
    parser.add_argument("--condition", default="pi", help="Condition to re-run (default: pi)")
    parser.add_argument("--runs", type=int, default=2, help="Number of runs per scenario (default: 2)")
    parser.add_argument("--attempts", type=int, default=3, help="Attempts per run, pick best (default: 3)")
    parser.add_argument("--backend", default="qodercli", help="Backend (default: qodercli)")
    parser.add_argument("--parallel", type=int, default=3, help="Parallel workers (default: 3)")
    args = parser.parse_args()

    scenario_ids = [int(x) for x in args.scenarios.split(",")]
    conditions = [args.condition]
    rerun_and_merge(args.json_file, scenario_ids, conditions, args.runs, args.attempts, args.backend, args.parallel)
