# Scenario 9: Training Pipeline End-to-End Audit
## Condition: nopua | Run: 2
## Duration: 118.88s

---

## Training Module Production Readiness Audit

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Dead code in `main()`** - `resume` parameter defined but never used | High | `trainer.py:326-331` |
| 2 | **Unused instance attributes** - `self._model`, `self._tokenizer`, `self._trainer` assigned but never read | Medium | `trainer.py:120-122` |
| 3 | **Stale example code** - `example_usage.py` documents removed fields (`use_flash_attention`, `data_format`) that will cause `TypeError` | High | `example_usage.py:27-57` |
| 4 | **Misleading docstring** - Module docstring claims ShareGPT/raw text support, but only instruction format is implemented | Medium | `data_loader.py:6-9` |
| 5 | **Incomplete GRPO trainer** - `_reward_model` and `_ref_model` declared but never initialized; `train()` raises `NotImplementedError` | Medium | `trainer.py:291-317` |
| 6 | **No checkpoint resume logic** - Config has `save_steps`/`save_total_limit` but no resume mechanism despite CLI offering `--resume` flag | High | `trainer.py:80-89, 326` |
| 7 | **Dataset not validated before training** - No schema validation, empty sample checks, or token length verification | High | `trainer.py:146-150` |
| 8 | **Unused imports** - `os`, `json` imported in `trainer.py` but never used | Low | `trainer.py:21-22` |
| 9 | **Hardcoded paths in presets** - `/data/guwen/...` and `/models/guwen-llm/...` don't exist on most machines | Medium | `config_builder.py:98-100` |
| 10 | **Perplexity computed on output only** - Ignores instruction context, gives artificially optimistic scores | Medium | `evaluator.py:240-258` |

---

### 2. Hidden Issues Beyond the Ask

| # | Hidden Issue | Impact |
|---|--------------|--------|
| H1 | **Label masking bug** - `instruction_tokens` shape calculation doesn't account for special tokens or template overhead, causing incorrect loss masking | Model trains with wrong gradient signals |
| H2 | **Race condition in data splitting** - `random.shuffle()` without fixed seed makes train/eval split non-reproducible | Cannot reproduce eval results across runs |
| H3 | **Memory leak risk** - `InstructionDataset` stores all tokenized samples in `self._data` without lazy loading; large datasets will OOM | Training fails on large datasets |
| H4 | **BLEU implementation ignores reference length edge case** - Division by zero when prediction is empty but reference isn't | Crashes on empty predictions |
| H5 | **SFTTrainer receives wrong dataset format** - Trainer passes `dataset_text_field="text"` but dataset provides `input_ids/attention_mask/labels` dict | SFTTrainer may fail or ignore pre-tokenized data |
| H6 | **No gradient accumulation warmup** - First few steps have unstable gradients when using `gradient_accumulation_steps > 1` | Training instability at start |
| H7 | **Evaluator loads model in bf16 without fallback** - Will crash on GPUs without bf16 support | Evaluation fails on older GPUs |
| H8 | **ConfigBuilder.validate() checks dataset existence but trainer never calls it** - Validation exists but is unused | Users discover missing datasets at training start, not config time |

---

### 3. Root Cause Analysis

**Primary Root Causes:**

1. **Incremental refactoring without cleanup** - The codebase evolved from v0.2 to v0.4 (per comments) but dead code, stale examples, and removed features were never cleaned up. This created documentation-code mismatches.

2. **Missing integration testing** - Individual components may work in isolation, but the integration points are broken:
   - `main()` declares `--resume` but `Trainer.train()` has no resume logic
   - `GRPOTrainer` exists but is a stub
   - Dataset validation exists in `ConfigBuilder` but isn't called by `Trainer`

3. **Assumption-driven development** - Code assumes:
   - Datasets always have correct schema
   - GPUs always support bf16
   - Users always override hardcoded paths
   - Token counts match between instruction and full sample

4. **Incomplete feature implementation** - Features were started but not finished:
   - Resume functionality (CLI flag added, implementation forgotten)
   - GRPO training (class skeleton only)
   - Multiple data formats (docstring claims support, code only handles one)

