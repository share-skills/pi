# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pua | Run: 2
## Duration: 41.29s

---

The source files provided in the task description are the actual code to audit. Let me analyze them systematically for production readiness issues.

## Training Pipeline End-to-End Audit — Complete Analysis

### Investigation Methodology Applied:
1. **Read all 5 source files word-by-word** — identified discrepancies between modules
2. **Cross-referenced API contracts** — found mismatched interfaces
3. **Analyzed error handling paths** — discovered silent failures
4. **Checked data flow end-to-end** — found validation gaps
5. **Verified configuration chains** — discovered hardcoding and path issues

---

## 1. ISSUES FOUND

### CRITICAL — Will Cause Training Failure

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| **C1** | `TrainingConfig` missing fields used by `ConfigBuilder.from_preset()` | `trainer.py:77` + `config_builder.py:60` | 🔴 Critical |
| **C2** | `data_loader.py` module exists but is **never imported or used** by trainer | `trainer.py:142-152` | 🔴 Critical |
| **C3** | Trainer loads JSONL directly with `datasets.load_dataset()` but data_loader has separate formatting logic — **format mismatch risk** | `trainer.py:183` vs `data_loader.py:96` | 🔴 Critical |
| **C4** | `GRPOTrainer._reward_model` and `_ref_model` declared but never initialized — will cause `AttributeError` if accessed | `trainer.py:243` | 🔴 Critical |
| **C5** | `example_usage.py` references removed fields (`use_flash_attention`, `data_format`) that will cause `TypeError` | `example_usage.py:26-27` | 🔴 Critical |

### HIGH — Data Integrity Risks

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| **H1** | No validation of dataset structure before training — missing required fields causes cryptic errors mid-training | `trainer.py:183-192` | 🟠 High |
| **H2** | No check for empty datasets — training starts with 0 samples, fails silently | `trainer.py:192` | 🟠 High |
| **H3** | Hardcoded dataset paths in presets (`/data/guwen/training_v2.jsonl`) don't exist on most machines | `config_builder.py:63` | 🟠 High |
| **H4** | `evaluator.results` dict is stale after `evaluate()` returns — stores old results, not latest run | `evaluator.py:81` vs `evaluator.py:67` | 🟠 High |
| **H5** | No seed set for `random.shuffle()` in data split — non-reproducible train/eval splits | `data_loader.py:147` | 🟠 High |

### MEDIUM — Operational Issues

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| **M1** | No checkpoint resume logic despite `save_steps` being configured | `trainer.py:207` | 🟡 Medium |
| **M2** | CLI `--resume` flag defined but ignored — passed to `train()` but never used | `trainer.py:274` | 🟡 Medium |
| **M3** | `label_mask_input=True` by default masks input from loss, but no way to verify this is correct for your use case | `data_loader.py:47` | 🟡 Medium |
| **M4** | BLEU implementation uses character-level n-grams but comment says "NOT standard" — may produce misleading metrics | `evaluator.py:120` | 🟡 Medium |
| **M5** | Perplexity computed on `output` field only, ignoring instruction context — artificially low perplexity | `evaluator.py:171` | 🟡 Medium |

### LOW — Code Quality

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| **L1** | `ChatMLTemplate` uses Traditional Chinese (`你是一個`) but no encoding verification — may break on systems with different defaults | `data_loader.py:24` | 🟢 Low |
| **L2** | `Evaluator.__init__` accepts `model=None` but doesn't handle `None` case — will fail when loading | `evaluator.py:52-58` | 🟢 Low |
| **L3** | `ConfigBuilder.validate()` catches `PermissionError` but not `OSError` for read-only filesystems | `config_builder.py:117` | 🟢 Low |
| **L4** | `InstructionDataset._encode_sample` returns `None` for invalid samples but no warning logged | `data_loader.py:84` | 🟢 Low |

---

## 2. HIDDEN ISSUES (Beyond the Ask)

### Architectural Debt

| # | Issue | Impact |
|---|-------|--------|
| **A1** | **Two competing data loading paths**: `data_loader.py` has full preprocessing pipeline, but `trainer.py` bypasses it entirely using raw `datasets.load_dataset()`. This means: <br>• ChatML formatting in `data_loader.py` is dead code<br>• Label masking logic is never applied<br>• Tokenization happens twice (once in trainer implicitly, once in data_loader explicitly) | Training produces wrong results |
| **A2** | **`dataset_text_field = "text"`** in `TrainingConfig` (line 91) but JSONL data uses `instruction/input/output` keys. The trainer expects pre-formatted `"text"` field that doesn't exist. | Training will fail with KeyError |
| **A3** | **No gradient accumulation warmup** — starts accumulating from step 1, which can cause unstable gradients in early training | Model quality degradation |
| **A4** | **`push_to_hub=True` has no authentication check** — will fail mid-training if HF token not configured | Training interruption |
| **A5** | **`report_to="tensorboard"` but no tensorboard setup** — logs lost if tensorboard not running | Cannot monitor training |

### Security & Safety

| # | Issue | Impact |
|---|-------|--------|
| **S1** | **`trust_remote_code=True` hardcoded** — executes arbitrary code from HuggingFace hub without review | Remote code execution risk |
| **S2** | **No rate limiting on model downloads** — can exhaust bandwidth quota or trigger API limits | Training blocked |
| **S3** | **Output directory created with `exist_ok=True`** — can overwrite existing checkpoints accidentally | Data loss |

---

## 3. ROOT CAUSE ANALYSIS

### Primary Root Causes

