# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pi | Run: 2
## Duration: 212.23s

---

---

# Training Pipeline End-to-End Audit Report

## 1. Issues Found

| # | File | Line | Issue |
|---|------|------|-------|
| 1 | trainer.py | 327-331 | `--resume` CLI option defined but never used in train() |
| 2 | trainer.py | 146-150 | Dataset loaded without validation (no schema/field checks) |
| 3 | data_loader.py | 221-222 | `random.shuffle()` without seed → non-reproducible splits |
| 4 | trainer.py | 187-203 | CUDA operations without deterministic flags |
| 5 | config_builder.py | 100-102 | Hardcoded paths (`/data/guwen/*`, `/models/guwen-llm/*`) |
| 6 | trainer.py | 203 | `device_map="auto"` may cause unexpected GPU memory allocation |
| 7 | evaluator.py | 66,71 | `trust_remote_code=True` without code audit (security risk) |
| 8 | trainer.py | 81-95 | No `__post_init__` validation in TrainingConfig |
| 9 | trainer.py | 280-288 | `_save_model()` only saves final model, not best checkpoint |
| 10 | trainer.py | 300-317 | GRPOTrainer is stub implementation (raises NotImplementedError) |
| 11 | trainer.py | 21-22 | Unused imports: `os`, `json`, `Dict`, `Any` |
| 12 | evaluator.py | 18,21,25,27 | Unused imports: `os`, `Any`, `Tuple`, `numpy`, `DataLoader` |
| 13 | data_loader.py | 18-19,22 | Unused imports: `Path`, `Callable`, `Union`, `torch` |
| 14 | config_builder.py | 13,15 | Unused imports: `os`, `Optional` |
| 15 | example_usage.py | 32-34 | Comments document removed fields but code still references stale API |

---

## 2. Hidden Issues

### Security Issues
| # | File | Line | Risk |
|---|------|------|------|
| H1 | evaluator.py | 66,71 | **HIGH**: `trust_remote_code=True` executes arbitrary code from HuggingFace Hub |
| H2 | config_builder.py | 100-102 | **MEDIUM**: Hardcoded absolute paths may point to non-existent or shared directories |
| H3 | trainer.py | 203 | **MEDIUM**: `device_map="auto"` may allocate all GPU memory, blocking multi-process training |

### Performance Issues
| # | File | Line | Impact |
|---|------|------|--------|
| H4 | trainer.py | All | No `torch.cuda.empty_cache()` → GPU memory fragmentation over long training |
| H5 | data_loader.py | 61 | `num_workers=4` hardcoded, not passed to DataLoader (unused config) |
| H6 | evaluator.py | 240-258 | Perplexity computed sample-by-sample without batching → slow evaluation |
| H7 | data_loader.py | 96-102 | Tokenization done sequentially without parallelization |

### Reproducibility Issues
| # | File | Line | Effect |
|---|------|------|--------|
| H8 | data_loader.py | 221-222 | Train/eval split differs each run → metrics not comparable |
| H9 | trainer.py | 92 | `seed=42` set but never applied to `torch.manual_seed()` or `np.random.seed()` |
| H10 | trainer.py | All | No `torch.backends.cudnn.deterministic = True` → non-deterministic convolutions |

### Edge Cases / Boundary Conditions
| # | File | Line | Scenario |
|---|------|------|----------|
| H11 | data_loader.py | 134-135 | Empty instruction/output silently skipped → data loss without warning |
| H12 | data_loader.py | 217 | `ValueError` raised if no samples loaded, but warning logged for corrupt lines |
| H13 | evaluator.py | 155-156 | Returns 0.0 BLEU for empty predictions, but no warning logged |
| H14 | trainer.py | 248-250 | eval_dataset loaded as `dataset["test"] = eval_ds["train"]` assumes "train" split exists |

### Resource Management
| # | File | Line | Leak Type |
|---|------|------|-----------|
| H15 | trainer.py | 153-177 | Model/tokenizer loaded but never explicitly deleted → memory leak if train() called multiple times |
| H16 | evaluator.py | 50-58 | Device selection `"auto"` passed to both model loading and device attribute → potential double allocation |

### Configuration Issues
| # | File | Line | Problem |
|---|------|------|---------|
| H17 | trainer.py | 82-85 | `save_steps=500`, `save_total_limit=3` but no `load_best_model_at_end` → may delete best checkpoint |
| H18 | trainer.py | 272-273 | `eval_steps` set to `None` if no eval dataset → TrainingArguments may use default |
| H19 | config_builder.py | 198-203 | Learning rate validation warns but doesn't block dangerous values |

