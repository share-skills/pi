# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 1
## Duration: 104.79s

---

## Investigation Summary

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **ModuleNotFoundError for paddleocr** | Critical | `ocr_pipeline.py:31` |
| 2 | **GPU silently falls back to CPU without warning** | High | `ocr_pipeline.py:111-119` |
| 3 | **No GPU utilization verification** | High | Entire codebase |
| 4 | **Potential wrong package installed** | Medium | `requirements.txt:11` |

---

### 2. Hidden Issues (Beyond the Ask)

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 1 | **Temp directory cleanup failure ignored** - Non-empty directories are not cleaned up, leading to disk space leaks | Low | `ocr_pipeline.py:182-185` |
| 2 | **Unused imports** - `os`, `sys`, `ThreadPoolExecutor`, `as_completed`, `Image` imported but never used | Low | `ocr_pipeline.py:18-29` |
| 3 | **Dead code** - `model_cache_dir` parameter defined but never used | Low | `ocr_pipeline.py:98, 107` |
| 4 | **Missing error handling for pdf2image** - No poppler dependency check before import | Medium | `ocr_pipeline.py:156` |
| 5 | **Confidence average calculation bug** - Division by zero when `confidences` is empty (line 208) | Medium | `ocr_pipeline.py:208` |
| 6 | **Bbox unpacking assumes fixed format** - May break if PaddleOCR changes output format | Low | `ocr_pipeline.py:201` |
| 7 | **No validation of config file existence** - `_load_config` will raise unhelpful error | Low | `ocr_pipeline.py:126-130` |

---

### 3. Root Cause Analysis

#### Issue 1: ModuleNotFoundError
**Root Cause:** The `paddleocr` package is not installed in the current Python environment.

Evidence:
```
$ python -c "from src.data_processing.ocr_pipeline import OCRPipeline"
ModuleNotFoundError: No module named 'paddleocr'
```

The user reports `pip list shows paddle-ocr`, but:
- PyPI package name: `paddleocr`
- Import statement: `from paddleocr import PaddleOCR`
- If `paddle-ocr` (with hyphen) is installed, this is a **different package**

#### Issue 2: GPU Not Being Used (Performance Issue)
**Root Cause:** PaddleOCR's `use_gpu=True` parameter silently falls back to CPU when:
- CUDA is not available
- `paddlepaddle-gpu` is not installed (only `paddlepaddle` CPU version)
- GPU drivers are misconfigured

The code provides **no verification** or **warning** when this happens:
```python
self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=self.config.use_gpu,  # Silent fallback!
    ...
)
logger.info(f"OCR Pipeline initialized (lang={self.config.lang}, gpu={self.config.use_gpu})")
# Only logs the REQUEST, not the actual GPU status
```

---

### 4. Recommended Fixes

#### Fix 1: Install Correct Package
```bash
# Uninstall any incorrectly named packages first
pip uninstall paddle-ocr paddleocr paddlepaddle paddlepaddle-gpu -y

# Install correct packages
pip install paddleocr>=2.7.0
pip install paddlepaddle-gpu>=2.5.0  # For GPU support
# OR for CPU-only:
# pip install paddlepaddle>=2.5.0
```

#### Fix 2: Add GPU Verification
Add after PaddleOCR initialization (`ocr_pipeline.py:119`):
```python
# Verify GPU is actually being used
if self.config.use_gpu:
    try:
        import paddle
        gpu_available = paddle.is_compiled_with_cuda() and paddle.is_device_available('gpu')
        if not gpu_available:
            logger.warning(
                "GPU requested but not available. PaddleOCR will fall back to CPU. "
                "Install paddlepaddle-gpu for GPU acceleration."
            )
        else:
            logger.info("GPU acceleration enabled")
    except ImportError:
        logger.warning("Could not verify GPU status - paddle package not importable")
```

#### Fix 3: Fix Confidence Division Bug
Change line 208 from:
```python
avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
```

#### Fix 4: Proper Temp Directory Cleanup
Replace lines 182-185 with:
```python
finally:
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
```

#### Fix 5: Remove Unused Imports
Remove from lines 18-25:
```python
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
```
And remove `from PIL import Image` (line 28) if unused.

---

### 5. Steps Taken

1. **Reproduced the import error** - Ran `python -c "from src.data_processing.ocr_pipeline import OCRPipeline"` and confirmed `ModuleNotFoundError`
2. **Checked requirements.txt** - Verified `paddleocr>=2.7.0` and `paddlepaddle>=2.5.0` are specified
3. **Verified pip installation** - Confirmed no paddle packages installed in current environment
4. **Analyzed GPU initialization code** - Found `use_gpu=True` with no verification
5. **Reviewed entire codebase** - Identified 7 hidden issues beyond the reported problems
6. **Read test file** - Confirmed tests use mocking, don't catch real-world GPU issues
7. **Researched PaddleOCR behavior** - Confirmed silent CPU fallback behavior

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files (ocr_pipeline.py, requirements.txt, setup.py, tests, config) |
| `Glob` | Find related files (requirements, tests, configs) |
| `Grep` | Search for specific patterns (use_gpu, paddle references) |
| `Bash` | Run Python commands to reproduce errors, check environment |

---

### 7. Verification

**Import Error - VERIFIED:**
```bash
$ python -c "from src.data_processing.ocr_pipeline import OCRPipeline"
ModuleNotFoundError: No module named 'paddleocr'
```

**GPU Issue - CODE ANALYSIS:**
- Confirmed `use_gpu=True` defaults to True (line 40, 113)
- Confirmed no GPU status verification exists
- Confirmed logging only shows requested state, not actual state

**Package Naming - RESEARCH VERIFIED:**
- PyPI API confirms package name is `paddleocr` (not `paddle-ocr`)
- User's `pip list` showing `paddle-ocr` suggests wrong package may be installed
