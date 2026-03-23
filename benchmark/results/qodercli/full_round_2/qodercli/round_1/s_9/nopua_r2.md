# Scenario 9: Training Pipeline End-to-End Audit
## Condition: nopua | Run: 2
## Duration: 50.61s

---

---

## 📋 Training Pipeline Production Readiness Audit

### 1. Issues Found

| # | File | Issue | Severity | Impact |
|---|------|-------|----------|--------|
| 1 | `trainer.py:98-102` | **No checkpoint resume mechanism** - Training cannot resume from interruption | 🔴 Critical | Training progress lost on interruption |
| 2 | `trainer.py:134-142` | **No dataset validation** - Loads data without checking required fields, empty samples, or tokenized lengths | 🔴 Critical | Silent training failures, corrupted models |
| 3 | `trainer.py:156` | **eval_steps can be None** - Passes `None` to TrainingArguments when no eval dataset | 🟠 High | Potential runtime error in HF trainer |
| 4 | `trainer.py:180-191` | **GRPOTrainer is non-functional stub** - Has uninitialized `_reward_model` and `_ref_model`, raises NotImplementedError | 🟠 High | Misleading API, breaks if user tries GRPO |
| 5 | `data_loader.py:103-108` | **Label masking logic is incorrect** - Masks by instruction token count, but this doesn't account for system prompt tokens | 🟠 High | Loss computed on wrong tokens, degraded model quality |
| 6 | `data_loader.py:76-82` | **Hardcoded system prompt in _get_instruction_part** - Uses hardcoded string instead of CHATML_TEMPLATE constants | 🟡 Medium | Inconsistent formatting, maintenance burden |
| 7 | `data_loader.py:155` | **Uses stdlib random instead of numpy** - Not reproducible with seed, inconsistent with PyTorch ecosystem | 🟡 Medium | Non-deterministic train/eval splits |
| 8 | `config_builder.py:97-100` | **validate() returns warnings but never raises** - Invalid configs proceed to training | 🟡 Medium | Users don't realize config issues until training fails |
| 9 | `config_builder.py:17-57` | **Hardcoded dataset paths in presets** - `/data/guwen/training_v2.jsonl` won't exist on most machines | 🟡 Medium | Presets fail out-of-the-box |
| 10 | `evaluator.py:74-85` | **Evaluation uses greedy decoding (temperature=0.1, do_sample=False)** - Doesn't match generation settings users may expect | 🟡 Medium | Underestimates model capabilities |
| 11 | `evaluator.py:149-159` | **_compute_perplexity computes on output only** - Should compute on full context for meaningful PPL | 🟡 Medium | Misleading perplexity scores |
| 12 | `example_usage.py:22-30` | **Example code references removed config fields** - `use_flash_attention`, `data_format` don't exist | 🟢 Low | Confusing for new users |

---

### 2. Hidden Issues (Beyond the Ask)

| # | File | Hidden Issue | Why It's Easy to Miss |
|---|------|--------------|----------------------|
| H1 | `trainer.py:58` | **`dataset_text_field = "text"` is wrong** - Data loader produces `input_ids`, `attention_mask`, `labels` dicts, not raw text field | SFTTrainer expects a text field but dataset returns pre-tokenized tensors |
| H2 | `data_loader.py:68-71` | **Padding strategy incompatible with dataset** - Uses `padding="max_length"` which creates fixed-length sequences, wasting compute on short samples | Should use `padding="longest"` with dynamic batching |
| H3 | `data_loader.py:97-99` | **EOS token not added despite config flag** - `add_eos_token=True` in DataConfig but never used in `_encode_sample` | Responses won't have proper termination |
| H4 | `trainer.py:147-150` | **SFTTrainer will double-tokenize** - Dataset already tokenized in InstructionDataset, but SFTTrainer expects raw text to tokenize | Token IDs will be treated as text, garbled output |
| H5 | `evaluator.py:48` | **Model loaded twice** - Once in Trainer.train(), once in Evaluator.__init__(). No shared state | Wastes VRAM, slow iteration |
| H6 | `config_builder.py:111-116` | **GPU check imports torch locally** - May trigger CUDA initialization before training, fragmenting GPU memory | Can cause OOM errors later |
| H7 | `trainer.py:45-51` | **LoRA target modules are Qwen2-specific** - Won't work for other model families without manual config changes | Users switching models get silent degradation |

---

### 3. Root Causes

1. **Incompatible design patterns**: The data loader returns pre-tokenized `Dataset` objects, but `SFTTrainer` expects raw text datasets to tokenize internally. This fundamental mismatch causes H1 and H4.

2. **Incomplete abstraction layers**: `GRPOTrainer` was started but never implemented. Config fields were removed (`use_flash_attention`) but examples weren't updated.

3. **Missing validation boundaries**: Data is assumed valid at every layer—no schema validation, no length checks post-tokenization, no warning escalation.

4. **Copy-paste architecture**: System prompts are duplicated across files instead of imported from a central constant file.

5. **Research-to-production gap**: Evaluation metrics (perplexity on output-only) reflect academic conventions, not production monitoring needs.

---

### 4. Recommended Fixes

#### Priority 1 (Blockers - Fix Before Running Training)

```python
# trainer.py: Fix dataset integration
# Option A: Use raw text dataset (recommended for SFTTrainer)
def _load_dataset(self):
    """Load dataset as raw text for SFTTrainer compatibility."""
    dataset = load_dataset("json", data_files=self.config.dataset_path)
    
    def format_sample(example):
        # Apply ChatML template here
        return {"text": self._format_chatml(example)}
    
    dataset = dataset.map(format_sample)
    return dataset

# trainer.py: Add checkpoint resume
def train(self, resume_from_checkpoint: Optional[str] = None):
    """Execute training with optional checkpoint resume."""
    # ... existing setup ...
    self._trainer.train(resume_from_checkpoint=resume_from_checkpoint)
```

```python
# data_loader.py: Fix label masking
def _get_instruction_part(self, sample: Dict) -> str:
    """Get instruction part including system prompt for accurate masking."""
    # Use same template constants as _format_sample
    instruction = sample.get("instruction", "")
    input_text = sample.get("input", "")
    
    if self.config.template == "chatml":
        if input_text.strip():
            return f"
