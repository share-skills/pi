# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 2
## Duration: 385.06s

---

Now I have enough information to provide a comprehensive summary. Let me compile the final report:

## Investigation Summary: OCR Pipeline Issues

### 1. Issues Found

#### Issue 1: Missing `paddlepaddle` Dependency (CRITICAL - P0)
**Location**: `requirements.txt:11-12`, `ocr_pipeline.py:31`

**Problem**: The code imports `from paddleocr import PaddleOCR`, but `paddlepaddle` (the core ML backend) is NOT installed. The `pip list` shows only `paddleocr 3.4.0` and `paddlex 3.4.2`, but not `paddlepaddle`.

**Evidence**:
```bash
$ python -c "import paddle"
ModuleNotFoundError: No module named 'paddle'
```

When trying to create the OCR pipeline:
```python
Error creating pipeline: ValueError: Unknown argument: show_log
```

**Root Cause**: PaddleOCR 3.x requires `paddlepaddle` as a runtime dependency, but it's not being installed. The `requirements.txt` specifies `paddlepaddle>=2.5.0` but it's not in the installed packages.

---

#### Issue 2: API Incompatibility - PaddleOCR 3.x Breaking Changes (CRITICAL - P0)
**Location**: `ocr_pipeline.py:111-119`

**Problem**: The code uses PaddleOCR 2.x API parameters that are **not supported** in PaddleOCR 3.x:

```python
self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=self.config.use_gpu,      # ❌ NOT supported in 3.x
    use_angle_cls=self.config.use_angle_cls,  # ⚠️ Deprecated, new name: use_textline_orientation
    det_model_dir=self.config.det_model_dir,  # ⚠️ Deprecated, new name: text_detection_model_dir
    rec_model_dir=self.config.rec_model_dir,  # ⚠️ Deprecated, new name: text_recognition_model_dir
    cls_model_dir=self.config.cls_model_dir,  # ⚠️ Deprecated, new name: textline_orientation_model_dir
    show_log=False,                   # ❌ NOT supported in 3.x
)
```

**Required Changes for 3.x**:
- `use_gpu=True/False` → `device="gpu"/"cpu"`
- `show_log=False` → Not directly supported; must configure logging separately
- Deprecated params need mapping via `_DEPRECATED_PARAM_NAME_MAPPING`

---

#### Issue 3: GPU Configuration Not Working (HIGH - P1)
**Location**: `ocr_pipeline.py:40`, `configs/ocr_config.yaml:3`

**Problem**: Even if `use_gpu: true` is set in config, the GPU will NOT be used because:
1. `paddlepaddle` is not installed (Issue 1)
2. The `use_gpu` parameter is ignored in PaddleOCR 3.x (Issue 2)
3. On macOS (current environment), GPU acceleration requires specific paddlepaddle builds that may not exist

**User Impact**: "much slower than expected" - OCR runs on CPU silently even when config says `use_gpu: true`.

---

### 2. Hidden Issues Discovered

#### Hidden Issue A: Unused Imports (LOW - P3)
**Location**: `ocr_pipeline.py:18-25`

```python
import os              # ❌ Never used
import sys             # ✅ Used in main()
from PIL import Image  # ❌ Never used
from dataclasses import dataclass, field  # ❌ 'field' never used
from concurrent.futures import ThreadPoolExecutor, as_completed  # ❌ Never used
```

**Impact**: Code clutter, minor memory waste, confusing for maintainers.

---

#### Hidden Issue B: Thread Safety Concern (MEDIUM - P2)
**Location**: `ocr_pipeline.py:287-297`

```python
for file_path in tqdm(files, desc="OCR Processing"):
    try:
        results = self.process_file(str(file_path))
        all_results[str(file_path)] = results
        # ...
    except Exception as e:
        logger.error(f"Failed to process {file_path.name}: {e}")
        self._stats["failed"] += 1  # ⚠️ Not thread-safe if parallelized
```

**Problem**: 
- `max_workers: int = 4` is defined in config but NEVER USED
- Processing is single-threaded despite having ThreadPoolExecutor imported
- If parallelization is added later, `_stats` dict access is not thread-safe

---

#### Hidden Issue C: Temporary Directory Cleanup Bug (LOW - P3)
**Location**: `ocr_pipeline.py:181-185`

```python
finally:
    try:
        tmp_dir.rmdir()
    except OSError:
        pass  # Directory not empty, but we ignore it
```

**Problem**: If PDF processing fails partway through, temporary image files are left behind. The code silently ignores this, leading to disk space leaks over time.

**Better approach**: Use `shutil.rmtree(tmp_dir, ignore_errors=True)` or proper cleanup of created files.

---

#### Hidden Issue D: Result Parsing Format Risk (MEDIUM - P2)
**Location**: `ocr_pipeline.py:200-205`

```python
for line_result in result[0]:
    bbox, (text, conf) = line_result  # ⚠️ Assumes specific tuple structure
```

**Problem**: PaddleOCR 3.x has a different return format than 2.x. The code assumes:
- `result[0]` is iterable with `(bbox, (text, conf))` tuples
- This format may change between versions

The new PaddleOCR 3.x returns results from `paddlex_pipeline.predict()` which may have a different structure.

---

#### Hidden Issue E: CLI `--format` Option Shadowing (LOW - P3)
**Location**: `ocr_pipeline.py:343-346`

