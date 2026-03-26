# Scenario 1: OCR Pipeline Import Error
## Condition: pua | Run: 1
## Duration: 144.51s

---

Now I have a complete picture. Let me document my findings:

## Investigation Summary

### Issues Found

**1. ModuleNotFoundError - Wrong Import Path (CRITICAL)**
- **Location**: `ocr_pipeline.py:31` - `from paddleocr import PaddleOCR`
- **Root Cause**: The code imports from `paddleocr` but the installed package structure has changed in PaddleOCR 3.x. While the import technically works (as shown by my test), the underlying `paddle` module (paddlepaddle) is NOT installed.
- **Evidence**: 
  - `pip show paddlepaddle` returns "Package not found"
  - requirements.txt lists `paddleocr>=2.7.0` and `paddlepaddle>=2.5.0` but neither is actually installed in the environment
  - Error when creating PaddleOCR: `ModuleNotFoundError: No module named 'paddle'`

**2. API Incompatibility - use_gpu Parameter Removed (CRITICAL)**
- **Location**: `ocr_pipeline.py:40, 113` - `use_gpu: bool = True` and `use_gpu=self.config.use_gpu`
- **Root Cause**: PaddleOCR 3.x completely removed the `use_gpu` parameter. The new API uses `device` parameter instead (e.g., `device='cpu'`, `device='gpu'`, `device='gpu:0'`).
- **Evidence**: 
  ```python
  # Old API (v2.x) - NO LONGER WORKS
  PaddleOCR(lang='ch', use_gpu=True, show_log=False)
  
  # New API (v3.x)
  PaddleOCR(lang='ch', device='gpu')  # or device='cpu'
  ```
  - My test confirmed: `ValueError: Unknown argument: use_gpu`

**3. API Incompatibility - show_log Parameter Removed (MEDIUM)**
- **Location**: `ocr_pipeline.py:118` - `show_log=False`
- **Root Cause**: This parameter doesn't exist in PaddleOCR 3.x API
- **Evidence**: Parameter not found in `inspect.signature(PaddleOCR.__init__)`

**4. Performance Issue - GPU Not Actually Used (HIGH)**
- **Location**: `ocr_pipeline.py:40, 113`
- **Root Cause**: Even if `use_gpu=True` is set, it's being ignored because:
  1. The parameter doesn't exist in v3.x API
  2. paddlepaddle isn't installed
  3. The new API defaults to CPU when no device is specified or when paddlepaddle GPU isn't available
- **Impact**: OCR processing runs significantly slower than expected

**5. Missing Dependency Installation (CRITICAL)**
- **Location**: `requirements.txt:11-12`
- **Root Cause**: Requirements list `paddleocr>=2.7.0` and `paddlepaddle>=2.5.0` but:
  - paddleocr 3.4.0 is installed (not compatible with v2.x API)
  - paddlepaddle is NOT installed at all
- **Evidence**: `pip show paddlepaddle` returns "Package(s) not found"

### Hidden Issues Discovered

**6. Return Format May Have Changed (UNVERIFIED)**
- The `_process_image` method at line 189-205 expects PaddleOCR to return results in format: `[(bbox, (text, conf)), ...]`
- PaddleOCR 3.x may have different return format that needs verification

**7. Deprecated Parameter Warnings**
- Parameters like `det_model_dir`, `rec_model_dir`, `cls_model_dir`, `use_angle_cls` are deprecated in v3.x and mapped to new names
- The code uses these at lines 41-43, 115-117

### Root Cause Analysis

The fundamental issue is a **version mismatch**:
- Code was written for PaddleOCR 2.x API
- Environment has PaddleOCR 3.4.0 installed (which uses PaddleX 3.4.2 backend)
- PaddleOCR 3.x has a completely redesigned API with different parameter names and structure
- Core dependency `paddlepaddle` is missing entirely

### Recommended Fixes

**Option A: Downgrade to PaddleOCR 2.x (Quick Fix)**
```bash
pip install paddleocr==2.9.0 paddlepaddle==2.5.0
```

**Option B: Update Code for PaddleOCR 3.x (Recommended)**

1. Update `OCRConfig` dataclass:
```python
@dataclass
class OCRConfig:
    lang: str = "ch"
    device: str = "gpu"  # Replace use_gpu with device
    # ... remove det_model_dir, rec_model_dir, cls_model_dir or map to new names
```

2. Update PaddleOCR initialization:
```python
self._engine = PaddleOCR(
    lang=self.config.lang,
    device=self.config.device,  # Changed from use_gpu
    # Remove show_log, use_angle_cls or map to new params
)
```

3. Install missing dependencies:
```bash
pip install paddlepaddle-gpu  # or paddlepaddle for CPU-only
```

### Steps Taken

1. Read the OCR pipeline source code (`ocr_pipeline.py`)
2. Checked requirements.txt for dependency versions
3. Inspected installed PaddleOCR package structure and version (3.4.0)
4. Read PaddleOCR 3.x source code to understand new API
5. Tested import and instantiation with both old and new API parameters
6. Verified paddlepaddle is NOT installed despite being in requirements.txt
7. Checked PaddleOCR constructor signature using `inspect.signature()`
8. Confirmed `use_gpu` and `show_log` parameters don't exist in v3.x

### Tools Used
- `Read` - Source code files
- `Glob` - Finding Python files
- `Grep` - Searching for import patterns
- `Bash` - Running pip commands, testing imports, inspecting API signatures

### Verification Evidence

```bash
# PaddleOCR version installed
$ pip list | grep paddle
paddleocr             3.4.0
paddlex               3.4.2

# paddlepaddle NOT installed
$ pip show paddlepaddle
WARNING: Package(s) not found: paddlepaddle

# Old API fails
$ python -c "from paddleocr import PaddleOCR; PaddleOCR(use_gpu=True)"
ValueError: Unknown argument: use_gpu

# New API works (but needs paddlepaddle)
$ python -c "from paddleocr import PaddleOCR; PaddleOCR(device='cpu')"
ModuleNotFoundError: No module named 'paddle'
```
