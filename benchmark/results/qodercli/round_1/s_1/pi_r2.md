# Scenario 1: OCR Pipeline Import Error
## Condition: pi | Run: 2
## Duration: 251.71s

---

Now let me compile the final report with all findings:

## 1. Issues Found

| # | Issue | Location |
|---|-------|----------|
| 1 | **PaddleOCR API incompatibility - `use_gpu` parameter removed** | `ocr_pipeline.py:113` |
| 2 | **PaddleOCR API incompatibility - `show_log` parameter doesn't exist** | `ocr_pipeline.py:118` |
| 3 | **Deprecated parameters causing runtime warnings** | `ocr_pipeline.py:114-117` |
| 4 | **Unused imports cluttering code** | `ocr_pipeline.py:18,25,28` |
| 5 | **Hard-coded Unix path `/tmp/guwen_ocr`** | `ocr_pipeline.py:50` |
| 6 | **Resource leak: temporary directory not properly cleaned** | `ocr_pipeline.py:182-185` |

---

## 2. Hidden Issues

| # | Issue | Location | Category |
|---|-------|----------|----------|
| 1 | **paddlepaddle base package not installed** (only paddleocr installed) | Environment | Dependency |
| 2 | **GPU silently falls back to CPU** - no warning when GPU requested but unavailable | `ocr_config.yaml:3` | Performance |
| 3 | **No input validation** on config values (confidence_threshold, dpi, etc.) | `ocr_pipeline.py:97-124` | Correctness |
| 4 | **Bare OSError catch hides real errors** during cleanup | `ocr_pipeline.py:184-185` | Error Handling |
| 5 | **Thread safety issue**: `_stats` dict modified without locks in concurrent context | `ocr_pipeline.py:109,176,297` | Thread Safety |
| 6 | **Missing return type annotation** on multiple public methods | `ocr_pipeline.py:126-333` | Code Quality |
| 7 | **Config file uses hard-coded absolute path** | `ocr_config.yaml:10` | Portability |

---

## 3. Root Cause

### Primary Issue: PaddleOCR v3.x Breaking API Changes

The code was written for PaddleOCR v2.x, but v3.x has breaking changes:

**Old API (v2.x):**
```python
PaddleOCR(
    lang='ch',
    use_gpu=True,           # ❌ REMOVED in v3.x
    use_angle_cls=True,     # ⚠️ Deprecated → use_textline_orientation
    det_model_dir=None,     # ⚠️ Deprecated → text_detection_model_dir
    rec_model_dir=None,     # ⚠️ Deprecated → text_recognition_model_dir
    cls_model_dir=None,     # ⚠️ Deprecated → textline_orientation_model_dir
    show_log=False,         # ❌ DOESN'T EXIST in v3.x
)
```

**New API (v3.x):**
```python
PaddleOCR(
    lang='ch',
    device='gpu',           # ✅ NEW: 'cpu', 'gpu', 'npu', 'gpu:0', etc.
    use_textline_orientation=True,
    text_detection_model_dir=None,
    text_recognition_model_dir=None,
    textline_orientation_model_dir=None,
)
```

**Evidence:**
```
$ python -c "from paddleocr import PaddleOCR; PaddleOCR(use_gpu=True)"
ValueError: Unknown argument: use_gpu

DeprecationWarnings:
- use_angle_cls → use_textline_orientation
- det_model_dir → text_detection_model_dir
- rec_model_dir → text_recognition_model_dir  
- cls_model_dir → textline_orientation_model_dir
```

---

## 4. Recommended Fix

### Fix 1: Update PaddleOCR initialization (CRITICAL)

**File:** `src/data_processing/ocr_pipeline.py:111-119`

**Before:**
```python
self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=self.config.use_gpu,
    use_angle_cls=self.config.use_angle_cls,
    det_model_dir=self.config.det_model_dir,
    rec_model_dir=self.config.rec_model_dir,
    cls_model_dir=self.config.cls_model_dir,
    show_log=False,
)
```

**After:**
```python
# Convert use_gpu to device string for PaddleOCR v3.x
device = "gpu" if self.config.use_gpu else "cpu"

self._engine = PaddleOCR(
    lang=self.config.lang,
    device=device,
    use_textline_orientation=self.config.use_angle_cls,
    text_detection_model_dir=self.config.det_model_dir,
    text_recognition_model_dir=self.config.rec_model_dir,
    textline_orientation_model_dir=self.config.cls_model_dir,
)
```

### Fix 2: Update OCRConfig dataclass

**File:** `src/data_processing/ocr_pipeline.py:36-53`