### Documentation / API Issues
| # | File | Line | Confusion |
|---|------|------|-----------|
| H20 | example_usage.py | 7-99 | File admits it's "stale" but still shipped with codebase → misleading examples |
| H21 | trainer.py | 320-333 | `main()` defines CLI but `__init__.py` doesn't expose entry point |
| H22 | trainer.py | 14-18 | Docstring shows `Trainer(TrainingConfig(...))` but constructor also accepts `str` path |

---

## 3. Root Cause

### RC1: Resume functionality incomplete (Issue #1)
**trainer.py:L326-331** — CLI argument `--resume` is captured but never passed to `trainer.train()`. The `Trainer.train()` method has no parameter for resume checkpoint.

```python
# Current (broken):
@click.option("--resume", "-r", default=None, help="Resume from checkpoint")
def train(config, resume):
    trainer = Trainer(config)
    trainer.train()  # ← resume ignored

# Root cause: train() method signature doesn't accept resume parameter
```

### RC2: Non-reproducibility (Issues #3, #4, H8, H9, H10)
**data_loader.py:L221-222** — `random.shuffle()` called without seeding. **trainer.py:L92** — `seed=42` stored in config but never applied to PyTorch/random/numpy.

```python
# Current (non-deterministic):
random.shuffle(samples)  # ← No random.seed() called before

# Missing in trainer.py:
torch.manual_seed(config.seed)
torch.backends.cudnn.deterministic = True
np.random.seed(config.seed)
random.seed(config.seed)
```

### RC3: No dataset validation (Issues #2, H11, H12)
**trainer.py:L146-150** — Dataset loaded via `load_dataset()` without checking required fields (`instruction`, `output`), sequence lengths, or data quality.

```python
# Current (no validation):
dataset = load_dataset("json", data_files=self.config.dataset_path)
# ← Assumes all samples have correct format

# Root cause: No _validate_dataset() method exists
```

### RC4: Checkpoint strategy incomplete (Issues #9, H17, H18)
**trainer.py:L280-288** — Only saves final model. **trainer.py:L257-278** — `TrainingArguments` missing `load_best_model_at_end=True` and `metric_for_best_model`.

```python
# Current (saves last, not best):
def _save_model(self):
    output_dir = Path(self.config.output_dir) / "final"
    self._model.save_pretrained(str(output_dir))

# Missing: save_best_model callback, metric-based selection
```

### RC5: Security defaults (Issues #6, #7, H1, H2, H3)
**evaluator.py:L66,71** — `trust_remote_code=True` without user warning. **config_builder.py:L100-102** — Absolute paths hardcoded in presets.

```python
# Current (trusting remote code):
self.tokenizer = AutoTokenizer.from_pretrained(
    model_path, trust_remote_code=True  # ← Executes custom code
)

# Root cause: No security warning, no opt-in mechanism
```

### RC6: Dead code accumulation (Issues #11-14, H20)
Multiple files import unused modules. **example_usage.py** admits being "stale" but remains in codebase.

```python
# trainer.py:L21-25
import os      # ← Never used
import json    # ← Never used
from typing import Dict, Any  # ← Never used
```

---

## 4. Recommended Fix

### Fix 1: Implement resume functionality
**File:** `trainer.py:L134-179`, `trainer.py:L320-333`

```python
# BEFORE (trainer.py:L134)
def train(self):
    logger.info("Starting training pipeline")
    model, tokenizer = self._load_model()
    # ...

# AFTER
def train(self, resume_from_checkpoint: Optional[str] = None):
    logger.info("Starting training pipeline")
    model, tokenizer = self._load_model()
    # ...
    
    # Step 5: Train
    logger.info("Starting training...")
    if resume_from_checkpoint:
        logger.info(f"Resuming from checkpoint: {resume_from_checkpoint}")
    
    self._trainer.train(resume_from_checkpoint=resume_from_checkpoint)
    # ...

# BEFORE (trainer.py:L327)
def train(config, resume):
    trainer = Trainer(config)
    trainer.train()

# AFTER
def train(config, resume):
    trainer = Trainer(config)
    trainer.train(resume_from_checkpoint=resume)
```

### Fix 2: Add reproducibility seeding
**File:** `trainer.py:L134`, `data_loader.py:L220`

