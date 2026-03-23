# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pua | Run: 1
## Duration: 23.97s

---

## Training Pipeline End-to-End Audit Report

### 1. Issues Found

#### CRITICAL - trainer.py:63-72 (TrainingConfig)
**Issue**: No checkpoint resume mechanism despite having `save_steps` and `save_total_limit` configured.
```python
# While save_steps and save_total_limit are set, there's no documentation
# about resuming from checkpoints, which checkpoints to keep, or how
# to handle training interruptions. The user might lose training progress.
```
**Risk**: Training interruption = lost compute hours/days. No `resume_from_checkpoint` field in config.

---

#### CRITICAL - trainer.py:139-158 (_load_model)
**Issue**: Quantization config applied unconditionally without GPU memory check.
```python
if self.config.quantization == "4bit":
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,  # Hardcoded
        bnb_4bit_use_double_quant=True,
    )
```
**Risk**: 
- `bnb_4bit_compute_dtype` hardcoded to bfloat16 — will fail on GPUs without bf16 support
- No fallback if GPU runs out of memory
- `device_map="auto"` can cause OOM on multi-GPU setups without proper partitioning

---

#### CRITICAL - trainer.py:179-188 (_load_dataset)
**Issue**: Dataset loaded without any validation of required fields.
```python
def _load_dataset(self):
    logger.info(f"Loading dataset: {self.config.dataset_path}")

    if self.config.dataset_path.endswith(".jsonl"):
        dataset = load_dataset("json", data_files=self.config.dataset_path)
    else:
        dataset = load_dataset(self.config.dataset_path)
```
**Risk**: 
- No check for required fields (`instruction`, `output`)
- Empty samples pass through silently
- Malformed JSONL files cause cryptic errors mid-training
- No statistics on sequence lengths — could exceed `max_seq_length`

---

#### HIGH - trainer.py:199-217 (_create_training_args)
**Issue**: `eval_steps` set to `None` when no eval dataset, but `evaluation_strategy="no"` still requires valid value.
```python
eval_steps=self.config.eval_steps if self.config.eval_dataset_path else None,
evaluation_strategy="steps" if self.config.eval_dataset_path else "no",
```
**Risk**: HuggingFace may raise error when `eval_steps=None` with certain configurations.

---

#### HIGH - data_loader.py:94-109 (_encode_sample)
**Issue**: Label masking logic assumes instruction length equals token count — off-by-one risk.
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
**Risk**: 
- Tokenizer may add special tokens not accounted for
- ChatML template includes `
