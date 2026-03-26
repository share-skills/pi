# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pua | Run: 1
## Duration: 139.31s

---

Now I have completed my investigation. Let me provide the structured summary:

---

## Training Pipeline End-to-End Audit — Production Readiness Report

### 1. Issues Found (Critical & High Priority)

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **data_loader module completely disconnected from trainer** | Critical | `trainer.py:134-170` |
| 2 | **Resume CLI option defined but never implemented** | Critical | `trainer.py:326-331` |
| 3 | **GRPOTrainer is a stub with uninitialized models** | High | `trainer.py:291-317` |
| 4 | **No dataset validation before training** | High | `trainer.py:156`, `trainer.py:238-253` |
| 5 | **Evaluator.results not updated after evaluate()** | High | `evaluator.py:75-129` |
| 6 | **Division by zero risk in BLEU brevity penalty** | Medium | `evaluator.py:212` |
| 7 | **Empty eval_data causes division by zero** | Medium | `evaluator.py:164` |
| 8 | **Hardcoded absolute paths in presets will fail on most machines** | High | `config_builder.py:100-102` |
| 9 | **Example usage file admits it's stale and may cause TypeError** | Medium | `example_usage.py:1-99` |
| 10 | **Module claims GRPO support but it's not implemented** | High | `__init__.py:3-7` |

---

### 2. Hidden Issues Discovered

| # | Issue | Impact |
|---|-------|--------|
| H1 | **Training has no error handling for model download failures** | Network issues during `from_pretrained()` will crash without actionable error |
| H2 | **No validation that LoRA target modules exist in the model** | Will fail at runtime if model architecture differs from Qwen |
| H3 | **SFTDataLoader.load() shuffles without fixed seed** | Non-reproducible train/eval splits |
| H4 | **Label masking logic assumes instruction length equals tokenized length** | May mask wrong tokens if tokenization differs |
| H5 | **Perplexity computation uses only output text, not full prompt** | Incorrect perplexity scores |
| H6 | **ConfigBuilder.validate() catches PermissionError but not OSError** | Other filesystem errors will crash |
| H7 | **TrainingConfig has no field for gradient_checkpointing kwargs** | Cannot customize checkpointing behavior |
| H8 | **No mechanism to export trained adapters separately from base model** | Wastes storage, harder deployment |
| H9 | **evaluation generate() uses greedy decoding (do_sample=False)** | May produce lower quality outputs than training |
| H10 | **No memory cleanup between training and evaluation** | OOM risk on low-VRAM GPUs |

---

### 3. Root Causes

| Root Cause | Issues Caused |
|------------|---------------|
| **Modular design without integration** | The `data_loader` module was built but never integrated into `trainer.py`. Trainer uses `datasets.load_dataset()` directly while a complete alternative loader exists unused. |
| **Incomplete feature implementation** | GRPO training was announced in docstrings but the `GRPOTrainer` class is a placeholder with `_reward_model` and `_ref_model` explicitly marked as "Never initialized". |
| **Dead CLI code** | The `--resume` option exists in the Click command but the variable is never passed to `trainer.train()` or used anywhere. |
| **State management bug** | `Evaluator.results` is an empty dict that's never assigned; `evaluate()` returns a new dict instead of updating instance state. |
| **Defensive programming gaps** | Multiple division operations lack guards for empty inputs; exception handling is inconsistent. |
| **Documentation drift** | Example file explicitly states it's from v0.2.0 while code is at v0.4.x; removed features are documented but examples aren't updated. |

---

### 4. Recommended Fixes

#### P0 — Blockers (Fix Before Any Training Run)

```python
# Fix 1: Integrate data_loader or remove it
# Option A: Use existing SFTDataLoader in trainer.py
from .data_loader import SFTDataLoader, DataConfig

def train(self):
    # ... after loading model
    if hasattr(self.config, 'use_custom_loader') and self.config.use_custom_loader:
        loader = SFTDataLoader(tokenizer, DataConfig())
        train_ds, eval_ds = loader.load(self.config.dataset_path)
    else:
        # Current datasets.load_dataset() path
        dataset = self._load_dataset()
```

```python
# Fix 2: Implement resume functionality
def train(self, resume_from: str = None):
    # ... existing setup
    self._trainer.train(resume_from_checkpoint=resume_from)

# In main():
def train(config, resume):
    trainer = Trainer(config)
    trainer.train(resume_from=resume)
```

```python
# Fix 3: Add dataset validation before training
def _load_dataset(self):
    dataset = load_dataset(...)
    
    # Validate required fields
    if "train" in dataset:
        sample = dataset["train"][0]
        if self.config.dataset_text_field not in sample:
            raise ValueError(
                f"Field '{self.config.dataset_text_field}' not found in dataset. "
                f"Available: {list(sample.keys())}"
            )
    
    # Check for empty samples
    if len(dataset["train"]) == 0:
        raise ValueError("Training dataset is empty")
    
    return dataset
```

