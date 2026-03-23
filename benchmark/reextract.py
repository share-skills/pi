#!/usr/bin/env python3
"""
Re-extract metrics from existing benchmark results.

Usage:
    python reextract.py results/qodercli/full_round_2/qodercli.json
    python reextract.py results/qodercli/full_round_2/qodercli.json --batch-size 6
"""

import json
import sys
from pathlib import Path

# Import the extraction function from local_run
sys.path.insert(0, str(Path(__file__).parent))
from local_run import extract_metrics_batch


def reextract(json_path: str, batch_size: int = 8, force: bool = False):
    path = Path(json_path)
    if not path.exists():
        print(f"Error: {path} not found")
        sys.exit(1)

    all_results = json.loads(path.read_text(encoding="utf-8"))
    print(f"Loaded {len(all_results)} results from {path}")

    # Check current state
    has_issues = sum(1 for r in all_results if len(r.get("issues_found", [])) > 0)
    has_response = sum(1 for r in all_results if r.get("raw_response"))
    print(f"  With raw_response: {has_response}")
    print(f"  With issues_found > 0: {has_issues}")

    if has_issues > 0 and not force:
        print(f"\n  ⚠️  {has_issues} results already have extracted metrics.")
        try:
            resp = input("  Re-extract all? [y/N] ")
        except EOFError:
            resp = "n"
        if resp.lower() != "y":
            # Only re-extract those with empty issues
            print("  Re-extracting only empty results...")
            empty_results = [r for r in all_results if not r.get("issues_found")]
            metrics_list = extract_metrics_batch(empty_results, batch_size=batch_size)
            empty_idx = 0
            for i, r in enumerate(all_results):
                if not r.get("issues_found"):
                    if empty_idx < len(metrics_list) and metrics_list[empty_idx]:
                        m = metrics_list[empty_idx]
                        r["issues_found"] = m.get("issues_found", [])
                        r["hidden_issues"] = m.get("hidden_issues", [])
                        r["steps_taken"] = m.get("steps_taken", 0)
                        r["tools_used"] = m.get("tools_used", [])
                        r["went_beyond_ask"] = m.get("went_beyond_ask", False)
                        r["verification_done"] = m.get("verification_done", False)
                        r["approach_changes"] = m.get("approach_changes", 0)
                        r["self_corrections"] = m.get("self_corrections", 0)
                        r["root_cause"] = m.get("root_cause", "")
                        r["recommended_fix"] = m.get("recommended_fix", "")
                    empty_idx += 1
            path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")
            final_issues = sum(1 for r in all_results if len(r.get("issues_found", [])) > 0)
            print(f"\n✅ Updated {path}: {final_issues}/{len(all_results)} with issues")
            return

    # Full re-extraction
    metrics_list = extract_metrics_batch(all_results, batch_size=batch_size)
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

    # Save
    path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8")

    final_issues = sum(1 for r in all_results if len(r.get("issues_found", [])) > 0)
    print(f"\n✅ Saved {path}: {final_issues}/{len(all_results)} with extracted issues")

    # Summary
    from collections import defaultdict
    by_cond = defaultdict(list)
    for r in all_results:
        if r.get("error"):
            continue
        by_cond[r.get("condition", "?")].append(r)

    print("\n=== Summary ===")
    for cond in sorted(by_cond.keys()):
        rs = by_cond[cond]
        issues = sum(len(r.get("issues_found", [])) for r in rs) / len(rs)
        hidden = sum(len(r.get("hidden_issues", [])) for r in rs) / len(rs)
        dur = sum(r.get("duration_seconds", 0) for r in rs) / len(rs)
        print(f"  {cond:8s}: n={len(rs):2d} issues={issues:.1f} hidden={hidden:.1f} dur={dur:.1f}s")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Re-extract metrics from benchmark results")
    parser.add_argument("json_file", help="Path to results JSON file")
    parser.add_argument("--batch-size", type=int, default=8, help="Batch size for extraction (default: 8)")
    parser.add_argument("--force", action="store_true", help="Force re-extract all (no confirmation)")
    args = parser.parse_args()
    reextract(args.json_file, args.batch_size, args.force)
