# Scenario 9: Training Pipeline End-to-End Audit
## Condition: nopua | Run: 1
## Duration: 57.1s

---

Based on my thorough analysis of all the provided source files, here is my comprehensive investigation report:

---

## Training Module Production Readiness Audit

### 1. Issues Found

#### **CRITICAL - trainer.py**

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **No checkpoint resume mechanism** - `save_steps` and `save_total_limit` configured but no `resume_from_checkpoint` parameter or logic | Critical | `trainer.py:68-70`, `trainer.py:97` |
| 2 | **GRPO trainer has uninitialized models** - `_reward_model` and `_ref_model` declared but never initialized, making GRPO unusable | Critical | `trainer.py:214-216` |
| 3 | **No data validation before training** - Dataset loaded without checking required fields, empty samples, or tokenized lengths | Critical | `trainer.py:105-107` |
| 4 | **Hardcoded dataset paths in config_builder presets** - `/data/guwen/training_v2.jsonl` won't exist on most machines | Critical | `config_builder.py:75-77` |
| 5 | **Training interruption = total loss** - No mechanism to recover from interrupted training despite checkpoint saving | Critical | `trainer.py:97-131` |

#### **HIGH - data_loader.py**

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 6 | **Label masking logic is incorrect** - Uses instruction token count to mask labels, but this doesn't account for system prompt tokens in ChatML template | High | `data_loader.py:89-95` |
| 7 | **No error handling for malformed samples** - Empty instruction/output silently skipped without logging which samples failed | High | `data_loader.py:74-76` |
| 8 | **Random seed not set for shuffle** - `random.shuffle()` called without seed, causing non-reproducible train/eval splits | High | `data_loader.py:134` |
| 9 | **Padding always uses "max_length"** - Wastes memory for short sequences; `padding="longest"` would be more efficient | Medium | `data_loader.py:45` |

#### **HIGH - evaluator.py**

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 10 | **Perplexity computation ignores instruction context** - Only computes loss on output text, not the full prompt+response | High | `evaluator.py:165-176` |
| 11 | **Character-level BLEU implementation is buggy** - When `pred_chars` is shorter than `max_n`, n-gram generation produces empty results | High | `evaluator.py:119-124` |
| 12 | **ROUGE scores not computed if package missing** - Silent failure with only a warning, no fallback or clear error | Medium | `evaluator.py:143-152` |
| 13 | **Evaluation uses greedy decoding (temperature=0.1, do_sample=False)** - Doesn't reflect actual generation quality with sampling | Medium | `evaluator.py:82-88` |

#### **MEDIUM - config_builder.py**

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 14 | **validate() returns warnings but doesn't raise errors** - Invalid configs can pass through silently | Medium | `config_builder.py:120-157` |
| 15 | **GPU check imports torch every time** - Should cache the result or check once at module load | Low | `config_builder.py:139-147` |
| 16 | **No validation for lora_target_modules** - Invalid module names will cause runtime errors during training | Medium | `config_builder.py:120-157` |

#### **LOW - example_usage.py**

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 17 | **Example code references removed parameters** - `use_flash_attention`, `data_format`, `wandb_project` don't exist | Low | `example_usage.py:22-26` |
| 18 | **Comments say paths "may differ" but examples are copy-paste ready** - Users will run broken code | Low | `example_usage.py:34-41` |

---

### 2. Hidden Issues (Beyond the Ask)

| # | Issue | Impact |
|---|-------|--------|
| H1 | **No distributed training support** - Single GPU only; no DDP/FSDP for multi-GPU setups | Cannot scale training |
| H2 | **No memory profiling or OOM protection** - No gradient accumulation auto-tuning based on available VRAM | Training may crash mid-run |
| H3 | **No validation dataset sanity check** - Eval dataset could be empty or have different distribution | Evaluation metrics meaningless |
| H4 | **Tokenizer special tokens not verified** - ChatML templates use `
