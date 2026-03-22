# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pi | Run: 1
## Duration: 91.38s

---

Now I have a complete picture. Let me compile the comprehensive analysis:

---

## 🧠 PI · 肃阵 · Training Pipeline Production Readiness Audit

---

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **Hardcoded absolute paths in presets** — `/data/guwen/training_v2.jsonl`, `/models/guwen-llm/checkpoints` | `config_builder.py:100-102` | 🔴 Critical |
| 2 | **No resume from checkpoint support** — `resume` CLI option ignored, no checkpoint loading logic | `trainer.py:326-327`, `trainer.py:134-179` | 🔴 Critical |
| 3 | **Dataset not validated before training** — No schema validation, no empty sample check | `trainer.py:146-150`, `trainer.py:238-253` | 🔴 Critical |
| 4 | **GRPOTrainer is unimplemented stub** — Always raises `NotImplementedError` | `trainer.py:291-317` | 🟠 High |
| 5 | **Unused imports** — `os` imported but never used in multiple files | `config_builder.py:13`, `evaluator.py:18`, `trainer.py:21` | 🟡 Medium |
| 6 | **Missing `__all__` exports** — `GRPOTrainer`, `DataConfig`, `SFTDataLoader` not exported | `__init__.py:17` | 🟡 Medium |
| 7 | **Example usage file has stale documentation** — References removed fields but still imports them in comments | `example_usage.py:32-34` | 🟡 Medium |
| 8 | **No validation for eval_ratio range** — Accepts any float including negative or >1.0 | `data_loader.py:205-233` | 🟡 Medium |
| 9 | **Perplexity computation uses only output text** — Ignores instruction context, inconsistent with training | `evaluator.py:240-258` | 🟡 Medium |
| 10 | **Random seed not set for reproducibility** — `random.shuffle()` called without seeding | `data_loader.py:221-222` | 🟡 Medium |
| 11 | **No OOM handling during evaluation** — Large eval batches can crash | `evaluator.py:75-129` | 🟡 Medium |
| 12 | **Label masking calculation may be incorrect** — Uses instruction token count, not accounting for system prompt | `data_loader.py:109-117` | 🟠 High |
| 13 | **File handle not closed on exception** — `from_file()` could leak handles on YAML parse error | `config_builder.py:118-121` | 🟠 High |
| 14 | **trust_remote_code=True by default** — Security risk for arbitrary code execution | `trainer.py:49`, `evaluator.py:66-67` | 🟠 High |

---

### 2. Hidden Issues

| # | Issue | Category | Location |
|---|-------|----------|----------|
| 1 | **Thread safety**: `self._presets` mutable via `deepcopy` but no lock if modified concurrently | Thread Safety | `config_builder.py:80` |
| 2 | **Memory leak risk**: `InstructionDataset` caches all tokenized data in `self._data` with no streaming option | Memory | `data_loader.py:76-88` |
| 3 | **Silent sample dropping**: `_encode_sample()` returns `None` for empty samples, no warning logged | Data Integrity | `data_loader.py:90-94` |
| 4 | **Division by zero in perplexity**: If `total_tokens == 0`, returns `float("inf")` without warning | Edge Case | `evaluator.py:257` |
| 5 | **BLEU score undefined for empty predictions**: Returns `0.0` but no warning about degenerate output | Metrics | `evaluator.py:173-181` |
| 6 | **Cross-platform path issue**: Hardcoded Unix-style paths will fail on Windows | Portability | `config_builder.py:100-102` |
| 7 | **GPU memory not cleared between eval runs**: No `torch.cuda.empty_cache()` call | Performance | `evaluator.py:75-129` |
| 8 | **No early stopping configuration**: Training runs full epochs regardless of eval loss | Training Quality | `trainer.py:255-278` |
| 9 | **Checkpoint selection ambiguity**: `save_total_limit=3` but no `load_best_model_at_end` | Training Quality | `trainer.py:83` |
| 10 | **Race condition in label masking**: Token count mismatch if tokenizer adds special tokens | Correctness | `data_loader.py:109-117` |
| 11 | **Missing validation for LoRA target modules**: No check if modules exist in model | Correctness | `trainer.py:220-228` |
| 12 | **No gradient accumulation warmup**: First few steps have unstable gradients | Training Stability | `trainer.py:255-278` |
| 13 | **Logging format inconsistent**: Some use f-string, some use `.format()` | Code Quality | Multiple files |
| 14 | **Type hints incomplete**: `load()` returns `tuple` instead of `Tuple[Dataset, Dataset]` | Type Safety | `data_loader.py:205-206` |

