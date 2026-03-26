# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pua | Run: 2
## Duration: 91.79s

---

## Training Pipeline End-to-End Audit — Production Readiness Report

### 1. Issues Found (Critical → Low Priority)

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| **1** | **No checkpoint resume capability** — Training cannot resume from interruptions | CRITICAL | `trainer.py:82-89, 326` |
| **2** | **GRPO trainer is non-functional stub** — Claims to support GRPO but raises `NotImplementedError` | CRITICAL | `trainer.py:291-317` |
| **3** | **No data validation before training** — Dataset loaded without checking required fields, empty samples, or tokenized lengths | CRITICAL | `trainer.py:146-150`, `trainer.py:238-253` |
| **4** | **Label masking bug** — Mask length calculated from instruction tokens may not align with full formatted text tokenization | HIGH | `data_loader.py:109-117` |
| **5** | **Perplexity computation uses only output text** — Should compute on full prompt+response for valid perplexity | HIGH | `evaluator.py:240-258` |
| **6** | **Hardcoded absolute paths in presets** — `/data/guwen/`, `/models/guwen-llm/` don't exist on most machines | HIGH | `config_builder.py:100-102` |
| **7** | **`evaluator.results` not updated** — Instance attribute never set; results returned but not stored | MEDIUM | `evaluator.py:60, 128` |
| **8** | **Random seed not set globally** — `random.shuffle()` in data_loader uses unseeded RNG | MEDIUM | `data_loader.py:221-222` |
| **9** | **Example file contains stale/broken code** — Comments describe removed features that would cause errors if uncommented | MEDIUM | `example_usage.py:32-34` |
| **10** | **Module docstring claims GRPO support** — But implementation is a stub | LOW | `__init__.py:3-4` |
| **11** | **CLI `--resume` option ignored** — Parameter accepted but never used | HIGH | `trainer.py:326` |
| **12** | **No early stopping or evaluation during training** — `eval_steps` set but no validation loss monitoring | MEDIUM | `trainer.py:255-278` |

---

### 2. Hidden Issues (Beyond Surface Problems)

| # | Hidden Issue | Impact |
|---|--------------|--------|
| **H1** | **Determinism not guaranteed** — No global seed setting for `torch`, `numpy`, or Python `random`; shuffling produces different splits each run | Reproducibility impossible |
| **H2** | **Memory leak risk in evaluator** — Model loaded with `device_map="auto"` but never explicitly unloaded; multiple evaluations could OOM | Long-running eval jobs fail |
| **H3** | **BLEU implementation doesn't handle empty predictions correctly** — Returns 0.0 silently, masking systematic generation failures | Bad models appear acceptable |
| **H4** | **No gradient explosion protection** — `max_grad_norm=1.0` set but no logging when clipped; silent training degradation | Training quality degrades unnoticed |
| **H5** | **Dataset text field mismatch** — `dataset_text_field="text"` default but data uses `instruction/input/output` format; SFTTrainer will fail | Training crashes at runtime |
| **H6** | **Quantization dtype mismatch** — bf16 compute dtype hardcoded in quantization config, but fp16 may be requested; conflict causes crash | Cannot train on GPUs without bf16 support |
| **H7** | **No distributed training support** — Single-GPU only; no DDP/FSDP setup for multi-GPU scaling | Cannot scale to larger models |
| **H8** | **Tokenization done in main thread** — No parallel preprocessing despite `num_workers=4` in DataConfig | Data loading bottleneck |

---

### 3. Root Cause Analysis

| Root Cause | Issues Caused |
|------------|---------------|
| **Incomplete feature implementation** — GRPO trainer and CLI resume were planned but never built | #2, #11 |
| **Missing input validation layer** — No schema validation for datasets or configs before use | #3, #5, #H5 |
| **Inconsistent state management** — Results computed but not stored; seeds not propagated | #7, #8, #H1 |
| **Hardcoded environment assumptions** — Paths, GPU capabilities, package availability assumed | #6, #H6 |
| **Documentation drift** — Module docstrings and examples not updated after refactors | #10, #9 |
| **Silent failure patterns** — Exceptions swallowed, warnings logged but not surfaced | #H3, #H4 |

---

### 4. Recommended Fixes

#### Critical (Must Fix Before Production)