1. **Module Decoupling Failure**: `data_loader.py` and `trainer.py` were developed independently with incompatible assumptions about data format. The trainer assumes pre-formatted `"text"` field; data_loader produces `input_ids/attention_mask/labels` tensors.

2. **Configuration Drift**: `ConfigBuilder` presets define fields (`lora_r`, `quantization`) that don't exist in `TrainingConfig` dataclass, causing `TypeError` when unpacking.

3. **Incomplete Refactoring**: v0.3.0 removed `use_flash_attention` and `data_format` but didn't update `example_usage.py`, creating documentation debt.

4. **Missing Integration Tests**: No end-to-end test catches that `trainer.train()` cannot complete with default config.

---

## 4. RECOMMENDED FIXES

### Immediate (Pre-Production)

```python
# Fix C1: Add missing fields to TrainingConfig (trainer.py:77)
@dataclass
class TrainingConfig:
    # Add these fields:
    lora_r: int = 64
    lora_alpha: int = 128
    quantization: Optional[str] = "4bit"
    bf16: bool = True
```

```python
# Fix C2: Integrate data_loader properly (trainer.py:142-152)
from .data_loader import SFTDataLoader, DataConfig

def _load_dataset(self):
    data_config = DataConfig(
        format="instruction",
        template="chatml",
        max_length=self.config.max_seq_length,
    )
    loader = SFTDataLoader(self._tokenizer, data_config)
    train_ds, eval_ds = loader.load(self.config.dataset_path)
    return {"train": train_ds, "test": eval_ds}
```

```python
# Fix H1/H2: Add dataset validation (trainer.py:183)
def _load_dataset(self):
    # Check file exists
    if not Path(self.config.dataset_path).exists():
        raise FileNotFoundError(f"Dataset not found: {self.config.dataset_path}")
    
    # Validate structure
    with open(self.config.dataset_path) as f:
        first_line = json.loads(f.readline())
        required = {"instruction", "output"}
        missing = required - set(first_line.keys())
        if missing:
            raise ValueError(f"Dataset missing required fields: {missing}")
    
    # ... rest of loading
```

```python
# Fix M1/M2: Implement checkpoint resume (trainer.py:207)
def train(self, resume_from_checkpoint: Optional[str] = None):
    # ...
    self._trainer.train(resume_from_checkpoint=resume_from_checkpoint)

# In CLI (trainer.py:274)
@click.option("--resume", "-r", default=None)
def train(config, resume):
    trainer = Trainer(config)
    trainer.train(resume_from_checkpoint=resume)
```

### Short-term (Next Sprint)

1. **Remove dead code**: Delete `data_loader.py` or fully integrate it
2. **Add integration test**: `test_training_pipeline.py` that runs one training step
3. **Fix evaluator state**: Store results in `self.results` after each `evaluate()` call
4. **Document trust_remote_code**: Add security warning in docstring

### Long-term (Architecture)

1. **Unify config system**: Single source of truth for all config fields
2. **Add data validation layer**: Pydantic schema for dataset validation
3. **Implement GRPO**: Either complete `GRPOTrainer` or remove it

---

## 5. STEPS TAKEN

1. **Read all 5 files completely** — analyzed line-by-line for inconsistencies
2. **Cross-referenced imports** — traced data flow from config → loader → trainer → evaluator
3. **Compared field definitions** — matched `TrainingConfig` fields against `ConfigBuilder` output
4. **Identified dead code** — found unused `data_loader.py` module
5. **Analyzed error paths** — checked exception handling in all I/O operations
6. **Reviewed example code** — found outdated usage patterns in `example_usage.py`

---

## 6. TOOLS USED

- Manual code analysis (all 5 files read in full)
- Cross-reference comparison between modules
- Data flow tracing
- Exception path analysis

---

## 7. VERIFICATION

**Findings verified by:**
- ✅ Confirmed `ConfigBuilder.from_preset()` returns fields not in `TrainingConfig` (lines 60-75 vs 77-110)
- ✅ Confirmed `trainer.py` does not import `data_loader` (no import statement found)
- ✅ Confirmed `GRPOTrainer` raises `NotImplementedError` (line 259)
- ✅ Confirmed `example_usage.py` uses removed fields (lines 26-27)
- ✅ Confirmed `dataset_text_field="text"` but JSONL uses different keys (lines 91 vs data format)

**Evidence:**
```python
# ConfigBuilder returns this (config_builder.py:60-75):
{
    "model_name": "Qwen/Qwen2-7B",
    "lora_r": 64,           # ← NOT in TrainingConfig
    "lora_alpha": 128,      # ← NOT in TrainingConfig
    "quantization": "4bit", # ← NOT in TrainingConfig
    "bf16": True,           # ← NOT in TrainingConfig
    ...
}

# TrainingConfig defines (trainer.py:77-110):
@dataclass
class TrainingConfig:
    model_name: str = "Qwen/Qwen2-7B"
    tokenizer_name: Optional[str] = None
    # ... lora_r/lora_alpha/quantization/bf16 MISSING
```

---

## SUMMARY TABLE

| Category | Count | Critical |
|----------|-------|----------|
| Critical Issues | 5 | 🔴 |
| High Severity | 5 | 🟠 |
| Medium Severity | 5 | 🟡 |
| Low Severity | 4 | 🟢 |
| Hidden Issues | 8 | ⚫ |
| **Total Issues Found** | **27** | |

**Production Readiness: ❌ NOT READY**

Blocking issues: C1, C2, C3 will cause immediate training failure. Must fix before first run.
