# Scenario 9: Training Pipeline End-to-End Audit
## Condition: nopua | Run: 2
## Duration: 48.58s

---

Now let me analyze each file systematically. I've already read all the source files provided. Let me identify issues:

## Investigation Summary

### Tools Used
- File analysis of 6 provided source files
- Static code analysis for production readiness patterns

---

## 1. Issues Found

### **CRITICAL - trainer.py**

#### Issue 1.1: No Data Validation Before Training (`trainer.py:157-171`)
```python
def train(self):
    # Step 2: Load dataset
    dataset = self._load_dataset()
    # ... no validation of loaded data
```
**Problem**: Dataset is loaded without checking:
- Required fields exist (`instruction`, `output`)
- Empty/corrupt samples
- Tokenized lengths within `max_seq_length`
- Data distribution (all same class?)

**Risk**: Training proceeds with invalid data, wasting hours of GPU time only to discover bad outputs later.

#### Issue 1.2: No Resume From Checkpoint Logic (`trainer.py:140-173`)
```python
# save_steps and save_total_limit are set, but no resume logic
def train(self):
    # ... training starts fresh always
```
**Problem**: Config has `save_steps=500` and `save_total_limit=3`, but:
- No `resume_from_checkpoint` parameter in `train()` method
- CLI has `--resume` option but it's unused (`train()` ignores it)
- If training crashes at step 2000, user loses all progress

**Risk**: Multi-day training jobs lost due to power/network failure.

#### Issue 1.3: GRPOTrainer Has Uninitialized Attributes (`trainer.py:229-247`)
```python
class GRPOTrainer:
    def __init__(self, config: TrainingConfig):
        self.config = config
        self._model = None
        self._reward_model = None  # Never initialized
        self._ref_model = None     # Never initialized

    def train(self):
        raise NotImplementedError(...)
```
**Problem**: 
- `_reward_model` and `_ref_model` declared but never initialized
- `train()` always raises `NotImplementedError`
- No loading/saving methods
- This is dead code that will fail if anyone tries to use it

**Risk**: User selects GRPO mode expecting RLHF training, gets runtime error after hours of setup.

#### Issue 1.4: Hardcoded Paths in Presets (`config_builder.py:28-67`)
```python
PRESETS = {
    "sft_7b": {
        # ...
        "dataset_path": "/data/guwen/training_v2.jsonl",  # Won't exist
        "eval_dataset_path": "/data/guwen/eval_v2.jsonl", # Won't exist
        "output_dir": "/models/guwen-llm/checkpoints",    # Won't exist
    },
}
```
**Problem**: Default paths are absolute and won't exist on most machines. No validation before training starts.

**Risk**: Training fails immediately or writes to wrong location.

#### Issue 1.5: Missing Error Handling for Model Loading (`trainer.py:176-211`)
```python
def _load_model(self):
    model = AutoModelForCausalLM.from_pretrained(
        self.config.model_name,
        # ... no try/except
    )
```
**Problem**: No handling for:
- Network failures (model download)
- Out of memory during model load
- Missing model on disk
- Corrupted model weights

**Risk**: Opaque crash with stack trace instead of actionable error message.

---

### **HIGH - data_loader.py**

#### Issue 2.1: Random Seed Not Set (`data_loader.py:188-194`)
```python
def load(self, data_path: str, eval_ratio: float = 0.05):
    samples = self._read_jsonl(data_path)
    import random
    random.shuffle(samples)  # Non-deterministic!
```
**Problem**: `random.shuffle()` without seed means:
- Train/eval split differs each run
- Results not reproducible
- Cannot debug data-related issues reliably

**Risk**: Evaluation scores vary randomly, making model comparison impossible.

#### Issue 2.2: Label Masking Bug for Empty Input (`data_loader.py:94-105`)
```python
if self.config.label_mask_input:
    instruction = self._get_instruction_part(sample)
    instruction_tokens = self.tokenizer(
        instruction,
        return_tensors="pt",
        add_special_tokens=False,
    )
    n_mask = instruction_tokens["input_ids"].shape[1]
    labels[:n_mask] = -100
```
**Problem**: This assumes instruction tokens appear at the start of the full token sequence. But ChatML template adds `
