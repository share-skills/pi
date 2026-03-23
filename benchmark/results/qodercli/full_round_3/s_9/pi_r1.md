# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pi | Run: 1
## Duration: 38.22s

---

Now let me systematically analyze each file for issues. I'll examine each function line by line.

## Analysis Complete — Structured Report

---

### 1. Issues Found

| # | File | Line | Issue |
|---|------|------|-------|
| 1 | `trainer.py` | 235-238 | **GRPO trainer references uninitialized models** — `_reward_model` and `_ref_model` set to `None` but never initialized; will cause `AttributeError` if accessed |
| 2 | `trainer.py` | 174-176 | **Dataset loaded without validation** — no check for required fields (`text`), empty samples, or corrupt data before passing to trainer |
| 3 | `config_builder.py` | 93-96 | **Validation writes to disk** — `validate()` calls `Path.mkdir()` which could have side effects; should be read-only |
| 4 | `evaluator.py` | 103-119 | **Perplexity computation uses wrong field** — computes loss on `output` only, ignoring instruction context; inconsistent with training data format |
| 5 | `data_loader.py` | 156-160 | **Label masking logic is incorrect** — masks by token count but doesn't verify alignment; truncated sequences will have wrong labels |
| 6 | `data_loader.py` | 86-90 | **Hardcoded system prompt** — "你是一個精通古典中文的 AI 助手" appears in 4 places; not configurable |
| 7 | `example_usage.py` | 24-26 | **Example code will crash** — passes removed parameters (`use_flash_attention`, `data_format`) to `TrainingConfig` |
| 8 | `trainer.py` | 147 | **No checkpoint resume support** — comment notes this but no implementation; training interruptions lose all progress |
| 9 | `evaluator.py` | 76-83 | **Batch size = 1 during evaluation** — no DataLoader batching; processes samples one at a time, extremely slow |
| 10 | `config_builder.py` | 76-78 | **Default paths are absolute and non-existent** — `/data/guwen/training_v2.jsonl` will fail validation on fresh machines |

---

### 2. Hidden Issues

| # | Category | File | Line | Issue |
|---|----------|------|------|-------|
| 11 | 🔴 Security | `config_builder.py` | 104-109 | **GPU check imports torch unconditionally** — could trigger import-side-effects; also catches `ImportError` but not `RuntimeError` (common with CUDA) |
| 12 | ⚡ Performance | `data_loader.py` | 67-78 | **Tokenization happens in `__init__`** — entire dataset tokenized synchronously; no caching; large datasets will take minutes to load every run |
| 13 | 📖 Resource Leak | `evaluator.py` | 115-117 | **No `torch.no_grad()` for perplexity** — builds computation graph for full dataset; will OOM on large eval sets |
| 14 | 🔒 Thread Safety | `data_loader.py` | 145-147 | **`random.shuffle` without seed** — non-deterministic splits; experiments not reproducible |
| 15 | ⚠️ Boundary | `data_loader.py` | 150 | **`split_idx` can be 0** — if `eval_ratio >= 1.0` or dataset tiny, train set becomes empty; no validation |
| 16 | ⚠️ Exception Handling | `evaluator.py` | 142-144 | **Bare `except ImportError`** — swallows all import errors including typos in module name |
| 17 | 📖 Readability | `trainer.py` | 45-52 | **`dataset_text_field` unused** — field exists in config but SFTTrainer receives raw dataset; mismatch between config and usage |
| 18 | ⚡ Performance | `trainer.py` | 180-185 | **No gradient accumulation warmup** — starts full accumulation from step 1; can cause early instability |
| 19 | 🔒 Security | `config_builder.py` | 67-69 | **YAML loading without safety note** — `yaml.safe_load` is safe but no warning against using `yaml.load` elsewhere |
| 20 | ⚠️ Correctness | `evaluator.py` | 58-62 | **BLEU implementation missing smoothing** — zero precision for any n-gram order causes entire score to be zero; no epsilon fallback |
| 21 | 📖 Maintainability | `trainer.py` | 228-245 | **`GRPOTrainer` is dead code** — raises `NotImplementedError` on `train()`; should be removed or marked experimental |
| 22 | ⚡ Memory | `data_loader.py` | 60-62 | **All samples stored in memory** — no streaming/lazy loading; multi-GB datasets will exhaust RAM |
| 23 | ⚠️ Cross-platform | `config_builder.py` | 76-78 | **Unix-style paths hardcoded** — `/data/guwen/...` will fail on Windows; should use `pathlib.Path` |
| 24 | 🔒 API Contract | `evaluator.py` | 93-96 | **`evaluate()` returns empty dict if metrics list empty** — silent failure; should raise or return all metrics by default |
| 25 | ⚠️ Validation | `trainer.py` | 127-130 | **No config validation before training** — invalid configs fail mid-training after hours of compute |

---

### 3. Root Cause

| Root Cause | Issues | Explanation |
|------------|--------|-------------|
| **Missing input validation** | 2, 10, 15, 25 | Dataset and config are consumed without schema validation; failures occur deep in training loop |
| **Incomplete implementation** | 1, 7, 8, 21 | GRPO trainer stubbed but exposed; example code not updated; resume feature documented but missing |
| **Resource management gaps** | 12, 13, 22 | No caching, no streaming, no gradient context management for eval; memory grows unbounded |
| **Hardcoded values** | 6, 10, 23 | System prompts, default paths, platform-specific paths embedded in code |
| **Non-determinism** | 14 | Random operations without seed control break reproducibility |
| **Silent failures** | 16, 19, 24 | Broad exception handlers and edge cases return empty results without warning |

---

### 4. Recommended Fix

#### Fix 1: Add Dataset Validation (trainer.py:174)
```python
# Before (line 174-176):
dataset = self._load_dataset()

# After:
dataset = self._load_dataset()
self._validate_dataset(dataset)

def _validate_dataset(self, dataset):
    """Validate dataset has required fields and reasonable content."""
    required_fields = ["text"]
    sample = dataset["train"][0] if "train" in dataset else dataset[0]
    for field_name in required_fields:
        if field_name not in sample:
            raise ValueError(f"Dataset missing required field: {field_name}")
    if len(sample.get("text", "")) == 0:
        raise ValueError("Dataset contains empty text samples")
```

#### Fix 2: Fix Perplexity Computation (evaluator.py:103)
```python
# Before (line 115-117):
outputs = self.model(**inputs, labels=inputs["input_ids"])
total_loss += outputs.loss.item() * inputs["input_ids"].shape[1]

# After:
with torch.no_grad():
    outputs = self.model(**inputs, labels=inputs["input_ids"])
    total_loss += outputs.loss.item() * inputs["input_ids"].shape[1]
```

#### Fix 3: Add Deterministic Seed (data_loader.py:145)
```python
# Before (line 145-147):
import random
random.shuffle(samples)

# After:
import random
random.seed(42)  # Configurable via DataConfig
random.shuffle(samples)
```

#### Fix 4: Remove Dead Code (trainer.py:228-245)
```python
# Delete entire GRPOTrainer class or add @deprecated decorator
```

#### Fix 5: Make System Prompt Configurable (data_loader.py:16-19)
```python
# Before:
CHATML_TEMPLATE = ("
