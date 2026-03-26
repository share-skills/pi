# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pua | Run: 1
## Duration: 100.75s

---

## Training Pipeline End-to-End Audit Report

### 1. Issues Found (Critical Production Readiness Gaps)

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **No checkpoint resume mechanism** - Training cannot resume from interruptions | Critical | `trainer.py:87-89,326-331` |
| 2 | **Dataset validation missing** - No schema/field validation before training | Critical | `trainer.py:146-150,238-253` |
| 3 | **Hardcoded paths in presets** - `/data/guwen/` and `/models/guwen-llm/` don't exist | High | `config_builder.py:100-102` |
| 4 | **No error handling in train()** - Single failure crashes entire pipeline | High | `trainer.py:134-179` |
| 5 | **GRPO trainer is non-functional stub** - Dead code with uninitialized attributes | High | `trainer.py:291-317` |
| 6 | **Evaluation results not stored** - `self.results` never updated after evaluate() | Medium | `evaluator.py:59-128` |
| 7 | **Label masking bug** - Uses instruction token count, not formatted prompt length | Medium | `data_loader.py:109-117` |
| 8 | **Random seed not set globally** - Non-deterministic shuffling across runs | Medium | `data_loader.py:221-222` |
| 9 | **Stale example_usage.py** - Documents removed fields, misleading comments | Medium | `example_usage.py:22-34` |
| 10 | **Perplexity computed on output only** - Should use full prompt+completion | Low | `evaluator.py:240-258` |

---

### 2. Hidden Issues Discovered

| # | Issue | Impact |
|---|-------|--------|
| H1 | **`dataset_text_field="text"` mismatch** - JSONL data uses `instruction/input/output`, not `text` field. SFTTrainer will fail or produce garbage. | Training produces unusable model |
| H2 | **Validation warnings ignored** - `ConfigBuilder.validate()` returns warnings but nothing enforces checking them | Invalid configs proceed to training |
| H3 | **No OOM protection** - bf16 requested without verifying GPU memory capacity | Mid-training crashes on smaller GPUs |
| H4 | **CLI `--resume` option does nothing** - Parameter accepted but never passed to `trainer.train()` | Users cannot resume training |
| H5 | **Exported symbols incomplete** - `SFTDataLoader`, `InstructionDataset`, `DataConfig`, `GRPOTrainer` not in `__all__` | Module API is incomplete |
| H6 | **Duplicate tokenizer initialization** - `InstructionDataset` tokenizes during `__init__`, but `SFTTrainer` also tokenizes | Wasted compute, potential double-tokenization |
| H7 | **No early stopping** - Training runs all epochs regardless of eval loss convergence | Wasted compute, overfitting risk |

---

### 3. Root Cause Analysis

**Primary Root Causes:**

1. **Incomplete abstraction layers** - `trainer.py` uses HuggingFace `SFTTrainer` which expects raw text in `dataset_text_field`, but the data loader produces pre-tokenized datasets with `input_ids/labels`. These two approaches are incompatible. (`trainer.py:162-170` vs `data_loader.py:122-126`)

2. **Development-stage code promoted to production** - Comments like `"TODO: Implement GRPO training"` and `"This is a placeholder"` indicate unfinished features shipped as production-ready. (`trainer.py:305-311`)

3. **No defensive programming** - Assumes files exist, paths are writable, GPUs are available, data is well-formed. Single point of failure at every I/O boundary.

4. **State management anti-patterns** - `Evaluator.results` is an instance attribute that's never updated; the method returns a fresh dict instead. This violates expected object behavior. (`evaluator.py:59,128`)

---

### 4. Recommended Fixes

#### P0 (Must Fix Before First Run):

```python
# trainer.py - Fix dataset_text_field to match actual JSONL structure
@dataclass
class TrainingConfig:
    dataset_text_field: str = "formatted_text"  # Or remove and use custom collate_fn

# trainer.py - Add resume_from_checkpoint support
def train(self, resume_from_checkpoint: Optional[str] = None):
    self._trainer.train(resume_from_checkpoint=resume_from_checkpoint)

# config_builder.py - Remove hardcoded absolute paths
config.setdefault("dataset_path", os.environ.get("DATASET_PATH", "./data/training.jsonl"))
config.setdefault("output_dir", os.environ.get("OUTPUT_DIR", "./outputs/guwen-llm"))
```

#### P1 (Should Fix):

```python
# trainer.py - Wrap train() in try/finally with cleanup
def train(self):
    try:
        # existing code
    except Exception as e:
        logger.error(f"Training failed: {e}")
        # Save partial checkpoint
        self._save_model()
        raise

# evaluator.py - Store results in instance state
def evaluate(self, eval_data, metrics=None):
    self.results = {...}  # Assign before return
    return self.results

# data_loader.py - Set random seed
import random
random.seed(42)  # Use config.seed
random.shuffle(samples)
```

#### P2 (Nice to Have):

- Remove `GRPOTrainer` class entirely or implement it
- Update `example_usage.py` to reflect current API
- Add `SFTDataLoader` etc. to `__all__`
- Implement early stopping callback
- Add data validation step before tokenization

---

### 5. Steps Taken

1. **Read all 6 training module files** - Full content analysis
2. **Searched for checkpoint/resume patterns** - Found CLI option unused
3. **Searched for validation logic** - Only config-level validation exists
4. **Searched for error handling** - Minimal try/except blocks found
5. **Cross-referenced data flow** - Discovered `dataset_text_field` mismatch
6. **Analyzed state management** - Found `Evaluator.results` never updated
7. **Reviewed label masking logic** - Identified token count mismatch bug
8. **Checked module exports** - Found incomplete `__all__`

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Full file content analysis (6 files) |
| `Grep` | Pattern search for resume, validate, error handling |
| `Bash` | CUDA/bf16 capability check (torch not installed) |
| `Glob` | Located actual file paths in test-project directories |

---

### 7. Verification

**Findings verified against source code:**

- ✅ Checkpoint resume: CLI accepts `--resume` but `train()` method signature has no parameter (line 134 vs 326-331)
- ✅ Dataset field mismatch: Config defaults to `"text"` but JSONL samples have `instruction/input/output` keys
- ✅ Evaluator.results bug: Instance attr initialized to `{}` (line 59), `evaluate()` returns local `results` dict (line 128) without assignment
- ✅ Label mask bug: `_get_instruction_part()` returns template prefix, but mask length calculated from unformatted instruction tokens (lines 109-117)
- ✅ Hardcoded paths: Presets set `/data/guwen/training_v2.jsonl` which doesn't exist on standard systems

---

### Summary

**The training pipeline is NOT production-ready.** It will likely fail on first run due to:
1. Missing dataset paths
2. `dataset_text_field` misconfiguration
3. No checkpoint recovery when (not if) training is interrupted

**Minimum viable fixes:** Override paths via env vars, fix the text field config, add resume support, wrap training in error handling. Without these, the first multi-day training run will be lost to any interruption.
