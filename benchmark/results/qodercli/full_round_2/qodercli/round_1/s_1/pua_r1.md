# Scenario 1: OCR Pipeline Import Error
## Condition: pua | Run: 1
## Duration: 158.78s

---

## Structured Investigation Summary

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Package name confusion**: User reports `paddle-ocr` but package is `paddleocr` | Critical | Environment |
| 2 | **Missing paddlepaddle dependency**: Required backend not installed | Critical | `requirements.txt:12` |
| 3 | **Deprecated `use_gpu` parameter**: Removed in PaddleOCR 3.4.0 | Critical | `ocr_pipeline.py:113` |
| 4 | **Deprecated `show_log` parameter**: Removed in PaddleOCR 3.4.0 | Critical | `ocr_pipeline.py:118` |
| 5 | **GPU not being used**: Falls back to CPU silently | High | Performance |
| 6 | **Missing pdf2image dependency**: Not installed in venv | High | `requirements.txt:14` |
| 7 | **Missing poppler-utils**: System dependency for PDF processing | High | System |

### 2. Hidden Issues Discovered Beyond the Ask

1. **API breaking changes**: PaddleOCR upgraded from 2.x to 3.4.0 with breaking API changes - code written for old version
2. **Incomplete dependency installation**: `requirements.txt` specifies packages but venv is missing critical deps
3. **Silent fallback behavior**: Code comment says "Falls back to CPU silently" (`configs/ocr_config.yaml:3`) - this is actually the problem, not a feature
4. **Test coverage gap**: Tests mock `PaddleOCR` so they don't catch initialization failures (`tests/test_ocr_pipeline.py:57-92`)

### 3. Root Cause

**Primary**: The code was written for PaddleOCR 2.x but the environment has PaddleOCR 3.4.0 which has breaking API changes:
- `use_gpu` parameter removed (now auto-detects via paddlex)
- `show_log` parameter removed
- Requires `paddlepaddle` backend which is not installed

**Secondary**: Incomplete environment setup - `pip install -r requirements.txt` was not run or failed silently.

### 4. Recommended Fix

#### Immediate Fixes (Code Changes):

```python
# src/data_processing/ocr_pipeline.py:111-119
# OLD (broken):
self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=self.config.use_gpu,  # REMOVE - deprecated
    use_angle_cls=self.config.use_angle_cls,
    det_model_dir=self.config.det_model_dir,
    rec_model_dir=self.config.rec_model_dir,
    cls_model_dir=self.config.cls_model_dir,
    show_log=False,  # REMOVE - deprecated
)

# NEW (fixed):
paddlex_params = {}
if self.config.det_model_dir:
    paddlex_params["text_detection_model_dir"] = self.config.det_model_dir
if self.config.rec_model_dir:
    paddlex_params["text_recognition_model_dir"] = self.config.rec_model_dir
if self.config.cls_model_dir:
    paddlex_params["textline_orientation_model_dir"] = self.config.cls_model_dir

self._engine = PaddleOCR(
    lang=self.config.lang,
    use_angle_cls=self.config.use_angle_cls if self.config.use_angle_cls else None,
    **paddlex_params,
)
```

#### Environment Fixes (Run in order):

```bash
cd data/test-project
source .venv/bin/activate

# Install missing Python dependencies
pip install paddlepaddle-gpu>=2.5.0  # Or paddlepaddle if no GPU
pip install pdf2image>=1.16.0

# Install system dependency (macOS)
brew install poppler

# Verify installation
python -c "from src.data_processing.ocr_pipeline import OCRPipeline; OCRPipeline()"
```

### 5. Steps Taken

1. **Located actual file**: Found at `data/test-project/src/data_processing/ocr_pipeline.py` (not Windows path provided)
2. **Tested import**: Confirmed module-level import succeeds (lazy loading)
3. **Tested instantiation**: Identified `ValueError: Unknown argument: use_gpu` and `show_log`
4. **Checked package versions**: PaddleOCR 3.4.0 installed, API changed from 2.x
5. **Verified dependencies**: `paddlepaddle` and `pdf2image` missing despite being in requirements.txt
6. **Checked system deps**: poppler-utils (`pdftoppm`) not installed
7. **Searched codebase**: Found 13 uses of `use_gpu`, config files, and tests that mock away the problem

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files (ocr_pipeline.py, requirements.txt, configs, tests) |
| `Glob` | Locate actual file paths |
| `Bash` | Test imports, check packages, verify dependencies |
| `Grep` | Search for deprecated parameter usage across codebase |

### 7. Verification

**Evidence collected:**
- Import test: Module import succeeds (lazy), instantiation fails with `ValueError: Unknown argument: use_gpu`
- Package list: Shows `paddleocr 3.4.0`, `paddlex 3.4.2` - NO `paddlepaddle`
- pdf2image test: `ModuleNotFoundError`
- poppler test: `pdftoppm not found`
- Comprehensive test script confirmed all 7 issues

**To verify fixes work:**
```bash
# After applying fixes, run:
python -c "
from src.data_processing.ocr_pipeline import OCRPipeline, OCRConfig
pipeline = OCRPipeline(OCRConfig(use_gpu=False))  # Should initialize without error
print('SUCCESS: Pipeline initialized')
"
```
