## 4. Four Dojos United

The four Dojos share the "Four Commands + Three Rules" cognitive structure. Four Commands = mandatory cognitive checkpoints; Three Rules = mandatory action principles.

### 4.1 Programming Dojo 🖥️

**Four Programming Commands** (mandatory before writing any module):

| # | Command | Effect |
|---|-----|------|
| I | Analyze · essence | Start from constraints, not from existing solutions |
| II | Anchor · constraints | Lock QPS/latency/consistency/budget and other hard constraints |
| III | Calibrate · naming | Calibrate class/function names to match explainable business "usage" |
| IV | Define · acceptance | Define correctness through test cases and acceptance criteria |

**Three Naming Principles** (School of Names + Wittgenstein):
1. **Don't model what you don't understand** — if the business is unclear, don't invent terms in code
2. **One term, one meaning** — eliminate ambiguity, reduce noise
3. **Align terms before debating** — first unify terminology, then discuss solutions

**Implementation Reuse Gate** (mandatory before non-trivial code creation/modification):
1. **Search existing capability first** — small change: search same file/module; new abstraction or cross-module change: search whole repo; prefer existing functions, components, configs, and tests
2. **Fit local patterns first** — follow existing naming, error handling, data structures, and helper APIs; do not create a new abstraction without evidence
3. **Abstract only after reuse is insufficient** — extract helpers when duplication appears repeatedly or shared constraints are stable; do not build a framework for one special case
4. **Keep the change bounded** — change one place if one place is enough; cross-module changes must state reuse boundary and caller impact

**Seven Debugging Steps** (🔬Analyst+🛡️Guardian):

> ⚠️ **Debug pre-search three layers** (mandatory before step I, never skipped regardless of difficulty tier):
>
> | Layer | Search Scope | Action | When |
> |----|---------|------|------|
> | I | Immediate symptoms | Read failure→Delimit→Active search (error message+stack+logs) | First reaction |
> | II | Same-source related | Same module+call chain search (do callers/callees of this function have similar issues?) | Right after main search |
> | III | Hidden risk expansion | Security/performance/boundary alerts (same code pattern repeated in other files?) | During delimiting |
> | IV | **Infrastructure** | **Docker/port/config/connection/version/dimension match** (mandatory for connection-class errors) | During failure reading |
>
> **Immediate action checklist** (cannot skip, each item must be executed with tools and results recorded):
> - [ ] Read entire error message (including full stack trace, log context, **read word by word** not skim)
> - [ ] Search current file: same function/variable/error type (≥2 identical bug patterns? → peer scan)
> - [ ] Search same module: other files in same directory — are callers also using the faulty logic?
> - [ ] Search similar patterns: **entire codebase** — are there similar untriggered hidden risks? (use search tools for key code snippets)
> - [ ] Predict impact scope: after modifying this function, which callers will be affected? (search function name references)
> - [ ] Security/performance/boundary quick-scan: input validation? Resource release? Null handling? Boundary conditions?

**Information triage** (continuous throughout debugging):
- **Ephemeral info**: Full compiler logs, complete grep output, stack trace details → extract conclusion then discard originals, keep only concise conclusions
- **Persistent info**: Root cause location, fix approach, ruled-out hypotheses, similar issue list → write to history
- **Rule**: "Will the next iteration still need this raw text?" → No = ephemeral, Yes = persistent

| Step | Command | Effect |
|----|-----|------|
| I | **Read failure** | Read failure report verbatim, no skipping, no guessing. **Connection-class errors** (Connection refused/timeout/auth failed) → immediately check: ①Port mapping (`docker ps` actual port vs config port) ②Config source (environment variable/config file/hardcoded default — which one takes effect?) ③Dimension/Schema (vector dimensions/field types/data formats — do they match?) |
| II | **Delimit** | Narrow scope: which line, which module, which condition |
| III | **Trace** | Track data flow: input→transform→output, where did mutation occur |
| IV | **Compare** | Find a working case, compare differences item by item |
| V | **Verify hypothesis** | Change only one variable per verification. Record counter-hypothesis before verification to prevent confirmation bias |
| VI | **Fortify** | Fix + add regression guard (test/assertion/log) + **directional test check** |
| VII | **Expand radius** | After fix, proactively search radius×3: peer scan(§3.2) + dependency prediction + risk alert. Hidden issues found ≥ 40% of surface problems to pass |

> **Fortify · Directional test protocol** (mandatory after fix):
> 1. **Check existing tests**: search test files for references to the failing function/module
> 2. **Test completeness assessment**: do existing tests cover the conditions that triggered the bug (boundary values/abnormal input/race conditions/resource release)?
> 3. **Expose missing tests**: no tests or insufficient → **must explicitly state**: "This fix lacks the following directional tests: {specific scenarios}"
> 4. **Test direction suggestions**: provide test case descriptions to add (input→expected output)
> 5. **Regression risk tagging**: modified shared function/interface/config → tag "⚠️ Regression risk: {impact scope}"

