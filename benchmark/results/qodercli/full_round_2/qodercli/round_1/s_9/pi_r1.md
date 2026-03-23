# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pi | Run: 1
## Duration: 40.09s

---

Now let me conduct a systematic code review. I'll analyze each file using the 审码四维 framework (Security, Performance, Readability, Correctness).

## Analysis Complete — Production Readiness Audit

### 1. Issues Found

| # | File | Line | Issue |
|---|------|------|-------|
| 1 | `trainer.py` | 147-152 | **Data validation missing** — Dataset loaded without checking required fields, empty samples, or data distribution |
| 2 | `trainer.py` | 189-193 | **No error handling for model loading** — Network failures, corrupted checkpoints will crash silently |
| 3 | `data_loader.py` | 106-110 | **Label masking bug** — Input token count calculated incorrectly; masks wrong positions when instruction length varies |
| 4 | `data_loader.py` | 149-152 | **Hardcoded system prompt** — "你是一個精通古典中文的 AI 助手" not configurable for different tasks |
| 5 | `evaluator.py` | 89-95 | **Memory leak in evaluation** — Model generates predictions but `torch.no_grad()` context doesn't prevent OOM on large eval sets |
| 6 | `evaluator.py` | 145-149 | **Division by zero risk** — `_sentence_bleu` returns 0.0 but brevity penalty divides by prediction length |
| 7 | `config_builder.py` | 91-96 | **Race condition in validation** — `Path(dataset_path).exists()` check can become stale before training starts |
| 8 | `config_builder.py` | 103-109 | **GPU detection race** — torch import and CUDA check happens at config time, not training time |
| 9 | `example_usage.py` | 24-26 | **Dead code with removed parameters** — `use_flash_attention`, `data_format`, `wandb_project` will cause TypeError if uncommented |
| 10 | `trainer.py` | 77 | **Missing resume documentation** — `save_steps`/`save_total_limit` set but no guidance on checkpoint resumption |
| 11 | `trainer.py` | 237-241 | **GRPO trainer incomplete** — `_reward_model` and `_ref_model` never initialized, `train()` raises NotImplementedError |
| 12 | `data_loader.py` | 177-180 | **Random seed not set** — `random.shuffle(samples)` produces non-reproducible splits |

---

### 2. Hidden Issues

| # | Category | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | 🔒 Security | `config_builder.py` | 79-80 | **Path traversal risk** — `output_path` from user not validated; could write to arbitrary locations |
| 2 | 🔒 Security | `trainer.py` | 189 | **trust_remote_code=True by default** — Loads untrusted code from HuggingFace hub without opt-in |
| 3 | ⚡ Performance | `data_loader.py` | 76-82 | **Inefficient tokenization** — Tokenizes instruction separately for masking; doubles computation |
| 4 | ⚡ Performance | `evaluator.py` | 133-138 | **Character-level BLEU is O(n²)** — Nested loops over prediction/reference chars; slow for long outputs |
| 5 | ⚡ Performance | `evaluator.py` | 158-165 | **ROUGE imports inside loop** — `rouge_score` imported per-evaluation instead of module-level |
| 6 | 🧵 Thread Safety | `data_loader.py` | 177 | **Global random.shuffle** — Not thread-safe; concurrent data loading will corrupt state |
| 7 | 🧵 Thread Safety | `config_builder.py` | 38 | **Shared PRESETS mutable** — `deepcopy(PRESETS)` protects outer dict but nested dicts remain shared references |
| 8 | ⚠️ Correctness | `trainer.py` | 156-159 | **Eval dataset split mismatch** — Loads as `test` key but trainer expects `eval` key |
| 9 | ⚠️ Correctness | `data_loader.py` | 113 | **Padding token mask applied after label copy** — If attention_mask changes, labels not updated |
| 10 | ⚠️ Correctness | `evaluator.py` | 79-82 | **Prompt template hardcoded** — Different from `data_loader.py` templates; train/eval mismatch |
| 11 | 📦 Resource Leak | `data_loader.py` | 171-175 | **File handle not closed on exception** — JSONL read lacks try/finally |
| 12 | 📦 Resource Leak | `config_builder.py` | 67-71 | **File write lacks atomic operation** — Partial writes on disk failure corrupt config |
| 13 | 🌐 Cross-platform | `config_builder.py` | 55-57 | **Hardcoded Linux paths** — `/data/guwen/`, `/models/guwen-llm/` won't exist on Windows/Mac |
| 14 | 🎯 Boundary Condition | `data_loader.py` | 180 | **eval_ratio=1.0 edge case** — `split_idx = max(1, ...)` ensures train has ≥1 sample, but eval could be empty |
| 15 | 🎯 Boundary Condition | `evaluator.py` | 126 | **Empty prediction handling** — Returns 0.0 BLEU but division in brevity penalty still executes |

---

### 3. Root Cause

| Issue | Root Cause |
|-------|------------|
| Data validation missing | No defensive programming mindset; assumes input data is always well-formed |
| Label masking bug | Algorithm assumes fixed instruction length; doesn't account for variable-length inputs |
| Memory leak in eval | Batch processing not implemented; all samples processed in single forward pass |
| Hardcoded paths/prompts | Configuration separation incomplete; some values hardcoded, some configurable |
| trust_remote_code=True | Security not prioritized; convenience over safety |
| Non-reproducible splits | Random seed management not centralized; shuffling happens without seed control |
| GRPO trainer incomplete | Feature flagged but not removed; stub code left in production path |
| Race conditions | Validation happens at config time, not at execution time when resources are actually needed |

---

### 4. Recommended Fix

#### Fix 1: Data Validation in Trainer (`trainer.py:147-152`)
```python
# Before:
dataset = self._load_dataset()

# After:
dataset = self._load_dataset()
self._validate_dataset(dataset)  # Add validation method

def _validate_dataset(self, dataset):
    """Validate dataset structure and content."""
    required_fields = ["instruction", "output"]
    for split_name, split_data in dataset.items():
        if len(split_data) == 0:
            raise ValueError(f"Dataset split '{split_name}' is empty")
        sample = split_data[0]
        for field in required_fields:
            if field not in sample:
                raise ValueError(f"Missing required field '{field}' in dataset")
```

#### Fix 2: Label Masking Bug (`data_loader.py:106-110`)
```python
# Before:
instruction_tokens = self.tokenizer(instruction, return_tensors="pt", add_special_tokens=False)
n_mask = instruction_tokens["input_ids"].shape[1]
labels[:n_mask] = -100

# After:
# Find the assistant response start position by searching for assistant token
assistant_token = self.tokenizer.encode("
