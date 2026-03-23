#!/usr/bin/env python3
"""
PI vs NoPUA Benchmark Analyzer

Compares investigation quality between PI and NoPUA conditions across models.

Usage:
    python analyze.py --input-dir results/
    python analyze.py --input-dir results/ --latex
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Metrics definition
# ---------------------------------------------------------------------------

METRICS = {
    "issues_found": {
        "extract": lambda r: len(r.get("issues_found", [])),
        "label": "Issues Found",
    },
    "hidden_issues": {
        "extract": lambda r: len(r.get("hidden_issues", [])),
        "label": "Hidden Issues",
    },
    "steps_taken": {
        "extract": lambda r: r.get("steps_taken", 0),
        "label": "Steps Taken",
    },
    "went_beyond_ask": {
        "extract": lambda r: 1 if r.get("went_beyond_ask") else 0,
        "label": "Went Beyond Ask",
    },
    "verification_done": {
        "extract": lambda r: 1 if r.get("verification_done") else 0,
        "label": "Verification Done",
    },
    "approach_changes": {
        "extract": lambda r: r.get("approach_changes", 0),
        "label": "Approach Changes",
    },
    "self_corrections": {
        "extract": lambda r: r.get("self_corrections", 0),
        "label": "Self-Corrections",
    },
    "tools_used": {
        "extract": lambda r: len(r.get("tools_used", [])),
        "label": "Tools Used",
    },
    "duration": {
        "extract": lambda r: round(r.get("duration_seconds", 0), 1),
        "label": "Duration (s)",
    },
}


def load_results(input_dir: Path) -> dict[str, list[dict]]:
    """Load results grouped by model."""
    by_model: dict[str, list[dict]] = defaultdict(list)
    for fpath in sorted(input_dir.glob("*.json")):
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for r in data:
                    model = r.get("model", fpath.stem)
                    by_model[model].append(r)
        except Exception as e:
            print(f"Warning: {fpath}: {e}")
    return dict(by_model)


def split_by_condition(results: list[dict]) -> dict[str, list[dict]]:
    """Split results by condition."""
    by_cond: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_cond[r.get("condition", "unknown")].append(r)
    return dict(by_cond)


def extract_values(results: list[dict], metric_key: str) -> np.ndarray:
    fn = METRICS[metric_key]["extract"]
    return np.array([fn(r) for r in results if not r.get("error")], dtype=float)


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------

def mann_whitney(x: np.ndarray, y: np.ndarray) -> dict:
    from scipy.stats import mannwhitneyu
    if len(x) < 2 or len(y) < 2:
        return {"p": 1.0, "effect_r": 0.0}
    stat, p = mannwhitneyu(x, y, alternative="two-sided")
    r = 1 - (2 * stat) / (len(x) * len(y))
    return {"p": round(p, 6), "effect_r": round(r, 3)}


def cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or len(y) < 2:
        return 0.0
    nx, ny = len(x), len(y)
    pooled = np.sqrt(
        ((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1))
        / (nx + ny - 2)
    )
    if pooled == 0:
        return 0.0
    return round(float((np.mean(x) - np.mean(y)) / pooled), 3)


def sig_marker(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return ""


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_model_comparison(model: str, nopua: list[dict], pi: list[dict]):
    """Print comparison table for one model."""
    w = 78
    print(f"\n{'=' * w}")
    print(f"  MODEL: {model}    (NoPUA: {len(nopua)} runs, PI: {len(pi)} runs)")
    print(f"{'=' * w}")
    print(f"{'Metric':<22} {'NoPUA':>10} {'PI':>10} {'Diff':>8} {'%':>7} {'p':>8} {'d':>7} {'Sig':>4}")
    print(f"{'-' * w}")

    for mk, minfo in METRICS.items():
        vn = extract_values(nopua, mk)
        vp = extract_values(pi, mk)
        mn = float(np.mean(vn)) if len(vn) > 0 else 0
        mp = float(np.mean(vp)) if len(vp) > 0 else 0
        diff = mp - mn
        pct = (diff / mn * 100) if mn != 0 else (float("inf") if diff > 0 else 0)

        stat = mann_whitney(vp, vn)
        d = cohens_d(vp, vn)
        sig = sig_marker(stat["p"])

        pct_str = f"+{pct:.0f}%" if pct > 0 else f"{pct:.0f}%"
        if pct == float("inf"):
            pct_str = "+∞"
        diff_str = f"+{diff:.1f}" if diff > 0 else f"{diff:.1f}"

        print(
            f"{minfo['label']:<22} {mn:>10.2f} {mp:>10.2f} "
            f"{diff_str:>8} {pct_str:>7} {stat['p']:>8.4f} {d:>7.2f} {sig:>4}"
        )

    print(f"{'=' * w}")


def print_scenario_breakdown(model: str, nopua: list[dict], pi: list[dict]):
    """Print per-scenario breakdown for one model."""
    # Group by scenario
    nopua_by_s = defaultdict(list)
    pi_by_s = defaultdict(list)
    for r in nopua:
        nopua_by_s[r["scenario_id"]].append(r)
    for r in pi:
        pi_by_s[r["scenario_id"]].append(r)

    all_sids = sorted(set(list(nopua_by_s.keys()) + list(pi_by_s.keys())))

    print(f"\n  Per-scenario: {model}")
    print(f"  {'S#':<4} {'Name':<35} {'NoPUA H':>8} {'PI H':>8} {'Δ':>6}")
    print(f"  {'-' * 65}")

    for sid in all_sids:
        nr = nopua_by_s.get(sid, [])
        pr = pi_by_s.get(sid, [])
        nh = extract_values(nr, "hidden_issues")
        ph = extract_values(pr, "hidden_issues")
        mn = float(np.mean(nh)) if len(nh) > 0 else 0
        mp = float(np.mean(ph)) if len(ph) > 0 else 0
        diff = mp - mn
        name = nr[0]["scenario_name"] if nr else (pr[0]["scenario_name"] if pr else "?")
        diff_str = f"+{diff:.1f}" if diff >= 0 else f"{diff:.1f}"
        print(f"  S{sid:<3} {name:<35} {mn:>8.1f} {mp:>8.1f} {diff_str:>6}")


def print_summary(all_models: dict[str, dict[str, list[dict]]]):
    """Print cross-model summary."""
    print(f"\n{'=' * 60}")
    print("CROSS-MODEL SUMMARY: PI vs NoPUA")
    print(f"{'=' * 60}")
    print(f"{'Model':<18} {'Hidden Δ':>10} {'Beyond Δ':>10} {'Steps Δ':>10} {'Winner':>8}")
    print(f"{'-' * 60}")

    for model, conds in all_models.items():
        nopua = conds.get("nopua", [])
        pi = conds.get("pi", [])

        def delta(mk):
            vn = extract_values(nopua, mk)
            vp = extract_values(pi, mk)
            return float(np.mean(vp) - np.mean(vn)) if len(vn) > 0 and len(vp) > 0 else 0

        dh = delta("hidden_issues")
        db = delta("went_beyond_ask")
        ds = delta("steps_taken")

        wins = sum(1 for d in [dh, db, ds] if d > 0)
        winner = "PI" if wins >= 2 else ("NoPUA" if wins == 0 else "TIE")

        fmt = lambda v: f"+{v:.2f}" if v >= 0 else f"{v:.2f}"
        print(f"{model:<18} {fmt(dh):>10} {fmt(db):>10} {fmt(ds):>10} {winner:>8}")

    print(f"{'=' * 60}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="PI vs NoPUA Benchmark Analyzer")
    parser.add_argument("--input-dir", required=True, help="Results directory")
    parser.add_argument("--latex", action="store_true", help="Output LaTeX tables")
    parser.add_argument("--json-report", action="store_true", help="Save JSON report")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"Error: {input_dir} not found")
        sys.exit(1)

    by_model = load_results(input_dir)
    if not by_model:
        print("No results found!")
        sys.exit(1)

    print(f"Loaded results from {input_dir}")
    for model, results in by_model.items():
        conds = split_by_condition(results)
        counts = {c: len(r) for c, r in conds.items()}
        print(f"  {model}: {counts}")

    # Per-model comparisons
    all_models = {}
    for model, results in by_model.items():
        conds = split_by_condition(results)
        all_models[model] = conds
        nopua = conds.get("nopua", [])
        pi = conds.get("pi", [])
        if nopua and pi:
            print_model_comparison(model, nopua, pi)
            print_scenario_breakdown(model, nopua, pi)

    # Cross-model summary
    if len(all_models) > 1:
        print_summary(all_models)

    # JSON report
    if args.json_report:
        report = {}
        for model, conds in all_models.items():
            report[model] = {}
            nopua = conds.get("nopua", [])
            pi = conds.get("pi", [])
            for mk in METRICS:
                vn = extract_values(nopua, mk)
                vp = extract_values(pi, mk)
                report[model][mk] = {
                    "nopua_mean": round(float(np.mean(vn)), 3) if len(vn) else 0,
                    "pi_mean": round(float(np.mean(vp)), 3) if len(vp) else 0,
                }
        report_path = input_dir / "report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
