# Scenario 9: Training Pipeline End-to-End Audit
## Condition: nopua | Run: 1
## Duration: 36.66s

---

Based on my detailed analysis of all the training module files, I've identified multiple critical issues. Let me compile a comprehensive report:

---

## Training Pipeline Production Readiness Audit

### 1. Issues Found

#### **CRITICAL - trainer.py:348-356 (GRPOTrainer)**
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
**Issue**: `GRPOTrainer` is a stub that always raises `NotImplementedError`. If user tries GRPO mode (documented in `__init__.py` as supported), training will crash.

---

#### **CRITICAL - trainer.py:127-130 (No Checkpoint Resume)**
```python
save_steps: int = 500
save_total_limit: int = 3
```
**Issue**: Checkpoints are saved but there's **no resume mechanism**. If training crashes at step 499, all progress is lost. The `--resume` CLI option exists (line 368) but is never used in the `train()` function.

---

#### **CRITICAL - data_loader.py:85-93 (Label Masking Bug)**
```python
if self.config.label_mask_input:
    instruction = self._get_instruction_part(sample)
    instruction_tokens = self.tokenizer(
        instruction, return_tensors="pt", add_special_tokens=False,
    )
    n_mask = instruction_tokens["input_ids"].shape[1]
    labels[:n_mask] = -100  # ❌ Assumes instruction length matches
```
**Issue**: Tokenizing instruction separately doesn't guarantee the token count matches the position in the full text. Special tokens, whitespace handling, or template differences can cause misalignment—masking wrong tokens or leaving instruction tokens unmasked.

---

#### **HIGH - evaluator.py:104-121 (Broken BLEU for Chinese)**
```python
def _sentence_bleu(self, prediction: str, reference: str, max_n: int = 4):
    pred_chars = list(prediction)
    ref_chars = list(reference)
    # ... character-level BLEU implementation
```
**Issue**: Character-level BLEU for Chinese is **linguistically invalid**. Chinese characters represent morphemes, not letters. "人工智能" (AI) vs "人工 智能" (artificial intelligence) would get penalized despite semantic similarity. Should use word segmentation (jieba) or call `sacrebleu` with proper tokenization.

---

#### **HIGH - trainer.py:174-179 (No Dataset Validation)**
```python
def _load_dataset(self):
    logger.info(f"Loading dataset: {self.config.dataset_path}")
    if self.config.dataset_path.endswith(".jsonl"):
        dataset = load_dataset("json", data_files=self.config.dataset_path)
    else:
        dataset = load_dataset(self.config.dataset_path)
```
**Issue**: No validation that:
- Required fields exist (`instruction`, `output`)
- Samples aren't empty or corrupted
- Data size is reasonable (>0 samples)
- Tokenized lengths fit within `max_seq_length`

A single malformed sample will crash training mid-run.

---

#### **HIGH - config_builder.py:109-112 (Validation Doesn't Block)**
```python
def validate(self, config: Dict[str, Any]) -> List[str]:
    warnings = []
    # ... checks
    return warnings  # ⚠️ Returns warnings but doesn't stop training
```
**Issue**: `validate()` returns warnings but nothing enforces calling it. User can start a 3-day training job with missing dataset path, and the code won't fail fast.

---

#### **MEDIUM - trainer.py:158-162 (Silent EOS Token Override)**
```python
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
```
**Issue**: Silent fallback can cause issues. Some models (e.g., Qwen) use `
