# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 1
## Duration: 178.84s

---

## Investigation Report: OCR Pipeline Issues

### 1. Issues Found

#### Issue #1: ModuleNotFoundError for `paddleocr` (CRITICAL)
**Location:** `ocr_pipeline.py:31`

```python
from paddleocr import PaddleOCR
```

**Root Cause:** The package name discrepancy between `pip list` output and import statement.

- User reports `pip list` shows `paddle-ocr` (with hyphen)
- Code imports from `paddleocr` (no hyphen, single word)
- **Official package name is `paddleocr`** - installed via `pip install paddleocr`
- If `pip list` shows `paddle-ocr`, this may be an unofficial/incorrect package

**Fix:**
```bash
# Uninstall any incorrect package
pip uninstall paddle-ocr

# Install the official package
pip install paddleocr
```

The import statement `from paddleocr import PaddleOCR` is correct for the official package.

---

#### Issue #2: GPU Not Being Used / Slow Performance (HIGH)
**Location:** `ocr_pipeline.py:111-119`

```python
self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=self.config.use_gpu,  # Line 113
    ...
)
```

**Root Cause:** Multiple potential issues identified:

1. **PaddleOCR 3.x parameter changes:** Recent versions of PaddleOCR have changed GPU configuration. The `use_gpu` parameter behavior may differ from expected.

2. **GPU driver/CUDA not properly configured:** Even with `use_gpu=True`, PaddleOCR falls back to CPU if:
   - CUDA drivers are missing or outdated
   - paddlepaddle-gpu is not installed (only CPU version)
   - GPU compute capability is incompatible

3. **Known issue from GitHub #11679:** Users report `use_gpu=true` setting not being respected at runtime.

**Fix:**
```bash
# Ensure GPU-enabled PaddlePaddle is installed
pip uninstall paddlepaddle
pip install paddlepaddle-gpu  # For GPU support

# Or for newer versions with CUDA 11.8
pip install paddlepaddle-gpu==3.0.0
```

```python
# In code, add GPU verification after initialization
import paddle
logger.info(f"Paddle device: {paddle.get_device()}")
logger.info(f"GPU available: {paddle.is_compiled_with_cuda()}")
```

---

### 2. Hidden Issues Discovered

#### Hidden Issue #1: Unused Imports (LOW)
**Location:** `ocr_pipeline.py:18-25, 27-29`

```python
import os          # UNUSED
import sys         # UNUSED (except in main())
from concurrent.futures import ThreadPoolExecutor, as_completed  # UNUSED
import yaml        # Used only in _load_config
from PIL import Image  # UNUSED
```

**Impact:** Increased import time, code clutter.

---

#### Hidden Issue #2: Missing PDF Dependency Handling (MEDIUM)
**Location:** `ocr_pipeline.py:156`

```python
from pdf2image import convert_from_path
```

**Problem:** `pdf2image` requires system-level dependencies (`poppler-utils` on Linux, `poppler` on macOS) that are not in `requirements.txt`. This will cause a runtime error even if the package is installed.

---

#### Hidden Issue #3: Temporary Directory Cleanup Failure (LOW)
**Location:** `ocr_pipeline.py:181-185`

```python
finally:
    try:
        tmp_dir.rmdir()
    except OSError:
        pass  # Directory not empty, but we ignore it
```

**Problem:** Images are saved to `tmp_dir` but never deleted before attempting `rmdir()`. The directory will accumulate files over time.

**Fix:** Use `shutil.rmtree(tmp_dir, ignore_errors=True)` instead.

---

#### Hidden Issue #4: No GPU Verification Logic (MEDIUM)
**Location:** `ocr_pipeline.py:111-124`

**Problem:** When `use_gpu=True` is configured, there's no verification that GPU is actually available or being used. The pipeline silently falls back to CPU.

**Recommendation:** Add GPU availability check with warning:
```python
import paddle
if self.config.use_gpu and not paddle.is_compiled_with_cuda():
    logger.warning("GPU requested but CUDA not available. Falling back to CPU.")
```

---

#### Hidden Issue #5: Thread Safety Concerns (MEDIUM)
**Location:** `ocr_pipeline.py:287-297`

