<!--
  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
-->

# Why Visualize AI Decisions? — The Complete PI Decision Visualization Guide

> 📖 中文版 / Chinese version: [WHY_VISUALIZE.md](WHY_VISUALIZE.md)

> **From "Black Box" to "Crystal Ball": Making Every AI Decision Visible**

> *"The skillful commander seeks victory through strategic momentum, not by demanding the impossible of individuals."*
> — *The Art of War*, Chapter on Momentum

---

## Table of Contents

1. [Why Visualization Matters](#1-why-visualization-matters)
2. [What PI Decision Visualization Can Do](#2-what-pi-decision-visualization-can-do)
3. [Quick Start: Up and Running in 5 Minutes](#3-quick-start-up-and-running-in-5-minutes)
4. [Understanding Decision Nodes](#4-understanding-decision-nodes)
5. [Real-World Scenarios](#5-real-world-scenarios)
6. [Advanced Usage](#6-advanced-usage)
7. [Best Practices](#7-best-practices)
8. [FAQ](#8-faq)
9. [Further Reading](#further-reading)

---

## 1. Why Visualization Matters

### The "Black Box" Problem

Every day, developers entrust AI assistants with complex tasks — debugging production incidents, architecting microservices, refactoring legacy code. The AI works. Sometimes brilliantly. Sometimes catastrophically. And in both cases, you have **no idea why**.

This is the Black Box problem:

| What You See | What Actually Happened |
|---|---|
| "I fixed the bug" | 3 failed attempts → strategy shift → root-cause isolation → targeted fix |
| "Here's the refactored code" | Analyzed 12 files → identified coupling → chose Strangler Pattern → incremental migration |
| "Tests are passing" | Missed edge case → false positive → silent regression introduced |

Without visibility into the decision process, three critical capabilities are lost:

- **🔁 Reproducibility** — You cannot reproduce success if you don't know what made it succeed.
- **🔍 Diagnosis** — You cannot diagnose failure if you don't see where reasoning went wrong.
- **👥 Alignment** — You cannot align your team if each member interacts with a different "black box."

### The Transformation: From Guessing to Knowing

PI Decision Visualization transforms the black box into a crystal ball. Every decision the AI makes — every strategy shift, every escalation, every cognitive mode switch — is captured, structured, and rendered as an interactive graph.

Instead of reading a wall of text and guessing what happened, you **see** the decision tree:

```
User prompt → Scene: 🔧 Debug → L1 Standard
    ├─ Tool: grep (success) → confidence: high
    ├─ Tool: bash test (failure ❌) → failure_count: 1
    ├─ ⚡ Escalation → L2 易辙 (Easy Shift) 🦅 Eagle activated
    │   └─ Strategy: "Survey landscape, find critical path"
    ├─ Tool: grep (broader search) → found root cause
    ├─ Tool: edit fix (success) → confidence: high
    └─ Tool: bash test (success ✅) → outcome: delivered
```

### A Concrete Example

**The scenario:** A WebSocket connection leaks memory in production. The AI is asked to debug it.

**Without visualization**, the developer sees: *"I found and fixed a memory leak in the WebSocket handler."* They merge the PR. Two weeks later, the leak returns — because the AI fixed a symptom, not the cause, and nobody could see the shallow reasoning path.

**With PI visualization**, the developer sees the full decision graph:

1. **L1 Standard** — AI grepped for `WebSocket` references, found 4 files
2. **Tool failure** — Initial test reproduced the leak but fix attempt failed
3. **L2 易辙 (Easy Shift)** — 🦅 Eagle activated: *"Survey the landscape"* — AI widened search to event listener lifecycle
4. **L3 深搜 (Deep Search)** — 🦈 Shark activated: *"Surface unsearched depths"* — found an unremoved `addEventListener` in a cleanup path
5. **Fix verified** — Tests passed, memory profile confirmed flat

The developer sees the AI explored the cleanup path, not just the handler. Confidence is high. The PR is merged with understanding.

---

## 2. What PI Decision Visualization Can Do

### Core Capabilities

| Capability | Description |
|---|---|
| **🌳 Decision Graph** | Interactive node-and-edge visualization of every decision point, zoomable and pannable |
| **⏱️ Timeline** | Scrub through the session chronologically; watch decisions unfold in order |
| **📊 Metrics Panel** | Token usage, complexity score, max battle level, beast activations, quality score |
| **📋 Detail Drawer** | Click any node to inspect: scene, strategy, classical reference, cognitive mode, payload |
| **📤 Export** | Privacy-protected JSON export for sharing, auditing, or feeding back into PI |
| **🔴 Live Monitoring** | WebSocket-powered real-time updates as the AI works — watch decisions appear live |
| **🤖 Multi-Agent** | Track sub-agent lifecycles: which agent started, what it did, when it stopped |

### Platform Support

PI visualization works across all major AI coding platforms:

| Platform | Integration Method | Data Capture |
|---|---|---|
| **Claude Code** | Native `hooks.json` | Automatic — hooks fire on every event |
| **GitHub Copilot CLI** | `install.sh` configuration | Automatic — AgentSkills integration |
| **Cursor** | `.cursorrules` + `pi-visualize.mdc` | Automatic — `alwaysApply: true` |
| **Kiro** | Steering rule files | Automatic — `inclusion: auto` |
| **Qoder** | Bash adapter script | Automatic — `pi-qoder-adapter.sh` |
| **Any other tool** | `capture-generic.sh` | Manual invocation or scripted |

### How Data Gets Captured: The Hooks System

PI uses a lightweight hook system — small Bash scripts that fire at key moments in the AI session lifecycle. No heavy agents, no background daemons, no performance impact.

```
AI Session Lifecycle              Hook Event              Script
─────────────────────────────────────────────────────────────────
User types a prompt         →  UserPromptSubmit    →  capture-prompt.sh
AI finishes responding      →  Stop                →  capture-decision.sh  ⭐ primary
Tool executes successfully  →  PostToolUse         →  capture-tool-result.sh success
Tool execution fails        →  PostToolUseFailure  →  capture-tool-result.sh failure
Sub-agent starts            →  SubagentStart       →  capture-subagent.sh start
Sub-agent finishes          →  SubagentStop        →  capture-subagent.sh stop
Context compaction begins   →  PreCompact          →  pre-compact.sh
```

Each hook appends a structured JSON event to a session file. The result is a complete, chronological record of every decision the AI made.

### Data Storage

All decision data is stored locally on your machine:

```
~/.pi/decisions/
├── 2025-01-15/
│   ├── session-abc123.json            ← session metadata
│   ├── session-abc123.events.jsonl    ← streaming events
│   ├── session-abc123.nodes.jsonl     ← decision tree nodes
│   └── session-def456.events.jsonl
├── 2025-01-16/
│   └── session-ghi789.events.jsonl
└── ...
```

- **Format:** JSONL (JSON Lines) — one event per line, append-only; plus JSON for session metadata
- **Organization:** By date (`YYYY-MM-DD`) and session ID
- **Privacy:** All data passes through `sanitize_text()` before storage (see [FAQ](#8-faq))
- **Size:** Typically 10–50 KB per session; negligible disk impact

---

## 3. Quick Start: Up and Running in 5 Minutes

### Step 1: Install PI with Visualization

**Option A — Full install (recommended):**

```bash
# Clone the repository
git clone https://github.com/share-skills/pi.git
cd pi

# Run the interactive installer
bash install.sh
```

The installer auto-detects your AI tools (Claude Code, Copilot CLI, Cursor, Kiro, etc.), installs PI skills, and sets up the visualization launcher at `~/.pi/visualize.sh`.

**Option B — Quick bootstrap (no clone needed):**

```bash
curl -fsSL https://raw.githubusercontent.com/share-skills/pi/main/install.sh | bash
```

### Step 2: Use PI Normally

Start your AI assistant and work as usual. PI hooks capture decisions automatically in the background.

```bash
# Example with Claude Code — just use /pi commands:
/pi coding "Fix the authentication middleware timeout issue"

# Work normally... hooks capture every decision silently
```

### Step 3: Launch the Visualizer

```bash
# Method 1: Via PI command (inside your AI session)
/pi visualize

# Method 2: Via shell script (from any terminal)
~/.pi/visualize.sh

# Method 3: From the PI repository directly
cd pi/visualize && npm run server
```

The visualizer starts on **port 3141** and automatically opens your browser.

### Step 4: Explore with Mock Data

No real decision data yet? Use mock mode for an immediate hands-on tour:

```bash
# Start with synthetic sample data
cd pi/visualize && npm run start:mock

# Or via the flag
npm run server -- --mock
```

Mock mode generates 8 sample sessions covering all PI scenarios — debugging, multi-agent collaboration, creative design, and more.

### UI Tour

```
┌──────────────────────────────────────────────────────┐
│ ⚡ PI Visualizer   [▶ Timeline ═══●════]   metrics   │  TopBar
├──────────┬───────────────────────┬───────────────────┤
│  📅 Date │    Decision Canvas    │    [Details]      │
│  Sessions│    (drag/zoom/pan)    │    Float Panel    │
│  Tree    │                      │                   │
├──────────┴───────────────────────┴───────────────────┤
│ tokens: 12.4k │ complexity: 3/5 │ status: ✅ success │  StatusBar
└──────────────────────────────────────────────────────┘
```

| Area | What It Shows |
|---|---|
| **TopBar** | Timeline scrubber, play/pause, session metrics at a glance |
| **Tree Nav** (left) | Date-grouped session list; click to load a session's decision graph |
| **Decision Canvas** (center) | The interactive graph — drag, zoom, pan; click nodes for details |
| **Detail Drawer** (right) | Full node metadata: scene, beast, strategy, tokens, outcome |
| **StatusBar** (bottom) | Aggregate stats: total tokens, complexity score, current status |

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `[` | Toggle sidebar |
| `]` | Toggle detail drawer |
| `↑` `↓` | Switch between sessions |
| `Space` | Play / Pause timeline |
| `?` | Show help overlay |
| `Esc` | Close open panels |

---

## 4. Understanding Decision Nodes

### Anatomy of a Decision Node

Every node in the decision graph represents a single decision point. Here is what each field means:

```json
{
  "node_id": "550e8400-...",
  "session_id": "uuid-...",
  "timestamp": "2025-01-15T14:23:45Z",
  "label": "🧠 PI · debugging · 🧠",
  "category": "battle",
  "decision_point": "session.stop",
  "scene": "debugging",
  "difficulty": "🧠",
  "battle_level": 2,
  "failure_count": 1,
  "agent_id": "pi",
  "payload": {
    "beast": "🦅鹰",
    "strategy": "穷搜广读",
    "pi_context": {
      "skill_name": "pi",
      "skill_version": "20",
      "scene_announcement": "🧠 PI · debugging · 🧠",
      "thought_chain_summary": "Widened search scope after initial fix failed",
      "cognitive_mode": "deep_analysis",
      "confidence": "high",
      "classical_reference": "以正合，以奇胜",
      "interaction_mode": "auto",
      "resonance_forms": "transparent_chain,state_signal"
    },
    "model_context": {
      "name": "Claude Opus 4.6",
      "provider": "anthropic",
      "input_tokens": 15000,
      "output_tokens": 22000
    }
  },
  "privacy_level": "redacted",
  "outcome": "success",
  "children_node_ids": ["..."]
}
```

| Field | Meaning |
|---|---|
| `scene` | Which of the 9 PI scenarios is active (coding, debug, testing, product, ops, creative, collaboration, interaction, companion) |
| `difficulty` | Visual indicator: ⚡ Light · 🧠 Standard · 🐲 Deep |
| `battle_level` | Escalation tier (0–6); higher = more failures, more aggressive strategy |
| `failure_count` | How many consecutive failures triggered this state |
| `payload.beast` | The 灵兽 (Spirit Beast) archetype guiding cognition at this point |
| `payload.strategy` | The tactical approach drawn from Sun Tzu or PI's strategy library |
| `payload.pi_context.cognitive_mode` | Active thinking mode for the decision |
| `payload.pi_context.classical_reference` | The classical Chinese wisdom informing the decision |
| `payload.pi_context.confidence` | AI's self-assessed confidence: high, medium, or low |
| `payload.model_context` | Model name, provider, input/output token counts |
| `outcome` | Result: success, failure, pending, or cancelled |

### The 12 灵兽 (Spirit Beasts)

Spirit Beasts are cognitive archetypes — not mascots, but functional lenses that shape how the AI processes information. When you see a beast activated in the visualization, it means the AI has shifted its cognitive strategy.

| Beast | Spirit | Cognitive Function | When Activated |
|---|---|---|---|
| 🦅 **Eagle** (鹰) | Insight | Holistic overview, O(n²)→O(n) reduction | Lost in details; need big-picture perspective |
| 🐺🐯 **Wolf-Tiger** (狼虎) | Candor + Truth | Eliminate confirmation bias, expose hidden risks | Assumptions unverified or known risks unspoken |
| 🦁 **Lion** (狮) | Valor | Break through local optima | About to give up prematurely |
| 🐎 **Horse** (马) | Speed | Tighten time constraints, accelerate delivery | Efficiency is dropping |
| 🐂 **Ox** (牛) | Grit | Exhaustive search, refuse to prune | Task seems impossibly large |
| 🦈 **Shark** (鲨) | Search | Maximize information gain, detect risks | Guessing instead of searching |
| 🐝 **Bee** (蜂) | Swarm | Parallel activation, synchronized output | Final sprint coordination |
| 🦊 **Fox** (狐) | Prudence | Meta-cognition, scrutinize output quality | Quality is drifting |
| 🐲 **Loong** (龙) | Extreme | Total resource commitment | Breakthrough desperately needed |
| 🦄 **Unicorn** (独角兽) | Excellence | Viable → optimal solution | Work is merely adequate |
| 🦉 **Owl** (猫头鹰) | Clarity | Activate deep reasoning, step-by-step | Jumping to conclusions too fast |
| 🐬 **Dolphin** (海豚) | Agility | Cross-domain analogy, lateral thinking | Rigid thinking, domain-locked |

> **Note:** Wolf (🐺) and Tiger (🐯) are a unified pair — "two sides of one coin" (一体两面). Wolf eliminates confirmation bias by insisting on evidence; Tiger exposes risks that remain unspoken. They always activate together.

**Reading the graph:** When a node shows 🦈 Shark, the AI has recognized it was guessing without evidence and is now forcing an exhaustive search. When you see 🦁 Lion, the AI was about to retreat and instead chose to concentrate force at the critical juncture.

### The 6 战势 (Battle Levels): Failure-Driven Escalation

PI doesn't just retry on failure — it **escalates**. Each level brings a fundamentally different cognitive strategy:

| Level | Name | Failures | Cognitive Shift | Core Strategy |
|---|---|---|---|---|
| **L1** | 易辙 (Easy Pivot) | 2 | Switch perspective | Change the angle of approach entirely |
| **L2** | 深搜 (Deep Search) | 3 | Root-cause analysis | Exhaustive search with evidence chain |
| **L3** | 系统 (Systematic) | 4 | Holistic system view | System-wide diagnostics, new strategy formulation |
| **L4** | 决死 (Decisive) | 5 | Radical new path | Minimum viable proof in isolated environment |
| **L5** | 截道 (Interception) | 6 | Unconventional methods | Reverse reasoning + cross-domain analogy |
| **L6** | 天行 (Cosmic Move) | 7+ | All archetypes | Full cognitive archetype rotation + external coordination |

**In the visualization**, escalation is immediately visible: nodes change color and grow more intense as battle level increases. Edges between escalation steps are highlighted, so you can trace exactly when and why the AI shifted strategy.

### Node Colors and Edge Meanings

Node border colors are determined by the node's **category**, while outcome is shown as a separate badge:

| Border Color | Category | Typical Content |
|---|---|---|
| 🔵 Blue | `exec` | Tool execution (bash, file edit, etc.) |
| 🟣 Purple | `battle` | Battle escalation point (strategy shift) |
| 🟢 Green | `delivery` | Session completion, final delivery |
| 🟡 Yellow | `interaction` | Human input, prompt submission |
| 🟠 Orange | `team` | Sub-agent start/stop |
| ⚪ Gray | `external` | External event capture |

| Edge Style | Meaning |
|---|---|
| Solid line | Sequential flow (A happened, then B) |
| Dashed line | Failure or skipped transition |
| Thick orange | Battle escalation transition (level increased) |

### Cognitive Modes

The `cognitive_mode` field tells you *how* the AI is thinking, not just *what* it's doing:

| Mode | Function | Analogy |
|---|---|---|
| **Analyst** | Decompose, investigate, find root cause | Detective examining evidence |
| **Architect** | Design structure, plan approach | Engineer drafting blueprints |
| **Executor** | Implement rapidly, ship code | Builder with hammer in hand |
| **Guardian** | Verify, test, protect quality | Quality inspector checking output |
| **Explorer** | Diverge, brainstorm, seek alternatives | Scout surveying unknown territory |
| **Integrator** | Synthesize, reconcile, unify | Diplomat bringing perspectives together |

---

## 5. Real-World Scenarios

### Scenario 1: Debugging a Complex Bug

**Situation:** CI is failing with a flaky test — passes locally, fails in CI 30% of the time.

**What the decision graph reveals:**

```
User: "Fix the flaky CI test in auth.spec.ts"
│
├─ [L1] Scene: 🔧 Debug │ Mode: analyst │ Beast: —
│  ├─ grep auth.spec.ts → found race condition suspect
│  └─ bash: run test locally × 10 → all pass ✅
│
├─ [L2 易辙] failure_count: 2 │ Beast: 🦅 Eagle
│  Strategy: "Survey the landscape — look beyond the test file"
│  ├─ grep: searched for shared state across test suite
│  └─ Found: global DB connection pool shared between tests
│
├─ [L3 深搜] failure_count: 3 │ Beast: 🦈 Shark
│  Strategy: "Surface unsearched depths"
│  ├─ Analyzed: connection pool lifecycle + test isolation
│  ├─ Root cause: pool.end() called in afterAll, but parallel tests reuse pool
│  └─ Fix: per-test connection with afterEach cleanup
│
└─ [L1] Verification │ Beast: — │ outcome: ✅
   ├─ bash: run test × 50 locally → all pass
   └─ bash: CI simulation with --parallel → all pass
```

**The insight:** Without visualization, you'd see "I fixed the flaky test." With visualization, you see the AI correctly identified that the problem wasn't in the test file itself but in shared infrastructure — and you can verify it explored the right path.

### Scenario 2: Multi-Agent Collaborative Development

**Situation:** A feature requires frontend changes, backend API updates, and database migration — three sub-agents work in parallel.

**What the decision graph reveals:**

```
Main Agent: "Implement user preferences feature"
│
├─ [SubagentStart] agent: "backend-api"
│  ├─ Scene: 🖥️ Programming │ Mode: architect
│  ├─ Designed: REST endpoints (GET/PUT /api/preferences)
│  ├─ Implemented: controller + service + validation
│  └─ [SubagentStop] outcome: success │ tokens: 4.2k
│
├─ [SubagentStart] agent: "database-migration"
│  ├─ Scene: 🖥️ Programming │ Mode: executor
│  ├─ Created: migration 20250115_add_preferences_table
│  └─ [SubagentStop] outcome: success │ tokens: 1.8k
│
├─ [SubagentStart] agent: "frontend-ui"
│  ├─ Scene: 🖥️ Programming │ Mode: architect
│  ├─ [L2 易辙] Initial approach failed (wrong component tree)
│  │   Beast: 🦅 Eagle │ "Restructured component hierarchy"
│  ├─ Implemented: PreferencesPanel + usePreferences hook
│  └─ [SubagentStop] outcome: success │ tokens: 5.1k
│
└─ Integration verification │ outcome: ✅
   Total tokens: 11.1k │ Max battle level: 2
```

**The insight:** You can see that the frontend sub-agent hit a problem and self-corrected. The database migration was straightforward. The backend was designed before implemented. This level of visibility is impossible without decision visualization.

### Scenario 3: Exported Data for PI Improvement

After exporting a session's decision data as JSON, you can analyze patterns:

```bash
# Export from the visualizer UI (click Export button)
# Or directly process the JSONL files:

# Find sessions with high battle levels (frequent struggles)
cat ~/.pi/decisions/2025-01-*/session-*.events.jsonl | \
  jq 'select(.battle_level >= 3)' | \
  jq '{scene, battle_level, strategy, outcome}' | head -20

# Count beast activations by type
cat ~/.pi/decisions/2025-01-*/session-*.events.jsonl | \
  jq -r '.payload.beast // empty' | sort | uniq -c | sort -rn
```

**What you discover:** If 🦈 Shark activates frequently in your debugging sessions, it means the AI is often guessing before searching — you might add explicit search instructions to your prompts. If 🐲 Loong (Dragon) appears often, your tasks may be consistently underspecified.

### Scenario 4: Team Retrospective

**Situation:** Your team of 5 developers all use PI. At the weekly retro, you review visualization data together.

**What you learn:**

| Developer | Avg Battle Level | Most Common Beast | Insight |
|---|---|---|---|
| Alice | 1.2 | 🦅 Eagle | Clean, well-scoped tasks; rarely escalates |
| Bob | 3.4 | 🦈 Shark | Tasks often underspecified; needs more upfront search |
| Carol | 2.1 | 🐂 Ox | Tackles hard problems; grit-driven approach |
| Dave | 1.8 | 🦊 Fox | Quality-focused; frequent meta-cognition checks |
| Eve | 4.2 | 🐲 Loong | Working on the hardest problems; may need task decomposition |

**The action:** Eve's consistently high battle levels suggest her tasks could be better decomposed before AI engagement. Bob's frequent Shark activations suggest adding more context to his initial prompts would reduce thrashing.

---

## 6. Advanced Usage

### Live Monitoring Mode

Watch decisions appear in real-time as the AI works:

```bash
# Start the visualizer in live mode (default)
~/.pi/visualize.sh

# Or explicitly:
cd pi/visualize && npm run server
```

In live mode, the visualizer uses WebSocket connections to push updates to your browser instantly. As hooks fire during your AI session, new nodes appear on the canvas without refreshing. This is particularly powerful when:

- Debugging a long-running session and wanting to see the AI's reasoning unfold
- Monitoring a multi-agent orchestration with parallel sub-agents
- Demonstrating PI's cognitive engine to your team in real-time

### Multi-Project Management

If you work across multiple projects, all decision data flows to the same `~/.pi/decisions/` directory. Sessions are automatically tagged with project context.

```bash
# View decisions from a specific project's PI data
npm run server -- --source ~/projects/my-api/.pi/decisions

# View decisions from another project on a different port
npm run server -- --source ~/projects/web-app/.pi/decisions --port 3142
```

### Session Management

The tree navigator (left panel) shows all sessions grouped by date:

- **🟢 Active sessions** — Currently in progress (events arriving within the last 30 minutes)
- **⚪ Inactive sessions** — Completed sessions from past work
- **🗑️ Delete** — Remove sessions you no longer need (right-click or use the context menu)

Session IDs are automatically managed across platforms:

| Platform | Session ID Source |
|---|---|
| Claude Code | `CLAUDE_SESSION_ID` environment variable |
| Copilot CLI | `COPILOT_SESSION_ID` environment variable |
| PI native | `PI_SESSION_ID` environment variable |
| Fallback | TTY + PPID + project root hash (30-minute TTL) |

### Export & Import

**Export** a session for sharing or analysis:

1. Open the session in the visualizer
2. Click the **Export** button in the TopBar
3. A privacy-sanitized JSON file is downloaded automatically

**Privacy protection:** Exported data is automatically sanitized:
- Home paths → `~`
- Project roots → `$PROJECT_ROOT`
- Credentials (passwords, tokens, API keys) → `[REDACTED]`
- Long tokens (20+ chars) → `[REDACTED]`

**Import:** Use the **Import** button in the TopBar to load a previously exported JSON file. The visualizer will parse and display it directly — no need to copy files to disk.

> **Note:** Exported files use `pi-session-*.json` / `pi-archive-*.json` naming. The UI import picker handles these natively.

---

## 7. Best Practices

### 1. The Daily 5-Minute Visualization Review

Build a habit: at the end of each day, spend 5 minutes reviewing your decision graphs.

**What to look for:**

- **Escalation patterns** — Are you frequently hitting L3+? Your tasks may need better scoping.
- **Beast activations** — Which beasts appear most? This reveals your AI interaction style.
- **Failure clusters** — Do failures cluster around specific scenes (debugging? testing?)? Focus improvement there.
- **Token efficiency** — Are some sessions consuming 50k tokens for simple tasks? The graph shows where waste occurs.

### 2. Data-Driven PI Optimization

Use visualization data to refine how you interact with PI:

```
Step 1: Export a week of sessions
Step 2: Analyze battle level distribution
Step 3: Identify top-3 escalation causes
Step 4: Adjust your prompts or task decomposition
Step 5: Compare next week's distribution
```

**Example feedback loop:**
- *Observation:* 60% of debugging sessions escalate to L3+ (Deep Search)
- *Root cause:* Initial prompts lack error messages and reproduction steps
- *Action:* Start including stack traces and `git diff` in debug prompts
- *Result:* L3+ escalation drops to 20% the following week

### 3. Team Collaboration Patterns

**Shared visualization reviews** help teams align on AI usage:

- **Pair programming with visibility** — One developer works with AI, another watches the decision graph. The observer catches when the AI goes off-track.
- **PR review enhancement** — Attach the decision graph export to PRs. Reviewers see not just *what* changed, but *how the AI arrived at the changes*.
- **Onboarding** — New team members explore mock sessions to understand PI's cognitive framework before using it on real tasks.

### 4. Identifying Escalation Anti-Patterns

Watch for these warning signs in your decision graphs:

| Anti-Pattern | What It Looks Like | What to Do |
|---|---|---|
| **Premature escalation** | L3+ reached with only 1 failure | Task may be too vague — add more context |
| **Stalled escalation** | Multiple failures at L1, no escalation | Hooks may not be firing — check installation |
| **Infinite loop** | Same strategy repeated across 5+ nodes | The AI is stuck — intervene manually with a `/pi` command |
| **Beast mismatch** | 🐎 Horse (speed) on a complex architecture task | Task classification may be wrong — reframe the prompt |

---

## 8. FAQ

### Data Security & Privacy

**Q: Where is my decision data stored?**
A: Locally on your machine at `~/.pi/decisions/`. Nothing is sent to any external server. The visualizer runs entirely on `localhost:3141`.

**Q: What about sensitive code in the captured data?**
A: All data passes through `sanitize_text()` before storage. This function:
1. Replaces your home directory with `~`
2. Replaces project root with `$PROJECT_ROOT`
3. Redacts credential flags (`--password`, `--token`, `--api-key`, `--secret`, `--auth`)
4. Redacts key-value secrets (`token=...`, `password=...`, `api_key=...`, `client_secret=...`)
5. Masks long tokens (20+ alphanumeric characters) as `[REDACTED]`
6. Masks sensitive path patterns (`/Users/username`, `/home/username`)

**Q: Can I disable data capture entirely?**
A: Yes. Remove or comment out the hook entries in your platform's configuration file (e.g., `hooks.json` for Claude Code, or the corresponding rules for Cursor/Kiro).

### Supported Platforms

**Q: Does this work with GPT / ChatGPT / other LLMs?**
A: PI visualization works with any AI tool that supports PI's hook system. Currently, Claude Code, Copilot CLI, Cursor, Kiro, and Qoder have native integrations. For other tools, use `capture-generic.sh` to manually emit events.

**Q: What about VS Code with Copilot (not CLI)?**
A: The GitHub Copilot VS Code extension doesn't yet support PI hooks natively. Use the Copilot CLI integration or Cursor for full visualization support.

### Troubleshooting

**Q: I see no data in the visualizer!**
A: Try these steps in order:
1. Check if hooks are installed: `ls ~/.pi/decisions/` — any files there?
2. Generate sample data: `npm run start:mock` — does mock mode work?
3. Check hook configuration: verify your platform's hook/rule files are in place
4. Check permissions: `ls -la ~/.pi/decisions/` — is the directory writable?
5. Check recent events: `ls -lt ~/.pi/decisions/*/*.events.jsonl | head -5`

**Q: The visualizer won't start!**
A: Ensure you have Node.js (v18+) and npm installed. Then:
```bash
cd pi/visualize
npm install
npm run build
npm run server
```

### Storage Management

**Q: How much disk space does decision data use?**
A: Typically 10–50 KB per session. Even heavy users (50+ sessions/day) would accumulate less than 100 MB per month.

**Q: How do I clean up old data?**
A: Delete date directories you no longer need:
```bash
# Remove data older than 30 days
find ~/.pi/decisions/ -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +
```

### Technical Details

**Q: What tech stack does the visualizer use?**
A:

| Component | Technology | Version |
|---|---|---|
| Frontend Framework | React | 19 |
| Graph Visualization | React Flow (@xyflow/react) | 12 |
| Styling | Tailwind CSS | 3.4 |
| Bundler | Vite | 6 |
| Server | Express | 4 |
| Real-time Updates | WebSocket (ws) | 8 |
| State Management | Zustand | 5 |
| File Watching | Chokidar | 4 |

**Q: Can I customize the visualizer?**
A: Yes. The visualizer is a standard React application in the `visualize/` directory. Fork it, modify components, add custom node renderers — it's all open source under the Apache 2.0 License.

---

## Further Reading

- **[README.en.md](../README.en.md)** — PI overview, installation guide, and platform support
- **[Why PI Works](WHY_PI_WORKS.en.md)** — The design philosophy behind PI's cognitive engine
- **[Why the Compiler](WHY_COMPILER.en.md)** — How PI compiles skills across platforms
- **[Design Philosophy](DESIGN_PHILOSOPHY.en.md)** — When *The Art of War* meets cognitive science
- **[PI Visualize Quick Reference](../PI_VISUALIZE_QUICK_REFERENCE.md)** — Technical quick-lookup table (Chinese)
- **[PI Visualize Analysis](../PI_VISUALIZE_ANALYSIS.md)** — Deep architectural analysis (Chinese)

---

> *"善战者之胜也，无智名，无勇功。"*
>
> *"The victories of the skillful commander are neither the product of brilliance nor the result of courage — they come from inevitability."*
> — *The Art of War*
>
> With PI Decision Visualization, every decision becomes visible. Every strategy becomes traceable. Every victory becomes reproducible. This is the path from guessing to knowing — from the black box to the crystal ball.