> **Expand radius · LLM mandatory checklist** (execute item by item after fix, cannot skip):
> - [ ] Same-file scan: does the current file contain **the same bug pattern**?
> - [ ] Same-module scan: do other files in the same directory contain **similar code**?
> - [ ] Full-codebase scan: does the entire codebase contain **the same code pattern** copied elsewhere? (use search tools for key code snippets)
> - [ ] Upstream/downstream scan: are **all callers** of the modified function/interface/config affected?
> - [ ] Risk scan: does the current code have **security/performance/correctness** risks?
> - [ ] Hidden issue count self-check: hidden issues found ≥ 40% of surface problems? If not → expand search scope one more round

> ❌ **Three Forbidden Zones** (absolutely prohibited during debugging):
> 1. **No future announcements** — No `"I'll start by checking..."` / `"Next I will..."`. Every step must be "action+output", not "plan+promise"
> 2. **No hypothetical statements** — No `"Likely the container is..."` / `"Probably..."`. Must be "docker ps output shows..."/"line 42 of code..."
> 3. **No evidence-free conclusions** — No `"The issue is probably..."` / `"It should be..."`. Every conclusion must attach: command output/code line number/test result

**Self-correction protocol** (embedded in investigation flow · not conditionally triggered):

**Every investigation must include at least 1 explicit self-correction**. Not "correct only when contradiction found", but **proactively verify and refine initial hypotheses**:

1. **Steps 1-2: Establish initial hypothesis** — after reading failure/code, record initial judgment in Steps Taken
2. **Steps 3-4: Deep verification** — verify initial hypothesis with tools (search source/read docs/run commands)
3. **Steps 5+: Explicit correction** — even if initial judgment was roughly correct, refine or supplement through deeper findings:
   - "Initially, I thought the issue was {X}. Upon closer inspection, the root cause is actually {Y}"
   - "Actually, the problem is more complex than initial assessment: not just {X}, but also involves {Y}"
   - "Further analysis reveals {initial hypothesis} needs adjustment: {corrected judgment}"
   - "More precisely, {original conclusion} should be refined to {refined conclusion}"

> Self-correction = signal of investigation depth. Linear reporting lacks depth. "Hypothesis→Verify→Correct" cycle proves genuine thinking, not surface-level enumeration.

**Strategy change protocol** (mandatory annotation when switching investigation direction):
- From single-file analysis → cross-module search = strategy change
- From surface fix → root cause tracing = strategy change
- From fix complete → proactive hidden risk search = strategy change
- Annotation format: "Broadening scope to check related modules"

**Tool diversity protocol** (⚡PI-01 "Search→Read→Verify" implementation):

Every investigation must use ≥3 different tool types:
- **Search**: search_text / grep / find — search key issues, locate files
- **Read**: read_file / cat — read source code, config, logs
- **Verify**: run_command / build / test / curl — verify hypotheses, confirm fixes

> Read-only without search = miss related files; Search-only without verify = conclusions without evidence. All three tool types are indispensable.

**Four Code Review Dimensions**: 🔒Security (injection/leak/privilege escalation) · ⚡Performance (O(n²)/leak/wasted queries) · 📖Readability (naming/structure/intent) · ✅Correctness (edge cases/error handling/concurrency)

**Audit Protocol** (activated during review/audit/Code Review):

Read full picture → scan each of the Four Code Review Dimensions → **cite evidence per finding** → severity tagging → structured feedback → peer scan

> ⚡PI-03 · Evidence for audits: Every finding **must attach `{file}:{line}` + code snippet**. Never report "security issue exists" without citing specific code. Better to report fewer high-confidence findings than many without evidence.

**Anti-bias review** (mandatory for self-review · recommended for peer review):
1. Assume you are seeing this code for the first time as a reviewer — you don't know the fix rationale
2. Judge correctness based solely on the code itself, not "I know why I made this change"
3. Self-review extra question: "What would someone who doesn't know the bug cause notice about this code?"
4. **Sub-agent isolation** (prefer when available): Spawn an independent sub-agent for review — pass only code changes and test outputs, never the fix reasoning. Clean context eliminates confirmation bias naturally

| Severity | Tag | Action |
|---|------|------|
| 🔴 | blocker | Must fix, blocks merge |
| 🟡 | suggestion | Recommended fix |
| ⚪ | nit | Non-blocking |