```python
# trainer.py — Add checkpoint resume
def train(self, resume_from_checkpoint: Optional[str] = None):
    # ... existing setup ...
    self._trainer.train(resume_from_checkpoint=resume_from_checkpoint)

# trainer.py — Add data validation
def _validate_dataset_schema(self, dataset):
    required_fields = ["instruction", "output"]
    for idx, sample in enumerate(dataset):
        for field in required_fields:
            if field not in sample or not sample[field]:
                raise ValueError(f"Sample {idx} missing required field: {field}")
```

```python
# trainer.py — Fix GRPO or remove misleading claims
class GRPOTrainer:
    def __init__(self, config: TrainingConfig, reward_model=None):
        if reward_model is None:
            raise ValueError("GRPO requires a reward_model. Pass one or use SFT trainer.")
        self._reward_model = reward_model
```

```python
# data_loader.py — Fix label mask alignment
def _encode_sample(self, sample: Dict) -> Optional[Dict]:
    text = self._format_sample(sample)
    tokens = self.tokenizer(text, ...)
    input_ids = tokens["input_ids"].squeeze(0)
    labels = input_ids.clone()

    if self.config.label_mask_input:
        instruction = self._get_instruction_part(sample)
        instruction_tokens = self.tokenizer(instruction, ..., add_special_tokens=False)
        n_mask = len(instruction_tokens["input_ids"][0])
        # Account for tokenizer differences
        labels[:n_mask] = -100
```

```python
# config_builder.py — Remove hardcoded paths
config.setdefault("dataset_path", "./data/training.jsonl")  # Use relative paths
config.setdefault("output_dir", "./outputs/checkpoints")
```

#### High Priority

```python
# data_loader.py — Set random seed
import random
random.seed(42)  # Use config.seed
random.shuffle(samples)
```

```python
# evaluator.py — Store results
def evaluate(self, eval_data, metrics=None):
    # ... compute results ...
    self.results = results  # Store for later access
    return results
```

```python
# trainer.py — Fix dataset_text_field mismatch
# Either change default or ensure data has "text" field
dataset_text_field: str = "formatted_text"  # Or preprocess to add "text" field
```

#### Medium Priority

```python
# evaluator.py — Fix perplexity computation
def _compute_perplexity(self, eval_data: List[Dict]) -> float:
    for sample in eval_data:
        # Use full prompt + response, not just output
        text = self._build_eval_prompt(sample) + sample.get("output", "")
```

```python
# example_usage.py — Remove or fix stale examples
# Delete commented lines that would cause errors if uncommented
```

---

### 5. Steps Taken

1. **Read all 6 training module files** — Full content analysis of `trainer.py`, `data_loader.py`, `evaluator.py`, `config_builder.py`, `example_usage.py`, `__init__.py`
2. **Line-by-line code inspection** — Identified comments indicating known issues (e.g., `trainer.py:87-89`, `trainer.py:146-150`)
3. **Cross-file consistency check** — Compared docstrings vs implementations, examples vs actual APIs
4. **Dependency verification** — Confirmed torch not installed in current environment (limits runtime testing)
5. **Search for related patterns** — Checked for seed settings, validation logic, error handling across files

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Full file content retrieval for all 6 source files |
| `Glob` | Search for training-related markdown/yaml config files |
| `Bash` | Verify torch installation status |
| `TodoWrite` | Track investigation progress |

---

### 7. Verification

**Findings verified against source code:**
- All line numbers cited are accurate (e.g., `trainer.py:291-317` for GRPO stub)
- Comments in code confirm known issues (e.g., `trainer.py:87-89` checkpoint comment, `trainer.py:146-150` data validation comment)
- Example file explicitly documents its own staleness (`example_usage.py:7, 21-25`)
- Missing imports confirmed (`import random` inside function at `data_loader.py:221`)

**Not verifiable without runtime:**
- Actual crash scenarios (requires torch/transformers installed)
- Memory leak confirmation (requires long-running eval session)
- BLEU score accuracy (requires test dataset)

---

### Summary: Production Readiness Assessment

**Current Status: NOT PRODUCTION READY**

**Blockers:** 3 critical issues (#1, #2, #3) must be fixed before any training job can reliably complete.

**Recommended Action:** 
1. Fix checkpoint resume first (most likely to cause lost work)
2. Remove or implement GRPO trainer (misleading API)
3. Add dataset validation layer
4. Run end-to-end test with small dataset to verify fixes