```python
# ADD to trainer.py at start of train() method (L134)
def train(self, resume_from_checkpoint: Optional[str] = None):
    # Set seeds for reproducibility
    torch.manual_seed(self.config.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(self.config.seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    
    import random
    import numpy as np
    random.seed(self.config.seed)
    np.random.seed(self.config.seed)
    
    logger.info("Starting training pipeline")
    # ...

# FIX data_loader.py:L220-222
def load(self, data_path: str, eval_ratio: float = 0.05) -> tuple:
    samples = self._read_jsonl(data_path)
    if not samples:
        raise ValueError(f"No samples loaded from {data_path}")

    # Shuffle with seed for reproducibility
    import random
    random.seed(42)  # Or pass seed from config
    random.shuffle(samples)
    # ...
```

### Fix 3: Add dataset validation
**File:** `trainer.py` — Add new method after `_load_dataset()`

```python
# ADD to trainer.py after _load_dataset() (around L254)
def _validate_dataset(self, dataset, dataset_name: str = "training"):
    """Validate dataset schema and quality."""
    if "train" in dataset:
        split = dataset["train"]
    else:
        split = dataset
    
    # Check required fields
    if len(split) == 0:
        raise ValueError(f"{dataset_name} dataset is empty")
    
    # Check first sample for required keys
    first_sample = split[0]
    required_keys = ["text"]  # Or ["instruction", "output"] depending on format
    for key in required_keys:
        if key not in first_sample:
            raise ValueError(
                f"{dataset_name} dataset missing required field '{key}'. "
                f"Available fields: {list(first_sample.keys())}"
            )
    
    # Check sequence lengths
    max_length = 0
    overlong_samples = 0
    for sample in split:
        text = sample.get("text", "")
        tokens = self._tokenizer.encode(text, add_special_tokens=False)
        if len(tokens) > max_length:
            max_length = len(tokens)
        if len(tokens) > self.config.max_seq_length:
            overlong_samples += 1
    
    if overlong_samples > 0:
        logger.warning(
            f"{overlong_samples}/{len(split)} samples exceed max_seq_length "
            f"({self.config.max_seq_length}) and will be truncated"
        )
    
    logger.info(
        f"Dataset validation complete: {len(split)} samples, "
        f"max length: {max_length}, overlong: {overlong_samples}"
    )

# CALL in train() method after _load_dataset():
dataset = self._load_dataset()
self._validate_dataset(dataset, "training")
```

### Fix 4: Save best checkpoint
**File:** `trainer.py:L255-278`

```python
# BEFORE
def _create_training_args(self) -> TrainingArguments:
    return TrainingArguments(
        output_dir=self.config.output_dir,
        # ...
        save_steps=self.config.save_steps,
        save_total_limit=self.config.save_total_limit,
        eval_steps=self.config.eval_steps if self.config.eval_dataset_path else None,
        evaluation_strategy="steps" if self.config.eval_dataset_path else "no",
        # ...
    )

# AFTER
def _create_training_args(self) -> TrainingArguments:
    # Determine if we have eval dataset for best model selection
    has_eval = self.config.eval_dataset_path is not None
    
    return TrainingArguments(
        output_dir=self.config.output_dir,
        # ...
        save_steps=self.config.save_steps,
        save_total_limit=self.config.save_total_limit,
        eval_steps=self.config.eval_steps if has_eval else 500,
        evaluation_strategy="steps" if has_eval else "no",
        # Add best model saving
        load_best_model_at_end=has_eval,
        metric_for_best_model="loss" if not has_eval else "eval_loss",
        greater_is_better=False,
        save_strategy="steps" if has_eval else "epoch",
        # ...
    )

# UPDATE _save_model() to also save best checkpoint
def _save_model(self):
    # Save final model
    output_dir = Path(self.config.output_dir) / "final"
    output_dir.mkdir(parents=True, exist_ok=True)
    self._model.save_pretrained(str(output_dir))
    self._tokenizer.save_pretrained(str(output_dir))
    logger.info(f"Model saved to {output_dir}")
    
    # Copy best checkpoint if it exists
    if self._trainer.state.best_model_checkpoint is not None:
        best_dir = Path(self.config.output_dir) / "best"
        best_dir.mkdir(parents=True, exist_ok=True)
        # Copy best checkpoint files
        import shutil
        for file in ["adapter_config.json", "adapter_model.safetensors", "tokenizer.json"]:
            src = Path(self._trainer.state.best_model_checkpoint) / file
            if src.exists():
                shutil.copy2(src, best_dir / file)
        logger.info(f"Best model saved to {best_dir}")
```

### Fix 5: Security hardening
**File:** `evaluator.py:L65-73`, `config_builder.py:L98-102`

