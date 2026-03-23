# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 1
## Duration: 286.88s

---

## Investigation Summary

### 1. Issues Found

| # | Issue | Severity | Evidence |
|---|-------|----------|----------|
| 1 | **PaddleOCR 3.x API incompatibility - `use_gpu` parameter removed** | Critical | `ValueError: Unknown argument: use_gpu` - PaddleOCR 3.4.0 has completely different API; `use_gpu` parameter no longer exists |
| 2 | **Missing `paddlepaddle` dependency** | Critical | `ModuleNotFoundError: No module named 'paddle'` when instantiating PaddleOCR - requirements.txt lists it but it's not installed |
| 3 | **Deprecated `show_log` parameter** | Critical | `ValueError: Unknown argument: show_log` - line 118 uses deprecated parameter |
| 4 | **Deprecated `cls` parameter in ocr() method** | High | Line 189: `self._engine.ocr(str(image_path), cls=self.config.use_angle_cls)` - new API only accepts `img` and `**kwargs` |
| 5 | **Missing `pdf2image` dependency** | High | `ModuleNotFoundError: No module named 'pdf2image'` - required for PDF processing |
| 6 | **Missing poppler system dependency** | High | `pdftoppm` not found - pdf2image requires this system library |
| 7 | **Temp directory leak** | Medium | Lines 182-185: `tmp_dir.rmdir()` fails silently with OSError, leaving temp files behind |
| 8 | **_merge_text_boxes missing space between lines** | Low | Lines 252: Same-paragraph lines joined without space (`merged.append(lines[i])` should be `merged.append(' ' + lines[i])`) |

### 2. Hidden Issues Beyond the Ask

1. **Dependency gap**: `requirements.txt` has `paddlepaddle>=2.5.0` but venv only has `paddleocr` + `paddlex` - no actual paddlepaddle installation
2. **Architecture change**: PaddleOCR 3.x now routes through PaddleX (`paddlex.create_pipeline`), changing how device selection works
3. **No device control**: New API auto-detects device via `get_default_device()` - no way to force CPU/GPU
4. **CLI config file validation**: No user-friendly error if config YAML doesn't exist
5. **Unused imports**: Lines 25-26 import `ThreadPoolExecutor, as_completed` but never used
6. **Unused dataclass field**: `field` imported but never used in OCRConfig

### 3. Root Cause

**Primary root cause**: The code was written for **PaddleOCR 2.x API** but the environment has **PaddleOCR 3.4.0** installed, which has a completely rewritten API:

- Old API: `PaddleOCR(lang='ch', use_gpu=True, show_log=False)`
- New API: `PaddleOCR(lang='ch')` with different internal parameters

Additionally, the `paddlepaddle` package (the core ML framework) is not installed, preventing any OCR inference from working at all.

### 4. Recommended Fixes

```python
# 1. Fix dependencies (requirements.txt):
paddlepaddle>=2.5.0      # Ensure this is actually installed
pdf2image>=1.16.0        # Add missing dependency
poppler-utils            # System dependency for pdf2image

# 2. Fix OCRPipeline.__init__ (lines 111-119):
self._engine = PaddleOCR(
    lang=self.config.lang,
    # Remove: use_gpu=self.config.use_gpu  (not supported in 3.x)
    # Remove: show_log=False  (not supported in 3.x)
    # Use new parameter names:
    use_textline_orientation=self.config.use_angle_cls,
    text_det_model_dir=self.config.det_model_dir,
    text_rec_model_dir=self.config.rec_model_dir,
    textline_orientation_model_dir=self.config.cls_model_dir,
)

# 3. Fix _process_image (line 189):
result = self._engine.ocr(str(image_path))  # Remove cls= parameter

# 4. Fix temp cleanup (lines 181-185):
finally:
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)  # Properly clean up

# 5. Fix _merge_text_boxes (line 252):
merged.append(' ' + lines[i])  # Add space between same-paragraph lines
```

### 5. Steps Taken

1. Read source file `src/data_processing/ocr_pipeline.py` (374 lines)
2. Read test file `tests/test_ocr_pipeline.py`
3. Verified package installation: `pip list | grep paddle`
4. Tested import: `from src.data_processing.ocr_pipeline import OCRPipeline`
5. Inspected PaddleOCR 3.4.0 source code to understand new API
6. Tested `PaddleOCR(use_gpu=True)` → `ValueError: Unknown argument: use_gpu`
7. Tested `PaddleOCR(lang='ch')` → `ModuleNotFoundError: No module named 'paddle'`
8. Checked `ocr()` method signature → only accepts `img` and `**kwargs`
9. Verified `pdf2image` and `poppler` not available
10. Analyzed `_merge_text_boxes` logic for edge cases
11. Tested temp directory cleanup behavior

### 6. Tools Used

- `Read`: Source code analysis
- `Bash`: Package verification, import testing, API inspection
- `Grep`: Pattern searching in installed packages
- `inspect` module: Runtime API signature analysis

### 7. Verification

**Verified findings:**
- ✓ Import works: `from src.data_processing.ocr_pipeline import OCRPipeline` succeeds
- ✓ Config creation works: `OCRConfig(use_gpu=True)` succeeds  
- ✓ Pipeline instantiation fails: `ValueError: Unknown argument: show_log`
- ✓ PaddleOCR 3.x does not accept `use_gpu` parameter (confirmed via source inspection)
- ✓ Missing `paddlepaddle` prevents actual OCR execution
- ✓ Temp directory cleanup confirmed to fail silently (tested with `rmdir`)