```python
# Fix 4: Update Evaluator.results
def evaluate(self, eval_data, metrics=None):
    # ... existing code
    results = {...}
    self.results = results  # Add this line
    return results
```

#### P1 — High Priority

```python
# Fix 5: Guard against division by zero in evaluator.py
def _compute_bleu(self, predictions, references):
    if not predictions or not references:
        return 0.0
    # ... 
    return total_score / len(predictions) if predictions else 0.0

def _sentence_bleu(self, prediction, reference, max_n=4):
    # ... existing code
    if len(pred_chars) == 0 or len(ref_chars) == 0:
        return 0.0
    # Brevity penalty - add guard
    if len(pred_chars) > 0 and len(pred_chars) < len(ref_chars):
        bp = math.exp(1 - len(ref_chars) / len(pred_chars))
    else:
        bp = 1.0
```

```python
# Fix 6: Remove misleading GRPO claims or implement it
# Option A: Remove from __init__.py exports
__all__ = ["Trainer", "TrainingConfig", "Evaluator", "ConfigBuilder"]
# Remove GRPOTrainer until implemented

# Option B: Add clear deprecation notice
class GRPOTrainer:
    """DEPRECATED: GRPO training is not yet available.
    
    This class is a placeholder. Use Trainer for SFT only.
    See GitHub issue #XXX for tracking.
    """
```

```python
# Fix 7: Make preset paths configurable
def from_preset(self, preset_name, **overrides):
    config = deepcopy(self._presets[preset_name])
    
    # Use relative paths or env vars instead of hardcoded absolutes
    config.setdefault(
        "dataset_path", 
        os.environ.get("GUWEN_DATASET_PATH", "./data/training_v2.jsonl")
    )
    config.setdefault(
        "eval_dataset_path",
        os.environ.get("GUWEN_EVAL_PATH", "./data/eval_v2.jsonl")
    )
    config.setdefault(
        "output_dir",
        os.environ.get("GUWEN_OUTPUT_DIR", "./outputs/guwen-llm/checkpoints")
    )
```

#### P2 — Quality Improvements

```python
# Fix 8: Add fixed seed for data splitting
import random
random.seed(self.config.seed)  # Use config seed
random.shuffle(samples)
```

```python
# Fix 9: Add LoRA target module validation
def _load_model(self):
    # ... after loading model
    model_arch = model.config.architectures[0] if hasattr(model.config, 'architectures') else 'unknown'
    logger.info(f"Model architecture: {model_arch}")
    
    # Warn if target modules might not exist
    known_modules = {"q_proj", "k_proj", "v_proj", "o_proj", "query", "key", "value"}
    for target in self.config.lora_target_modules:
        if target not in known_modules:
            logger.warning(
                f"LoRA target module '{target}' may not exist in this model. "
                "Training may fail if module is not found."
            )
```

---

### 5. Steps Taken (Investigation Methodology)

1. **File Discovery**: Used Glob to locate all training module files across the codebase
2. **Source Analysis**: Read all 6 Python files in `src/training/` directory
3. **Cross-Reference Search**: Searched for:
   - Module imports between trainer/data_loader
   - Usage of `resume` parameter throughout codebase
   - GRPO-related code and its actual implementation status
   - Error handling patterns (`try/except/raise`)
4. **Edge Case Analysis**: Checked for:
   - Division operations without guards
   - Empty input handling
   - Exception coverage completeness
5. **Documentation Verification**: Compared README claims vs actual implementation
6. **Dependency Check**: Reviewed requirements.txt for missing dependencies

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Glob` | Located all `.py` files in training module |
| `Read` | Full source code review of all 6 files |
| `Grep` | Pattern searches for imports, error handling, specific features |
| `TodoWrite` | Tracked investigation progress |

---

### 7. Verification

All findings verified by:
- **Direct source reading** — Every issue cites exact file paths and line numbers
- **Pattern search confirmation** — Cross-checked that `data_loader` imports don't exist in `trainer.py`
- **Logic tracing** — Followed execution paths to confirm dead code (resume option) and state bugs (evaluator.results)
- **Mathematical analysis** — Identified division by zero conditions in evaluator formulas

---

### Production Readiness Verdict: **NOT READY**

The training pipeline has **critical integration gaps** and **incomplete features** that would cause immediate failure on first production run. Minimum fixes required before any training attempt:

1. Integrate or remove `data_loader` module
2. Implement resume functionality or remove the CLI option
3. Add dataset validation
4. Fix Evaluator state management
5. Remove misleading GRPO claims

**Recommendation**: Dedicate 1-2 days to fix P0/P1 issues, then run a small-scale test training job (<100 samples) to validate the end-to-end pipeline before committing GPU resources.