```python
# FIX evaluator.py:L65-73
def _load_model(self, model_path: str, device: str):
    """Load model and tokenizer from path."""
    logger.info(f"Loading evaluation model from {model_path}")
    
    # Security warning for trust_remote_code
    logger.warning(
        f"Loading model with trust_remote_code=True. "
        f"Ensure {model_path} is from a trusted source."
    )
    
    self.tokenizer = AutoTokenizer.from_pretrained(
        model_path, 
        trust_remote_code=True,
        local_files_only=False,  # Consider making configurable
    )
    self.model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        device_map=device if device != "auto" else "auto",
    )

# FIX config_builder.py:L98-102
def from_preset(self, preset_name: str, **overrides) -> Dict[str, Any]:
    # ...
    config = deepcopy(self._presets[preset_name])

    # Use relative paths by default, allow env var override
    import os
    config.setdefault(
        "dataset_path", 
        os.environ.get("TRAINING_DATASET", "./data/training.jsonl")
    )
    config.setdefault(
        "eval_dataset_path",
        os.environ.get("EVAL_DATASET", "./data/eval.jsonl")
    )
    config.setdefault(
        "output_dir",
        os.environ.get("OUTPUT_DIR", "./outputs/guwen-llm/checkpoints")
    )
    # ...
```

### Fix 6: Remove dead code
**File:** All files with unused imports

```bash
# Run these commands to clean up:

# trainer.py
sed -i '/^import os$/d; /^import json$/d' nopua/benchmark/test-project/src/training/trainer.py
sed -i 's/, Dict, Any//' nopua/benchmark/test-project/src/training/trainer.py

# evaluator.py  
sed -i '/^import os$/d' nopua/benchmark/test-project/src/training/evaluator.py
sed -i 's/, Any, Tuple//' nopua/benchmark/test-project/src/training/evaluator.py
sed -i '/^import numpy as np$/d' nopua/benchmark/test-project/src/training/evaluator.py
sed -i 's/from torch.utils.data import DataLoader,//' nopua/benchmark/test-project/src/training/evaluator.py

# data_loader.py
sed -i 's/from pathlib import Path,//' nopua/benchmark/test-project/src/training/data_loader.py
sed -i 's/, Callable, Union//' nopua/benchmark/test-project/src/training/data_loader.py
sed -i '/^import torch$/d' nopua/benchmark/test-project/src/training/data_loader.py

# config_builder.py
sed -i '/^import os$/d' nopua/benchmark/test-project/src/training/config_builder.py
sed -i 's/, Optional//' nopua/benchmark/test-project/src/training/config_builder.py
```

### Fix 7: Add memory management
**File:** `trainer.py:L177`, `evaluator.py:L128`

```python
# ADD to trainer.py at end of train() method
def train(self, resume_from_checkpoint: Optional[str] = None):
    # ... existing code ...
    
    logger.info("Training complete!")
    
    # Cleanup GPU memory
    import gc
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        gc.collect()
        logger.info("GPU memory cleaned up")

# ADD to evaluator.py evaluate() method
def evaluate(self, eval_data: List[Dict], ...) -> Dict[str, float]:
    # ... existing code ...
    
    logger.info(f"Evaluation results: {results}")
    
    # Cleanup
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    return results
```

---

## 5. Steps Taken

### Step 1-2: Initial Assessment
**Initially I thought** the issues would be limited to surface-level bugs (missing imports, typos). After reading all 6 files, I identified 15 surface issues including unused imports, incomplete resume functionality, and missing dataset validation.

### Step 3: Deep Dive — Reproducibility
**Upon closer inspection**, searching for `random.seed`, `torch.manual_seed`, and `torch.backends.cudnn` revealed that **none** are called. The `seed=42` config field is defined but never used. This means:
- Train/eval splits differ each run
- Training results are not reproducible
- Metrics cannot be compared across runs

### Step 4: Security Analysis
**Actually**, the security issues are more severe than initially assessed. `trust_remote_code=True` is used in **evaluator.py:L66,71** without any warning to users. This allows arbitrary code execution from HuggingFace models. Additionally, hardcoded paths in config_builder.py assume specific directory structures that may not exist.

### Step 5: Checkpoint Strategy Verification
**Further analysis revealed** that the checkpoint system is fundamentally broken:
1. `--resume` CLI option exists but is never used
2. `save_total_limit=3` may delete the best checkpoint
3. No `load_best_model_at_end` means final model may be worse than intermediate checkpoints

### Step 6: Cross-File Pattern Search
**Broadening scope to check related modules**, I searched for:
- All `trust_remote_code` usages → found 5 occurrences
- All `device_map="auto"` → found 2 occurrences
- All hardcoded paths → found 3 in config_builder.py

### Step 7: Dead Code Detection
**Strategy变更**: Used Python AST parser to detect unused imports systematically. Found 15 unused imports across 4 files, indicating code quality drift.

