# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pua | Run: 2
## Duration: 84.17s

---

Now I have a comprehensive understanding of the training module. Let me compile my structured audit report:

---

## Training Pipeline End-to-End Audit Report

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **No data validation before training** - Dataset loaded without checking required fields, empty samples, or tokenized lengths | CRITICAL | `trainer.py:146-156`, `trainer.py:238-253` |
| 2 | **Hardcoded absolute paths in presets** - `/data/guwen/training_v2.jsonl` won't exist on most machines | HIGH | `config_builder.py:100-102` |
| 3 | **GRPOTrainer is unimplemented stub** - Claims to support GRPO but `train()` raises `NotImplementedError` | HIGH | `trainer.py:291-317` |
| 4 | **No checkpoint resume logic** - `save_steps` set but no resume mechanism documented or implemented | MEDIUM | `trainer.py:87-89`, `trainer.py:326` |
| 5 | **Evaluator.results not updated** - `evaluate()` returns results dict but never updates `self.results` instance attribute | MEDIUM | `evaluator.py:60`, `evaluator.py:75-129` |
| 6 | **No OOM handling during evaluation** - Large eval datasets can cause CUDA OOM with no batch fallback | MEDIUM | `evaluator.py:95-115` |
| 7 | **Stale example_usage.py** - Contains commented-out removed fields, misleading documentation | LOW | `example_usage.py:1-99` |
| 8 | **Missing sharegpt/raw format support** - `data_loader.py` docstring claims support but only implements instruction format | MEDIUM | `data_loader.py:6-9`, `data_loader.py:64-184` |
| 9 | **Label masking bug** - Instruction token count assumes contiguous tokens, may mask wrong positions | MEDIUM | `data_loader.py:109-117` |
| 10 | **Perplexity computed on output only** - Should compute on full prompt+completion for meaningful PPL | LOW | `evaluator.py:240-258` |

---

### 2. Hidden Issues (Beyond Initial Ask)

| # | Hidden Issue | Impact | Location |
|---|--------------|--------|----------|
| H1 | **trust_remote_code=True everywhere** - Security risk when loading arbitrary models from Hub | SECURITY | `trainer.py:49`, `evaluator.py:66-71` |
| H2 | **No seed setting for reproducibility** - `seed=42` in config but never passed to `random`, `numpy`, `torch` | REPRODUCIBILITY | `trainer.py:92`, `data_loader.py:221-222` |
| H3 | **Random shuffle without fixed seed** - `random.shuffle(samples)` produces non-reproducible splits | REPRODUCIBILITY | `data_loader.py:221-222` |
| H4 | **Padding to max_length wastes memory** - `padding="max_length"` pre-allocates all samples to 2048 tokens | PERFORMANCE | `data_loader.py:57`, `data_loader.py:96-102` |
| H5 | **No gradient accumulation warmup** - First few steps have unstable gradients with high accumulation | TRAINING STABILITY | `trainer.py:68` |
| H6 | **BLEU implementation missing smoothing** - Zero BLEU for sentences with no matching n-grams (common early in training) | METRICS ACCURACY | `evaluator.py:167-216` |
| H7 | **ROUGE argument order swapped** - `scorer.score(ref, pred)` should be `(pred, ref)` per rouge_score API | METRICS CORRECTNESS | `evaluator.py:229` |
| H8 | **CLI `--resume` flag does nothing** - Accepted but never passed to trainer or used | UX/BUILD | `trainer.py:326` |

---

### 3. Root Cause Analysis

**Primary Root Causes:**

1. **Incomplete implementation cycle** - GRPOTrainer advertised but not implemented; CLI resume flag added but not wired up
2. **Missing defensive programming** - No data validation, no OOM handlers, no error handling for edge cases
3. **Assumption-driven development** - Assumes dataset paths exist, assumes GPU availability, assumes data format consistency
4. **Inconsistent state management** - `evaluator.results` initialized but never updated; confusing API design
5. **Documentation drift** - Docstrings claim features (sharegpt support) that don't exist; example file stale

---

### 4. Recommended Fixes

| Priority | Fix | Files to Modify |
|----------|-----|-----------------|
| P0 | Add data validation step before training (check fields, sample counts, seq lengths) | `trainer.py:146-156` |
| P0 | Remove hardcoded paths from presets; use relative defaults or require explicit override | `config_builder.py:100-102` |
| P0 | Implement GRPOTrainer or remove from module and docs | `trainer.py:291-317`, `__init__.py` |
| P1 | Wire up `--resume` flag to actually resume from checkpoint | `trainer.py:326`, `trainer.py:134-179` |
| P1 | Update `evaluator.results` after each evaluate() call | `evaluator.py:128-129` |
| P1 | Add OOM handling with batch size fallback in evaluator | `evaluator.py:95-115` |
| P1 | Fix ROUGE scorer argument order | `evaluator.py:229` |
| P2 | Add seed control to data loader shuffle | `data_loader.py:221-222` |
| P2 | Change padding to `"longest"` instead of `"max_length"` | `data_loader.py:57` |
| P2 | Add smoothing to BLEU computation | `evaluator.py:167-216` |
| P3 | Delete or update `example_usage.py` to reflect current API | `example_usage.py` |
| P3 | Document security implications of `trust_remote_code=True` | `trainer.py:49`, README |

---

### 5. Steps Taken

1. **Read all 6 training module source files** - Full content analysis of trainer, evaluator, config_builder, data_loader, example_usage, and __init__
2. **Read test file** - Analyzed `test_training_pipeline.py` to understand existing test coverage and known issues
3. **Read configuration files** - Examined `training_config.yaml` and `requirements.txt` for dependency and config context
4. **Read eval criteria** - Reviewed `benchmark/eval_criteria.md` to understand production readiness standards
5. **Searched for TODO/FIXME/BUG markers** - Found unimplemented GRPO training
6. **Syntax validation** - Confirmed Python syntax is valid
7. **Cross-referenced docstrings vs implementations** - Identified feature gaps (sharegpt support, etc.)

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read all 6 source files, tests, configs, and eval criteria |
| `Glob` | Located training module files, config files, and test files |
| `Grep` | Searched for TODO/FIXME/BUG markers in code |
| `Bash` | Validated Python syntax with `ast.parse()` |

---

### 7. Verification

**Verification Evidence:**

1. ✅ **All source files read** - Line-by-line analysis completed for all 6 files
2. ✅ **Issues cross-referenced** - Each issue mapped to specific line numbers
3. ✅ **Test coverage analyzed** - Existing tests confirm some issues (hardcoded paths, stale fields, GRPO unimplemented)
4. ✅ **Config validated** - YAML config fields match TrainingConfig dataclass (except resume not wired)
5. ✅ **Dependencies checked** - All imports are from packages listed in requirements.txt

**Unverified (would require runtime):**
- ⚠️ Actual training run (requires GPU + dataset)
- ⚠️ OOM behavior under load
- ⚠️ BLEU/ROUGE metric accuracy on real data

---

## Production Readiness Summary

**Current Status: NOT PRODUCTION READY**

The training module has **10 critical/high/medium issues** and **8 hidden issues** that would cause failures in a real training job:

1. A user running the first training job would immediately hit **dataset not found** errors due to hardcoded paths
2. If they override paths, they'd face **no data validation** - corrupt or malformed data would fail mid-training
3. If training is interrupted, **no resume capability** means losing all progress
4. The **GRPO trainer is a stub** - anyone trying RLHF would waste hours debugging
5. **Evaluation metrics may be incorrect** due to ROUGE argument swap and BLEU smoothing issues

**Recommendation:** Address P0 and P1 issues before any production training run.
