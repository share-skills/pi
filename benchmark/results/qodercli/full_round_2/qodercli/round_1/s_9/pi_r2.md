# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pi | Run: 2
## Duration: 39.3s

---

Now let me systematically analyze each file for issues:

## Analysis Complete

---

## 1. Issues Found

| # | File | Line | Issue |
|---|------|------|-------|
| 1 | `trainer.py` | 234-238 | **GRPO trainer incomplete** - `_reward_model` and `_ref_model` never initialized, `train()` raises `NotImplementedError` |
| 2 | `trainer.py` | 157-160 | **No dataset validation** - Dataset loaded without checking required fields, empty samples, or data quality |
| 3 | `trainer.py` | 198-200 | **Hardcoded LoRA target modules** - Qwen2 architecture may have different module names (e.g., `attn.qkv`, `feed_forward`) |
| 4 | `data_loader.py` | 104-107 | **Label masking bug** - Masking based on instruction length assumes contiguous tokens, but tokenizer may split differently |
| 5 | `data_loader.py` | 169 | **Random seed not set** - `random.shuffle()` without seed makes training non-reproducible |
| 6 | `evaluator.py` | 89-92 | **Perplexity computation error** - Uses `sample.get("output")` only, should use full prompt + completion for proper LM evaluation |
| 7 | `evaluator.py` | 147 | **Division by zero risk** - `total_tokens` could be 0 if eval_data is empty |
| 8 | `config_builder.py` | 98-101 | **Path validation race condition** - `Path.exists()` check followed by later use creates TOCTOU vulnerability |
| 9 | `example_usage.py` | 24-26 | **Dead code with commented imports** - References removed/renamed classes, will confuse users |
| 10 | `__init__.py` | 10 | **Missing export** - `SFTDataLoader` and `DataConfig` from `data_loader.py` not exported |

---

## 2. Hidden Issues

| # | Category | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | **Security** | `config_builder.py` | 72-75 | **Path traversal risk** - `output_path` in `save()` uses `Path(output_path).parent.mkdir()` without validating path is within allowed directory |
| 2 | **Security** | `trainer.py` | 186 | **trust_remote_code=True hardcoded** - No user opt-out for loading untrusted model code |
| 3 | **Resource Leak** | `data_loader.py` | 163-168 | **File handle not closed on exception** - `_read_jsonl()` uses bare `open()` without context manager exception safety |
| 4 | **Resource Leak** | `evaluator.py` | 47-52 | **Model not moved to device consistently** - `device_map="auto"` in `_load_model()` conflicts with manual `.to(device)` calls |
| 5 | **Performance** | `data_loader.py` | 83-94 | **Inefficient tokenization** - Tokenizes instruction separately for masking, doubling tokenization work |
| 6 | **Performance** | `evaluator.py` | 74-86 | **Batch size hardcoded to 1** - Evaluation processes samples one-by-one, extremely slow on large datasets |
| 7 | **Memory** | `trainer.py` | 175-180 | **No memory cleanup** - After training, no `del model`, `torch.cuda.empty_cache()`, risking OOM during save |
| 8 | **Thread Safety** | `data_loader.py` | 29-34 | **Module-level templates are mutable** - If code modifies these strings at runtime, affects all instances |
| 9 | **Boundary** | `data_loader.py` | 161 | **Empty dataset unhandled** - `split_idx = max(1, ...)` returns 1 even if samples is empty list |
| 10 | **Boundary** | `evaluator.py` | 120-121 | **Empty prediction handling** - BLEU returns 0.0 but no warning logged for degenerate cases |
| 11 | **Exception** | `config_builder.py` | 113-117 | **Bare except on torch import** - Catches all ImportErrors including unrelated imports inside the try block |
| 12 | **Configuration** | `trainer.py` | 93 | **Hardcoded default dataset path** - `"./data/training.jsonl"` won't exist on most machines |
| 13 | **Cross-platform** | `config_builder.py` | 72 | **Unix-style paths in presets** - `/data/guwen/...` and `/models/...` won't work on Windows |
| 14 | **API Contract** | `trainer.py` | 236 | **Return type mismatch** - `train()` returns None but docstring implies it returns trained model |
| 15 | **Logging** | `trainer.py` | 157-170 | **No logging of dataset statistics** - Users can't verify data distribution before training |
| 16 | **Correctness** | `data_loader.py` | 107 | **Mask value assumption** - Assumes `-100` is ignored by loss function, but this is framework-specific |
| 17 | **Correctness** | `evaluator.py` | 65 | **Temperature=0.1 with do_sample=False** - Temperature has no effect when sampling is disabled |
| 18 | **Unused Import** | `evaluator.py` | 14 | **Counter imported but unused** - `from collections import Counter` not used anywhere |
| 19 | **Unused Import** | `evaluator.py` | 13 | **Optional imported but misused** - Used in type hints but `List[Dict]` doesn't use it for nullable types |
| 20 | **Documentation** | `trainer.py` | 28-30 | **Docstring lies** - Claims `dataset_text_field: str = "text"` but actual usage expects formatted prompts |