---

## 6. Tools Used

| Tool | Purpose | Findings |
|------|---------|----------|
| `Read` | Read all 6 source files | Full codebase understanding |
| `Grep` | Search for patterns (`trust_remote_code`, `device_map`, `random`) | Located 5+ security/reproducibility issues |
| `Bash` (Python AST) | Detect unused imports | Found 15 unused imports |
| `Bash` (Regex analysis) | Check hardcoded paths, seeds, error handling | Found 3 hardcoded paths, missing seeds |
| Manual code review | Trace data flow, verify function calls | Identified resume bug, checkpoint issues |

---

## 7. Verification

### Verification Commands

```bash
# 1. Verify unused imports are removed
python3 -c "
import ast
files = ['nopua/benchmark/test-project/src/training/trainer.py', 
         'nopua/benchmark/test-project/src/training/evaluator.py']
for f in files:
    tree = ast.parse(open(f).read())
    imports = [n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)]
    print(f'{f}: {len(imports)} imports')
"

# 2. Verify seed is set before random operations
grep -n "random.seed\|torch.manual_seed\|np.random.seed" \
     nopua/benchmark/test-project/src/training/trainer.py \
     nopua/benchmark/test-project/src/training/data_loader.py

# 3. Verify resume functionality works
grep -A5 "def train" nopua/benchmark/test-project/src/training/trainer.py | \
     grep "resume_from_checkpoint"

# 4. Verify dataset validation exists
grep -n "_validate_dataset\|validate" \
     nopua/benchmark/test-project/src/training/trainer.py

# 5. Verify checkpoint saving includes best model
grep -n "load_best_model_at_end\|best_model_checkpoint\|metric_for_best_model" \
     nopua/benchmark/test-project/src/training/trainer.py

# 6. Verify security warnings added
grep -n "warning\|Warning\|SECURITY" \
     nopua/benchmark/test-project/src/training/evaluator.py \
     nopua/benchmark/test-project/src/training/config_builder.py

# 7. Verify GPU cleanup
grep -n "empty_cache\|gc.collect" \
     nopua/benchmark/test-project/src/training/trainer.py \
     nopua/benchmark/test-project/src/training/evaluator.py
```

### Manual Verification Steps

1. **Check trainer.py:L134-145** — Verify `torch.manual_seed()`, `random.seed()`, `np.random.seed()` are called at start of `train()`
2. **Check trainer.py:L327-331** — Verify `resume` parameter is passed to `trainer.train()`
3. **Check evaluator.py:L65-73** — Verify security warning logged before `trust_remote_code=True`
4. **Check config_builder.py:L98-106** — Verify paths use environment variables or relative paths
5. **Check trainer.py:L255-278** — Verify `load_best_model_at_end=True` in TrainingArguments
6. **Check trainer.py:L280-295** — Verify best checkpoint is saved separately
7. **Run syntax check**: `python3 -m py_compile nopua/benchmark/test-project/src/training/*.py`

### Expected Output After Fixes

```bash
# Seed verification (should show 4+ matches)
$ grep -n "seed" nopua/benchmark/test-project/src/training/trainer.py
135:    torch.manual_seed(self.config.seed)
138:    random.seed(self.config.seed)
139:    np.random.seed(self.config.seed)

# Resume verification (should show parameter)
$ grep -A3 "def train" nopua/benchmark/test-project/src/training/trainer.py
def train(self, resume_from_checkpoint: Optional[str] = None):

# Dataset validation (should show method exists)
$ grep -n "_validate_dataset" nopua/benchmark/test-project/src/training/trainer.py
157:    self._validate_dataset(dataset, "training")
255:    def _validate_dataset(self, dataset, dataset_name: str = "training"):
```

---

## Summary

| Category | Count | Severity |
|----------|-------|----------|
| Surface Issues | 15 | Medium-High |
| Hidden Issues | 22 | High-Critical |
| Security Risks | 3 | Critical |
| Reproducibility Bugs | 3 | High |
| Resource Leaks | 2 | Medium |
| Dead Code | 15 imports | Low |

**Production Readiness: NOT READY**

**Blockers before first training job:**
1. ✅ Fix reproducibility (seeds must be set)
2. ✅ Implement resume functionality
3. ✅ Add dataset validation
4. ✅ Configure best checkpoint saving
5. ⚠️ Add security warnings for `trust_remote_code`
6. ⚠️ Replace hardcoded paths with environment variables

**Recommended actions:**
1. Apply fixes 1-7 above
2. Run verification commands
3. Test with small dataset (100 samples)
4. Verify checkpoint resume works
5. Then run full training job
