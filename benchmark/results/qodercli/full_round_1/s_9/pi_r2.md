# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pi | Run: 2
## Duration: 68.63s

---

Now I'll systematically analyze each file against the 10-point checklist and identify all issues.

---

## 🧠 PI · Production Readiness Audit · Training Pipeline

---

## 1. Issues Found

| # | File | Line | Issue |
|---|------|------|-------|
| 1 | `trainer.py` | 237-245 | **GRPOTrainer._reward_model and _ref_model never initialized** - Attributes set to None but never used, dead code |
| 2 | `trainer.py` | 246-253 | **GRPOTrainer.train() raises NotImplementedError** - Placeholder implementation, not production ready |
| 3 | `trainer.py` | 97-101 | **No checkpoint resume logic** - Comment notes missing resume functionality, training interruptions lose all progress |
| 4 | `trainer.py` | 118-141 | **_load_model() no error handling** - Model loading can fail silently or crash on network/disk errors |
| 5 | `trainer.py` | 157-168 | **_load_dataset() no validation** - Dataset loaded without checking required fields, empty samples, or corruption |
| 6 | `trainer.py` | 204-210 | **eval_steps can be None** - When eval_dataset_path is None, eval_steps=None may cause HuggingFace warnings/errors |
| 7 | `config_builder.py` | 78-80 | **Hardcoded dataset paths** - `/data/guwen/training_v2.jsonl` won't exist on most machines |
| 8 | `config_builder.py` | 143-146 | **validate() catches PermissionError only** - Other OSError variants (FileNotFoundError, etc.) not handled |
| 9 | `data_loader.py` | 105-112 | **_encode_sample no null check** - If sample is None or missing keys, will crash |
| 10 | `data_loader.py` | 174-177 | **random.shuffle without seed** - Non-deterministic data split, results vary between runs |
| 11 | `data_loader.py` | 186-196 | **_read_jsonl no file existence check** - Will raise unhandled FileNotFoundError |
| 12 | `evaluator.py` | 69-71 | **device="auto" logic flawed** - Falls back to CPU silently, user may not realize GPU not used |
| 13 | `evaluator.py` | 103-120 | **evaluate() no batch handling** - Processes samples one-by-one, extremely slow for large eval sets |
| 14 | `evaluator.py` | 158-184 | **_sentence_bleu edge case bug** - When pred_chars is empty after non-empty check, returns 0.0 but division may occur |
| 15 | `evaluator.py` | 208-218 | **_compute_perplexity no model.eval() context** - Model already calls eval() but no gradient context manager |
| 16 | `example_usage.py` | 25-35 | **example_basic_training() uses removed fields** - use_flash_attention, data_format, wandb_project will cause TypeError |
| 17 | `example_usage.py` | 52-58 | **example_with_preset() overrides wrong keys** - TrainingConfig field names differ from config_dict keys |
| 18 | `__init__.py` | N/A | **Missing exports** - data_loader module not exported (DataLoader, SFTDataLoader, DataConfig missing) |

---

## 2. Hidden Issues

| # | Category | File | Line | Issue |
|---|----------|------|------|-------|
| H1 | 🔴 Security | `config_builder.py` | 133-136 | **YAML load unsafe pattern** - yaml.safe_load is safe, but merging configs could allow key injection |
| H2 | 🔴 Security | `trainer.py` | 87-91 | **trust_remote_code=True by default** - Loads arbitrary code from HuggingFace hub without user consent |
| H3 | ⚠️ Performance | `data_loader.py` | 89-95 | **Tokenization in __init__ blocks** - All samples tokenized synchronously during Dataset init, no lazy loading |
| H4 | ⚠️ Performance | `evaluator.py` | 103-120 | **No DataLoader batching for eval** - Sequential processing wastes GPU parallelism |
| H5 | ⚠️ Resource Leak | `evaluator.py` | 69-71 | **Model loaded but never unloaded** - No cleanup method, long-running processes accumulate models |
| H6 | ⚠️ Memory | `data_loader.py` | 89-95 | **All tokens stored in memory** - Large datasets (100k+ samples) will OOM |
| H7 | ⚠️ Thread Safety | `config_builder.py` | 48-50 | **_presets mutable instance variable** - deepcopy in __init__ but merge_configs shares state |
| H8 | ⚠️ Exception | `trainer.py` | 157-168 | **_load_dataset bare exception risk** - datasets.load_dataset can raise multiple exception types |
| H9 | ⚠️ Boundary | `data_loader.py` | 174-177 | **eval_ratio=0 means no eval set** - Split produces empty eval dataset with no warning |
| H10 | ⚠️ Boundary | `evaluator.py` | 158-184 | **BLEU with empty reference** - Division by zero when reference is empty string |
| H11 | ⚠️ Config | `trainer.py` | 57 | **dataset_text_field="text" hardcoded default** - But data_loader produces formatted text, field name mismatch |
| H12 | ⚠️ Cross-platform | `config_builder.py` | 78-80 | **Unix-style absolute paths** - `/data/guwen/...` fails on Windows |
| H13 | ⚠️ API Contract | `evaluator.py` | 97-100 | **evaluate() returns Dict but type hint says Dict[str, float]** - ROUGE scores nested dict doesn't match |
| H14 | ⚠️ Unused Import | `evaluator.py` | 17 | **numpy imported but never used** |
| H15 | ⚠️ Logging | `trainer.py` | 118-141 | **No progress logging during model load** - Long operation appears hung |
| H16 | ⚠️ Validation | `config_builder.py` | 153-157 | **Learning rate validation too weak** - Only warns, doesn't prevent dangerous values like 0 or negative |

