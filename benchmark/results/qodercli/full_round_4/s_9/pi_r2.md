# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pi | Run: 2
## Duration: 133.92s

---

## Training Pipeline End-to-End Audit

---

### 1. Issues Found

| # | File | Line | Issue |
|---|------|------|-------|
| 1 | `trainer.py` | 126 | Missing encoding parameter in `open()` for YAML config loading |
| 2 | `trainer.py` | 49, 202, 210 | `trust_remote_code=True` hardcoded - security risk for arbitrary code execution |
| 3 | `trainer.py` | 203, 248-250 | No validation that dataset file exists before training starts |
| 4 | `trainer.py` | 87-89 | No checkpoint resume mechanism documented or implemented despite CLI option existing |
| 5 | `data_loader.py` | 221-222 | Random shuffle without seed - non-reproducible train/eval splits |
| 6 | `data_loader.py` | 134-135 | Silent data loss: samples without instruction/output return empty string, skipped with no warning |
| 7 | `evaluator.py` | 66, 71 | `trust_remote_code=True` hardcoded in evaluation - same security risk |
| 8 | `evaluator.py` | 240-258 | Perplexity computation only uses output text, ignores full context - incorrect metric |
| 9 | `config_builder.py` | 100-102 | Hardcoded absolute paths (`/data/guwen/`, `/models/guwen-llm/`) - not portable |
| 10 | `trainer.py` | 291-317 | `GRPOTrainer` is a stub - raises `NotImplementedError` but exported in `__init__.py` |
| 11 | `example_usage.py` | 26-35 | Example code contains commented-out removed parameters - will confuse users |
| 12 | `evaluator.py` | 50-54 | Inconsistent initialization: passing model=None creates unbound attributes |

---

### 2. Hidden Issues

| # | Category | File | Line | Issue |
|---|----------|------|------|-------|
| 1 | **Security** | `trainer.py` | 49, 202, 210 | `trust_remote_code=True` allows arbitrary code execution from HuggingFace models |
| 2 | **Security** | `evaluator.py` | 66, 71 | Same `trust_remote_code=True` vulnerability in evaluator |
| 3 | **Correctness** | `data_loader.py` | 109-117 | Label masking logic assumes instruction length equals token count - off-by-one risk with special tokens |
| 4 | **Correctness** | `evaluator.py` | 212 | Brevity penalty formula inverted: `exp(1 - ref/pred)` should be `exp(1 - pred/ref)` when pred < ref |
| 5 | **Performance** | `evaluator.py` | 159-164 | BLEU computation loops sequentially; no batching for large eval sets |
| 6 | **Resource Leak** | `config_builder.py` | 118-121 | File handle lacks context manager in `from_file()` - minor but inconsistent |
| 7 | **Thread Safety** | `data_loader.py` | 221-222 | `random.shuffle` uses global RNG without local seed - affects reproducibility across processes |
| 8 | **Boundary** | `trainer.py` | 282-286 | `_save_model()` has no error handling for disk full / permission denied scenarios |
| 9 | **Configuration** | `trainer.py` | 61-63 | LoRA target modules hardcoded to Qwen architecture - breaks for other models |
| 10 | **API Contract** | `trainer.py` | 272-273 | `eval_steps=None` passed to TrainingArguments when no eval dataset - may cause unexpected behavior |
| 11 | **Data Integrity** | `data_loader.py` | 238-247 | JSONL parsing logs warnings but continues silently - corrupted data goes unnoticed |
| 12 | **Memory** | `evaluator.py` | 98-108 | Evaluation moves all inputs to device without batch size limit - OOM risk on large eval sets |
| 13 | **Cross-Platform** | `config_builder.py` | 100-102 | Unix-style absolute paths will fail on Windows |
| 14 | **Unused Import** | `trainer.py` | 22 | `import json` unused in trainer.py |
| 15 | **Unused Import** | `evaluator.py` | 27 | `DataLoader` imported but never used |

