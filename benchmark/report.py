#!/usr/bin/env python3
"""
PI Benchmark Report Generator — Dynamic Web UI

Generates a standalone HTML report with interactive charts, dark tech theme,
and multi-dimensional comparison of benchmark results.

Usage:
    python report.py --input-dir results/
    python report.py --input-dir results/ --output report.html --open
    python report.py --demo  # Generate demo report with sample data
"""

import argparse
import json
import os
import sys
import webbrowser
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Metrics definition (must stay in sync with run.py / analyze.py)
# ---------------------------------------------------------------------------

METRICS = {
    "issues_found": {
        "extract": lambda r: len(r.get("issues_found", [])),
        "label": "Issues Found",
        "icon": "🔍",
        "higher_better": True,
    },
    "hidden_issues": {
        "extract": lambda r: len(r.get("hidden_issues", [])),
        "label": "Hidden Issues",
        "icon": "🕵️",
        "higher_better": True,
    },
    "steps_taken": {
        "extract": lambda r: r.get("steps_taken", 0),
        "label": "Steps Taken",
        "icon": "👣",
        "higher_better": True,
    },
    "went_beyond_ask": {
        "extract": lambda r: 1 if r.get("went_beyond_ask") else 0,
        "label": "Beyond Ask",
        "icon": "🚀",
        "higher_better": True,
    },
    "verification_done": {
        "extract": lambda r: 1 if r.get("verification_done") else 0,
        "label": "Verified",
        "icon": "✅",
        "higher_better": True,
    },
    "approach_changes": {
        "extract": lambda r: r.get("approach_changes", 0),
        "label": "Approach Δ",
        "icon": "🔄",
        "higher_better": True,
    },
    "self_corrections": {
        "extract": lambda r: r.get("self_corrections", 0),
        "label": "Self-Correct",
        "icon": "🪞",
        "higher_better": True,
    },
    "tools_used": {
        "extract": lambda r: len(r.get("tools_used", [])),
        "label": "Tools Used",
        "icon": "🔧",
        "higher_better": True,
    },
    "duration": {
        "extract": lambda r: round(r.get("duration_seconds", 0), 1),
        "label": "Duration (s)",
        "icon": "⏱️",
        "higher_better": False,
    },
}


# ---------------------------------------------------------------------------
# Data loading and aggregation
# ---------------------------------------------------------------------------

def load_results(input_dir: Path) -> list[dict]:
    """Load all result JSON files from input directory."""
    all_results = []
    for fpath in sorted(input_dir.glob("*.json")):
        if fpath.name == "report_data.json":
            continue
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            if isinstance(data, list):
                all_results.extend(data)
        except Exception as e:
            print(f"Warning: {fpath}: {e}")
    return all_results


