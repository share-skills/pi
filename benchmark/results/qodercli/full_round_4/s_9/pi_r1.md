# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pi | Run: 1
## Duration: 102.69s

---

## Training Pipeline End-to-End Audit Report

---

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **Hardcoded absolute paths in presets** - `/data/guwen/training_v2.jsonl`, `/models/guwen-llm/checkpoints` will not exist on most machines | `config_builder.py:100-102` | 🔴 blocker |
| 2 | **Dataset validation missing** - No schema validation, no required field checks, no empty sample handling before training | `trainer.py:146-156`, `data_loader.py:235-249` | 🔴 blocker |
| 3 | **No checkpoint resume capability** - Training interruption means total progress loss; `resume` CLI param ignored | `trainer.py:87-89`, `trainer.py:326` | 🔴 blocker |
| 4 | **GRPOTrainer dead code** - Uninitialized `_reward_model` and `_ref_model`, raises `NotImplementedError` | `trainer.py:291-317` | 🟡 suggestion |
| 5 | **Stale example_usage.py** - Documents removed fields (`use_flash_attention`, `data_format`) that cause `TypeError` | `example_usage.py:22-34` | 🟡 suggestion |
| 6 | **evaluator.results not updated** - `self.results` stays `{}` after `evaluate()`; users must use return value | `evaluator.py:60`, `evaluator.py:75-129` | 🟡 suggestion |
| 7 | **Missing random seed for reproducibility** - `import random` inside function, no seed set despite config having `seed=42` | `data_loader.py:221-222`, `trainer.py:92` | 🟡 suggestion |
| 8 | **File handles lack context managers** - `open()` without `with` in trainer config loading | `trainer.py:126` | 🟡 suggestion |
| 9 | **trust_remote_code=True hardcoded** - Security risk for arbitrary code execution from HF models | `trainer.py:49`, `evaluator.py:66-71` | 🔴 blocker |
| 10 | **No OOM handling during evaluation** - Large eval batches can crash without recovery | `evaluator.py:95-115` | 🟡 suggestion |
| 11 | **Label masking logic error** - Masking based on instruction token count assumes contiguous tokens | `data_loader.py:109-117` | 🟡 suggestion |
| 12 | **Unused import in evaluator** - `numpy as np` imported but never used | `evaluator.py:25` | ⚪ nit |

---

### 2. Hidden Issues

| # | Issue | Category | Location |
|---|-------|----------|----------|
| 1 | **Security: Arbitrary code execution** - `trust_remote_code=True` allows model authors to run任意代码 | 🔒 Security | `trainer.py:49,202`, `evaluator.py:66-71` |
| 2 | **Resource leak: No cleanup on training failure** - If train() raises, model/tokenizer may not be saved properly | ⚡ Performance/Correctness | `trainer.py:134-179` |
| 3 | **Data corruption: Silent sample dropping** - Samples without `instruction` or `output` silently skipped, no warning | ✅ Correctness | `data_loader.py:134-135` |
| 4 | **Boundary condition: Empty dataset crashes** - `max(1, int(len(samples) * ...))` returns 1 even if samples is empty | ✅ Correctness | `data_loader.py:224` |
| 5 | **Thread safety: Global random state** - `random.shuffle()` affects global state, may break parallel data loading | 🧵 Thread Safety | `data_loader.py:222` |
| 6 | **Memory: No gradient accumulation warmup** - First step uses full accumulation, may OOM | ⚡ Performance | `trainer.py:255-278` |
| 7 | **Configuration: bf16/fp16 mutual exclusion not enforced** - Both could be True simultaneously | ✅ Correctness | `trainer.py:76-77` |
| 8 | **API contract: eval_steps can be 0** - When no eval dataset, `eval_steps=None` passed, behavior undefined | ✅ Correctness | `trainer.py:272-273` |
| 9 | **Cross-platform: Hardcoded Unix paths** - Presets use `/data/`, `/models/` which fail on Windows | 🌐 Cross-platform | `config_builder.py:100-102` |
| 10 | **Observability: No structured logging** - Cannot pipe logs to external monitoring systems | 📖 Observability | All files |

---

### 3. Root Cause

| Issue | Root Cause |
|-------|------------|
| Hardcoded paths | Development environment paths were committed without abstraction to config/env vars (`config_builder.py:100-102`) |
| Missing data validation | Assumption that input JSONL is always well-formed; no defensive programming (`trainer.py:146-156`) |
| No checkpoint resume | Training loop designed for single-run only; `resume` CLI param added but never implemented (`trainer.py:326`) |
| GRPO dead code | Feature was planned but deprioritized; stub left in production code without feature flag (`trainer.py:291-317`) |
| Stale examples | Documentation lag behind API changes; no automated sync between code and examples (`example_usage.py`) |
| evaluator.results bug | Instance attribute initialized but never assigned in `evaluate()` method (`evaluator.py:60`) |
| Missing random seed | Reproducibility config exists but not plumbed through to data shuffling (`data_loader.py:221-222`) |
| trust_remote_code risk | Convenience over security; default should be False with explicit opt-in |

---

### 4. Recommended Fix

#### Priority 1: Blockers (Must fix before production)

