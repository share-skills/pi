#!/usr/bin/env bash
# ===========================================================================
# PI Benchmark — One-Click CLI
#
# Usage:
#   ./bench.sh demo       # Generate demo report (no API calls, instant)
#   ./bench.sh run        # Run benchmark (requires GITHUB_TOKEN)
#   ./bench.sh local      # Run benchmark locally (claude sonnet)
#   ./bench.sh local-quick # Quick local benchmark (3 scenarios, 1 run)
#   ./bench.sh qoder      # Run benchmark with qodercli lite (free)
#   ./bench.sh qoder-perf # Run benchmark with qodercli performance
#   ./bench.sh report     # Generate report from existing results
#   ./bench.sh full       # Run + analyze + report + open
#   ./bench.sh dry-run    # Preview what will happen
#   ./bench.sh help       # Show this help
#
# Supports: GitHub Copilot CLI, Claude Code, standalone terminal
# ===========================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'  # No Color
BOLD='\033[1m'

banner() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}⚡ PI Benchmark${NC} — 4-Way Skill Comparison     ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
    echo ""
}

check_deps() {
    local missing=0
    for cmd in python3; do
        if ! command -v "$cmd" &>/dev/null; then
            echo -e "${RED}✗ Missing: $cmd${NC}"
            missing=1
        fi
    done
    # Check Python packages
    if ! python3 -c "import openai" 2>/dev/null; then
        echo -e "${YELLOW}⚠ Python 'openai' package not installed${NC}"
        echo -e "  Install: ${BOLD}pip install openai numpy scipy${NC}"
        if [ "${1:-}" != "demo" ] && [ "${1:-}" != "report" ] && [ "${1:-}" != "dry-run" ]; then
            missing=1
        fi
    fi
    if [ $missing -eq 1 ] && [ "${1:-}" != "demo" ]; then
        echo -e "${RED}Please install missing dependencies first.${NC}"
        exit 1
    fi
}

check_token() {
    if [ -z "${GITHUB_TOKEN:-}" ]; then
        # Try to get from gh CLI
        if command -v gh &>/dev/null; then
            export GITHUB_TOKEN=$(gh auth token 2>/dev/null || true)
        fi
    fi
    if [ -z "${GITHUB_TOKEN:-}" ]; then
        echo -e "${RED}✗ GITHUB_TOKEN not set${NC}"
        echo -e "  Run: ${BOLD}export GITHUB_TOKEN=\$(gh auth token)${NC}"
        echo -e "  Or:  ${BOLD}export GITHUB_TOKEN=your_pat_token${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ GitHub token configured${NC}"
}

cmd_demo() {
    echo -e "${PURPLE}▸ Generating demo report (no API calls)...${NC}"
    python3 report.py --demo --open
    echo ""
    echo -e "${GREEN}✓ Demo report opened in browser!${NC}"
    echo -e "  ${BOLD}This uses synthetic data to preview the report UI.${NC}"
    echo -e "  Run ${BOLD}./bench.sh full${NC} for real benchmark results."
}

cmd_run() {
    check_token
    echo -e "${PURPLE}▸ Running PI vs PI-lite vs PUA vs NoPUA benchmark...${NC}"
    echo ""
    python3 run.py "$@"
    echo ""
    echo -e "${GREEN}✓ Benchmark complete!${NC}"
    echo -e "  Results in: ${BOLD}results/${NC}"
    echo -e "  Next: ${BOLD}./bench.sh report${NC}"
}

cmd_report() {
    echo -e "${PURPLE}▸ Generating HTML report...${NC}"
    python3 report.py --input-dir results/ --open
    echo ""
    echo -e "${GREEN}✓ Report opened in browser!${NC}"
}

cmd_analyze() {
    echo -e "${PURPLE}▸ Running statistical analysis...${NC}"
    python3 analyze.py --input-dir results/
}

cmd_full() {
    check_token
    echo -e "${PURPLE}▸ Full benchmark pipeline: run → analyze → report${NC}"
    echo ""
    python3 run.py --report "$@"
    echo ""
    echo -e "${PURPLE}▸ Statistical analysis...${NC}"
    python3 analyze.py --input-dir results/ 2>/dev/null || true
    echo ""
    echo -e "${GREEN}════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ Benchmark pipeline complete!${NC}"
    echo -e "${GREEN}════════════════════════════════════════${NC}"
}

cmd_dry_run() {
    echo -e "${PURPLE}▸ Dry run (no API calls)...${NC}"
    python3 run.py --dry-run "$@"
}

cmd_local() {
    echo -e "${PURPLE}▸ Running local benchmark (claude sonnet)...${NC}"
    echo ""
    python3 local_run.py --backend claude "$@"
    echo ""
    echo -e "${GREEN}✓ Local benchmark complete!${NC}"
    echo -e "  Results in: ${BOLD}results/${NC}"
    echo -e "  Next: ${BOLD}./bench.sh report${NC}"
}

cmd_local_quick() {
    echo -e "${PURPLE}▸ Quick local benchmark (3 scenarios × all conditions × 1 run)...${NC}"
    echo ""
    python3 local_run.py --backend claude --scenario 1 --runs 1 "$@"
    python3 local_run.py --backend claude --scenario 4 --runs 1 "$@"
    python3 local_run.py --backend claude --scenario 7 --runs 1 "$@"
    echo ""
    echo -e "${GREEN}✓ Quick benchmark complete!${NC}"
}

