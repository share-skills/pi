# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pi | Run: 2
## Duration: 132.43s

---

Now I have a comprehensive understanding of the codebase. Let me compile my findings:

---

# Training Pipeline End-to-End Audit Report

## 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | GRPOTrainer not implemented - raises NotImplementedError | trainer.py:300-312 | 🔴 Blocker |
| 2 | Dataset validation missing before training | trainer.py:146-156, trainer.py:238-253 | 🔴 Blocker |
| 3 | No checkpoint resume support despite save_steps configured | trainer.py:80-89, trainer.py:174 | 🔴 Blocker |
| 4 | Random seed not set for data shuffle (non-deterministic) | data_loader.py:221-222 | 🟡 Major |
| 5 | Evaluator results stored in instance var but never updated | evaluator.py:60, evaluator.py:128 | 🟡 Major |
| 6 | Hardcoded absolute paths in presets (will fail on most machines) | config_builder.py:100-102 | 🟡 Major |
| 7 | Example usage file is stale/misleading with commented-out broken code | example_usage.py:32-34 | 🟡 Major |
| 8 | Unused imports: `os`, `json` in trainer.py | trainer.py:21-22 | ⚪ Minor |
| 9 | Unused import: `np` in evaluator.py | evaluator.py:25 | ⚪ Minor |
| 10 | Click dependency for CLI not guarded (import inside function) | trainer.py:322-333 | ⚪ Minor |

---

## 2. Hidden Issues

| # | Issue | Location | Category |
|---|-------|----------|----------|
| 1 | **Security**: `trust_remote_code=True` hardcoded without user opt-out | trainer.py:49, evaluator.py:66-71 | 🔒 Security |
| 2 | **Security**: No API key/auth check for model hub access | trainer.py:198-204, evaluator.py:65-73 | 🔒 Security |
| 3 | **Resource leak risk**: No cleanup for partially loaded models on failure | trainer.py:181-236 | ⚡ Performance |
| 4 | **Memory**: Label masking may be incorrect for variable-length sequences | data_loader.py:109-120 | ✅ Correctness |
| 5 | **Race condition**: Global random state used without local seeding | data_loader.py:221-222 | 🧵 Thread Safety |
| 6 | **Silent failure**: Empty samples returned as empty string without logging | data_loader.py:134-135 | ⚠️ Error Handling |
| 7 | **Division by zero**: perplexity returns inf but no warning logged | evaluator.py:257 | ⚠️ Edge Case |
| 8 | **Hardcoded dtype**: Evaluator forces bfloat16 regardless of config | evaluator.py:70 | ⚙️ Configuration |
| 9 | **Missing dependency check**: rouge_score import not in requirements | evaluator.py:222 | ⚙️ Configuration |
| 10 | **Inconsistent template**: CHATML template uses Traditional Chinese but module targets Classical Chinese | data_loader.py:39-48 | 📖 Consistency |
| 11 | **No gradient accumulation warmup**: First step has different behavior | trainer.py:255-278 | ⚡ Performance |
| 12 | **Unused class attributes**: `_reward_model`, `_ref_model` never initialized | trainer.py:297-298 | 🗑️ Dead Code |
| 13 | **No eval during training**: evaluation_strategy="no" when no eval dataset | trainer.py:273 | 📊 Monitoring |
| 14 | **Label smoothing not configurable**: Missing hyperparameter | trainer.py:43-95 | ⚙️ Configuration |
| 15 | **No OOM protection**: No memory-efficient loading fallback | trainer.py:198-204 | ⚡ Performance |

---

## 3. Root Cause Analysis

### 3.1 GRPOTrainer Not Implemented (trainer.py:300-312)
**Root Cause**: The GRPO (Group Relative Policy Optimization) training pipeline requires complex infrastructure (reward model, reference model, KL penalty computation) that was never built. The class exists as a stub.

**Evidence**: 
- Line 305: `# TODO: Implement GRPO training`
- Lines 297-298: `self._reward_model = None` and `self._ref_model = None` are explicitly marked as "Never initialized"
- Line 310-312: Raises `NotImplementedError`

### 3.2 Missing Dataset Validation (trainer.py:146-156)
**Root Cause**: The `_load_dataset()` method loads data directly without validating schema, required fields, or data quality. This causes silent failures or corrupted training.

