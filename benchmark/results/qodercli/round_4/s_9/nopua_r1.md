# Scenario 9: Training Pipeline End-to-End Audit
## Condition: nopua | Run: 1
## Duration: 95.49s

---

---

## 📋 Training Module Production Readiness Audit

### Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 8 |
| 🟠 High | 7 |
| 🟡 Medium | 5 |
| **Total Issues** | **20** |
| **Hidden Issues** | **6** |

---

## 1. Issues Found

### 🔴 CRITICAL (Blocking for Production)

#### 1.1 No Data Validation Before Training (`trainer.py:167-173`)
**Location:** `trainer.py:167-173`
```python
# Step 2: Load dataset
dataset = self._load_dataset()
```
**Problem:** Dataset is loaded without any validation:
- No check for required fields (`instruction`, `output`)
- No validation for empty/corrupt samples
- No check for data distribution
- No validation that tokenized lengths fit within `max_seq_length`

**Risk:** Training will fail mid-run or produce corrupted models if data is malformed.

---

#### 1.2 Checkpoint Resume Not Implemented (`trainer.py:57-62`)
**Location:** `TrainingConfig` dataclass comment acknowledges the gap:
```python
# While save_steps and save_total_limit are set, there's no documentation
# about resuming from checkpoints, which checkpoints to keep, or how
# to handle training interruptions. The user might lose training progress.
```
**Problem:** 
- No `resume_from_checkpoint` parameter in `TrainingConfig`
- CLI has `--resume` flag but it's unused in the `train()` function
- If training crashes at step 4500 (with `save_steps=500`), all progress since step 4000 is lost

**Risk:** Wasted compute hours and money on long-running jobs.

---

#### 1.3 GRPO Trainer Is Non-Functional Placeholder (`trainer.py:259-280`)
**Location:** `trainer.py:259-280`
```python
class GRPOTrainer:
    def __init__(self, config: TrainingConfig):
        self.config = config
        self._model = None
        self._reward_model = None  # Never initialized
        self._ref_model = None     # Never initialized

    def train(self):
        raise NotImplementedError(
            "GRPO training is not yet implemented. Use SFT trainer instead."
        )
```
**Problem:** 
- `_reward_model` and `_ref_model` are declared but never initialized
- `train()` raises `NotImplementedError`
- No error handling or graceful degradation

**Risk:** Users importing `GRPOTrainer` will crash at runtime with no warning.

---

#### 1.4 Hardcoded Dataset Paths in Presets (`config_builder.py:44-72`)
**Location:** `config_builder.py:44-72`
```python
config.setdefault("dataset_path", "/data/guwen/training_v2.jsonl")
config.setdefault("eval_dataset_path", "/data/guwen/eval_v2.jsonl")
config.setdefault("output_dir", "/models/guwen-llm/checkpoints")
```
**Problem:** 
- Paths like `/data/guwen/training_v2.jsonl` won't exist on most machines
- No validation that these paths exist before training starts
- Users must remember to override every preset

**Risk:** Immediate failure when running presets without manual overrides.

---

#### 1.5 Evaluator Uses Wrong Results Cache (`evaluator.py:98-123`)
**Location:** `evaluator.py:98-123`
```python
def evaluate(self, eval_data: List[Dict], ...) -> Dict[str, float]:
    ...
    logger.info(f"Evaluation results: {results}")
    return results
```
But `example_usage.py:50-53` warns:
```python
# This returns results correctly...
results = evaluator.evaluate(eval_data)
print("Returned results:", results)

# evaluator.results may not reflect the latest run
print("evaluator.results:", evaluator.results)
```
**Problem:** The `self.results` attribute is set in `__init__` but never updated after `evaluate()` runs. Users accessing `evaluator.results` get stale data.

---

#### 1.6 Example File Contains Broken Code (`example_usage.py:24-35`)
**Location:** `example_usage.py:24-35`
```python
config = TrainingConfig(
    model_name="Qwen/Qwen2-7B",
    ...
    # use_flash_attention=True,   # Removed in v0.3.0 — will cause TypeError
    # data_format="alpaca",       # Removed in v0.3.0 — will cause TypeError
)
```
**Problem:** 
- File explicitly states it's "stale" and may cause `TypeError`
- Still ships as part of the module without being marked as deprecated
- No deprecation warnings or migration guide

**Risk:** Users copy-pasting examples will hit immediate errors.

---

#### 1.7 No Error Handling for Model Loading (`trainer.py:181-211`)
**Location:** `trainer.py:181-211`
```python
def _load_model(self):
    logger.info(f"Loading model: {self.config.model_name}")
    
    bnb_config = None
    if self.config.quantization == "4bit":
        bnb_config = BitsAndBytesConfig(...)
    
    model = AutoModelForCausalLM.from_pretrained(...)
```
**Problem:**
- No try/except for network failures
- No check for disk space before downloading multi-GB models
- No fallback if quantization fails on incompatible hardware

**Risk:** Cryptic errors instead of actionable messages.

---

#### 1.8 Evaluation Prompt Mismatch (`evaluator.py:131-144` vs `data_loader.py:17-25`)
**Location:** `evaluator.py:131-144`
```python
def _build_eval_prompt(self, sample: Dict) -> str:
    if input_text:
        return (
            f"