def aggregate_results(results: list[dict]) -> dict:
    """Aggregate results into a structure suitable for the report."""
    # Group by condition, model, scenario
    by_condition: dict[str, list[dict]] = defaultdict(list)
    by_model: dict[str, list[dict]] = defaultdict(list)
    by_scenario: dict[int, list[dict]] = defaultdict(list)
    conditions = set()
    models = set()
    scenarios = {}

    for r in results:
        if r.get("error"):
            continue
        cond = r.get("condition", "unknown")
        model = r.get("model", "unknown")
        sid = r.get("scenario_id", 0)
        conditions.add(cond)
        models.add(model)
        by_condition[cond].append(r)
        by_model[model].append(r)
        by_scenario[sid].append(r)
        if sid not in scenarios:
            scenarios[sid] = {
                "id": sid,
                "name": r.get("scenario_name", f"Scenario {sid}"),
            }

    # Compute per-condition averages for each metric
    condition_avgs = {}
    for cond in sorted(conditions):
        cond_results = by_condition[cond]
        avgs = {}
        for mk, mdef in METRICS.items():
            values = [mdef["extract"](r) for r in cond_results]
            avgs[mk] = {
                "mean": round(sum(values) / len(values), 2) if values else 0,
                "total": sum(values),
                "count": len(values),
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
            }
        condition_avgs[cond] = avgs

    # Compute per-scenario per-condition averages (for heatmap)
    scenario_data = {}
    for sid in sorted(scenarios.keys()):
        s_results = by_scenario[sid]
        scenario_data[sid] = {
            "name": scenarios[sid]["name"],
            "conditions": {},
        }
        for cond in sorted(conditions):
            cond_s_results = [r for r in s_results if r.get("condition") == cond]
            cond_avgs = {}
            for mk, mdef in METRICS.items():
                values = [mdef["extract"](r) for r in cond_s_results]
                cond_avgs[mk] = round(sum(values) / len(values), 2) if values else 0
            scenario_data[sid]["conditions"][cond] = cond_avgs

    # Compute per-model per-condition averages
    model_data = {}
    for model in sorted(models):
        m_results = by_model[model]
        model_data[model] = {}
        for cond in sorted(conditions):
            cond_m_results = [r for r in m_results if r.get("condition") == cond]
            cond_avgs = {}
            for mk, mdef in METRICS.items():
                values = [mdef["extract"](r) for r in cond_m_results]
                cond_avgs[mk] = round(sum(values) / len(values), 2) if values else 0
            model_data[model][cond] = cond_avgs

    # Compute improvement percentages
    # Use PUA as the baseline (denominator) — all others are compared against PUA.
    # This shows how much each condition improves (or regresses) vs PUA.
    improvements = {}
    cond_list = sorted(conditions)
    if len(cond_list) >= 2:
        # PUA is always the baseline; compare PI (or first non-pua) against PUA
        baseline = "pua" if "pua" in cond_list else cond_list[-1]
        primary = "pi" if "pi" in cond_list else [c for c in cond_list if c != baseline][0]
        c1, c2 = primary, baseline
        for mk in METRICS:
            v1 = condition_avgs[c1][mk]["mean"]
            v2 = condition_avgs[c2][mk]["mean"]
            if v2 != 0:
                pct = round((v1 - v2) / v2 * 100, 1)
            elif v1 != 0:
                pct = float("inf")
            else:
                pct = 0
            improvements[mk] = pct

    # Composite score per condition: weighted sum across all metrics.
    composite_weights = {
        "issues_found": 2, "hidden_issues": 3, "steps_taken": 1,
        "went_beyond_ask": 3, "verification_done": 3, "self_corrections": 2,
        "approach_changes": 1, "tools_used": 1,
    }
    composite_scores = {}
    for cond in sorted(conditions):
        total = 0
        for mk, w in composite_weights.items():
            total += condition_avgs[cond].get(mk, {}).get("mean", 0) * w
        composite_scores[cond] = round(total, 2)

    # Per-scenario composite scores
    scenario_composites = {}
    for sid in sorted(scenarios.keys()):
        scenario_composites[sid] = {}
        for cond in sorted(conditions):
            sc = scenario_data[sid]["conditions"].get(cond, {})
            total = sum(sc.get(mk, 0) * w for mk, w in composite_weights.items())
            scenario_composites[sid][cond] = round(total, 2)

    # ── Per-model aggregation (for model tab switching) ──
    per_model = {}
    for model in sorted(models):
        m_results = by_model[model]
        m_conditions = set(r.get("condition", "unknown") for r in m_results)

        # Per-condition averages within this model
        m_condition_avgs = {}
        for cond in sorted(m_conditions):
            cond_results = [r for r in m_results if r.get("condition") == cond]
            avgs = {}
            for mk, mdef in METRICS.items():
                values = [mdef["extract"](r) for r in cond_results]
                avgs[mk] = {
                    "mean": round(sum(values) / len(values), 2) if values else 0,
                    "total": sum(values),
                    "count": len(values),
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                }
            m_condition_avgs[cond] = avgs

        # Per-scenario breakdown within this model
        m_scenario_data = {}
        for sid in sorted(scenarios.keys()):
            s_results_m = [r for r in m_results if r.get("scenario_id") == sid]
            if not s_results_m:
                continue
            m_scenario_data[sid] = {
                "name": scenarios[sid]["name"],
                "conditions": {},
            }
            for cond in sorted(m_conditions):
                cond_s = [r for r in s_results_m if r.get("condition") == cond]
                cond_avgs_m = {}
                for mk, mdef in METRICS.items():
                    values = [mdef["extract"](r) for r in cond_s]
                    cond_avgs_m[mk] = round(sum(values) / len(values), 2) if values else 0
                m_scenario_data[sid]["conditions"][cond] = cond_avgs_m

        # Composite scores within this model
        m_composite = {}
        for cond in sorted(m_conditions):
            total = 0
            for mk, w in composite_weights.items():
                total += m_condition_avgs[cond].get(mk, {}).get("mean", 0) * w
            m_composite[cond] = round(total, 2)

        m_scenario_composites = {}
        for sid in sorted(scenarios.keys()):
            if sid not in m_scenario_data:
                continue
            m_scenario_composites[sid] = {}
            for cond in sorted(m_conditions):
                sc = m_scenario_data[sid]["conditions"].get(cond, {})
                total = sum(sc.get(mk, 0) * w for mk, w in composite_weights.items())
                m_scenario_composites[sid][cond] = round(total, 2)

        per_model[model] = {
            "conditions": sorted(m_conditions),
            "condition_avgs": m_condition_avgs,
            "scenario_data": m_scenario_data,
            "composite_scores": m_composite,
            "scenario_composites": m_scenario_composites,
            "total_valid": len(m_results),
        }

    return {
        "conditions": sorted(conditions),
        "models": sorted(models),
        "scenarios": scenarios,
        "condition_avgs": condition_avgs,
        "scenario_data": scenario_data,
        "model_data": model_data,
        "improvements": improvements,
        "composite_scores": composite_scores,
        "scenario_composites": scenario_composites,
        "per_model": per_model,
        "total_results": len(results),
        "total_valid": len([r for r in results if not r.get("error")]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metric_labels": {k: v["label"] for k, v in METRICS.items()},
        "metric_icons": {k: v["icon"] for k, v in METRICS.items()},
    }


# ---------------------------------------------------------------------------
# Demo data (for --demo mode, no API calls needed)
# ---------------------------------------------------------------------------

def generate_demo_data() -> list[dict]:
    """Generate realistic demo data for report preview."""
    import random
    random.seed(42)

    scenarios = [
        (1, "OCR Pipeline Import Error"),
        (2, "Text Cleaner Regex Backtracking"),
        (3, "RAG Pipeline Milvus Connection"),
        (4, "API Response Format Mismatch"),
        (5, "Synthesizer Silent Failure"),
        (6, "Unicode Boundary Split"),
        (7, "Quality Filter Code Review"),
        (8, "Inference Security Audit"),
        (9, "Training Pipeline Audit"),
    ]
    models = ["gpt-4.1", "gpt-5-mini"]
    conditions = ["pi", "pi-lite", "pua", "nopua"]

    # PI: wisdom-driven, thorough, self-correcting
    # PI-lite: simplified Chinese version, slightly less structured
    # PUA: fear-driven, aggressive but less methodical
    # NoPUA: anti-manipulation, balanced, clear-thinking
    profiles = {
        "pi": {
            "issues_found": (3, 5), "hidden_issues": (3, 7),
            "steps_taken": (4, 7), "went_beyond": 0.95,
            "verified": 0.85, "approach_changes": (1, 3),
            "self_corrections": (1, 3), "tools": (3, 5),
        },
        "pi-lite": {
            "issues_found": (3, 5), "hidden_issues": (2, 6),
            "steps_taken": (3, 6), "went_beyond": 0.88,
            "verified": 0.78, "approach_changes": (1, 3),
            "self_corrections": (1, 2), "tools": (3, 5),
        },
        "pua": {
            "issues_found": (2, 5), "hidden_issues": (1, 4),
            "steps_taken": (2, 5), "went_beyond": 0.60,
            "verified": 0.30, "approach_changes": (0, 2),
            "self_corrections": (0, 1), "tools": (2, 4),
        },
        "nopua": {
            "issues_found": (3, 5), "hidden_issues": (2, 6),
            "steps_taken": (3, 6), "went_beyond": 0.80,
            "verified": 0.70, "approach_changes": (1, 2),
            "self_corrections": (1, 2), "tools": (3, 5),
        },
    }

    results = []
    for model in models:
        for cond in conditions:
            p = profiles[cond]
            for sid, sname in scenarios:
                for run in range(1, 3):
                    issues = [f"Issue-{i}" for i in range(random.randint(*p["issues_found"]))]
                    hidden = [f"Hidden-{i}" for i in range(random.randint(*p["hidden_issues"]))]
                    results.append({
                        "scenario_id": sid,
                        "scenario_name": sname,
                        "condition": cond,
                        "model": model,
                        "run_number": run,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "issues_found": issues,
                        "hidden_issues": hidden,
                        "steps_taken": random.randint(*p["steps_taken"]),
                        "tools_used": ["read_file", "search_text", "run_command",
                                       "list_dir"][:random.randint(*p["tools"])],
                        "went_beyond_ask": random.random() < p["went_beyond"],
                        "verification_done": random.random() < p["verified"],
                        "approach_changes": random.randint(*p["approach_changes"]),
                        "self_corrections": random.randint(*p["self_corrections"]),
                        "root_cause": "Demo root cause" if cond == "pi" else "",
                        "recommended_fix": "Demo fix" if cond == "pi" else "",
                        "raw_response": "",
                        "duration_seconds": round(random.uniform(8, 25), 2),
                        "error": "",
                    })
    return results


# ---------------------------------------------------------------------------
# HTML template — Dark tech theme with neon accents
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PI Benchmark Report</title>
<style>
/* ========== CSS Reset & Base ========== */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg-primary: #0a0e17;
  --bg-secondary: #111827;
  --bg-card: #1a2332;
  --bg-card-hover: #1f2b3d;
  --border: #2d3748;
  --border-glow: #3b82f6;
  --text-primary: #e2e8f0;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --neon-blue: #3b82f6;
  --neon-cyan: #06b6d4;
  --neon-purple: #8b5cf6;
  --neon-green: #10b981;
  --neon-amber: #f59e0b;
  --neon-red: #ef4444;
  --neon-pink: #ec4899;
  --pi-color: #3b82f6;
  --pi-lite-color: #8b5cf6;
  --pua-color: #ef4444;
  --nopua-color: #10b981;
  --baseline-color: #64748b;
  --glow-blue: 0 0 20px rgba(59, 130, 246, 0.3);
  --glow-cyan: 0 0 20px rgba(6, 182, 212, 0.3);
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --radius: 12px;
  --radius-sm: 8px;
}