---

### 3. Root Cause

| Issue | Root Cause |
|-------|------------|
| Security vulnerabilities (trust_remote_code) | Default convenience overrode security - no mechanism to disable remote code execution for production |
| Non-reproducible splits | Random seed set for training (`seed: 42` at L92) but not applied to data shuffling in `data_loader.py:L221-222` |
| Silent data loss | `_format_sample()` returns empty string for invalid samples instead of raising error or logging which samples failed |
| Incorrect perplexity | `_compute_perplexity()` only tokenizes output text, not the full prompt+output pair, breaking the language model probability calculation |
| Hardcoded paths | ConfigBuilder presets designed for specific deployment environment, not generalizable |
| Stub GRPOTrainer | Feature was planned but never implemented; class remains as placeholder without clear deprecation |
| Inverted brevity penalty | Formula error in BLEU implementation: division operands reversed at `evaluator.py:L212` |
| No resume support | CLI has `--resume` flag (`trainer.py:L326`) but `Trainer.train()` method has no logic to handle it |

---

### 4. Recommended Fix

#### Fix 1: Security - Make trust_remote_code configurable
```python
# trainer.py:L49
@dataclass
class TrainingConfig:
    # Model
    model_name: str = "Qwen/Qwen2-7B"
    tokenizer_name: Optional[str] = None
    trust_remote_code: bool = False  # Changed default to False
```

```python
# evaluator.py:L49
def __init__(self, model=None, tokenizer=None, device: str = "auto", 
             trust_remote_code: bool = False):  # Add parameter
    # ... use self.trust_remote_code in _load_model()
```

#### Fix 2: Reproducibility - Seed the random shuffle
```python
# data_loader.py:L205-222
def load(self, data_path: str, eval_ratio: float = 0.05,
         seed: int = 42) -> tuple:  # Add seed parameter
    # ...
    import random
    random.seed(seed)  # Add explicit seeding
    random.shuffle(samples)
```

#### Fix 3: Data validation - Log skipped samples
```python
# data_loader.py:L128-136
def _format_sample(self, sample: Dict) -> str:
    instruction = sample.get("instruction", "")
    input_text = sample.get("input", "")
    output = sample.get("output", "")

    if not instruction or not output:
        logger.warning(f"Skipping invalid sample: missing instruction or output. Keys: {sample.keys()}")
        return ""  # Consider raising ValueError instead
```

#### Fix 4: Correct perplexity computation
```python
# evaluator.py:L240-258
def _compute_perplexity(self, eval_data: List[Dict]) -> float:
    total_loss = 0.0
    total_tokens = 0

    self.model.eval()
    with torch.no_grad():
        for sample in eval_data:
            # Build full prompt including instruction, not just output
            prompt = self._build_eval_prompt(sample)
            full_text = prompt + sample.get("output", "")
            inputs = self.tokenizer(
                full_text, return_tensors="pt", truncation=True, max_length=2048
            ).to(self.device)
            # ... rest unchanged
```

#### Fix 5: Fix brevity penalty formula
```python
# evaluator.py:L210-214
# Brevity penalty
if len(pred_chars) < len(ref_chars):
    bp = math.exp(1 - len(pred_chars) / len(ref_chars))  # Fixed: pred/ref not ref/pred
else:
    bp = 1.0
```

#### Fix 6: Remove or implement GRPOTrainer
```python
# trainer.py:L291-317
# Option A: Remove entirely and update __init__.py
# Option B: Add clear deprecation notice
class GRPOTrainer:
    """DEPRECATED: GRPO training is not available in this version.
    
    This class is a placeholder and will raise NotImplementedError if used.
    Use SFT Trainer instead.
    """
    # ... add @deprecated decorator or remove from __all__
```