---

### 4. Recommended Fixes

#### P0 (Blocking Production Use)

| Fix | Files | Description |
|-----|-------|-------------|
| **F1** | `trainer.py` | Remove `--resume` CLI option OR implement checkpoint resume using `TrainingArguments.resume_from_checkpoint` |
| **F2** | `trainer.py:134-179` | Add dataset validation: check required fields, validate sample count, verify token lengths |
| **F3** | `trainer.py:162-170` | Fix SFTTrainer integration - either pass raw dataset with `dataset_text_field` OR remove and use custom training loop with pre-tokenized data |
| **F4** | `example_usage.py` | Delete or update to reflect current API (remove references to removed fields) |

#### P1 (High Priority)

| Fix | Files | Description |
|-----|-------|-------------|
| **F5** | `data_loader.py:221-222` | Add `random.seed(42)` before shuffle for reproducibility |
| **F6** | `config_builder.py:98-100` | Change hardcoded paths to relative defaults or environment variables |
| **F7** | `trainer.py` | Remove unused imports (`os`, `json`) and instance attributes (`self._model`, etc.) |
| **F8** | `evaluator.py:240-258` | Fix perplexity to compute over full prompt+response, not just response |

#### P2 (Medium Priority)

| Fix | Files | Description |
|-----|-------|-------------|
| **F9** | `data_loader.py` | Either implement ShareGPT/raw format support or remove from docstring |
| **F10** | `trainer.py:291-317` | Either implement GRPO trainer or remove the stub and update module exports |
| **F11** | `data_loader.py:76-88` | Implement lazy tokenization or warn about memory usage for large datasets |
| **F12** | `config_builder.py` | Call `validate()` in `Trainer.__init__()` and fail fast on invalid configs |

---

### 5. Steps Taken

1. **Read all 6 source files** in the training module to understand architecture
2. **Searched for field references** (`use_flash_attention`, `data_format`) to verify API changes
3. **Cross-referenced docstrings with implementations** to find mismatches
4. **Traced data flow** from config → dataset → trainer → evaluation
5. **Identified dead code** by tracking variable usage throughout files
6. **Annotated inline comments** left by developers (e.g., lines 87-89, 146-150 in trainer.py)
7. **Compared claimed features** (module docstrings) vs actual implementation

---

### 6. Tools Used

- **File reading**: Read all 6 Python files in full
- **Pattern search**: Grep for specific field names and removed features
- **Glob**: Located all training module files across the project
- **Manual code tracing**: Followed variable assignments, method calls, and data flow

---

### 7. Verification

**Findings verified by direct code evidence:**

| Finding | Verification Method |
|---------|---------------------|
| `resume` unused | Read `trainer.py:326` (CLI defines it) → `trainer.py:134-179` (train() never reads it) |
| Dead attributes | Read `trainer.py:120-122` (assignment) → searched entire file (no reads) |
| Stale examples | Read `example_usage.py:27-57` → compared with `trainer.py:43-95` (TrainingConfig fields) |
| Missing validation | Read `trainer.py:156` (`_load_dataset()`) → no schema/field checks present |
| Label mask bug | Read `data_loader.py:109-117` → instruction token count doesn't include template overhead |
| Non-reproducible split | Read `data_loader.py:221-222` → `random.shuffle()` without seed |

**Not verified by execution:**
- Did not run training pipeline (requires GPU + dataset)
- Did not run unit tests (none found in project structure)
- Did not validate BLEU/ROUGE math (assumed correct formula, noted edge cases)

---

### Summary Assessment

**Production Readiness: NOT READY**

The training module has **4 blocking issues** (P0) that would cause real failures:
1. Resume flag does nothing (silent data loss if training interrupted)
2. No dataset validation (crashes mid-training on bad data)
3. SFTTrainer integration mismatch (may silently ignore pre-tokenized data)
4. Example code crashes if copied (removed fields cause TypeError)

**Recommendation:** Block production use until P0 fixes are complete. P1/P2 fixes can follow in next iteration.