Add a comment documenting the API mapping:
```python
@dataclass
class OCRConfig:
    """Configuration for the OCR pipeline.
    
    Note: use_gpu is converted to 'device' parameter for PaddleOCR v3.x
    """
    lang: str = "ch"
    use_gpu: bool = True  # Converted to device='gpu' or 'cpu'
    # ... rest unchanged
```

### Fix 3: Remove unused imports

**File:** `src/data_processing/ocr_pipeline.py:18-31`

**Before:**
```python
import os
import sys
# ...
from concurrent.futures import ThreadPoolExecutor, as_completed
# ...
from PIL import Image
```

**After:**
```python
import sys
# ... (remove os, ThreadPoolExecutor, as_completed, Image)
```

### Fix 4: Fix temp directory cleanup

**File:** `src/data_processing/ocr_pipeline.py:181-185`

**Before:**
```python
finally:
    try:
        tmp_dir.rmdir()
    except OSError:
        pass  # Directory not empty, but we ignore it
```

**After:**
```python
finally:
    # Clean up temporary directory with files
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
```

### Fix 5: Make tmp_dir cross-platform

**File:** `src/data_processing/ocr_pipeline.py:50`

**Before:**
```python
tmp_dir: str = "/tmp/guwen_ocr"
```

**After:**
```python
import tempfile
tmp_dir: str = str(Path(tempfile.gettempdir()) / "guwen_ocr")
```

---

## 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read `ocr_pipeline.py` fully | Identified PaddleOCR usage at line 31 |
| 2 | Checked installed packages | `paddleocr 3.4.0` installed, `paddle-ocr` NOT found |
| 3 | Tested import directly | Import succeeds but PaddleOCR init fails |
| 4 | Ran `PaddleOCR(use_gpu=True)` test | `ValueError: Unknown argument: use_gpu` |
| 5 | Read PaddleOCR v3.x source code | Found `device` replaces `use_gpu` |
| 6 | Checked deprecation warnings | 4 deprecated parameters identified |
| 7 | Searched for unused imports | `os`, `ThreadPoolExecutor`, `as_completed`, `Image` never used |
| 8 | Analyzed temp directory handling | `rmdir()` fails on non-empty dir, files left behind |
| 9 | Checked cross-platform compatibility | Hard-coded `/tmp/` won't work on Windows |
| 10 | Reviewed thread safety | `_stats` dict has no lock protection |
| 11 | Searched同类 issues in codebase | `text_cleaner.py` has no similar issues |

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files (ocr_pipeline.py, text_cleaner.py, ocr_config.yaml) |
| `Grep` | Search for parameter usage patterns across codebase |
| `Glob` | Find related files (requirements.txt, config files) |
| `Bash` | Run Python tests, check package versions, verify API behavior |
| `ast.parse()` | Programmatically analyze imports |

---

## 7. Verification

### Verification Commands

```bash
# 1. Verify current package installation
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
source .venv/bin/activate
pip list | grep paddle

# Expected output:
# paddleocr             3.4.0
# paddlex               3.4.2

# 2. Test that old API fails
python -c "from paddleocr import PaddleOCR; PaddleOCR(use_gpu=True)"
# Expected: ValueError: Unknown argument: use_gpu

# 3. Test that new API works
python -c "from paddleocr import PaddleOCR; PaddleOCR(device='cpu', lang='ch')"
# Expected: Success (may show model download progress)

# 4. After fix - test OCRPipeline import and init
python -c "
from src.data_processing.ocr_pipeline import OCRPipeline, OCRConfig
config = OCRConfig(use_gpu=False)
pipeline = OCRPipeline(config)
print('SUCCESS: Pipeline initialized')
"

# 5. Verify GPU detection
python -c "
import paddle
if paddle.device.is_compiled_with_cuda():
    print('GPU support available')
else:
    print('GPU not available - will use CPU')
"
```

### Current State Evidence

```
$ pip show paddleocr
Name: paddleocr
Version: 3.4.0
Requires: paddlex, PyYAML, requests, typing-extensions

$ pip show paddle-ocr  
WARNING: Package(s) not found: paddle-ocr

$ python -c "from paddleocr import PaddleOCR; PaddleOCR(use_gpu=True)"
ValueError: Unknown argument: use_gpu
```

---

## Summary

**Root cause:** The code targets PaddleOCR v2.x API, but v3.x is installed which has breaking changes. The `use_gpu` parameter was completely removed (not just deprecated) and replaced with `device`. This causes immediate failure when instantiating `PaddleOCR`.

**Impact:** 
- Import works but instantiation fails with `ValueError`
- Even if it didn't fail, 4 deprecated parameters produce warnings
- GPU acceleration cannot be enabled with current code

**Fix priority:** CRITICAL - blocks all OCR functionality
