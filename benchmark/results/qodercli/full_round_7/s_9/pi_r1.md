# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pi | Run: 1
## Duration: 62.91s

---

Now I have a comprehensive view. Let me compile the full audit report with all 7 sections.

---

## 🧠 PI · Training Pipeline End-to-End Audit Report

---

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **GRPOTrainer not implemented** — raises `NotImplementedError` when called | `trainer.py:300-312` | 🔴 Blocker |
| 2 | **Dataset validation missing** — no schema/field validation before training | `trainer.py:146-156` | 🔴 Blocker |
| 3 | **Random seed not set for data shuffle** — `random.shuffle()` without seed in data_loader | `data_loader.py:222` | 🔴 Blocker |
| 4 | **Hardcoded absolute paths in presets** — `/data/guwen/`, `/models/guwen-llm/` won't exist on most machines | `config_builder.py:100-102` | 🟡 High |
| 5 | **Example file contains stale/broken code** — commented-out removed fields, will mislead users | `example_usage.py:32-34` | 🟡 High |
| 6 | **No checkpoint resume support** — `save_steps` configured but no resume logic | `trainer.py:87-89, 134-179` | 🟡 High |
| 7 | **Perplexity computation uses wrong text field** — evaluates on `output` only, ignores instruction context | `evaluator.py:247-248` | 🟡 High |
| 8 | **Label masking logic incorrect** — masks by instruction length but doesn't account for assistant prefix | `data_loader.py:109-117` | 🟡 High |
| 9 | **Unused imports** — `os`, `json` imported in trainer.py but never used | `trainer.py:21-22` | ⚪ Low |
| 10 | **Unused instance variable** — `self.results` in Evaluator never updated after evaluate() | `evaluator.py:60, 128` | ⚪ Low |

---

### 2. Hidden Issues

| # | Issue | Category | Location |
|---|-------|----------|----------|
| 1 | **Security: `trust_remote_code=True` by default** — allows arbitrary code execution from HuggingFace models | 🔒 Security | `trainer.py:49`, `evaluator.py:66,71` |
| 2 | **Resource leak: File handles not closed on error** — `_read_jsonl()` uses bare `with` but exceptions mid-read leave state unclear | 📦 Resource | `data_loader.py:238-247` |
| 3 | **Memory explosion: No max_length enforcement during tokenization** — samples exceeding `max_seq_length` truncated AFTER tokenization | ⚡ Performance | `data_loader.py:96-102` |
| 4 | **Division by zero risk** — `total_tokens` could be 0 if eval_data is empty | ⚠️ Edge Case | `evaluator.py:257` |
| 5 | **Thread safety: `random.shuffle()` not seeded** — different results across runs even with same config.seed | 🧵 Thread Safety | `data_loader.py:222` |
| 6 | **Silent failure: Empty samples raise ValueError** — `if not samples` check at line 217, but empty JSONL file silently produces empty list | ⚠️ Edge Case | `data_loader.py:216-218` |
| 7 | **Cross-platform: Hardcoded POSIX paths** — `/data/guwen/` won't work on Windows | 🖥️ Cross-Platform | `config_builder.py:100-102` |
| 8 | **Configuration drift: Presets don't match TrainingConfig defaults** — preset batch_size=4 vs default batch_size=4 (ok), but lora_target_modules not overridable via preset | ⚙️ Configuration | `trainer.py:61-63`, `config_builder.py:26-62` |
| 9 | **Missing gradient accumulation warmup** — first few steps have unstable gradients with high accumulation | ⚡ Performance | `trainer.py:260-261` |
| 10 | **No early stopping** — training runs full epochs regardless of eval loss | ⚡ Performance | `trainer.py:255-278` |
| 11 | **BLEU score edge case** — returns 0.0 for empty predictions but doesn't warn | ⚠️ Edge Case | `evaluator.py:155-156` |
| 12 | **ROUGE import swallowed** — ImportError logged but evaluation continues silently | ⚠️ Error Handling | `evaluator.py:236-238` |

---

### 3. Root Cause

| Issue | Root Cause Analysis |
|-------|---------------------|
| **GRPOTrainer incomplete** | Initially I thought this was intentional stub code. Upon closer inspection, the class has placeholder attributes (`_reward_model`, `_ref_model` never initialized) and the `train()` method explicitly raises `NotImplementedError`. This is incomplete feature creep — GRPO was planned but never delivered. |
| **Dataset validation missing** | Actually, the root cause is architectural: `Trainer.train()` loads dataset directly via `_load_dataset()` at `trainer.py:156` without any intermediate validation layer. The `ConfigBuilder.validate()` exists but is never called by `Trainer`. |
| **Random seed not set** | Initially I assumed the seed from `TrainingConfig.seed:92` would propagate. Actually, `random.shuffle()` at `data_loader.py:222` uses Python's global random state, which is never seeded. The training seed only affects PyTorch operations. |
| **Hardcoded paths** | The presets in `config_builder.py:26-62` were designed for a specific deployment environment (`/data/guwen/`). These are not parameterized and `from_preset()` applies them via `setdefault()` at lines 100-102, making overrides awkward. |
| **Label masking incorrect** | The logic at `data_loader.py:109-117` counts instruction tokens but doesn't account for the `