---

## 3. Root Cause

| Issue | Root Cause |
|-------|-----------|
| 1-2 (GRPO incomplete) | **Feature stubbed but exposed in public API** - GRPOTrainer class visible but not implemented |
| 3 (No resume) | **TrainingArguments checkpoint not configured** - No resume_from_checkpoint parameter passed |
| 4-5-8-11 (Missing validation/error handling) | **Assumption of perfect inputs** - Code assumes datasets/files/configs always valid |
| 6 (eval_steps=None) | **Conditional logic incomplete** - Should provide default value or skip evaluation_strategy |
| 7-12 (Hardcoded paths) | **Environment-specific defaults** - Paths should be configurable via environment or CLI |
| 9-10-14 (Data loader issues) | **No defensive programming** - Missing null checks, seeds, file existence verification |
| 13 (Device fallback) | **Silent degradation** - User should be notified when GPU unavailable |
| 15 (Perplexity computation) | **Inefficient per-sample processing** - Should batch for efficiency |
| 16-17 (Stale examples) | **Documentation drift** - Examples not updated after refactors |
| 18 (Missing exports) | **Incomplete __all__** - New modules not added to package exports |
| H1-H2 (Security) | **Trust boundaries not enforced** - Remote code execution enabled by default |
| H3-H6 (Performance/Memory) | **No streaming/lazy loading** - All data loaded into memory upfront |
| H7 (Thread safety) | **Mutable shared state** - ConfigBuilder instances can share _presets reference |
| H9-H10 (Boundary) | **Edge cases not tested** - Empty strings, zero ratios not handled |
| H11 (API mismatch) | **Module decoupling failure** - trainer expects different data format than data_loader produces |
| H12 (Cross-platform) | **Path handling not abstracted** - Should use pathlib throughout |
| H13 (Return type) | **Type hint inaccurate** - ROUGE returns nested dict, not flat Dict[str, float] |
| H14 (Unused import) | **Dead code** - numpy import leftover from development |
| H15-H16 (Logging/Validation) | **Observability gaps** - Long operations silent, invalid values only warned |

---

## 4. Recommended Fix

### Fix 1: GRPOTrainer - Remove or Implement
```python
# BEFORE (trainer.py:237-253)
class GRPOTrainer:
    def __init__(self, config: TrainingConfig):
        self.config = config
        self._model = None
        self._reward_model = None
        self._ref_model = None

# AFTER: Remove incomplete class or mark as internal
class _GRPOTrainerPlaceholder:
    """GRPO training - NOT YET IMPLEMENTED.
    
    This class is a placeholder and should not be used in production.
    See TODO: Implement reward model integration, KL penalty, group scoring.
    """
    pass
```

### Fix 2: Add Checkpoint Resume
```python
# BEFORE (trainer.py:97-101)
# While save_steps and save_total_limit are set, there's no documentation
# about resuming from checkpoints...

# AFTER: Add resume capability
def train(self, resume_from_checkpoint: Optional[str] = None):
    """Execute the full training pipeline.
    
    Args:
        resume_from_checkpoint: Path to checkpoint directory to resume from.
                               If None, starts fresh training.
    """
    # ... existing code ...
    
    # Step 5: Train
    logger.info("Starting training...")
    if resume_from_checkpoint:
        logger.info(f"Resuming from checkpoint: {resume_from_checkpoint}")
    self._trainer.train(resume_from_checkpoint=resume_from_checkpoint)
```

