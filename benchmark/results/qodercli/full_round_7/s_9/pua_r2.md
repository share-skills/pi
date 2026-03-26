# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pua | Run: 2
## Duration: 63.0s

---

## Training Pipeline End-to-End Audit — Complete Analysis

### Investigation Methodology

**Files Analyzed:**
- `trainer.py` (337 lines) - Main training pipeline
- `config_builder.py` (216 lines) - Configuration management
- `data_loader.py` (249 lines) - Data loading and preprocessing
- `evaluator.py` (258 lines) - Model evaluation
- `example_usage.py` (99 lines) - Usage examples
- `__init__.py` (17 lines) - Module exports

---

## 1. ISSUES FOUND

### **CRITICAL Issues**

#### Issue 1.1: No Resume from Checkpoint Support (`trainer.py:80-95`)
**Location:** `TrainingConfig` dataclass, `trainer.py:80-95`

**Problem:** The config has `save_steps` and `save_total_limit` but:
- No `resume_from_checkpoint` field
- No logic in `train()` to detect/resume from interrupted training
- CLI has `--resume` option (`trainer.py:326`) but it's unused in the function body

**Impact:** Training interruptions cause complete loss of progress. For multi-day training jobs on large models, this is catastrophic.

**Evidence:**
```python
# trainer.py:326-331 - resume parameter exists but is NEVER USED
@click.option("--resume", "-r", default=None, help="Resume from checkpoint")
def train(config, resume):
    """Run model training."""
    logging.basicConfig(level=logging.INFO)
    trainer = Trainer(config)
    trainer.train()  # <-- resume is ignored!
```

---

#### Issue 1.2: Dataset Validation Completely Missing (`trainer.py:238-253`)
**Location:** `_load_dataset()` method, `trainer.py:238-253`

**Problem:** The dataset is loaded without any validation:
- No check for required fields (`instruction`, `output`)
- No check for empty/corrupt samples
- No check for tokenized sequence lengths vs `max_seq_length`
- No statistics on data distribution

**Impact:** Silent training failures or garbage-in-garbage-out scenarios.

**Evidence:**
```python
# trainer.py:146-150 - Comment acknowledges the problem but no fix
# The dataset is loaded and used directly without checking:
# - Required fields exist
# - No empty/corrupt samples
# - Data distribution is reasonable
# - Tokenized lengths are within max_seq_length
```

---

#### Issue 1.3: GRPOTrainer is Non-Functional Stub (`trainer.py:291-317`)
**Location:** `GRPOTrainer` class, `trainer.py:291-317`

**Problem:** 
- `_reward_model` and `_ref_model` declared but never initialized
- `train()` raises `NotImplementedError`
- `_compute_rewards()` returns `[0.0] * len(outputs)` — always zero reward

**Impact:** If users attempt RLHF training, they will get a runtime error mid-pipeline.

---

#### Issue 1.4: Hardcoded Paths in Presets Will Fail (`config_builder.py:100-102`)
**Location:** `from_preset()` method, `config_builder.py:100-102`

**Problem:** Presets set absolute paths that won't exist on most machines:
```python
config.setdefault("dataset_path", "/data/guwen/training_v2.jsonl")
config.setdefault("eval_dataset_path", "/data/guwen/eval_v2.jsonl")
config.setdefault("output_dir", "/models/guwen-llm/checkpoints")
```

**Impact:** Users must manually override these paths or training will fail with "file not found" errors.

---

### **HIGH Severity Issues**

#### Issue 2.1: Label Masking Bug — Off-by-One Error (`data_loader.py:108-117`)
**Location:** `_encode_sample()` method, `data_loader.py:108-117`

**Problem:** The label masking logic assumes instruction tokens are at the start, but ChatML template includes system prompt before the instruction:
```python
# data_loader.py:116-117
n_mask = instruction_tokens["input_ids"].shape[1]
labels[:n_mask] = -100  # WRONG: misses the
