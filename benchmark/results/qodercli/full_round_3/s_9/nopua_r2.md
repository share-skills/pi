# Scenario 9: Training Pipeline End-to-End Audit
## Condition: nopua | Run: 2
## Duration: 30.14s

---

Now let me systematically analyze each file for production readiness issues:

## Investigation Summary

### Tools Used
- **Manual Code Review**: Analyzed all 6 provided source files line-by-line
- **Pattern Recognition**: Identified anti-patterns, missing error handling, and security concerns

---

## 1. Issues Found

### **P0: Critical Issues**

#### Issue 1.1: Hardcoded Paths Will Cause Immediate Failure
**Location**: `config_builder.py:78-80`, `trainer.py:93`
```python
config.setdefault("dataset_path", "/data/guwen/training_v2.jsonl")
config.setdefault("eval_dataset_path", "/data/guwen/eval_v2.jsonl")
config.setdefault("output_dir", "/models/guwen-llm/checkpoints")
```
**Problem**: These paths don't exist on most machines. Training will fail immediately with "Dataset not found" or permission errors.

#### Issue 1.2: No Data Validation Before Training
**Location**: `trainer.py:144-152`
```python
def _load_dataset(self):
    dataset = load_dataset("json", data_files=self.config.dataset_path)
```
**Problem**: No validation that:
- Required fields exist in JSONL records (`instruction`, `output`)
- Data is not empty or corrupted
- Samples have reasonable token lengths

#### Issue 1.3: GRPO Trainer Is Non-Functional Placeholder
**Location**: `trainer.py:217-244`
```python
class GRPOTrainer:
    def __init__(self, config: TrainingConfig):
        self._model = None
        self._reward_model = None  # Never initialized
        self._ref_model = None     # Never initialized
    
    def train(self):
        raise NotImplementedError("GRPO training is not yet implemented...")
```
**Problem**: GRPO trainer claims to be a feature but raises `NotImplementedError`. Users may waste time configuring it.

#### Issue 1.4: Evaluator Silently Skips Metrics on Import Error
**Location**: `evaluator.py:134-143`
```python
def _compute_rouge(self, predictions, references):
    try:
        from rouge_score import rouge_scorer
        ...
    except ImportError:
        logger.warning("rouge_score not installed, skipping ROUGE")
        return {}  # Returns empty dict - user may not notice metric missing
```
**Problem**: ROUGE silently returns `{}` if library not installed. User may think evaluation passed when key metrics are missing.

---

### **P1: High Severity Issues**

#### Issue 2.1: BLEU Score Calculation Bug for Short Predictions
**Location**: `evaluator.py:106-117`
```python
if len(pred_chars) < len(ref_chars):
    bp = math.exp(1 - len(ref_chars) / len(pred_chars))
else:
    bp = 1.0
```
**Problem**: When prediction is shorter than reference, the brevity penalty can produce negative values inside `exp()`, leading to incorrect scores. For very short predictions, this produces extremely small penalties.

#### Issue 2.2: Division by Zero in Perplexity
**Location**: `evaluator.py:155-161`
```python
total_loss = 0.0
total_tokens = 0
...
avg_loss = total_loss / total_tokens if total_tokens > 0 else float("inf")
return math.exp(avg_loss)
```
**Problem**: If `eval_data` is empty, returns `math.exp(inf) = inf`. No warning logged when this happens.

#### Issue 2.3: Random Seed Not Set for Reproducibility
**Location**: `data_loader.py:171`
```python
import random
random.shuffle(samples)
```
**Problem**: `random.seed()` never called. Dataset shuffling is non-deterministic between runs even though `TrainingConfig.seed = 42` exists.

#### Issue 2.4: ConfigBuilder.validate() Returns Warnings But Never Blocks
**Location**: `config_builder.py:112-147`
```python
def validate(self, config: Dict[str, Any]) -> List[str]:
    warnings = []
    # ... adds warnings but never raises
    return warnings
```
**Problem**: Method returns warnings list but nothing enforces checking them. Training proceeds with invalid configs.

---

### **P2: Medium Severity Issues**

#### Issue 3.1: Example Usage File Contains Outdated Code
**Location**: `example_usage.py:17-25`
```python
config = TrainingConfig(
    model_name="Qwen/Qwen2-7B",
    # use_flash_attention=True,   # Removed in v0.3.0 — will cause TypeError
    # data_format="alpaca",       # Removed in v0.3.0 — will cause TypeError
)
```
**Problem**: Comments document removed parameters but code still shows them. Users copying examples get confused.

#### Issue 3.2: Label Masking Logic May Be Incorrect
**Location**: `data_loader.py:85-92`
```python
if self.config.label_mask_input:
    instruction = self._get_instruction_part(sample)
    instruction_tokens = self.tokenizer(
        instruction, return_tensors="pt", add_special_tokens=False,
    )
    n_mask = instruction_tokens["input_ids"].shape[1]
    labels[:n_mask] = -100
```
**Problem**: Assumes instruction tokens always appear at start of full text. With ChatML template, special tokens (`