**Evidence**:
- Lines 146-150: Comment acknowledges the issue: "The dataset is loaded and used directly without checking..."
- Lines 238-253: Only checks file format (.jsonl), not content structure

### 3.3 No Checkpoint Resume (trainer.py:80-89)
**Root Cause**: While `save_steps` and `save_total_limit` are configured, there's no mechanism to resume from checkpoints after interruption. Training progress is lost.

**Evidence**:
- Lines 87-89: Comment notes "there's no documentation about resuming from checkpoints"
- Line 174: `self._trainer.train()` called without `resume_from_checkpoint` parameter
- CLI has `--resume` option (line 326) but it's never passed to train()

### 3.4 Non-Deterministic Data Shuffling (data_loader.py:221-222)
**Root Cause**: `random.shuffle()` uses global random state without seeding, making train/eval splits non-reproducible.

**Evidence**:
- Line 222: `random.shuffle(samples)` with no prior `random.seed()` call
- Config has `seed: int = 42` (trainer.py:92) but it's not propagated to DataLoader

### 3.5 Evaluator Results Stale (evaluator.py:60, 128)
**Root Cause**: `self.results` is initialized but never updated after `evaluate()` runs. The method returns a local `results` dict instead.

**Evidence**:
- Line 60: `self.results: Dict[str, float] = {}`
- Line 128: `return results` (local variable, not assigned to self.results)
- example_usage.py lines 78-79 confirms this bug: "evaluator.results may not reflect the latest run"

### 3.6 Hardcoded Absolute Paths (config_builder.py:100-102)
**Root Cause**: Presets use hardcoded paths like `/data/guwen/training_v2.jsonl` that won't exist on most systems.

**Evidence**:
- Lines 100-102: `config.setdefault("dataset_path", "/data/guwen/training_v2.jsonl")`
- These paths assume specific directory structure that doesn't exist

### 3.7 Security: trust_remote_code=True Hardcoded
**Root Cause**: Remote code execution is enabled by default without user awareness or opt-out mechanism.

**Evidence**:
- trainer.py:49: `trust_remote_code: bool = True` (default value)
- evaluator.py:66-71: Both tokenizer and model load with `trust_remote_code=True`

---

## 4. Recommended Fixes

### 4.1 Fix GRPOTrainer or Remove It
```python
# Option A: Remove the stub entirely (recommended)
# Delete lines 290-317 from trainer.py

# Option B: Mark as deprecated
class GRPOTrainer:
    """DEPRECATED: Use SFT trainer instead. GRPO support removed."""
    def __init__(self, config: TrainingConfig):
        raise DeprecationWarning("GRPOTrainer is deprecated. Use Trainer for SFT.")
```

### 4.2 Add Dataset Validation
```python
# In trainer.py, add before training:
def _validate_dataset(self, dataset):
    """Validate dataset structure and content."""
    if not dataset:
        raise ValueError("Dataset is empty")
    
    # Check required fields
    sample = dataset[0] if isinstance(dataset, list) else dataset["train"][0]
    required_fields = ["input_ids", "attention_mask", "labels"]
    for field in required_fields:
        if field not in sample:
            raise ValueError(f"Missing required field: {field}")
    
    # Check for NaN/Inf
    if torch.isnan(sample["input_ids"]).any():
        raise ValueError("Dataset contains NaN values")
```

### 4.3 Add Checkpoint Resume Support
```python
# In trainer.py train() method:
def train(self, resume_from_checkpoint: Optional[str] = None):
    # ... existing code ...
    
    # Step 5: Train with resume support
    logger.info("Starting training...")
    self._trainer.train(resume_from_checkpoint=resume_from_checkpoint)
```

### 4.4 Fix Random Seeding
```python
# In data_loader.py load() method:
def load(self, data_path: str, eval_ratio: float = 0.05, seed: int = 42):
    # ... existing code ...
    
    # Set seeds for reproducibility
    import random
    random.seed(seed)
    torch.manual_seed(seed)
    random.shuffle(samples)
```