cmd_qoder() {
    echo -e "${PURPLE}▸ Running qodercli lite benchmark (free)...${NC}"
    echo ""
    python3 local_run.py --backend qodercli "$@"
    echo ""
    echo -e "${GREEN}✓ Qoder benchmark complete!${NC}"
}

cmd_qoder_perf() {
    echo -e "${PURPLE}▸ Running qodercli performance benchmark...${NC}"
    echo ""
    python3 local_run.py --backend qodercli-perf "$@"
    echo ""
    echo -e "${GREEN}✓ Qoder performance benchmark complete!${NC}"
}

cmd_gemini() {
    echo -e "${PURPLE}▸ Running Gemini CLI benchmark (free)...${NC}"
    echo ""
    python3 local_run.py --backend gemini "$@"
    echo ""
    echo -e "${GREEN}✓ Gemini benchmark complete!${NC}"
}

cmd_qwen() {
    echo -e "${PURPLE}▸ Running Qwen Code benchmark (free)...${NC}"
    echo ""
    python3 local_run.py --backend qwen "$@"
    echo ""
    echo -e "${GREEN}✓ Qwen benchmark complete!${NC}"
}

show_help() {
    banner
    echo -e "${BOLD}Commands:${NC}"
    echo ""
    echo -e "  ${GREEN}demo${NC}         Generate demo report with sample data (instant, no API)"
    echo -e "  ${GREEN}run${NC}          Run benchmark via GitHub Models API (requires GITHUB_TOKEN)"
    echo -e "  ${GREEN}local${NC}        Run benchmark locally (claude sonnet, subscription)"
    echo -e "  ${GREEN}local-quick${NC}  Quick local benchmark (3 scenarios, 1 run)"
    echo -e "  ${GREEN}qoder${NC}        Run benchmark with qodercli lite (free)"
    echo -e "  ${GREEN}qoder-perf${NC}   Run benchmark with qodercli performance (paid)"
    echo -e "  ${GREEN}gemini${NC}       Run benchmark with Gemini CLI (free, Google account)"
    echo -e "  ${GREEN}qwen${NC}         Run benchmark with Qwen Code CLI (free, 1000 req/day)"
    echo -e "  ${GREEN}report${NC}       Generate HTML report from existing results"
    echo -e "  ${GREEN}analyze${NC}      Run statistical analysis (terminal tables)"
    echo -e "  ${GREEN}full${NC}         Run + analyze + report + open browser"
    echo -e "  ${GREEN}dry-run${NC}      Preview what will happen (no API calls)"
    echo -e "  ${GREEN}help${NC}         Show this help"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo ""
    echo -e "  ${CYAN}# Quick demo to see the report UI${NC}"
    echo -e "  ./bench.sh demo"
    echo ""
    echo -e "  ${CYAN}# Run full benchmark with specific model${NC}"
    echo -e "  ./bench.sh run --models gpt-4o"
    echo ""
    echo -e "  ${CYAN}# Run specific scenario${NC}"
    echo -e "  ./bench.sh run --scenario 3"
    echo ""
    echo -e "  ${CYAN}# Full pipeline${NC}"
    echo -e "  ./bench.sh full"
    echo ""
    echo -e "${BOLD}Integration:${NC}"
    echo ""
    echo -e "  ${CYAN}# In GitHub Copilot CLI:${NC}"
    echo -e "  Ask: \"Run the PI benchmark demo\""
    echo -e "  → copilot executes: cd benchmark && ./bench.sh demo"
    echo ""
    echo -e "  ${CYAN}# In Claude Code:${NC}"
    echo -e "  Ask: \"Run PI benchmark with gpt-4o and show report\""
    echo -e "  → executes: cd benchmark && ./bench.sh full --models gpt-4o"
    echo ""
    echo -e "${BOLD}Environment:${NC}"
    echo ""
    echo -e "  GITHUB_TOKEN   GitHub PAT or 'gh auth token' output"
    echo -e "                 Required for run/full. Not needed for demo/report."
    echo ""
}

# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------
banner

case "${1:-help}" in
    demo)        check_deps demo; cmd_demo ;;
    run)         check_deps run;  shift; cmd_run "$@" ;;
    local)       check_deps local; shift; cmd_local "$@" ;;
    local-quick) check_deps local-quick; shift; cmd_local_quick "$@" ;;
    qoder)       check_deps qoder; shift; cmd_qoder "$@" ;;
    qoder-perf)  check_deps qoder-perf; shift; cmd_qoder_perf "$@" ;;
    gemini)      check_deps gemini; shift; cmd_gemini "$@" ;;
    qwen)        check_deps qwen; shift; cmd_qwen "$@" ;;
    report)      check_deps report; cmd_report ;;
    analyze)     check_deps analyze; cmd_analyze ;;
    full)        check_deps full; shift; cmd_full "$@" ;;
    dry-run)     check_deps dry-run; shift; cmd_dry_run "$@" ;;
    help|--help|-h) show_help ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Run: ./bench.sh help"
        exit 1
        ;;
esac
