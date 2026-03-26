# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pua | Run: 1
## Duration: 67.46s

---

Now I have a comprehensive understanding of the training module. Let me compile my structured audit report:

---

# Training Pipeline End-to-End Audit Report

## 1. Issues Found (≥3 required)

### Issue 1.1: Hardcoded Dataset Paths in ConfigBuilder Presets
**Location:** `config_builder.py:100-102`, `training_config.yaml:7-8`
**Severity:** CRITICAL

```python
config.setdefault("dataset_path", "/data/guwen/training_v2.jsonl")
config.setdefault("eval_dataset_path", "/data/guwen/eval_v2.jsonl")
config.setdefault("output_dir", "/models/guwen-llm/checkpoints")
```

**Problem:** Presets inject absolute paths that will not exist on most machines. The config validation at `config_builder.py:176-177` warns about missing datasets, but the user cannot override these defaults easily when using `from_preset()`.

**Impact:** Training pipeline will fail immediately with "Dataset not found" errors for first-time users.

---

### Issue 1.2: No Data Validation Before Training
**Location:** `trainer.py:146-150`, `trainer.py:238-253`

**Problem:** Dataset is loaded without any validation:
- No check for required fields (`instruction`, `output`)
- No check for empty/corrupt samples
- No check for tokenized sequence lengths vs `max_seq_length`
- No data distribution analysis

The comment at line 146-150 acknowledges this gap but no fix is implemented.

**Impact:** Training may fail mid-run or produce degraded models due to bad data.

---

### Issue 1.3: GRPOTrainer is Unimplemented Stub
**Location:** `trainer.py:291-317`

```python
def train(self):
    raise NotImplementedError(
        "GRPO training is not yet implemented. Use SFT trainer instead."
    )
```

**Problem:** Module docstring claims "Provides SFT and GRPO training" but GRPO is completely unimplemented. The `_reward_model` and `_ref_model` attributes are declared but never initialized.

**Impact:** Users attempting GRPO training will get runtime errors. Documentation is misleading.

---

### Issue 1.4: Evaluator.results Not Updated After evaluate()
**Location:** `evaluator.py:60`, `evaluator.py:75-129`, `example_usage.py:74-79`

```python
self.results: Dict[str, float] = {}  # Line 60

def evaluate(self, eval_data, metrics=None):
    results = {}  # Local variable, NOT assigned to self.results
    # ... compute metrics into local results ...
    return results  # User must capture return value
```

The test file explicitly documents this bug at `test_training_pipeline.py:54-71`.

**Impact:** Users accessing `evaluator.results` after `evaluate()` will get stale `{}` instead of actual results.

---

### Issue 1.5: No Checkpoint Resume Logic
**Location:** `trainer.py:80-89`, `trainer.py:280-288`

```python
# Checkpointing
output_dir: str = "./outputs/guwen-llm"
save_steps: int = 500
save_total_limit: int = 3
# While save_steps and save_total_limit are set, there's no documentation
# about resuming from checkpoints, which checkpoints to keep, or how
# to handle training interruptions.
```

**Problem:** Checkpoints are saved but there's no resume mechanism. The CLI has a `--resume` flag (`trainer.py:326`) but it's unused—the `train()` function ignores it.

**Impact:** Training interruptions result in lost progress and wasted compute resources.

---

### Issue 1.6: Label Masking Bug in InstructionDataset
**Location:** `data_loader.py:108-117`

```python
if self.config.label_mask_input:
    instruction = self._get_instruction_part(sample)
    instruction_tokens = self.tokenizer(
        instruction,
        return_tensors="pt",
        add_special_tokens=False,
    )
    n_mask = instruction_tokens["input_ids"].shape[1]
    labels[:n_mask] = -100  # BUG: assumes instruction is at start
```

**Problem:** The mask count `n_mask` is computed from re-tokenizing the instruction part, but this assumes the instruction tokens appear at exactly the same positions in the full formatted text. With ChatML templates containing special tokens (`