### 4.5 Fix Evaluator Results
```python
# In evaluator.py evaluate() method:
def evaluate(self, eval_data: List[Dict], metrics: Optional[List[str]] = None):
    # ... existing code ...
    
    self.results = results  # Add this line
    return results
```

### 4.6 Remove Hardcoded Paths
```python
# In config_builder.py from_preset() method:
def from_preset(self, preset_name: str, **overrides) -> Dict[str, Any]:
    # ... existing code ...
    
    # Use relative paths or require explicit override
    config.setdefault("dataset_path", "./data/training.jsonl")
    config.setdefault("eval_dataset_path", "./data/eval.jsonl")
    config.setdefault("output_dir", "./outputs/checkpoints")
```

### 4.7 Make trust_remote_code Configurable
```python
# In TrainingConfig:
trust_remote_code: bool = False  # Default to False for security

# User must explicitly enable if needed
```

---

## 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read all 6 training module files | Identified module structure |
| 2 | Searched for `trust_remote_code` usage | Found hardcoded True in 5 locations |
| 3 | Searched for `device_map` usage | Found auto device mapping without fallback |
| 4 | Searched for `NotImplementedError` | Found GRPO stub at trainer.py:310 |
| 5 | Searched for random seed settings | **Initially thought** seeds were set properly, **but upon closer inspection** only TrainingConfig has seed field - it's never propagated to DataLoader |
| 6 | Searched for TODO/FIXME comments | Found unimplemented GRPO at trainer.py:305 |
| 7 | Searched for exception handling patterns | Found proper exception handling (no bare excepts) |
| 8 | Searched for file I/O patterns | Found all file operations use context managers (good) |
| 9 | Analyzed evaluator.py results handling | **Initially I thought** results were stored correctly, **actually** self.results is never updated |
| 10 | Compared preset paths vs typical filesystem | Confirmed hardcoded paths will fail |
| 11 | Cross-referenced example_usage.py with current API | Found stale comments and misleading examples |
| 12 | Expanded scope to check for unused imports | Found os, json unused in trainer.py; np unused in evaluator.py |

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read all 6 Python source files |
| `Grep` | Search for patterns across files (trust_remote_code, NotImplementedError, random.seed, etc.) |
| `Glob` | Locate training module files in repository |
| `Bash` | Verify directory structure |

---

## 7. Verification

Run these commands to verify findings:

```bash
# 1. Verify GRPO not implemented
grep -n "raise NotImplementedError" benchmark/data/test-project/src/training/trainer.py
# Expected: Line 310

# 2. Verify missing dataset validation
grep -A5 "def _load_dataset" benchmark/data/test-project/src/training/trainer.py
# Expected: No validation logic

# 3. Verify random seed not set
grep -B2 -A2 "random.shuffle" benchmark/data/test-project/src/training/data_loader.py
# Expected: No random.seed() call

# 4. Verify evaluator.results not updated
grep -A3 "def evaluate" benchmark/data/test-project/src/training/evaluator.py | tail -5
grep "self.results =" benchmark/data/test-project/src/training/evaluator.py
# Expected: No assignment to self.results

# 5. Verify hardcoded paths
grep -n "/data/guwen" benchmark/data/test-project/src/training/config_builder.py
# Expected: Lines 100-102

# 6. Verify trust_remote_code hardcoded
grep -n "trust_remote_code.*True" benchmark/data/test-project/src/training/*.py
# Expected: Multiple matches with True literal

# 7. Verify unused imports
python3 -c "
import ast
with open('benchmark/data/test-project/src/training/trainer.py') as f:
    tree = ast.parse(f.read())
imports = [n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)]
print('Imports:', imports)
# Manually verify os, json not used
"
```

---

## Summary

**Total Issues Found**: 25
- Surface Issues: 10
- Hidden Issues: 15

**Critical Blockers**: 3
1. GRPO not implemented but exposed in API
2. No dataset validation before training
3. No checkpoint resume despite save configuration

**Security Concerns**: 2
1. `trust_remote_code=True` without opt-out
2. No auth/API key validation for model hub

**Production Readiness**: ❌ **NOT READY**

The training module requires significant work before production use. Primary blockers are the unimplemented GRPO trainer, missing dataset validation, and lack of checkpoint resume. Security concerns around remote code execution should also be addressed.