---

### 3. Root Cause

| Root Cause | Issues Caused | Location |
|------------|---------------|----------|
| **Development-stage code promoted to production without hardening** | 1, 2, 3, 4, 8, 10, 11 | All files |
| **Missing input validation layer** | 3, 8, 11, 14 (hidden) | `trainer.py`, `data_loader.py` |
| **Inconsistent API design between modules** | 7, 9, 12 (hidden) | `evaluator.py` vs `data_loader.py` |
| **Security considerations deferred** | 14, 6 (hidden) | `trainer.py`, `evaluator.py` |
| **Error handling not implemented for edge cases** | 4 (hidden), 5 (hidden) | `evaluator.py` |
| **Resource management not prioritized** | 13, 2 (hidden), 7 (hidden) | `config_builder.py`, `data_loader.py` |

---

### 4. Recommended Fix

#### Fix 1: Hardcoded Paths (Critical)
```python
# config_builder.py:100-102
# BEFORE:
config.setdefault("dataset_path", "/data/guwen/training_v2.jsonl")
config.setdefault("eval_dataset_path", "/data/guwen/eval_v2.jsonl")
config.setdefault("output_dir", "/models/guwen-llm/checkpoints")

# AFTER:
import os
config.setdefault("dataset_path", os.environ.get("GUWEN_DATASET_PATH", "./data/training.jsonl"))
config.setdefault("eval_dataset_path", os.environ.get("GUWEN_EVAL_DATASET_PATH"))
config.setdefault("output_dir", os.environ.get("GUWEN_OUTPUT_DIR", "./outputs/guwen-llm"))
```

#### Fix 2: Resume from Checkpoint (Critical)
```python
# trainer.py:134-179
# Add after line 159:
def train(self, resume_from_checkpoint: Optional[str] = None):
    """Execute the full training pipeline."""
    # ... existing code ...
    
    # Step 5: Train with resume support
    logger.info("Starting training...")
    self._trainer.train(resume_from_checkpoint=resume_from_checkpoint)
```

```python
# trainer.py:255-278
# Add to _create_training_args():
TrainingArguments(
    # ... existing args ...
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss" if self.config.eval_dataset_path else None,
    greater_is_better=False,
)
```

#### Fix 3: Dataset Validation (Critical)
```python
# trainer.py:238-253
# Replace _load_dataset with:
def _load_dataset(self):
    """Load and validate the training dataset."""
    logger.info(f"Loading dataset: {self.config.dataset_path}")
    
    if not Path(self.config.dataset_path).exists():
        raise FileNotFoundError(f"Dataset not found: {self.config.dataset_path}")
    
    if self.config.dataset_path.endswith(".jsonl"):
        dataset = load_dataset("json", data_files=self.config.dataset_path)
    else:
        dataset = load_dataset(self.config.dataset_path)
    
    # Validate dataset structure
    self._validate_dataset(dataset)
    
    if self.config.eval_dataset_path:
        if not Path(self.config.eval_dataset_path).exists():
            raise FileNotFoundError(f"Evaluation dataset not found: {self.config.eval_dataset_path}")
        eval_ds = load_dataset("json", data_files=self.config.eval_dataset_path)
        dataset["test"] = eval_ds["train"]
    
    logger.info(f"Dataset loaded: {dataset}")
    return dataset

def _validate_dataset(self, dataset):
    """Validate dataset has required fields and non-empty samples."""
    required_fields = ["instruction", "output"]
    ds = dataset["train"] if "train" in dataset else dataset
    
    for i, sample in enumerate(ds):
        for field in required_fields:
            if field not in sample:
                raise ValueError(f"Sample {i} missing required field: {field}")
        if not sample.get("instruction") or not sample.get("output"):
            logger.warning(f"Sample {i} has empty instruction or output, will be skipped")
```

#### Fix 4: Remove Unused Imports
```python
# config_builder.py:13 - REMOVE: import os
# evaluator.py:18 - REMOVE: import os  
# trainer.py:21-22 - REMOVE: import os, import json (json not used)
```

