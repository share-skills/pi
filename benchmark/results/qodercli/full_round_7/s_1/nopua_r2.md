# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 2
## Duration: 186.39s

---

Now let me provide the structured summary:

## Investigation Summary: OCR Pipeline Issues

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **`use_gpu` parameter causes `ValueError`** | Critical | `ocr_pipeline.py:111-119` |
| 2 | **PaddleOCR API breaking change (v2.x → v3.x)** | Critical | Entire codebase |
| 3 | **`show_log=False` parameter no longer exists** | Medium | `ocr_pipeline.py:118` |
| 4 | **`cls` parameter in `ocr()` method signature changed** | Medium | `ocr_pipeline.py:189` |

### 2. Hidden Issues Beyond the Ask

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 1 | **Unused imports**: `os`, `sys`, `ThreadPoolExecutor`, `as_completed`, `field`, `Image` | Code quality | `ocr_pipeline.py:18-29` |
| 2 | **`model_cache_dir` parameter unused** | Functionality gap | `ocr_pipeline.py:97-107` |
| 3 | **Temp directory cleanup bug**: `rmdir()` fails silently for non-empty dirs, leaving orphaned files | Resource leak | `ocr_pipeline.py:181-185` |
| 4 | **`box_merge_threshold` config unused**: Defined but never used in `_merge_text_boxes()` | Feature broken | `ocr_pipeline.py:53, 220-254` |
| 5 | **Missing error handling for PDF conversion**: `pdf2image.convert_from_path()` can fail without graceful handling | Stability | `ocr_pipeline.py:154-179` |
| 6 | **CLI `--format` option bug**: Uses `fmt` as destination name but passes to `output_format` incorrectly | CLI broken | `ocr_pipeline.py:344, 353` |
| 7 | **Config docstring outdated**: References `use_gpu` as valid option when it's deprecated | Documentation | `ocr_pipeline.py:13` |

### 3. Root Cause

**Primary Issue**: PaddleOCR underwent a **major API breaking change from v2.x to v3.x**:

- **Old API (v2.x)**: `PaddleOCR(lang='ch', use_gpu=True, ...)`
- **New API (v3.x)**: `PaddleOCR(lang='ch', device='gpu', ...)` or `PaddleOCR(lang='ch')` (auto-detects GPU)

The `use_gpu` parameter:
1. Is **NOT** in the deprecation mapping (`_DEPRECATED_PARAM_NAME_MAPPING`)
2. Gets passed to `parse_common_args()` which raises `ValueError: Unknown argument: use_gpu`
3. The installed version is **paddleocr 3.4.0** (requirements.txt specifies `>=2.7.0`)

**Why users report slowness**: Even if `use_gpu=True` was accepted, the code doesn't properly specify GPU device. PaddleOCR 3.x uses `device='gpu'` or `device='gpu:0'` format, and defaults to auto-detection.

### 4. Recommended Fixes

#### Fix 1: Update `OCRConfig` dataclass
```python
@dataclass
class OCRConfig:
    lang: str = "ch"
    device: str = "gpu"  # Replace use_gpu with device
    # ... rest of config
```

#### Fix 2: Update `OCRPipeline.__init__()` to use new API
```python
self._engine = PaddleOCR(
    lang=self.config.lang,
    device=self.config.device,  # Changed from use_gpu
    use_textline_orientation=self.config.use_angle_cls,  # New param name
    text_detection_model_dir=self.config.det_model_dir,
    text_recognition_model_dir=self.config.rec_model_dir,
    textline_orientation_model_dir=self.config.cls_model_dir,
)
```

#### Fix 3: Update config file (`configs/ocr_config.yaml`)
```yaml
ocr:
  lang: ch
  device: gpu  # Changed from use_gpu
  # ...
```

#### Fix 4: Fix temp directory cleanup
```python
finally:
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
```

#### Fix 5: Remove unused imports and parameters
- Remove: `os`, `sys`, `ThreadPoolExecutor`, `as_completed`, `field`, `Image`
- Remove: `model_cache_dir` parameter or implement it

#### Fix 6: Update requirements.txt to pin compatible version
```txt
paddleocr>=3.4.0,<4.0.0  # Pin to 3.x API
paddlepaddle>=2.5.0      # Required dependency
```

### 5. Steps Taken

1. **Read source files**: `ocr_pipeline.py`, `requirements.txt`, `ocr_config.yaml`, `setup.py`, test files
2. **Examined PaddleOCR 3.4.0 source code**: `_pipelines/ocr.py`, `_common_args.py`, `deprecation.py`
3. **Verified the error**: Ran `.venv/bin/python -c "from paddleocr import PaddleOCR; p = PaddleOCR(lang='ch', use_gpu=True)"` → Confirmed `ValueError: Unknown argument: use_gpu`
4. **Compared API signatures**: Mapped old v2.x params to new v3.x equivalents
5. **Code review**: Identified unused imports, broken features, and resource leaks

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files, configs, tests |
| `Glob` | Locate related files (requirements, configs) |
| `Grep` | Search for `use_gpu` handling in PaddleOCR source |
| `Bash` | Test actual PaddleOCR instantiation, verify errors |

### 7. Verification Evidence

**Error confirmed via direct execution**:
```bash
$ .venv/bin/python -c "from paddleocr import PaddleOCR; p = PaddleOCR(lang='ch', use_gpu=True)"
ValueError: Unknown argument: use_gpu
```

**API verified in PaddleOCR source** (`_pipelines/ocr.py:37-49`):
```python
_DEPRECATED_PARAM_NAME_MAPPING = {
    "det_model_dir": "text_detection_model_dir",
    "use_angle_cls": "use_textline_orientation",
    "cls_model_dir": "textline_orientation_model_dir",
    # NOTE: use_gpu is NOT here - it's rejected as unknown
}
```

**Device handling verified** (`_common_args.py:32-45`):
```python
default_vals = {
    "device": DEFAULT_DEVICE,  # Not use_gpu
    # ...
}
# Line 45: raise ValueError(f"Unknown argument: {name}")
```

---

### Priority Summary

| Priority | Action |
|----------|--------|
| **P0** | Replace `use_gpu` with `device` parameter throughout codebase |
| **P0** | Install `paddlepaddle` package (missing dependency) |
| **P1** | Fix temp directory resource leak |
| **P1** | Update all deprecated parameter names |
| **P2** | Remove unused imports and dead code |
| **P2** | Fix CLI `--format` option bug |