#### Fix 7: Add checkpoint resume support
```python
# trainer.py:L134-179
def train(self, resume_from_checkpoint: Optional[str] = None):
    # ... existing setup ...
    
    # Step 5: Train with resume support
    logger.info("Starting training...")
    self._trainer.train(resume_from_checkpoint=resume_from_checkpoint)
```

---

### 5. Steps Taken

1. **Read all 6 source files** in the training module to understand the complete architecture
2. **Searched for security patterns**: `trust_remote_code`, `device_map="auto"` - found 5 occurrences across trainer.py and evaluator.py
3. **Searched for reproducibility issues**: `random.shuffle`, `seed` - discovered shuffle at data_loader.py:L221-222 lacks seeding
4. **Searched for checkpoint/resume functionality**: found CLI flag at L326 but no implementation in train() method
5. **Analyzed each function** using the Zone 2 checklist:
   - Checked import usage (found unused `json` in trainer.py, `DataLoader` in evaluator.py)
   - Checked parameter validation (missing null checks in multiple places)
   - Checked exception handling (silent failures in data loading)
   - Checked resource management (file handles mostly correct with context managers)
   - Checked cross-platform compatibility (hardcoded Unix paths in config_builder.py)
6. **Verified mathematical formulas**: Found brevity penalty inversion at evaluator.py:L212
7. **Compared API contracts**: Eval dataset handling inconsistent between trainer.py and config_builder.py
8. **Cross-referenced example_usage.py**: Confirmed stale documentation with commented-out removed parameters

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read all 6 source files in training module |
| `Grep` | Search for patterns: trust_remote_code, device_map, random, seed, resume, except, TODO, open(), torch.cuda |
| `Glob` | Locate training module files in repository |
| Manual code review | Function-by-function analysis using Zone 2 checklist |

---

### 7. Verification

**Immediate verification commands:**

```bash
# 1. Check for trust_remote_code usage
grep -n "trust_remote_code" nopua/benchmark/test-project/src/training/*.py

# 2. Verify random seed usage
grep -n "random\|seed" nopua/benchmark/test-project/src/training/data_loader.py

# 3. Check for checkpoint resume implementation
grep -n "resume" nopua/benchmark/test-project/src/training/trainer.py

# 4. Verify BLEU formula (line 212)
sed -n '210,214p' nopua/benchmark/test-project/src/training/evaluator.py

# 5. Check unused imports
python3 -c "import ast; print([node.names[0].name for node in ast.walk(ast.parse(open('nopua/benchmark/test-project/src/training/trainer.py').read())) if isinstance(node, ast.Import)])"
```

**Production readiness checklist:**

| Item | Status | Action Required |
|------|--------|-----------------|
| Security audit | ❌ FAIL | Disable trust_remote_code by default, add opt-in mechanism |
| Reproducibility | ❌ FAIL | Add seed parameter to data loader shuffle |
| Data validation | ❌ FAIL | Add strict mode for data format validation |
| Error handling | ⚠️ PARTIAL | Add disk space / permission error handling |
| Documentation | ❌ FAIL | Update example_usage.py, document resume workflow |
| Feature completeness | ❌ FAIL | Remove or implement GRPOTrainer |
| Cross-platform | ❌ FAIL | Replace hardcoded paths with environment variables |
| Metric correctness | ❌ FAIL | Fix BLEU brevity penalty and perplexity computation |

**Recommendation**: **NOT PRODUCTION READY**. Critical blockers: security vulnerabilities (trust_remote_code), incorrect metrics (BLEU/perplexity), non-reproducible splits, and silent data loss. Estimated 8-12 engineering hours to address P0 issues.

---

```
📋 交付确认
□ 目标匹配: 完整审查训练模块的生产就绪性 → 发现 12 项表面问题 + 15 项隐藏问题
□ 边界覆盖: 安全/性能/正确性/可复现性/跨平台/资源管理/异常处理全部扫描
□ 风险可控: 已标注关键风险（trust_remote_code 代码执行、指标计算错误、数据静默丢失），附修复方案
```