### Fix 3: Add Dataset Validation
```python
# BEFORE (trainer.py:157-168)
def _load_dataset(self):
    logger.info(f"Loading dataset: {self.config.dataset_path}")
    if self.config.dataset_path.endswith(".jsonl"):
        dataset = load_dataset("json", data_files=self.config.dataset_path)
    else:
        dataset = load_dataset(self.config.dataset_path)
    # ...

# AFTER: Add validation
def _load_dataset(self):
    logger.info(f"Loading dataset: {self.config.dataset_path}")
    
    # Validate file exists
    if not Path(self.config.dataset_path).exists():
        raise FileNotFoundError(f"Dataset not found: {self.config.dataset_path}")
    
    try:
        if self.config.dataset_path.endswith(".jsonl"):
            dataset = load_dataset("json", data_files=self.config.dataset_path)
        else:
            dataset = load_dataset(self.config.dataset_path)
    except Exception as e:
        raise RuntimeError(f"Failed to load dataset: {e}") from e
    
    # Validate dataset structure
    self._validate_dataset(dataset)
    return dataset

def _validate_dataset(self, dataset):
    """Validate dataset has required fields and reasonable content."""
    required_fields = ["instruction", "output"]  # or "text" depending on format
    sample = dataset["train"][0] if "train" in dataset else dataset[0]
    for field in required_fields:
        if field not in sample:
            raise ValueError(f"Dataset missing required field: {field}")
```

### Fix 4: Fix Hardcoded Paths
```python
# BEFORE (config_builder.py:78-80)
config.setdefault("dataset_path", "/data/guwen/training_v2.jsonl")
config.setdefault("eval_dataset_path", "/data/guwen/eval_v2.jsonl")
config.setdefault("output_dir", "/models/guwen-llm/checkpoints")

# AFTER: Use environment variables or relative paths
import os
config.setdefault("dataset_path", os.environ.get("GUWEN_DATASET_PATH", "./data/training_v2.jsonl"))
config.setdefault("eval_dataset_path", os.environ.get("GUWEN_EVAL_PATH", "./data/eval_v2.jsonl"))
config.setdefault("output_dir", os.environ.get("GUWEN_OUTPUT_DIR", "./outputs/guwen-llm/checkpoints"))
```

### Fix 5: Add Deterministic Seed
```python
# BEFORE (data_loader.py:174-177)
import random
random.shuffle(samples)

# AFTER:
import random
random.seed(self.config.seed if hasattr(self.config, 'seed') else 42)
random.shuffle(samples)
logger.info(f"Shuffled samples with seed={random.getstate()}")
```

### Fix 6: Fix Type Hint and Return Value
```python
# BEFORE (evaluator.py:88-92)
def evaluate(self, eval_data: List[Dict],
             metrics: Optional[List[str]] = None) -> Dict[str, float]:

# AFTER:
from typing import Union
def evaluate(self, eval_data: List[Dict],
             metrics: Optional[List[str]] = None) -> Dict[str, Union[float, Dict]]:
```

### Fix 7: Remove Unused Import
```python
# BEFORE (evaluator.py:17)
import torch
import numpy as np
from transformers import AutoModelForCausalLM, AutoTokenizer

# AFTER:
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
```

### Fix 8: Add Proper Error Handling
```python
# BEFORE (data_loader.py:186-196)
def _read_jsonl(self, path: str) -> List[Dict]:
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            # ...

# AFTER:
def _read_jsonl(self, path: str) -> List[Dict]:
    if not Path(path).exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            # ...
```

### Fix 9: Add Null Check in encode_sample
```python
# BEFORE (data_loader.py:105-112)
def _encode_sample(self, sample: Dict) -> Optional[Dict]:
    text = self._format_sample(sample)
    if not text:
        return None

# AFTER:
def _encode_sample(self, sample: Dict) -> Optional[Dict]:
    if not sample or not isinstance(sample, dict):
        logger.warning(f"Invalid sample: {sample}")
        return None
    text = self._format_sample(sample)
    if not text:
        return None
```