---

## 3. Root Cause

| Issue | Root Cause |
|-------|------------|
| GRPO trainer incomplete | Feature was planned but implementation deferred; placeholder class left in production code without clear deprecation notice |
| Dataset validation missing | Assumption that data synthesis pipeline always produces valid data; no defensive programming |
| Label masking bug | Misunderstanding of how tokenizers work - character counts don't map 1:1 to token IDs |
| Reproducibility issues | Random operations (shuffle) without seed control; TrainingConfig has seed but DataLoader doesn't use it |
| Hardcoded paths | Development environment paths leaked into preset configurations |
| Performance issues | No batching in evaluation; redundant tokenization in data loading |
| Resource management | Missing cleanup code after GPU-intensive operations; file handles not wrapped properly |
| Security concerns | Default trust_remote_code=True without user awareness of risks |

---

## 4. Recommended Fix

### Fix 1: GRPO Trainer - Remove or Mark Deprecated
```python
# trainer.py:220-240
# BEFORE:
class GRPOTrainer:
    """Group Relative Policy Optimization trainer."""
    def __init__(self, config: TrainingConfig):
        self.config = config
        self._model = None
        self._reward_model = None  # Never initialized
        self._ref_model = None     # Never initialized
    def train(self):
        raise NotImplementedError(...)

# AFTER:
# GRPOTrainer removed - feature not yet implemented
# TODO: Implement when reward modeling infrastructure is ready
```

### Fix 2: Dataset Validation
```python
# trainer.py:155-165
# BEFORE:
def _load_dataset(self):
    logger.info(f"Loading dataset: {self.config.dataset_path}")
    if self.config.dataset_path.endswith(".jsonl"):
        dataset = load_dataset("json", data_files=self.config.dataset_path)
    ...

# AFTER:
def _load_dataset(self):
    logger.info(f"Loading dataset: {self.config.dataset_path}")
    
    # Validate dataset exists and is readable
    if not Path(self.config.dataset_path).exists():
        raise FileNotFoundError(f"Dataset not found: {self.config.dataset_path}")
    
    if self.config.dataset_path.endswith(".jsonl"):
        dataset = load_dataset("json", data_files=self.config.dataset_path)
    
    # Validate required fields
    required_fields = ["instruction", "output"]
    sample = dataset["train"][0] if "train" in dataset else dataset[0]
    for field_name in required_fields:
        if field_name not in sample:
            raise ValueError(f"Dataset missing required field: {field_name}")
    
    # Log dataset statistics
    logger.info(f"Dataset fields: {list(sample.keys())}")
    logger.info(f"Sample count: {len(dataset['train'])}")
    
    if self.config.eval_dataset_path:
        eval_ds = load_dataset("json", data_files=self.config.eval_dataset_path)
        dataset["test"] = eval_ds["train"]
        logger.info(f"Eval samples: {len(eval_ds['train'])}")
    
    return dataset
```

### Fix 3: Label Masking Correction
```python
# data_loader.py:95-110
# BEFORE:
if self.config.label_mask_input:
    instruction = self._get_instruction_part(sample)
    instruction_tokens = self.tokenizer(
        instruction,
        return_tensors="pt",
        add_special_tokens=False,
    )
    n_mask = instruction_tokens["input_ids"].shape[1]
    labels[:n_mask] = -100

# AFTER:
if self.config.label_mask_input:
    # Find the assistant response marker and mask everything before it
    input_ids = encoded["input_ids"]
    assistant_token = self.tokenizer.encode("
