# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pua | Run: 1
## Duration: 58.23s

---

## Training Pipeline End-to-End Audit — Structured Summary

### 1. Issues Found (Critical → Low Priority)

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **No checkpoint resume support** — Training cannot resume from interruptions; `resume` CLI option is ignored | Critical | `trainer.py:326`, `trainer.py:134-179` |
| 2 | **No data validation before training** — Dataset loaded without checking required fields, empty samples, or tokenized length overflow | Critical | `trainer.py:146-150`, `trainer.py:238-253` |
| 3 | **GRPO trainer is non-functional stub** — `GRPOTrainer.train()` raises `NotImplementedError`; reward/ref models never initialized | Critical | `trainer.py:291-317` |
| 4 | **Hardcoded absolute paths in presets** — `/data/guwen/training_v2.jsonl`, `/models/guwen-llm/checkpoints` will fail on most machines | High | `config_builder.py:100-102` |
| 5 | **Stale example file with removed features** — References to `use_flash_attention`, `data_format`, `wandb_project` that no longer exist | High | `example_usage.py:22-34` |
| 6 | **Label masking logic is incorrect** — Masks by instruction token count, but ChatML template adds system/user tokens not counted | High | `data_loader.py:108-117` |
| 7 | **No eval dataset validation** — Eval dataset loaded but never validated for existence or format | High | `trainer.py:247-250` |
| 8 | **Perplexity computation uses only output text** — Should compute over full prompt+response for causal LM | Medium | `evaluator.py:240-258` |
| 9 | **Random seed not set globally** — `random.shuffle()` used but `random.seed()` never called; results not reproducible | Medium | `data_loader.py:221-222` |
| 10 | **No early stopping or patience config** — Training runs all epochs regardless of eval loss | Medium | `trainer.py:255-278` |
| 11 | **Missing `__all__` export for `GRPOTrainer`** — Module doc claims GRPO support but class not exported | Low | `__init__.py:17` |
| 12 | **Click dependency not declared** — `main()` imports click at runtime; may fail if not installed | Low | `trainer.py:322-333` |

---

### 2. Hidden Issues Discovered

| # | Issue | Why It's Hidden |
|---|-------|-----------------|
| H1 | **System prompt hardcoded in 3 places** — ChatML template in `data_loader.py`, `evaluator.py`, and `_get_instruction_part()` all duplicate the system prompt string; inconsistency risk | Copy-paste duplication across modules |
| H2 | **`dataset_text_field="text"` but data uses instruction/input/output** — SFTTrainer expects a single text field, but JSONL has structured fields | Mismatch between `TrainingConfig.dataset_text_field` and actual data format |
| H3 | **Validation warnings are silent** — `ConfigBuilder.validate()` returns warnings list but nothing logs/fails on them | No caller checks return value |
| H4 | **BLEU brevity penalty formula inverted** — Line 212: `exp(1 - ref/pred)` should be `exp(1 - pred/ref)` when pred < ref | Formula bug masked by character-level approximation |
| H5 | **Padding during tokenization wastes memory** — `padding="max_length"` pads ALL samples to 2048 tokens even if short | `DataConfig.padding` default is inefficient |
| H6 | **No gradient accumulation warmup** — First step has full gradient norm; can cause early instability | TrainingArguments doesn't configure gradual ramp-up |

---

### 3. Root Cause Analysis

| Root Cause | Issues Caused |
|------------|---------------|
| **Incomplete abstraction layer** — Trainer uses HF `load_dataset()` directly but assumes JSONL structure without validation | 2, 7 |
| **Feature creep without implementation** — GRPO mentioned in module docstring but never implemented | 3 |
| **Development environment leakage** — Absolute paths from dev machine hardcoded into presets | 4 |
| **Refactoring debt** — Example file not updated after v0.3.0 API changes | 5 |
| **Template drift** — System prompt duplicated instead of centralized constant | H1 |
| **API mismatch** — `dataset_text_field` designed for raw text datasets, not structured instruction data | H2 |
| **Defensive programming gaps** — Validation exists but no enforcement or escalation | H3 |

---

### 4. Recommended Fixes

| Priority | Fix | Files to Modify |
|----------|-----|-----------------|
| P0 | Add checkpoint resume: pass `resume_from_checkpoint` to `SFTTrainer.train()` and implement CLI flag handling | `trainer.py:174`, `trainer.py:326` |
| P0 | Implement data validation: check required fields (`instruction`, `output`), sample counts, avg token length | `trainer.py:_load_dataset()`, new `_validate_dataset()` |
| P0 | Remove or implement GRPO: either delete `GRPOTrainer` stub or add working implementation | `trainer.py:291-317` |
| P1 | Make paths relative/environment-based: use `os.getenv()` or resolve relative to project root | `config_builder.py:100-102` |
| P1 | Sync example file: remove commented-out fields or mark clearly as historical | `example_usage.py` |
| P1 | Fix label masking: count template tokens (system + user + assistant header) not just instruction text | `data_loader.py:108-117` |
| P2 | Centralize system prompt: define `SYSTEM_PROMPT` constant and import across modules | New `constants.py`, update `data_loader.py`, `evaluator.py` |
| P2 | Set random seeds: call `random.seed(config.seed)` and `torch.manual_seed()` at train start | `trainer.py:144`, `data_loader.py:221` |
| P2 | Add early stopping: extend `TrainingConfig` with `early_stopping_patience`, pass to `TrainingArguments` | `trainer.py:75`, `trainer.py:255-278` |
| P3 | Fix BLEU formula: correct brevity penalty calculation | `evaluator.py:211-214` |
| P3 | Change padding default: use `"longest"` instead of `"max_length"` for efficiency | `data_loader.py:57` |

---

### 5. Steps Taken

1. **Read all 6 training module files** — Full content analysis line-by-line
2. **Searched for TODO/FIXME/XXX markers** — Found 1 TODO (GRPO implementation)
3. **Searched for NotImplementedError/placeholder** — Found GRPO stub
4. **Cross-referenced module docstring vs implementation** — Identified GRPO claim vs reality
5. **Annotated comments in source** — Lines 87-89, 146-150 already had developer notes about gaps
6. **Compared preset paths vs typical deployment** — Identified hardcoded absolute paths
7. **Traced data flow** — From `config_builder` → `trainer` → `data_loader` → `SFTTrainer`
8. **Reviewed evaluation pipeline** — Identified perplexity and BLEU issues

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read all 6 Python source files in full |
| `Grep` | Search for TODO/FIXME/NotImplementedError patterns |
| `Bash` | Attempted import verification (torch not available) |

---

### 7. Verification

| Finding | Verification Method | Status |
|---------|--------------------