**Fix 1: Make paths configurable via environment variables**
```python
# config_builder.py:100-102
config.setdefault("dataset_path", os.environ.get(
    "GUWEN_DATASET_PATH", "/data/guwen/training_v2.jsonl"))
config.setdefault("eval_dataset_path", os.environ.get(
    "GUWEN_EVAL_DATASET_PATH", "/data/guwen/eval_v2.jsonl"))
config.setdefault("output_dir", os.environ.get(
    "GUWEN_OUTPUT_DIR", "/models/guwen-llm/checkpoints"))
```

**Fix 2: Add data validation before training**
```python
# trainer.py: Add new method
def _validate_dataset(self, dataset):
    """Validate dataset schema and content."""
    required_fields = ["input_ids", "labels", "attention_mask"]
    if len(dataset) == 0:
        raise ValueError("Dataset is empty")
    sample = dataset[0]
    for field in required_fields:
        if field not in sample:
            raise ValueError(f"Missing required field: {field}")
    logger.info(f"Dataset validated: {len(dataset)} samples")
```

**Fix 3: Implement checkpoint resume**
```python
# trainer.py:134
def train(self, resume_from_checkpoint: Optional[str] = None):
    # ... existing setup ...
    self._trainer.train(resume_from_checkpoint=resume_from_checkpoint)
```

**Fix 4: Default trust_remote_code to False**
```python
# trainer.py:49
trust_remote_code: bool = False  # Security: require explicit opt-in
```

#### Priority 2: Suggestions

**Fix 5: Update evaluator.results after compute**
```python
# evaluator.py:128
self.results = results  # Add this line before return
return results
```

**Fix 6: Set random seed for reproducibility**
```python
# data_loader.py:221-222
import random
random.seed(42)  # Or pass config.seed
random.shuffle(samples)
```

**Fix 7: Remove or gate GRPOTrainer**
```python
# Option A: Remove entirely
# Option B: Add feature flag check
if not os.environ.get("ENABLE_GRPO_EXPERIMENTAL"):
    raise RuntimeError("GRPO is experimental. Set ENABLE_GRPO_EXPERIMENTAL=1")
```

---

### 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read all 6 training module source files | Identified module structure and dependencies |
| 2 | Searched for TODO/FIXME/XXX markers | Found 1 TODO in GRPOTrainer |
| 3 | Searched for bare except/pass patterns | No silent exception swallowing found |
| 4 | Searched for random usage | Found unseeded random.shuffle() |
| 5 | Searched for file I/O patterns | Found 7 open()/save calls, mixed context manager usage |
| 6 | Searched for trust_remote_code usage | Found 5 instances, all defaulting to True |
| 7 | Read test file | Tests confirm hardcoded paths, missing OOM handling, stale examples |
| 8 | Analyzed data flow: config → load → train → save | Identified missing validation at each stage |
| 9 | Analyzed evaluator metrics computation | Found character-level BLEU, missing numpy usage |
| 10 | Cross-referenced example_usage.py with current API | Confirmed 3+ stale code examples |

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read all 6 source files + test file |
| `Grep` | Search for TODO/FIXME, exception handlers, random usage, file I/O patterns |
| `Glob` | Find related test files |
| `Bash` | Check Python availability |

---

### 7. Verification

**Recommended verification commands:**

```bash
# 1. Verify hardcoded paths don't exist
test -f /data/guwen/training_v2.jsonl && echo "EXISTS" || echo "MISSING (expected)"

# 2. Run existing tests
cd /Users/hepin/IdeaProjects/pi/nopua/benchmark/test-project
pytest tests/test_training_pipeline.py -v

# 3. Test data validation (should fail gracefully)
python3 -c "
from src.training.trainer import Trainer, TrainingConfig
config = TrainingConfig(dataset_path='./nonexistent.jsonl')
trainer = Trainer(config)
# This should raise ValueError, not cryptic HF error
trainer.train()
"

# 4. Test evaluator.results bug
python3 -c "
from src.training.evaluator import Evaluator
evaluator = Evaluator.__new__(Evaluator)
evaluator.results = {}
evaluator.model = None
evaluator.tokenizer = None
evaluator.device = 'cpu'
results = evaluator.evaluate([])
print('evaluator.results:', evaluator.results)  # Should be {}, not updated
print('returned results:', results)  # Should have actual values
"

# 5. Verify random seed reproducibility
python3 -c "
import random
random.seed(42)
data = list(range(10))
random.shuffle(data)
print('Shuffle 1:', data)

random.seed(42)
data = list(range(10))
random.shuffle(data)
print('Shuffle 2:', data)  # Should match Shuffle 1
"
```

**Verification Matrix:**

| Fix | Verification Method | Pass Criteria |
|-----|---------------------|---------------|
| Hardcoded paths | Env var override test | Training starts with custom paths |
| Data validation | Empty/invalid dataset test | Raises ValueError with clear message |
| Checkpoint resume | Interrupted training test | Can resume from last checkpoint |
| trust_remote_code=False | Load remote model test | Requires explicit opt-in |
| evaluator.results | Post-eval inspection | `evaluator.results == returned_results` |
| Random seed | Reproducibility test | Same seed → same shuffle |

---

### Summary Statistics

- **Total Issues Found**: 12 surface issues + 10 hidden issues = **22 issues**
- **Blocker Issues**: 4
- **Suggestion Issues**: 7  
- **Nit Issues**: 1
- **Files Audited**: 6
- **Test Coverage**: Partial (tests exist but don't cover training execution path)
- **Production Readiness**: ❌ **NOT READY** - Must fix Priority 1 blockers before first real training job