body {
  font-family: var(--font-sans);
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.6;
  min-height: 100vh;
}

/* ========== Animated background grid ========== */
body::before {
  content: '';
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image:
    linear-gradient(rgba(59, 130, 246, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 130, 246, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: 0;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
  position: relative;
  z-index: 1;
}

/* ========== Header ========== */
header {
  text-align: center;
  padding: 40px 0 32px;
  position: relative;
}

header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 200px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--neon-blue), var(--neon-cyan), transparent);
}

h1 {
  font-size: 2.5rem;
  font-weight: 800;
  background: linear-gradient(135deg, var(--neon-blue), var(--neon-cyan), var(--neon-purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.02em;
  margin-bottom: 8px;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 1rem;
  font-family: var(--font-mono);
}

.meta-bar {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.meta-tag {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 4px 16px;
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

/* ========== Section headers ========== */
.section-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 40px 0 20px;
  padding-left: 16px;
  border-left: 3px solid var(--neon-blue);
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ========== Cards grid ========== */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.card:hover {
  background: var(--bg-card-hover);
  border-color: var(--neon-blue);
  box-shadow: var(--glow-blue);
  transform: translateY(-2px);
}

.card .icon {
  font-size: 1.5rem;
  margin-bottom: 8px;
}

.card .label {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.card .value {
  font-size: 2rem;
  font-weight: 800;
  font-family: var(--font-mono);
}

.card .delta {
  font-size: 0.85rem;
  font-family: var(--font-mono);
  margin-top: 4px;
}

.delta.positive { color: var(--neon-green); }
.delta.negative { color: var(--neon-red); }
.delta.neutral { color: var(--text-muted); }

/* ========== Comparison bars ========== */
.comparison-section {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  margin-bottom: 32px;
}

.bar-group {
  margin-bottom: 20px;
}

.bar-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.9rem;
}

.bar-label .metric-name {
  font-weight: 600;
}

.bar-track {
  height: 32px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  position: relative;
  overflow: hidden;
  margin-bottom: 4px;
}

.bar-fill {
  height: 100%;
  border-radius: 6px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  font-size: 0.8rem;
  font-weight: 700;
  font-family: var(--font-mono);
  color: white;
  transition: width 1s cubic-bezier(0.22, 1, 0.36, 1);
  position: relative;
  overflow: hidden;
}

.bar-fill::after {
  content: '';
  position: absolute;
  top: 0; left: -100%; right: -100%; bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
  animation: shimmer 3s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.bar-fill.pi { background: linear-gradient(90deg, var(--pi-color), #60a5fa); }
.bar-fill.pi-lite { background: linear-gradient(90deg, var(--pi-lite-color), #a78bfa); }
.bar-fill.pua { background: linear-gradient(90deg, var(--pua-color), #f87171); }
.bar-fill.nopua { background: linear-gradient(90deg, var(--nopua-color), #34d399); }
.bar-fill.baseline { background: linear-gradient(90deg, var(--baseline-color), #94a3b8); }

/* ========== Radar / Spider chart (SVG) ========== */
.radar-container {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  margin-bottom: 32px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.radar-svg {
  max-width: 500px;
  width: 100%;
}

.radar-svg text {
  fill: var(--text-secondary);
  font-size: 11px;
  font-family: var(--font-sans);
}

.radar-svg .axis-line {
  stroke: var(--border);
  stroke-width: 0.5;
}

.radar-svg .grid-line {
  stroke: rgba(255, 255, 255, 0.06);
  fill: none;
  stroke-width: 0.5;
}

.radar-svg .data-area {
  stroke-width: 2;
  fill-opacity: 0.15;
  transition: fill-opacity 0.3s;
}

.radar-svg .data-area:hover {
  fill-opacity: 0.3;
}

/* ========== Heatmap ========== */
.heatmap-container {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 24px;
  margin-bottom: 32px;
  overflow-x: auto;
}

.heatmap-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  font-family: var(--font-mono);
}

.heatmap-table th {
  padding: 10px 12px;
  text-align: center;
  color: var(--text-secondary);
  font-weight: 600;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.heatmap-table td {
  padding: 8px 12px;
  text-align: center;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  transition: all 0.2s;
}

.heatmap-table td.scenario-name {
  text-align: left;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.heatmap-table tr:hover td {
  background: rgba(59, 130, 246, 0.05);
}

.heat-cell {
  border-radius: 4px;
  padding: 4px 8px;
  display: inline-block;
  min-width: 40px;
}

/* ========== Legend ========== */
.legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin: 16px 0;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

/* ========== Model breakdown ========== */
.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.model-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
}

.model-card h3 {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: 16px;
  font-family: var(--font-mono);
  color: var(--neon-cyan);
}

.mini-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.mini-bar .mlabel {
  width: 100px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  text-align: right;
  flex-shrink: 0;
}

.mini-bar .mtrack {
  flex: 1;
  height: 20px;
  background: rgba(255,255,255,0.05);
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}

.mini-bar .mfill {
  height: 100%;
  border-radius: 4px;
  display: flex;
  align-items: center;
  padding-left: 8px;
  font-size: 0.75rem;
  font-weight: 700;
  color: white;
  font-family: var(--font-mono);
  transition: width 0.8s ease;
}

/* ========== Footer ========== */
footer {
  text-align: center;
  padding: 32px 0 16px;
  color: var(--text-muted);
  font-size: 0.8rem;
  font-family: var(--font-mono);
}

footer a {
  color: var(--neon-blue);
  text-decoration: none;
}

/* ========== Animations ========== */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-in {
  animation: fadeInUp 0.6s ease forwards;
  opacity: 0;
}

/* Stagger children */
.cards-grid > *:nth-child(1) { animation-delay: 0.05s; }
.cards-grid > *:nth-child(2) { animation-delay: 0.1s; }
.cards-grid > *:nth-child(3) { animation-delay: 0.15s; }
.cards-grid > *:nth-child(4) { animation-delay: 0.2s; }
.cards-grid > *:nth-child(5) { animation-delay: 0.25s; }
.cards-grid > *:nth-child(6) { animation-delay: 0.3s; }
.cards-grid > *:nth-child(7) { animation-delay: 0.35s; }
.cards-grid > *:nth-child(8) { animation-delay: 0.4s; }

/* ========== Model Tabs ========== */
.model-tabs {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin: 24px 0 16px;
  flex-wrap: wrap;
}

.model-tab {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 8px 20px;
  font-size: 0.9rem;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
}

.model-tab:hover {
  border-color: var(--neon-cyan);
  color: var(--text-primary);
}

.model-tab.active {
  background: linear-gradient(135deg, var(--neon-blue), var(--neon-cyan));
  border-color: var(--neon-cyan);
  color: white;
  font-weight: 600;
  box-shadow: var(--glow-cyan);
}

/* ========== Responsive ========== */
@media (max-width: 768px) {
  .container { padding: 16px; }
  h1 { font-size: 1.8rem; }
  .cards-grid { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
  .model-grid { grid-template-columns: 1fr; }
  .meta-bar { gap: 8px; }
}
</style>
</head>
<body>
<div class="container">

<!-- ========== Header ========== -->
<header>
  <h1>⚡ PI Benchmark Report</h1>
  <p class="subtitle">PI 智行合一 — Multi-Dimensional Skill Comparison</p>
  <div class="meta-bar" id="metaBar"></div>
</header>

<!-- ========== Model Tabs ========== -->
<div class="model-tabs" id="modelTabs"></div>

<!-- ========== Summary Cards ========== -->
<h2 class="section-title">📊 Summary Dashboard</h2>
<div class="cards-grid" id="summaryCards"></div>

<!-- ========== Legend ========== -->
<div class="legend" id="legend"></div>

<!-- ========== Comparison Bars ========== -->
<h2 class="section-title">📈 Metric Comparison</h2>
<div class="comparison-section" id="comparisonBars"></div>

<!-- ========== Radar Chart ========== -->
<h2 class="section-title">🕸️ Multi-Dimensional Profile</h2>
<div class="radar-container" id="radarContainer"></div>

<!-- ========== Scenario Heatmap ========== -->
<h2 class="section-title">🗺️ Per-Scenario Breakdown</h2>
<div class="heatmap-container" id="heatmapContainer"></div>

<!-- ========== Per-Model Breakdown ========== -->
<h2 class="section-title">🤖 Per-Model Analysis</h2>
<div class="model-grid" id="modelGrid"></div>

<!-- ========== Footer ========== -->
<footer>
  <p>Generated by <a href="https://github.com/share-skills/pi">PI 智行合一</a> Benchmark Suite</p>
  <p id="footerTimestamp"></p>
</footer>

</div>

<script>
// ============================================================
// Inject data (replaced by report.py)
// ============================================================
const DATA = __REPORT_DATA__;

// ============================================================
// State: current model filter (null = all models)
// ============================================================
let currentModel = null;

function getView() {
  if (currentModel && DATA.per_model && DATA.per_model[currentModel]) {
    const m = DATA.per_model[currentModel];
    return {
      conditions: m.conditions || DATA.conditions,
      condition_avgs: m.condition_avgs || DATA.condition_avgs,
      scenario_data: m.scenario_data || DATA.scenario_data,
      composite_scores: m.composite_scores || DATA.composite_scores,
      scenario_composites: m.scenario_composites || DATA.scenario_composites,
      total_valid: m.total_valid || DATA.total_valid,
    };
  }
  return {
    conditions: DATA.conditions,
    condition_avgs: DATA.condition_avgs,
    scenario_data: DATA.scenario_data,
    composite_scores: DATA.composite_scores,
    scenario_composites: DATA.scenario_composites,
    total_valid: DATA.total_valid,
  };
}

// ============================================================
// Color mapping
// ============================================================
const CONDITION_COLORS = {
  pi:       { bg: '#3b82f6', border: '#60a5fa', class: 'pi' },
  'pi-lite': { bg: '#8b5cf6', border: '#a78bfa', class: 'pi-lite' },
  pua:      { bg: '#ef4444', border: '#f87171', class: 'pua' },
  nopua:    { bg: '#10b981', border: '#34d399', class: 'nopua' },
  baseline: { bg: '#64748b', border: '#94a3b8', class: 'baseline' },
};

const CONDITION_LABELS = {
  pi: 'PI 智行合一',
  'pi-lite': 'PI 白话版',
  pua: 'PUA (Fear-driven)',
  nopua: 'NoPUA (Wisdom)',
  baseline: 'Baseline',
};

// ============================================================
// Utility
// ============================================================
function pct(val, max) { return max > 0 ? Math.round((val / max) * 100) : 0; }

function deltaStr(val) {
  if (val === Infinity || val === null || val === undefined) return { text: '+∞', cls: 'positive' };
  if (val > 0) return { text: `+${val}%`, cls: 'positive' };
  if (val < 0) return { text: `${val}%`, cls: 'negative' };
  return { text: '0%', cls: 'neutral' };
}

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// ============================================================
// Render: Model Tabs
// ============================================================
function renderModelTabs() {
  const container = document.getElementById('modelTabs');
  if (DATA.models.length <= 1) {
    container.style.display = 'none';
    return;
  }
  let html = `<div class="model-tab ${currentModel === null ? 'active' : ''}" data-model="__all__">📊 All Models (${DATA.total_valid})</div>`;
  for (const model of DATA.models) {
    const count = DATA.per_model?.[model]?.total_valid || '?';
    const active = currentModel === model ? 'active' : '';
    html += `<div class="model-tab ${active}" data-model="${model}">🤖 ${model} (${count})</div>`;
  }
  container.innerHTML = html;

  // Bind click handlers
  container.querySelectorAll('.model-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const model = tab.dataset.model;
      currentModel = model === '__all__' ? null : model;
      renderAll();
    });
  });
}

// ============================================================
// Render: Meta bar
// ============================================================
function renderMeta() {
  const bar = document.getElementById('metaBar');
  const view = getView();
  const modelLabel = currentModel || DATA.models.join(' · ');
  const tags = [
    `🗓 ${new Date(DATA.timestamp).toLocaleDateString()}`,
    `📊 ${view.total_valid} results`,
    `🤖 ${modelLabel}`,
    `⚔️ ${view.conditions.map(c => CONDITION_LABELS[c] || c).join(' vs ')}`,
  ];
  bar.innerHTML = tags.map(t => `<span class="meta-tag">${t}</span>`).join('');
}

// ============================================================
// Render: Summary Cards
// ============================================================
function renderSummaryCards() {
  const grid = document.getElementById('summaryCards');
  const view = getView();
  const conditions = view.conditions;

  // ─── Composite Score overview (PUA as baseline = 100) ───
  const composites = view.composite_scores || {};
  const puaScore = composites['pua'] || 1;

  let html = '<div class="composite-header" style="grid-column:1/-1; text-align:center; margin-bottom:12px;">' +
    '<h3 style="color:#e2e8f0; margin:0 0 8px 0; font-size:1.3em;">🏆 综合评分 (PUA = 100 基线)</h3>' +
    '<div style="display:flex; justify-content:center; gap:32px; flex-wrap:wrap;">';

  for (const cond of conditions) {
    const rawScore = composites[cond] || 0;
    const normalizedScore = Math.round((rawScore / puaScore) * 100);
    const colors = CONDITION_COLORS[cond] || { bg: '#64748b' };
    const label = CONDITION_LABELS[cond] || cond;
    const cls = normalizedScore > 100 ? 'positive' : normalizedScore < 100 ? 'negative' : 'neutral';
    const arrow = normalizedScore > 100 ? '▲' : normalizedScore < 100 ? '▼' : '●';
    html += `<div style="text-align:center;">
      <div style="font-size:2.2em; font-weight:bold; color:${colors.bg};">${normalizedScore}</div>
      <div style="font-size:0.85em; color:#94a3b8;">${label}</div>
      <div class="delta ${cls}" style="font-size:0.8em;">${arrow} vs PUA ${normalizedScore > 100 ? '+' : ''}${normalizedScore - 100}%</div>
    </div>`;
  }
  html += '</div></div>';

  // ─── Per-metric cards (PI values, delta vs PUA) ───
  const keyMetrics = ['hidden_issues', 'issues_found', 'steps_taken', 'went_beyond_ask',
                      'verification_done', 'approach_changes', 'self_corrections', 'tools_used', 'duration'];

  const piAvgs = view.condition_avgs['pi'] || view.condition_avgs[conditions[0]] || {};
  const puaAvgs = view.condition_avgs['pua'] || {};

  for (const mk of keyMetrics) {
    const avgData = piAvgs[mk];
    if (!avgData) continue;
    const icon = DATA.metric_icons[mk] || '📊';
    const label = DATA.metric_labels[mk] || mk;
    const piVal = avgData.mean;
    const puaVal = puaAvgs[mk] ? puaAvgs[mk].mean : 0;
    const higher_better = mk !== 'duration';
    let delta;
    if (puaVal !== 0) {
      delta = Math.round((piVal - puaVal) / puaVal * 100 * 10) / 10;
      if (!higher_better) delta = -delta;  // For duration, lower is better
    } else {
      delta = piVal !== 0 ? Infinity : 0;
    }
    const d = deltaStr(delta);
    const unit = mk === 'duration' ? 's' : '';

    html += `
      <div class="card animate-in">
        <div class="icon">${icon}</div>
        <div class="label">${label}</div>
        <div class="value">${piVal}${unit}</div>
        <div class="delta ${d.cls}">PI vs PUA: ${d.text}</div>
      </div>`;
  }
  grid.innerHTML = html;
}

// ============================================================
// Render: Legend
// ============================================================
function renderLegend() {
  const legend = document.getElementById('legend');
  const view = getView();
  let html = '';
  for (const cond of view.conditions) {
    const colors = CONDITION_COLORS[cond] || { bg: '#64748b' };
    const label = CONDITION_LABELS[cond] || cond;
    html += `<div class="legend-item">
      <div class="legend-dot" style="background:${colors.bg}"></div>
      <span>${label}</span>
    </div>`;
  }
  legend.innerHTML = html;
}

// ============================================================
// Render: Comparison Bars
// ============================================================
function renderComparisonBars() {
  const container = document.getElementById('comparisonBars');
  const view = getView();
  const metrics = Object.keys(DATA.metric_labels);
  const conditions = view.conditions;

  // Find global max for scaling
  let globalMax = 0;
  for (const cond of conditions) {
    const avgs = view.condition_avgs[cond];
    if (!avgs) continue;
    for (const mk of metrics) {
      if (avgs[mk] && avgs[mk].mean > globalMax) globalMax = avgs[mk].mean;
    }
  }

  let html = '';
  for (const mk of metrics) {
    const label = DATA.metric_labels[mk];
    const icon = DATA.metric_icons[mk];
    const unit = mk === 'duration' ? 's' : '';

    html += `<div class="bar-group">
      <div class="bar-label">
        <span class="metric-name">${icon} ${label}</span>
      </div>`;

    // For duration, use its own max since it has different scale
    let metricMax = 0;
    if (mk === 'duration') {
      for (const cond of conditions) {
        const val = view.condition_avgs[cond]?.[mk]?.mean || 0;
        if (val > metricMax) metricMax = val;
      }
    } else {
      metricMax = globalMax;
    }

    for (const cond of conditions) {
      const avgs = view.condition_avgs[cond];
      const val = avgs && avgs[mk] ? avgs[mk].mean : 0;
      const width = pct(val, metricMax);
      const colors = CONDITION_COLORS[cond] || { class: 'baseline' };
      const condLabel = CONDITION_LABELS[cond] || cond;

      html += `<div class="bar-track">
        <div class="bar-fill ${colors.class}" style="width: ${width}%">
          ${condLabel}: ${val}${unit}
        </div>
      </div>`;
    }
    html += `</div>`;
  }
  container.innerHTML = html;
}

// ============================================================
// Render: Radar Chart
// ============================================================
function renderRadar() {
  const container = document.getElementById('radarContainer');
  const view = getView();
  // Exclude duration from radar (different scale/direction)
  const metrics = Object.keys(DATA.metric_labels).filter(m => m !== 'duration');
  const n = metrics.length;
  const cx = 300, cy = 300, r = 180;
  const angleStep = (2 * Math.PI) / n;

  // Normalize values to 0-1
  let maxVals = {};
  for (const mk of metrics) {
    let mv = 0;
    for (const cond of view.conditions) {
      const v = view.condition_avgs[cond]?.[mk]?.mean || 0;
      if (v > mv) mv = v;
    }
    maxVals[mk] = mv || 1;
  }

  // Grid rings
  let gridLines = '';
  for (let ring = 1; ring <= 4; ring++) {
    const rr = r * ring / 4;
    let points = [];
    for (let i = 0; i < n; i++) {
      const angle = -Math.PI / 2 + i * angleStep;
      points.push(`${cx + rr * Math.cos(angle)},${cy + rr * Math.sin(angle)}`);
    }
    gridLines += `<polygon points="${points.join(' ')}" class="grid-line"/>`;
  }

  // Axis lines and labels
  let axes = '';
  for (let i = 0; i < n; i++) {
    const angle = -Math.PI / 2 + i * angleStep;
    const lx = cx + (r + 25) * Math.cos(angle);
    const ly = cy + (r + 25) * Math.sin(angle);
    axes += `<line x1="${cx}" y1="${cy}" x2="${cx + r * Math.cos(angle)}" y2="${cy + r * Math.sin(angle)}" class="axis-line"/>`;
    const anchor = Math.abs(Math.cos(angle)) < 0.1 ? 'middle' :
                   Math.cos(angle) > 0 ? 'start' : 'end';
    axes += `<text x="${lx}" y="${ly}" text-anchor="${anchor}" dominant-baseline="middle">${DATA.metric_labels[metrics[i]]}</text>`;
  }

  // Data polygons
  let dataPolygons = '';
  for (const cond of view.conditions) {
    const colors = CONDITION_COLORS[cond] || { bg: '#64748b', border: '#94a3b8' };
    let points = [];
    for (let i = 0; i < n; i++) {
      const mk = metrics[i];
      const val = view.condition_avgs[cond]?.[mk]?.mean || 0;
      const norm = val / maxVals[mk];
      const angle = -Math.PI / 2 + i * angleStep;
      points.push(`${cx + r * norm * Math.cos(angle)},${cy + r * norm * Math.sin(angle)}`);
    }
    dataPolygons += `<polygon points="${points.join(' ')}" class="data-area"
      stroke="${colors.border}" fill="${colors.bg}"/>`;
  }

  container.innerHTML = `
    <svg class="radar-svg" viewBox="0 0 600 600" xmlns="http://www.w3.org/2000/svg">
      ${gridLines}
      ${axes}
      ${dataPolygons}
    </svg>`;
}

// ============================================================
// Render: Scenario Heatmap
// ============================================================
function renderHeatmap() {
  const container = document.getElementById('heatmapContainer');
  const view = getView();
  const keyMetrics = ['hidden_issues', 'issues_found', 'steps_taken', 'went_beyond_ask', 'duration'];
  const conditions = view.conditions;
  const scenarioEntries = Object.entries(view.scenario_data).sort((a, b) => Number(a[0]) - Number(b[0]));

  if (scenarioEntries.length === 0) {
    container.innerHTML = '<p style="text-align:center; color:var(--text-muted);">No scenario data for this model.</p>';
    return;
  }

  // Build header with composite score column
  let headerHtml = '<tr><th>Scenario</th><th>🏆 Winner</th>';
  for (const cond of conditions) {
    const label = CONDITION_LABELS[cond] || cond;
    headerHtml += `<th style="color:${(CONDITION_COLORS[cond]||{bg:'#fff'}).bg}">⚡ ${label.split(' ')[0]}</th>`;
  }
  for (const mk of keyMetrics) {
    for (const cond of conditions) {
      const label = CONDITION_LABELS[cond] || cond;
      headerHtml += `<th>${DATA.metric_icons[mk]}<br>${label.split(' ')[0]}</th>`;
    }
  }
  headerHtml += '</tr>';

  // Build rows with composite + winner
  let rowsHtml = '';
  const composites = view.scenario_composites || {};
  for (const [sid, s] of scenarioEntries) {
    const sc = composites[sid] || {};
    // Find winner for this scenario
    let winner = null, maxScore = -1;
    for (const cond of conditions) {
      if ((sc[cond] || 0) > maxScore) { maxScore = sc[cond] || 0; winner = cond; }
    }

    rowsHtml += `<tr><td class="scenario-name">${s.name}</td>`;
    // Winner badge
    const wColor = CONDITION_COLORS[winner] || { bg: '#64748b' };
    const wLabel = (CONDITION_LABELS[winner] || winner).split(' ')[0];
    rowsHtml += `<td><span style="background:${wColor.bg}; color:#fff; padding:2px 8px; border-radius:4px; font-size:0.8em;">${wLabel}</span></td>`;

    // Composite scores per condition
    for (const cond of conditions) {
      const val = sc[cond] || 0;
      const isWinner = cond === winner;
      const colors = CONDITION_COLORS[cond] || { bg: '#64748b' };
      const style = isWinner ? `font-weight:bold; color:${colors.bg};` : '';
      rowsHtml += `<td style="${style}">${val}${isWinner ? ' 👑' : ''}</td>`;
    }

    // Metric breakdown
    for (const mk of keyMetrics) {
      let maxVal = 0;
      for (const ss of scenarioEntries) {
        for (const cond of conditions) {
          const v = ss[1].conditions?.[cond]?.[mk] || 0;
          if (v > maxVal) maxVal = v;
        }
      }
      for (const cond of conditions) {
        const val = s.conditions?.[cond]?.[mk] || 0;
        const intensity = maxVal > 0 ? val / maxVal : 0;
        const colors = CONDITION_COLORS[cond] || { bg: '#64748b' };
        const alpha = 0.1 + intensity * 0.6;
        const bg = hexToRgba(colors.bg, alpha);
        const unit = mk === 'duration' ? 's' : '';
        rowsHtml += `<td><span class="heat-cell" style="background:${bg}">${val}${unit}</span></td>`;
      }
    }
    rowsHtml += '</tr>';
  }

  // Totals row
  rowsHtml += '<tr style="border-top: 2px solid #475569; font-weight:bold;"><td>TOTAL</td>';
  const totalComposites = view.composite_scores || {};
  let totalWinner = null, totalMax = -1;
  for (const cond of conditions) {
    if ((totalComposites[cond] || 0) > totalMax) { totalMax = totalComposites[cond] || 0; totalWinner = cond; }
  }
  const twColor = CONDITION_COLORS[totalWinner] || { bg: '#64748b' };
  const twLabel = (CONDITION_LABELS[totalWinner] || totalWinner).split(' ')[0];
  rowsHtml += `<td><span style="background:${twColor.bg}; color:#fff; padding:2px 8px; border-radius:4px; font-size:0.8em;">${twLabel}</span></td>`;
  for (const cond of conditions) {
    const val = totalComposites[cond] || 0;
    const isW = cond === totalWinner;
    const colors = CONDITION_COLORS[cond] || { bg: '#64748b' };
    rowsHtml += `<td style="${isW ? 'font-weight:bold; color:'+colors.bg+';' : ''}">${val}${isW ? ' 👑' : ''}</td>`;
  }
  // Metric averages in totals row
  for (const mk of keyMetrics) {
    for (const cond of conditions) {
      const avgs = view.condition_avgs[cond]?.[mk];
      const unit = mk === 'duration' ? 's' : '';
      rowsHtml += `<td>${avgs ? avgs.mean : 0}${unit}</td>`;
    }
  }
  rowsHtml += '</tr>';

  container.innerHTML = `<table class="heatmap-table">
    <thead>${headerHtml}</thead>
    <tbody>${rowsHtml}</tbody>
  </table>`;
}

// ============================================================
// Render: Per-Model Breakdown
// ============================================================
function renderModelBreakdown() {
  const grid = document.getElementById('modelGrid');
  const keyMetrics = ['hidden_issues', 'issues_found', 'steps_taken', 'verification_done', 'duration'];

  // If viewing a specific model, show per-scenario cards instead
  if (currentModel) {
    grid.innerHTML = '';
    return;
  }

  let html = '';
  for (const model of DATA.models) {
    const modelInfo = DATA.model_data[model] || {};

    html += `<div class="model-card">
      <h3>🤖 ${model}</h3>`;

    for (const mk of keyMetrics) {
      const label = DATA.metric_labels[mk];
      // Find max value for this metric across conditions
      let maxVal = 0;
      for (const cond of DATA.conditions) {
        const v = modelInfo[cond]?.[mk] || 0;
        if (v > maxVal) maxVal = v;
      }

      html += `<div style="margin-bottom:12px;font-size:0.85rem;color:var(--text-muted);">${DATA.metric_icons[mk]} ${label}</div>`;
      for (const cond of DATA.conditions) {
        const val = modelInfo[cond]?.[mk] || 0;
        const width = maxVal > 0 ? Math.round((val / maxVal) * 100) : 0;
        const colors = CONDITION_COLORS[cond] || { class: 'baseline' };
        const condLabel = (CONDITION_LABELS[cond] || cond).split(' ')[0];
        const unit = mk === 'duration' ? 's' : '';

        html += `<div class="mini-bar">
          <span class="mlabel">${condLabel}</span>
          <div class="mtrack">
            <div class="mfill ${colors.class}" style="width:${width}%">${val}${unit}</div>
          </div>
        </div>`;
      }
    }
    html += `</div>`;
  }
  grid.innerHTML = html;
}

function renderFooter() {
  document.getElementById('footerTimestamp').textContent =
    `Report generated: ${new Date(DATA.timestamp).toLocaleString()}`;
}

// ============================================================
// Render all (called on init and on model tab switch)
// ============================================================
function renderAll() {
  renderModelTabs();
  renderMeta();
  renderSummaryCards();
  renderLegend();
  renderComparisonBars();
  renderRadar();
  renderHeatmap();
  renderModelBreakdown();
  renderFooter();
}

// ============================================================
// Initialize
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  renderAll();
});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(input_dir: Path, output_path: Path,
                    extra_results: list[dict] | None = None):
    """Generate standalone HTML report from benchmark results."""
    if extra_results:
        results = extra_results
    else:
        results = load_results(input_dir)

    if not results:
        print(f"Error: No results found in {input_dir}")
        sys.exit(1)

    print(f"Loaded {len(results)} results")
    report_data = aggregate_results(results)
    print(f"Conditions: {report_data['conditions']}")
    print(f"Models: {report_data['models']}")
    print(f"Scenarios: {len(report_data['scenarios'])}")

    # Inject data into HTML template
    # Escape </script> sequences to prevent XSS when embedding JSON in a <script> tag
    data_json = json.dumps(report_data, indent=None, ensure_ascii=False)
    data_json = data_json.replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__REPORT_DATA__", data_json)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    print(f"Report saved: {output_path} ({len(html)} bytes)")
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PI Benchmark Report Generator",
    )
    parser.add_argument(
        "--input-dir", type=str, default=str(SCRIPT_DIR / "results"),
        help="Directory containing result JSON files",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output HTML path (default: <input-dir>/report.html)",
    )
    parser.add_argument(
        "--open", action="store_true",
        help="Open report in browser after generating",
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Generate demo report with sample data (no results dir needed)",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output) if args.output else input_dir / "report.html"

    if args.demo:
        print("Generating demo report with sample data...")
        demo_results = generate_demo_data()
        # Save demo data for inspection
        demo_dir = SCRIPT_DIR / "demo"
        demo_dir.mkdir(exist_ok=True)
        demo_file = demo_dir / "demo_results.json"
        demo_file.write_text(json.dumps(demo_results, indent=2, ensure_ascii=False),
                             encoding="utf-8")
        print(f"Demo data saved: {demo_file}")

        # Respect --output if provided; otherwise default to demo/report.html
        if not args.output:
            output_path = demo_dir / "report.html"
        generate_report(demo_dir, output_path, extra_results=demo_results)
    else:
        if not input_dir.exists():
            print(f"Error: {input_dir} not found")
            print("Run benchmark first: python run.py")
            print("Or use --demo for sample data")
            sys.exit(1)
        generate_report(input_dir, output_path)

    if args.open:
        webbrowser.open(f"file://{output_path.resolve()}")
        print("Opened in browser")


if __name__ == "__main__":
    main()
