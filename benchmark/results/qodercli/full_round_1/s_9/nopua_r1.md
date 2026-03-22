# Scenario 9: Training Pipeline End-to-End Audit
## Condition: nopua | Run: 1
## Duration: 41.55s

---

### **Hidden Issue 1: Data Leakage in Label Masking** (`data_loader.py:97-104`)

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

**Problem:** The masking assumes instruction tokens are at the start, but ChatML template adds `
