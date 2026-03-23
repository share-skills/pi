# Scenario 1: OCR Pipeline Import Error
## Condition: pua | Run: 1
## Duration: 427.06s

---

## Investigation Summary

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **`use_gpu` parameter not supported** - PaddleOCR 3.x removed this parameter, causes `ValueError: Unknown argument: use_gpu` | Critical | Line 113, 40, 353 |
| 2 | **`show_log` parameter not supported** - Causes `ValueError: Unknown argument: show_log` | Critical | Line 118 |
| 3 | **Missing `paddle` package** - PaddlePaddle framework not installed, causes `ModuleNotFoundError: No module named 'paddle'` when instantiating OCR engine | Critical | Environment dependency |
| 4 | **GPU configuration impossible** - No way to enable GPU acceleration with current API; device must be passed via `device` kwarg (e.g., `device="gpu:0"` or `device="cpu"`) | Critical | Lines 111-119 |
| 5 | **Deprecated parameters used** - `det_model_dir`, `rec_model_dir`, `cls_model_dir`, `use_angle_cls` still work but trigger deprecation warnings | Warning | Lines 115-117, 114 |

### 2. Hidden Issues Discovered

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 6 | **Unused imports** - `os`, `ThreadPoolExecutor`, `as_completed`, `Image`, `field` imported but never used | Code quality | Lines 18, 25, 28, 24 |
| 7 | **Unused config fields** - `max_workers`, `enable_table_detection` defined but never used | Feature incomplete | Lines 46, 51 |
| 8 | **No error handling around OCR calls** - `_engine.ocr()` call has no try/except protection | Stability risk | Line 189 |
| 9 | **Inefficient PDF processing** - Saves PIL images to disk then reloads; could process in-memory | Performance | Lines 172-174 |
| 10 | **Silent temp file cleanup failure** - OSError ignored in finally block may leave temp files | Resource leak risk | Lines 182-185 |
| 11 | **No config validation** - Fields like `dpi`, `confidence_threshold` accept invalid values | Robustness | OCRConfig class |
| 12 | **Fragile result parsing** - Assumes `bbox, (text, conf)` format that may break with API changes | Maintenance risk | Line 201 |

### 3. Root Cause

**Primary Root Cause**: The code was written for PaddleOCR 2.x API but is running against PaddleOCR 3.4.0 which has breaking API changes:

- `use_gpu` parameter removed entirely (not even deprecated - completely removed)
- `show_log` parameter removed
- Device configuration now uses `device` parameter passed through kwargs (values: `"cpu"`, `"gpu:0"`, `"npu:0"`)
- Underlying `paddle` (PaddlePaddle) framework is not installed as a dependency

**Why users report slow performance**: Even if the code ran, there's no way to enable GPU acceleration because:
1. The `use_gpu=True` config throws an error before pipeline creation
2. The new API requires `device="gpu:0"` but no such configuration exists in OCRConfig

### 4. Recommended Fixes

#### Immediate Fixes (Critical):

```python
# 1. Add paddlepaddle to dependencies
# pip install paddlepaddle-gpu  # For GPU support
# OR
# pip install paddlepaddle      # For CPU only

# 2. Update OCRConfig dataclass (line 36-53):
@dataclass
class OCRConfig:
    lang: str = "ch"
    device: str = "cpu"  # Replace use_gpu with device (options: "cpu", "gpu:0", "gpu:1", etc.)
    # ... remove use_gpu field
    
# 3. Update PaddleOCR initialization (lines 111-119):
self._engine = PaddleOCR(
    lang=self.config.lang,
    device=self.config.device,  # Use device instead of use_gpu
    use_textline_orientation=self.config.use_angle_cls,  # Updated parameter name
    text_detection_model_dir=self.config.det_model_dir,  # Updated parameter name
    text_recognition_model_dir=self.config.rec_model_dir,
    textline_orientation_model_dir=self.config.cls_model_dir,
    # Remove show_log - not supported
)
```

#### Secondary Fixes (Recommended):

- Remove unused imports: `os`, `ThreadPoolExecutor`, `as_completed`, `Image`, `field`
- Remove or implement unused config fields: `max_workers`, `enable_table_detection`
- Add error handling around `_engine.ocr()` call
- Add config value validation in `OCRConfig.__post_init__()`
- Consider in-memory image processing for PDF conversion

### 5. Steps Taken

1. **Reproduced import** - Confirmed `from src.data_processing.ocr_pipeline import OCRPipeline` succeeds but instantiation fails
2. **Verified package installation** - `paddleocr 3.4.0` and `paddlex 3.4.2` installed; `paddle` (PaddlePaddle) NOT installed
3. **Tested each parameter** - Individually tested all old API parameters against PaddleOCR 3.x
4. **Read PaddleOCR source** - Examined `/paddleocr/_pipelines/ocr.py` to understand new API structure
5. **Traced device handling** - Followed `device` parameter through `PaddleXPipelineWrapper` → `create_pipeline` → `BasePipeline`
6. **Static code analysis** - Used AST parsing to identify unused imports and config fields
7. **Pattern matching** - Searched for error handling, validation, and resource management issues

### 6. Tools Used

- `Bash` - Package inspection, import testing, parameter validation
- `Read` - Source code examination (ocr_pipeline.py, PaddleOCR internals)
- `Glob` - File location
- `WebFetch` - PaddleX documentation for device configuration
- `WebSearch` - PaddleOCR 3.x API changes
- Python `ast` module - Static analysis of imports and usage
- Python `inspect` module - Runtime signature inspection

### 7. Verification

**Evidence collected:**

```
# Import test - succeeds
$ .venv/bin/python -c "from src.data_processing.ocr_pipeline import OCRPipeline"
# Exit code: 0

# Instantiation test - fails with ValueError
$ .venv/bin/python -c "OCRPipeline(OCRConfig(use_gpu=True))"
ValueError: Unknown argument: show_log

# Parameter tests:
use_gpu: ValueError - Unknown argument: use_gpu
show_log: ValueError - Unknown argument: show_log
use_angle_cls: DeprecationWarning (still works)
det_model_dir: DeprecationWarning (still works)

# Dependency check:
$ pip list | grep paddle
paddleocr             3.4.0
paddlex               3.4.2
# NOTE: paddle/paddlepaddle NOT installed
```

**Verification complete**: All findings confirmed with reproducible test cases and source code evidence.