#### Fix 5: Add Reproducibility Seed
```python
# data_loader.py:220-222
# BEFORE:
import random
random.shuffle(samples)

# AFTER:
import random
random.seed(self.config.seed if hasattr(self.config, 'seed') else 42)
random.shuffle(samples)
```

#### Fix 6: Context Manager for File Handles
```python
# config_builder.py:118-121
# BEFORE:
with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# AFTER:
try:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
except yaml.YAMLError as e:
    logger.error(f"Failed to parse config file: {e}")
    raise
```

#### Fix 7: Eval Ratio Validation
```python
# data_loader.py:205-233
# Add validation at start of load():
if not 0.0 <= eval_ratio < 1.0:
    raise ValueError(f"eval_ratio must be in [0.0, 1.0), got {eval_ratio}")
```

---

### 5. Steps Taken

| Step | Action | Discovery |
|------|--------|-----------|
| 1 | Read all 6 training module source files | Identified module structure and dependencies |
| 2 | Read test file (`test_training_pipeline.py`) | Found tests confirming hardcoded paths, GRPO unimplemented, stale fields |
| 3 | Read pipeline runner script (`run_pipeline.py`) | Discovered `resume` CLI option exists but is never passed to trainer |
| 4 | Grep for `TrainingConfig` usage | Found config instantiation patterns across codebase |
| 5 | Grep for `GRPOTrainer` usage | Confirmed only used in tests expecting `NotImplementedError` |
| 6 | Cross-reference docstrings with implementation | Found mismatches (e.g., `evaluator.results` not updated) |
| 7 | Analyze each function against checklist | Found unused imports, missing validation, resource leaks |
| 8 | Compare template strings across files | Found duplicated ChatML templates (DRY violation) |
| 9 | Check type hints completeness | Found incomplete annotations (`-> tuple`) |
| 10 | Verify error handling patterns | Found bare except clauses and silent failures |

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read all 6 source files + test file + pipeline script |
| `Grep` | Search for `TrainingConfig`, `GRPOTrainer` usage patterns |
| `Glob` | Locate training module files in benchmark directory |
| Manual code analysis | Apply逐函数检查清单 to each function |

---

### 7. Verification

#### Run Static Analysis
```bash
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
python -m py_compile src/training/*.py  # Verify syntax
```

#### Run Tests
```bash
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
pytest tests/test_training_pipeline.py -v  # Run existing tests
```

#### Verify Hardcoded Paths Issue
```bash
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
python -c "
from src.training.config_builder import ConfigBuilder
builder = ConfigBuilder()
config = builder.from_preset('sft_7b')
from pathlib import Path
print('Dataset exists:', Path(config['dataset_path']).exists())
print('Eval dataset exists:', Path(config['eval_dataset_path']).exists())
print('Output dir writable:', Path(config['output_dir']).parent.exists())
"
```

#### Verify GRPO Not Implemented
```bash
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
python -c "
from src.training.trainer import GRPOTrainer, TrainingConfig
grpo = GRPOTrainer(TrainingConfig())
try:
    grpo.train()
except NotImplementedError as e:
    print('GRPO correctly raises NotImplementedError:', str(e))
"
```

#### Verify Unused Imports
```bash
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
python -m flake8 src/training/config_builder.py src/training/evaluator.py src/training/trainer.py --select=F401
```

#### Verify Resume Option Ignored
```bash
grep -n "resume" src/training/trainer.py  # Should show only CLI definition, no usage
grep -n "resume" scripts/run_pipeline.py   # Should show option defined but not passed
```

---

## Summary

| Category | Count |
|----------|-------|
| **Surface Issues** | 14 |
| **Hidden Issues** | 14 |
| **Critical** | 3 |
| **High Severity** | 4 |
| **Medium Severity** | 7 |

**Production Readiness Assessment**: ❌ **NOT READY**

The training pipeline has significant gaps that would cause failures in production:
1. **Hardcoded paths** will fail on any machine without those exact directories
2. **No checkpoint resume** means training interruptions lose all progress
3. **No dataset validation** allows corrupt/empty data to crash training mid-run
4. **Security risks** from `trust_remote_code=True` by default

Recommended: Address all 🔴 Critical and 🟠 High issues before first real training job.
