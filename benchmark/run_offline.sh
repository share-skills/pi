#!/usr/bin/env bash
# ===========================================================================
# PI Benchmark — Offline Runner (run OUTSIDE Claude Code session)
#
# Usage:
#   # Exit Claude Code first, then:
#   cd benchmark && ./run_offline.sh
#
# This script runs benchmark via `claude -p` which conflicts with an active
# Claude Code session. Run this in a plain terminal.
# ===========================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  PI Benchmark — Offline Runner               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "Running: all 4 conditions × scenario 1 × 1 run"
echo "Backend: claude sonnet (local)"
echo ""

# Run benchmark
python3 local_run.py \
    --backend claude \
    --scenario 1 \
    --runs 1 \
    --report

echo ""
echo "Done! Results in results/ directory."
echo "Re-enter Claude Code to analyze: python3 report.py --input-dir results/ --open"