```python
@click.option("--format", "fmt", default="txt", help="Output format (txt/json/jsonl)")
# ...
def run(input, output, config, fmt, gpu):
```

**Problem**: Using `fmt` as parameter name to avoid shadowing `format` builtin is correct, but the docstring says `"Output format"` while the actual option is `--format`. This could cause confusion.

---

### 3. Root Cause Analysis

**Primary Root Cause**: **PaddleOCR underwent a major version upgrade (2.x → 3.x) with breaking API changes**, but the code was not updated accordingly.

**Version Timeline**:
- PaddleOCR 2.x: Used `use_gpu`, `show_log`, direct `ocr()` method
- PaddleOCR 3.x: Uses `device`, paddlex backend, deprecated 2.x params partially mapped

**Why Users See Slow Performance**:
1. `paddlepaddle` not installed → falls back to CPU-only mode
2. Even if installed, macOS doesn't support GPU acceleration for PaddlePaddle
3. Config says `use_gpu: true` but this parameter is ignored in 3.x

---

### 4. Recommended Fixes

#### Fix 1: Install Missing Dependency
```bash
# Add to requirements.txt or install directly
pip install paddlepaddle  # CPU version
# OR for GPU (if available):
pip install paddlepaddle-gpu
```

#### Fix 2: Update PaddleOCR Initialization for 3.x API
```python
# ocr_pipeline.py:111-119
self._engine = PaddleOCR(
    lang=self.config.lang,
    device="gpu" if self.config.use_gpu else "cpu",  # Changed from use_gpu
    use_textline_orientation=self.config.use_angle_cls,  # New param name
    text_detection_model_dir=self.config.det_model_dir,  # New param name
    text_recognition_model_dir=self.config.rec_model_dir,  # New param name
    textline_orientation_model_dir=self.config.cls_model_dir,  # New param name
    # show_log removed - configure logging via Python logging module instead
)
```

#### Fix 3: Remove Unused Imports
```python
# ocr_pipeline.py:18-25 - Remove these:
# import os              # ❌ Remove
# from PIL import Image  # ❌ Remove  
# from dataclasses import field  # ❌ Remove (keep only 'dataclass')
# from concurrent.futures import ThreadPoolExecutor, as_completed  # ❌ Remove
```

#### Fix 4: Fix Temporary Directory Cleanup
```python
# ocr_pipeline.py:181-185
finally:
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)  # Properly clean up all temp files
```

#### Fix 5: Add GPU Availability Check
```python
# Add method to check if GPU is actually available
def _check_gpu_available(self) -> bool:
    """Check if GPU acceleration is actually available."""
    try:
        import paddle
        return paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
    except ImportError:
        return False

# Then in __init__:
if self.config.use_gpu and not self._check_gpu_available():
    logger.warning("GPU requested but not available. Falling back to CPU.")
    self.config.use_gpu = False
```

---

### 5. Steps Taken

| Step | Tool | Description |
|------|------|-------------|
| 1 | `Read` | Read ocr_pipeline.py source code line by line |
| 2 | `Bash` | Tested import: `python -c "from src.data_processing.ocr_pipeline import OCRPipeline"` |
| 3 | `Bash` | Checked installed packages: `pip list \| grep paddle` |
| 4 | `Bash` | Verified paddlepaddle is missing: `import paddle` fails |
| 5 | `Read` | Examined PaddleOCR 3.x source in `.venv/lib/python3.14/site-packages/paddleocr/` |
| 6 | `Bash` | Tested PaddleOCR 3.x API: checked constructor signature, deprecated params |
| 7 | `Grep` | Searched for unused imports and dead code |
| 8 | `Read` | Reviewed configs/ocr_config.yaml |
| 9 | `Bash` | Attempted to create OCRPipeline instance to verify error messages |

---

### 6. Tools Used

- `Read` - Source code analysis
- `Glob` - File discovery
- `Grep` - Pattern searching (unused imports, parameter usage)
- `Bash` - Running Python commands, checking package versions, testing imports
- `TodoWrite` - Tracking investigation progress

---

### 7. Verification

**Verified Findings**:
- ✅ `paddlepaddle` NOT installed (confirmed via `import paddle` failure)
- ✅ PaddleOCR 3.x uses different API (confirmed via `inspect.signature()`)
- ✅ `use_gpu` and `show_log` not supported in 3.x (confirmed via error: `ValueError: Unknown argument: show_log`)
- ✅ Unused imports identified (confirmed via regex search excluding import lines)
- ✅ `ThreadPoolExecutor` imported but never used (confirmed via grep)

**Test Command That Reproduced Issue**:
```bash
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
source .venv/bin/activate
python -c "
import os
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
from src.data_processing.ocr_pipeline import OCRPipeline, OCRConfig
pipeline = OCRPipeline(OCRConfig(use_gpu=True))
"
# Output: ValueError: Unknown argument: show_log
```

---

### Priority Summary

| Priority | Issue | Impact |
|----------|-------|--------|
| **P0** | Missing `paddlepaddle` dependency | Import/runtime failure |
| **P0** | PaddleOCR 3.x API incompatibility | Cannot instantiate pipeline |
| **P1** | GPU configuration broken | Severe performance degradation |
| **P2** | Result parsing format risk | May break with PaddleOCR updates |
| **P2** | Thread safety concern | Limits future parallelization |
| **P3** | Unused imports | Code quality |
| **P3** | Temp directory leak | Disk space over time |