### Fix 10: Add Package Exports
```python
# BEFORE (__init__.py:11-12)
from .trainer import Trainer, TrainingConfig
from .evaluator import Evaluator
from .config_builder import ConfigBuilder

__all__ = ["Trainer", "TrainingConfig", "Evaluator", "ConfigBuilder"]

# AFTER:
from .trainer import Trainer, TrainingConfig
from .evaluator import Evaluator
from .config_builder import ConfigBuilder
from .data_loader import SFTDataLoader, DataConfig, InstructionDataset

__all__ = [
    "Trainer", "TrainingConfig", "Evaluator", "ConfigBuilder",
    "SFTDataLoader", "DataConfig", "InstructionDataset"
]
```

---

## 5. Steps Taken

| Step | Action | Discovery |
|------|--------|-----------|
| 1 | Read all 6 source files | Identified file structure and module dependencies |
| 2 | Analyzed trainer.py line-by-line | Found GRPO placeholder, missing resume, no dataset validation |
| 3 | Analyzed config_builder.py | Found hardcoded paths, weak validation, exception handling gaps |
| 4 | Analyzed data_loader.py | Found non-deterministic shuffle, no file checks, memory issues |
| 5 | Analyzed evaluator.py | Found unused numpy, type hint mismatch, sequential eval |
| 6 | Analyzed example_usage.py | Found stale examples with removed fields |
| 7 | Applied 10-point checklist to each function | Found 16 surface issues + 16 hidden issues |
| 8 | Cross-referenced modules | Found API mismatches between trainer and data_loader |
| 9 | Reviewed security implications | Found trust_remote_code=True default, YAML loading |
| 10 | Compiled findings into structured report | This deliverable |

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| Manual code review | Line-by-line analysis of all 6 files |
| 10-point function checklist | Systematic inspection of each function |
| Dependency graph analysis | Traced data flow between modules |
| Type hint verification | Checked return type annotations vs actual returns |
| Security pattern matching | Identified trust_remote_code, YAML loading risks |
| Edge case analysis | Identified boundary conditions (empty strings, zero ratios) |

---

## 7. Verification

### Commands to Verify Findings

```bash
# 1. Verify GRPOTrainer raises NotImplementedError
python -c "from src.training.trainer import GRPOTrainer; t = GRPOTrainer(None); t.train()"

# 2. Verify hardcoded paths don't exist
test -f /data/guwen/training_v2.jsonl && echo "EXISTS" || echo "NOT FOUND (expected)"

# 3. Verify numpy is unused in evaluator.py
grep -n "np\." src/training/evaluator.py  # Should return nothing

# 4. Verify missing exports
python -c "from src.training import SFTDataLoader"  # Should fail before fix

# 5. Verify non-deterministic shuffle
python -c "
from src.training.data_loader import SFTDataLoader
import random
# Run twice and compare order
"

# 6. Verify trust_remote_code default
grep -n "trust_remote_code=True" src/training/trainer.py  # Lines 87, 131

# 7. Verify example_usage has stale fields
grep -n "use_flash_attention\|data_format\|wandb_project" src/training/example_usage.py
```

### Pre-Flight Checklist Before First Training Run

```bash
# □ Override dataset_path from hardcoded /data/guwen/...
# □ Set output_dir to writable location
# □ Verify CUDA/GPU availability: python -c "import torch; print(torch.cuda.is_available())"
# □ Verify bf16 support: python -c "import torch; print(torch.cuda.is_bf16_supported())"
# □ Install rouge_score if ROUGE metrics needed: pip install rouge_score
# □ Review trust_remote_code=True security implications
# □ Set WANDB_PROJECT env var if wandb reporting desired
# □ Test with small dataset subset first
```

---

## Summary

**Total Issues Found: 34**
- Surface Issues: 18
- Hidden Issues: 16

**Critical Blockers (must fix before first run):**
1. Hardcoded dataset paths (`/data/guwen/...`)
2. No dataset validation (corrupt/missing data will crash mid-training)
3. No checkpoint resume (training interruption = total loss)
4. GRPOTrainer exposed but non-functional

**High Priority:**
5. Non-deterministic data splits (reproducibility)
6. Silent GPU→CPU fallback (performance surprise)
7. Stale example code (misleading documentation)
8. Missing module exports

**Production Readiness: ❌ NOT READY**

Recommend addressing critical blockers before first training run, then iterating on high-priority items.