```python
for file_path in tqdm(files, desc="OCR Processing"):
    try:
        results = self.process_file(str(file_path))
```

**Problem:** `process_directory` mentions `max_workers` config but uses sequential processing with `tqdm`. The `ThreadPoolExecutor` import is unused. Either:
- Should use parallel processing as config suggests
- Or remove `max_workers` config option

---

#### Hidden Issue #6: Hardcoded Unix Path (LOW)
**Location:** `ocr_pipeline.py:50`

```python
tmp_dir: str = "/tmp/guwen_ocr"
```

**Problem:** This path doesn't exist on Windows by default. Should use platform-agnostic temp directory.

**Fix:**
```python
import tempfile
tmp_dir: str = field(default_factory=lambda: str(Path(tempfile.gettempdir()) / "guwen_ocr"))
```

---

### 3. Root Cause Summary

| Issue | Root Cause |
|-------|------------|
| ModuleNotFoundError | Package name mismatch: user has `paddle-ocr` installed, but official package is `paddleocr` |
| GPU not working | Likely CPU-only `paddlepaddle` installed instead of `paddlepaddle-gpu`; no GPU verification |
| Slow performance | GPU fallback to CPU due to missing CUDA support or incorrect package |
| Temp dir accumulation | Images saved but never cleaned up before `rmdir()` call |
| Missing poppler | `pdf2image` requires system dependency not listed in requirements |

---

### 4. Recommended Fixes

#### Immediate (Blocking Issues):

1. **Fix package installation:**
   ```bash
   pip uninstall paddle-ocr paddlepaddle
   pip install paddleocr paddlepaddle-gpu
   ```

2. **Add GPU verification in `__init__`:**
   ```python
   import paddle
   
   # After line 119, add:
   if self.config.use_gpu:
       if not paddle.is_compiled_with_cuda():
           logger.warning("GPU requested but PaddlePaddle CUDA not available. Falling back to CPU.")
       else:
           logger.info(f"PaddleOCR using GPU: {paddle.get_device()}")
   ```

3. **Fix temp directory cleanup:**
   ```python
   import shutil
   
   # Replace lines 181-185:
   finally:
       shutil.rmtree(tmp_dir, ignore_errors=True)
   ```

#### Secondary (Quality Improvements):

4. **Add poppler to documentation** or include in Docker setup
5. **Use platform-agnostic temp path** (see Hidden Issue #6)
6. **Remove unused imports** or implement parallel processing
7. **Add model path validation** before passing to PaddleOCR

---

### 5. Steps Taken

1. ✅ Read full `ocr_pipeline.py` source code (374 lines)
2. ✅ Examined `requirements.txt` and `setup.py` for dependency info
3. ✅ Checked project structure and `__init__.py` files
4. ✅ Searched web for `paddleocr` vs `paddle-ocr` package naming issues
5. ✅ Researched PaddleOCR GPU usage problems and known bugs
6. ✅ Fetched official PaddleOCR installation documentation
7. ✅ Analyzed code for additional hidden issues (unused imports, cleanup logic, etc.)

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files (ocr_pipeline.py, requirements.txt, setup.py, __init__.py) |
| `Glob` | Find related Python files and project structure |
| `Bash` | Check Python path, installed packages |
| `WebSearch` | Research package naming issues, GPU problems |
| `WebFetch` | Fetch official PaddleOCR documentation and GitHub issues |

---

### 7. Verification

**Verified findings:**
- ✅ Confirmed official package name is `paddleocr` (via PyPI and GitHub docs)
- ✅ Confirmed `use_gpu` parameter issues are known bugs (GitHub #11679, #1882)
- ✅ Verified `pdf2image` requires poppler system dependency (not in requirements.txt)
- ✅ Verified temp directory cleanup logic is broken (images saved, only `rmdir()` called)
- ✅ Verified unused imports: `os`, `ThreadPoolExecutor`, `PIL.Image`

**Not verified (would require runtime environment):**
- ❌ Actual GPU hardware/driver status
- ❌ Current installed package versions
- ❌ Runtime execution of the pipeline
