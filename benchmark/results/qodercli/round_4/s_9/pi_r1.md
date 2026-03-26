# Scenario 9: Training Pipeline End-to-End Audit
## Condition: pi | Run: 1
## Duration: 173.94s

---

Now I have a comprehensive understanding of the issues. Let me compile the full investigation report:

---

## 🧠 PI · Training Pipeline Production Readiness Audit

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **GRPOTrainer not implemented** - raises `NotImplementedError` but exposed in `__all__` | `trainer.py:L291-317` | 🔴 Blocker |
| 2 | **Resume flag ignored** - CLI accepts `--resume` but never passes to `trainer.train()` | `trainer.py:L326-331` | 🔴 Blocker |
| 3 | **No checkpoint resume mechanism** - `TrainingConfig` lacks `resume_from_checkpoint` field | `trainer.py:L80-95` | 🔴 Blocker |
| 4 | **Label masking incorrect** - masks by instruction token count, ignores special tokens mismatch | `data_loader.py:L109-117` | 🔴 Blocker |
| 5 | **Dataset validation missing** - no schema/field validation before training | `trainer.py:L146-156` | 🟡 Major |
| 6 | **Hard-coded absolute paths in presets** - `/data/guwen/`, `/models/guwen-llm/` won't exist | `config_builder.py:L100-102` | 🟡 Major |
| 7 | **Unused import**: `import os` (trainer.py, evaluator.py), `import json` (trainer.py), `import numpy as np` (evaluator.py) | `trainer.py:L21`, `evaluator.py:L18,L25` | ⚪ Minor |
| 8 | **`DataLoader` unused import** - `from torch.utils.data import DataLoader` never used | `evaluator.py:L27` | ⚪ Minor |
| 9 | **`Callable`, `Union` unused imports** in data_loader.py | `data_loader.py:L19` | ⚪ Minor |
| 10 | **Example file warns it's stale** - documents removed fields, will mislead users | `example_usage.py:L7-L34` | 🟡 Major |
| 11 | **`evaluator.results` not updated** - instance attribute never synced with latest `evaluate()` return | `evaluator.py:L60,L128` | 🟡 Major |
| 12 | **No random seed for data shuffle** - `random.shuffle()` not reproducible | `data_loader.py:L221-222` | 🟡 Major |
| 13 | **Evaluation split can be empty** - `max(1, ...)` ensures ≥1 train but eval can be 0 | `data_loader.py:L224-226` | 🟡 Major |
| 14 | **trust_remote_code=True hardcoded** - security risk for untrusted models | `trainer.py:L49,L202,L210`, `evaluator.py:L66,L71` | 🔴 Blocker |
| 15 | **device_map="auto" without memory constraints** - can OOM on multi-GPU | `trainer.py:L203`, `evaluator.py:L72` | 🟡 Major |

---

### 2. Hidden Issues

| # | Issue | Location | Category |
|---|-------|----------|----------|
| H1 | **No gradient accumulation warmup** - first step has unstable gradients | `trainer.py:L261` | Performance |
| H2 | **No max_grad_norm clipping verification** - set to 1.0 but never verified effective | `trainer.py:L73` | Correctness |
| H3 | **BLEU brevity penalty division by zero** - if `len(pred_chars)==0` and `len(ref_chars)>0`, `bp` formula divides by zero | `evaluator.py:L212` | Bug |
| H4 | **Perplexity computation uses only output text** - should use full prompt+response for causal LM | `evaluator.py:L240-258` | Correctness |
| H5 | **No eval during training** - `eval_steps` set but `evaluation_strategy` only enabled if `eval_dataset_path` provided | `trainer.py:L272-273` | Functionality |
| H6 | **SFTTrainer expects dataset with "text" field** - but `_load_dataset()` returns raw JSONL structure | `trainer.py:L169` | Bug |
| H7 | **No early stopping** - training runs all epochs regardless of eval loss | `trainer.py:L255-278` | Performance |
| H8 | **No memory cleanup** - model loaded but never explicitly deleted, can cause OOM in multi-run scenarios | `trainer.py:L153-177` | Resource Leak |
| H9 | **Template inconsistency** - training uses ChatML but evaluation uses different prompt format | `data_loader.py:L38-48` vs `evaluator.py:L131-147` | Correctness |
| H10 | **No validation for LoRA target modules** - assumes all models have `q_proj`, `k_proj`, etc. | `trainer.py:L61-63` | Compatibility |
| H11 | **Batch size too small for large models** - preset `sft_72b` has `batch_size=1`, will be extremely slow | `config_builder.py:L55` | Performance |
| H12 | **No distributed training support** - single GPU only, no DDP/FSDP | Entire module | Scalability |
| H13 | **WandB/tensorboard not configured** - `report_to="tensorboard"` but no logging dir setup | `trainer.py:L94` | Observability |
| H14 | **No data quality checks** - empty strings, duplicates, toxic content not filtered | `data_loader.py:L235-249` | Data Quality |
| H15 | **No overflow handling for long sequences** - truncation happens silently, no warning if >10% truncated | `data_loader.py:L96-101` | Data Quality |

---

### 3. Root Cause

**RC1 - GRPOTrainer not implemented**: The class is a stub with `raise NotImplementedError` at `trainer.py:L310`. It's exported in `__init__.py` but provides no functionality.

**RC2 - Resume mechanism missing**: CLI defines `--resume` at `trainer.py:L326` but the parameter is never passed to `Trainer.train()`, and `TrainingConfig` has no corresponding field.

**RC3 - Label masking logic flawed**: At `data_loader.py:L116-117`, the code counts instruction tokens separately but doesn't account for special tokens (`
