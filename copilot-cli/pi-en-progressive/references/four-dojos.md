## 4. Four Dao United

The four Dao share the "Four Directives + Three Rules" cognitive structure. Four Directives = mandatory cognitive checkpoints; Three Rules = mandatory action principles.

### 4.1 Coding Domain 🖥️

**Coding Four Directives** (mandatory before writing any module):

| # | Directive | Effect |
|---|-----|------|
| I | Analyze · essence | Start from constraints, not from existing solutions |
| II | Anchor · constraints | Lock QPS/latency/consistency/budget and other hard constraints |
| III | Calibrate · naming | Calibrate class/function names to match explainable business "usage" |
| IV | Define · acceptance | Define correctness through test cases and acceptance criteria |

**Naming Three Rules**:
1. **Don't model what you don't understand** — if the business is unclear, don't invent terms in code
2. **One term, one meaning** — eliminate ambiguity, reduce noise
3. **Align terms before debating** — first unify terminology, then discuss solutions

**Debug Six Steps**:

| Step | Directive | Effect |
|----|-----|------|
| I | **Read failure** | Read failure report verbatim, no skipping, no guessing |
| II | **Delimit** | Narrow scope: which line, which module, which condition |
| III | **Trace** | Track data flow: input→transform→output, where did mutation occur |
| IV | **Compare** | Find a working case, compare differences item by item |
| V | **Verify hypothesis** | Change only one variable per verification |
| VI | **Fortify** | Fix + add regression guard (test/assertion/log) |

**Code Review Four Dimensions**: 🔒Security (injection/leak/privilege escalation) · ⚡Performance (O(n²)/leak/wasted queries) · 📖Readability (naming/structure/intent) · ✅Correctness (edge cases/error handling/concurrency)

**Refactoring Principles**: When (rule of three/ripple effects/future-reader confusion) → How (tests first/small steps/don't mix refactor with features)

**Architecture Decision Tree**: Requirements + constraints → current system satisfies → don't change / doesn't satisfy → list candidates (≤3) → evaluate against constraints → pick simplest; tie-break by team familiarity

**Tech Debt**: Identify (`// TODO: tech-debt`) → Assess (impact × frequency) → Repay (alongside feature iterations)

**Commit-per-win** (commit immediately after each win, secure gains, leave no unsecured ground):
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

### 4.2 Testing Domain 🧪

**Testing Four Directives** (mandatory before designing any test):

| # | Directive | Effect |
|---|-----|------|
| I | Anchor · objective | Lock core value and expected behavior |
| II | Delimit · boundaries | List input/state/timing boundaries |
| III | Define · expectation | "Given X → should get Y" format |
| IV | Analyze · failure | Each failure points precisely to one cause |

**QA Three Rules**:
1. **Test before code** — write test descriptions of expectations first, then implement (TDD spirit)
2. **Boundaries first** — 80% of defects lurk at boundaries; boundaries > happy path
3. **Guard against regression** — every fixed bug must have a regression test, never repeat the same mistake

**Verification Six Steps**: Define (Testing Four Directives) → Design (equivalence partitioning + boundary values + exception paths) → Implement (independent, repeatable) → Execute (record results) → Analyze (distinguish code bug from test bug) → Fortify (integrate into CI/CD)

**Test Strategy Selection**:
| Level | When to use | Coverage |
|------|----------|--------|
| Unit tests | Core business logic, algorithms | ≥90% |
| Integration tests | API boundaries, inter-service calls | Critical paths |
| E2E tests | Core user flows | Main flow + exception flows |
| Manual testing | Exploratory testing, UX verification | Targeted |

### 4.3 Product Domain 📊

**Product Four Directives** (mandatory before any product decision):

| # | Directive | Effect |
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

### 4.4 Ops Domain 📈

**Ops Four Directives** (mandatory before any ops action):

| # | Directive | Effect |
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

| Domain | Quality Standard | Verification Method |
|------|---------|---------|
| 🖥️ Coding | Compiles + tests green + Code Review 4D no red flags | build/test output |
| 🧪 Testing | Boundaries covered + independent repeatable + failure pinpoints cause | Test report |
| 📊 Product | Pain point quantifiable + solution minimal + metrics measurable | Data/user feedback |
| 📈 Ops | Experiment measurable + success criteria clear + feedback loop | Experiment card |

---

