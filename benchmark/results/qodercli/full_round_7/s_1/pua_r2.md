# Scenario 1: OCR Pipeline Import Error
## Condition: pua | Run: 2
## Duration: 87.43s

---

## Investigation Summary

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **ModuleNotFoundError: No module named 'paddleocr'** | Critical | `ocr_pipeline.py:31` |
| 2 | **GPU usage not verified - silent fallback to CPU** | High | `ocr_pipeline.py:111-119` |
| 3 | **No GPU availability detection logic** | High | `OCRConfig` class |
| 4 | **Package name mismatch in user environment** | Critical | Environment |

### 2. Hidden Issues Discovered

| # | Issue | Impact |
|---|-------|--------|
| 1 | **`tmp_dir.rmdir()` silently fails** - Line 183-185 catches OSError but doesn't log warning, leaving temp files behind | Disk space leak |
| 2 | **No validation of `use_gpu=True` actually working** - PaddleOCR may silently fall back to CPU if GPU unavailable | Performance degradation |
| 3 | **Missing lazy import pattern** - Unlike `__init__.py` which uses lazy imports for heavy deps, `ocr_pipeline.py` imports `PaddleOCR` at module level (line 31), causing import errors even when OCR isn't used | Import failures |
| 4 | **Test `test_paddleocr_import` always passes** - Line 50-55 in test file just checks if `isinstance(imported, bool)` which is always True regardless of import success | False positive tests |
| 5 | **No CUDA/GPU detection before enabling GPU mode** - Should check `paddle.fluid.is_compiled_with_cuda()` before setting `use_gpu=True` | Misconfigured performance |

### 3. Root Cause Analysis

**Issue 1: ModuleNotFoundError**
- The code imports `from paddleocr import PaddleOCR` (line 31)
- Package `paddle-ocr` is NOT the same as `paddleocr`
- Correct package name in requirements.txt is `paddleocr>=2.7.0` (line 11)
- User stated "pip list shows paddle-ocr" - this is the WRONG package name
- The correct installation command is: `pip install paddleocr paddlepaddle`

**Issue 2: GPU Performance**
- `OCRConfig.use_gpu` defaults to `True` (line 40)
- No runtime verification that GPU is actually available
- PaddlePaddle requires:
  - `paddlepaddle-gpu` package (NOT `paddlepaddle`) for GPU support
  - CUDA toolkit installed and compatible
- Without these, PaddleOCR silently falls back to CPU, causing 10-50x slowdown

### 4. Recommended Fixes

#### Fix 1: Add Lazy Import Pattern
```python
# Remove top-level import (line 31)
# from paddleocr import PaddleOCR  # DELETE THIS

# Add lazy import in __init__ method
def __init__(self, config: Union[OCRConfig, str, Dict] = None,
             model_cache_dir: Optional[str] = None):
    # ... existing config logic ...
    
    # Lazy import to avoid heavy dependency load
    from paddleocr import PaddleOCR
    
    self._engine = PaddleOCR(...)
```

#### Fix 2: Add GPU Detection Logic
```python
@dataclass
class OCRConfig:
    lang: str = "ch"
    use_gpu: bool = field(default_factory=lambda: _detect_gpu())
    # ... rest of config
    
def _detect_gpu() -> bool:
    """Detect if GPU is available for PaddlePaddle."""
    try:
        import paddle
        return paddle.is_compiled_with_cuda()
    except ImportError:
        return False
```

#### Fix 3: Fix Temp Directory Cleanup
```python
finally:
    import shutil
    try:
        shutil.rmtree(tmp_dir)  # Use rmtree instead of rmdir
    except OSError as e:
        logger.warning(f"Failed to clean up temp dir {tmp_dir}: {e}")
```

#### Fix 4: Fix Test Assertion Bug
The test at line 55 should be:
```python
assert imported is True  # Not isinstance(imported, bool)
```

### 5. Steps Taken

1. **Read source code** - Full `ocr_pipeline.py` (375 lines) analyzed
2. **Checked requirements.txt** - Verified correct package names (`paddleocr`, `paddlepaddle`)
3. **Searched codebase** - Found all GPU-related configurations and usages
4. **Examined test file** - Discovered false positive test assertion
5. **Checked `__init__.py`** - Found lazy import pattern that should be mirrored
6. **Verified environment** - Confirmed no paddle packages installed in current environment

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files (ocr_pipeline.py, requirements.txt, test file, __init__.py) |
| `Glob` | Find all related files in project |
| `Grep` | Search for GPU/CUDA references, paddle imports |
| `Bash` | Check Python version, pip packages, CUDA availability |

### 7. Verification

**Verified findings:**
- ✅ Package name mismatch confirmed: `paddleocr` (correct) vs `paddle-ocr` (incorrect)
- ✅ No GPU detection logic exists in codebase
- ✅ Temp directory cleanup uses `rmdir()` which fails on non-empty dirs
- ✅ Test assertion bug confirmed at line 55
- ✅ Module-level import causes eager loading (line 31)

**Evidence:**
- Requirements.txt line 11-12: `paddleocr>=2.7.0` and `paddlepaddle>=2.5.0`
- Code line 31: `from paddleocr import PaddleOCR` (module-level)
- Code line 183-185: `tmp_dir.rmdir()` with silent OSError catch
- Test line 55: `assert isinstance(imported, bool)` (always True)

---

## Immediate Action Required

1. **Install correct packages:**
   ```bash
   pip uninstall paddle-ocr  # If installed
   pip install paddleocr paddlepaddle  # CPU version
   # OR for GPU:
   pip install paddleocr paddlepaddle-gpu  # GPU version
   ```

2. **Verify GPU setup (if using GPU):**
   ```bash
   python3 -c "import paddle; print(paddle.is_compiled_with_cuda())"
   ```

3. **Apply code fixes** for lazy imports, GPU detection, and temp cleanup
