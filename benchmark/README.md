# PI Benchmark — Skill Comparison Suite

Compares AI investigation quality between **PI (智行合一)** and **PUA (fear-driven)** prompting strategies using [NoPUA's benchmark scenarios](../nopua/benchmark/).

## One-Click Usage

```bash
# Instant demo — see the report UI with sample data (no API needed)
./benchmark/bench.sh demo

# Full benchmark pipeline
./benchmark/bench.sh full

# Dry run — preview what will happen
./benchmark/bench.sh dry-run
```

## Quick Start

```bash
# 1. Set up GitHub token (for GitHub Models API)
export GITHUB_TOKEN=$(gh auth token)

# 2. Install dependencies
pip install openai numpy scipy

# 3. Dry run — see what will happen
./benchmark/bench.sh dry-run

# 4. Run full benchmark (3 models × 2 conditions × 9 scenarios × 2 runs = 108 calls)
./benchmark/bench.sh full

# 5. Demo report (instant, no API calls)
./benchmark/bench.sh demo
```

## Commands

| Command | Description | API Required |
|---------|-------------|:---:|
| `demo` | Generate demo report with synthetic data | ❌ |
| `run` | Run benchmark against models | ✅ |
| `report` | Generate HTML report from existing results | ❌ |
| `analyze` | Run statistical analysis (terminal tables) | ❌ |
| `full` | Run + analyze + report + open browser | ✅ |
| `dry-run` | Preview what will happen (no API calls) | ❌ |

## Conditions

| Condition | Description | Source |
|-----------|-------------|--------|
| **PI** (智行合一) | Wisdom-driven cognitive engine (v20) | `SKILL.md` (project root) |
| **PUA** (fear-driven) | Performance pressure prompt | `data/pua_prompt.txt` |
| **NoPUA** (wisdom) | Anti-manipulation, balanced approach | `nopua/SKILL.md` |
| **Baseline** (optional) | No skill loaded | *(none)* |

> Default: PI vs PUA vs NoPUA three-way comparison. Use `--conditions pi pua` for head-to-head.

## Modes

### API Mode (automated)

Calls models via [GitHub Models API](https://github.com/marketplace/models) (OpenAI-compatible endpoint).

```bash
# All models, all scenarios, 2 runs each
python benchmark/run.py

# Single model
python benchmark/run.py --models gpt-4o

# Specific scenario
python benchmark/run.py --scenario 3

# More runs for statistical power
python benchmark/run.py --runs 5

# Three-way comparison
python benchmark/run.py --conditions pi pua baseline
```

### Prompt Mode (manual Copilot Chat)

Generates markdown files you can paste into GitHub Copilot Chat directly.

```bash
python benchmark/run.py --prompts
# → benchmark/results/prompts/s01_pua.md, s01_pi.md, ...
```

Each file contains system prompt + user prompt. Paste into Copilot Chat, record the response, score manually.

## Report

The HTML report is a standalone single-file with dark tech theme:
- **Radar chart** — multi-metric comparison (SVG)
- **Heatmap** — per-scenario, per-model performance
- **Bar charts** — condition vs condition breakdown
- **Per-model detail** — drill into each model's performance
- Zero external dependencies (all CSS/JS inline)

```bash
# Generate from existing results
python benchmark/report.py --input-dir results/

# Demo with synthetic data
python benchmark/report.py --demo --open
```

## Models

| Alias | Model ID | Provider |
|-------|----------|----------|
| `gpt-4o` | gpt-4o | OpenAI |
| `claude-sonnet` | claude-sonnet-4-20250514 | Anthropic |
| `gemini-flash` | gemini-2.0-flash | Google |

All accessed through GitHub Models API — single token, single endpoint.

## Metrics

| Metric | Description |
|--------|-------------|
| Issues Found | Explicit bugs/problems identified |
| Hidden Issues | Problems found beyond the original ask |
| Steps Taken | Distinct investigation steps |
| Went Beyond Ask | Did the agent investigate more than requested? |
| Verification Done | Did the agent verify its findings? |
| Approach Changes | Times the agent changed direction |
| Self-Corrections | Times the agent corrected its own conclusion |
| Tools Used | Number of distinct tools used |

## Analysis Output

```bash
# Console tables with statistical tests
python benchmark/analyze.py --input-dir benchmark/results/

# Save JSON report
python benchmark/analyze.py --input-dir benchmark/results/ --json-report
```

Includes: Mann-Whitney U test, Cohen's d effect size, significance markers (* p<0.05, ** p<0.01, *** p<0.001).

## Cost Estimate

Each API call ≈ $0.10–0.15 (input ~4K tokens + output ~4K tokens + extraction ~2K tokens).

| Configuration | Calls | Est. Cost |
|---------------|-------|-----------|
| Full (3 models × 9 scenarios × 2 conditions × 2 runs) | 108 | ~$13 |
| Single model, 2 runs | 36 | ~$4 |
| Single scenario, all models | 12 | ~$1.5 |

## Prerequisites

- **GitHub Token**: `gh auth token` or a PAT with `models:read` scope
- **Python 3.10+**
- **pip packages**: `openai`, `numpy`, `scipy`
- **NoPUA benchmark data**: `nopua/benchmark/scenarios.json` + `nopua/benchmark/test-project/`

## Integration

### GitHub Copilot CLI

**是的，完全支持！** 在 Copilot CLI 中直接告诉 AI 你想做什么即可：

```
# 直接对话：
"Run the PI benchmark demo"           → ./benchmark/bench.sh demo
"Show me how PI compares to PUA"      → ./benchmark/bench.sh full --models gpt-4o
"Dry run the benchmark"               → ./benchmark/bench.sh dry-run
"Generate benchmark report"           → ./benchmark/bench.sh report
```

Copilot CLI 会自动识别并执行对应命令。你也可以直接在终端运行 `./benchmark/bench.sh demo`。

### Claude Code

Ask: *"Run PI benchmark with gpt-4o and show report"* → Executes `cd benchmark && ./bench.sh full --models gpt-4o`

## Architecture

```
benchmark/                    # 完全独立，自包含
├── bench.sh                  # One-click CLI wrapper (start here)
├── run.py                    # Runner: builds prompts, calls API, extracts metrics
├── report.py                 # HTML report generator (standalone dark-tech theme)
├── analyze.py                # Statistical comparison, tables, reports
├── data/                     # Self-contained test fixtures
│   ├── scenarios.json        # 9 scenarios (6 debugging + 3 proactive)
│   ├── pua_prompt.txt        # PUA condition system prompt
│   └── test-project/         # 20 Python files simulating AI pipeline
├── demo/                     # Demo output directory
│   ├── demo_results.json
│   └── report.html
├── results/                  # Benchmark output directory (git-ignored)
│   ├── gpt-4o.json
│   ├── claude-sonnet.json
│   ├── gemini-flash.json
│   └── prompts/              # Generated prompt files (--prompts mode)
└── README.md

# External references (skill files being tested):
../SKILL.md                   # PI skill (project root)
../nopua/SKILL.md             # NoPUA skill
```