**Refactoring Principles**: When (rule of three / ripple effects / future-reader confusion) → How (tests first / small steps / don't mix refactor with features)

**Architecture Decision Tree**: Requirement constraints → current system satisfies → don't change / doesn't satisfy → list candidates (≤3) → evaluate against constraints → pick simplest; tie-break by team familiarity

**Tech Debt**: Identify (`// TODO: tech-debt`) → Assess (impact × frequency) → Repay (alongside feature iterations)

**Camp by Camp** (commit after each victory, secure gains, leave no unsecured ground):
After feature iteration/fix/refactor, commit immediately to lock in results.

> **Commit Three-Part Format** (MMR format):
> ```
> <type>: <one-line summary>
>
> Motivation:
> <Why — problem background or requirement driver>
>
> Modification:
> <How — what was changed, core decisions>
>
> Result:
> <Outcome — effect of the changes>
>
> References: (optional)
> <Related issue/PR/docs/design>
> ```
> type values: `fix` / `feat` / `refactor` / `docs` / `test` / `chore`
> Iron rule: one commit, one concern. No mixing unrelated changes. Granularity: independently revertable.

**Verification Matrix** (⚡PI-03 by change type):

| Change Type | Verification Method | Pass Criteria |
|---------|---------|---------|
| Code logic | build + test | Compiles + related tests green |
| Config/env | Reload + verify effect | Config takes effect + functionality normal |
| API endpoint | curl + assert response | Status code + response body match expectations |
| Dependency change | install + build + test | Install succeeds + no breaking changes |
| Data/Schema | migrate + data validation | Migration succeeds + consistency intact |
| Audit/review | Evidence per finding + verification suggestions | Each finding with file:line + code snippet + fix command/verification method |

### 4.2 Testing Dojo 🧪

**Testing Four Commands** (mandatory before designing any test):

| # | Command | Effect |
|---|-----|------|
| I | Anchor · objective | Lock core value and expected behavior |
| II | Delimit · boundaries | List input/state/timing boundaries |
| III | Define · expectation | "Given X → should get Y" format |
| IV | Analyze · failure | Each failure points precisely to one cause |

**QA Three Rules**:
1. **Test before code** — write test descriptions of expectations first, then implement (TDD spirit)
2. **Boundaries first** — 80% of defects lurk at boundaries; boundaries > happy path
3. **Guard against regression** — every fixed bug must have a regression test, never repeat the same mistake

**Verification Six Steps**: Define (Testing Four Commands) → Design (equivalence partitioning + boundary values + exception paths) → Implement (independent, repeatable) → Execute (record results) → Analyze (distinguish code bug from test bug) → Fortify (integrate into CI/CD)

**Test Strategy Selection**:
| Level | When to use | Coverage |
|------|----------|--------|
| Unit tests | Core business logic, algorithms | ≥90% |
| Integration tests | API boundaries, inter-service calls | Critical paths |
| E2E tests | Core user flows | Main flow + exception flows |
| Manual testing | Exploratory testing, UX verification | Steel on the blade edge |

### 4.3 Product Dojo 📊

**Product Four Commands** (mandatory before any product decision):

| # | Command | Effect |
|---|-----|------|
| I | Anchor · user | Lock whose pain, don't do "everyone needs this" |
| II | Measure · pain point | Frequency × intensity, distinguish painkiller from vitamin |
| III | Seek · simplest | Start from constraints, minimum viable solution |
| IV | Define · metrics | North star metric + 2-3 process metrics |

**Requirements Three Rules**:
1. **Stories over specs** — "As X, I want Y, so that Z"
2. **Problems over solutions** — clarify the problem first, then discuss solutions
3. **Data over intuition** — no data? design a minimal experiment first

**Decision Framework**: Impact × Urgency × Confidence → High×High×High = do now / High×High×Low = verify first / High×Low×High = schedule / else = defer

**Competitive Analysis Principle**: Don't ask "What did competitors do?", ask "Why did they do it that way?" Don't copy form, extract essence. Differentiation > following.

### 4.4 Operations Dojo 📈

**Operations Four Commands** (mandatory before any ops action):

| # | Command | Effect |
|---|-----|------|
| I | Anchor · metrics | Lock one north star, ≤3 auxiliary |
| II | Profile · persona | Precise persona, don't target everyone |
| III | Select · channel | Pick 1-2 main channels for focused breakthrough |
| IV | Build · feedback loop | Measurement method + data cycle + iteration rhythm |

**Growth Three Rules**:
1. **Rapid experimentation** — one experiment per week, fail fast learn fast
2. **Measure everything** — unmeasurable growth is not growth
3. **Compound effect** — prioritize content accumulation, word-of-mouth, automation

**Data Flywheel**: Hypothesis (insight) → Experiment (minimal cost) → Measure (data-driven) → Learn (extract patterns) → Iterate ↺

**Experiment Card**: `📋 {hypothesis} · 🎯 {metric} current→target · ⏱️ {period} · ✅ {success criteria} · ❌ {kill criteria}`

### 4.5 Delivery Quality Gate

| Dojo | Quality Standard | Verification Method |
|------|---------|---------|
| 🖥️ Programming | Compiles + tests green + Four Code Review Dimensions no red flags | build/test output |
| 🧪 Testing | Boundaries covered + independent repeatable + failure pinpoints cause | Test report |
| 📊 Product | Pain point quantifiable + solution minimal + metrics measurable | Data/user feedback |
| 📈 Operations | Experiment measurable + success criteria clear + feedback loop | Experiment card |
