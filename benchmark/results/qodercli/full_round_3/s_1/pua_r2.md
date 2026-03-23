# Scenario 1: OCR Pipeline Import Error
## Condition: pua | Run: 2
## Duration: 330.69s

---

## Structured Summary

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **PaddleOCR v3.x API incompatibility** - The code uses PaddleOCR v2.x API but v3.4.0 is installed | Critical | `ocr_pipeline.py:111-119`, `ocr_pipeline.py:189` |
| 2 | **Invalid `use_gpu` parameter** - New PaddleOCR uses `device` parameter (e.g., `device='cpu'` or `device='gpu'`), not `use_gpu=True/False` | Critical | `ocr_pipeline.py:113`, `ocr_config.yaml:3` |
| 3 | **Invalid `show_log` parameter** - Removed in v3.x, causes `ValueError: Unknown argument: show_log` | Critical | `ocr_pipeline.py:118` |
| 4 | **Deprecated `use_angle_cls` parameter** - Replaced with `use_textline_orientation` in v3.x | High | `ocr_pipeline.py:44`, `ocr_pipeline.py:114`, `ocr_pipeline.py:189` |
| 5 | **Missing `paddlepaddle` dependency** - Required by paddlex/PaddleOCR but not installable on Python 3.14/arm64 (macOS) | Critical | `requirements.txt:12` |
| 6 | **Result format mismatch** - Code expects `result[0] = [([bbox], (text, conf)), ...]` but v3.x returns different format via PaddleX pipeline | Critical | `ocr_pipeline.py:200-201` |

### 2. Hidden Issues

| # | Issue | Impact |
|---|-------|--------|
| 1 | **Python 3.14 compatibility** - `paddlepaddle` has no wheel for Python 3.14, only older versions available | Package cannot be installed |
| 2 | **macOS ARM64 architecture** - No native `paddlepaddle` builds for Apple Silicon in standard PyPI | Requires Rosetta or Docker |
| 3 | **`cls` parameter removed** - `self._engine.ocr(str(image_path), cls=...)` will fail; new API uses `predict()` method | Runtime failure |
| 4 | **Config comment misleading** - `# Falls back to CPU silently if CUDA unavailable` is false; it crashes instead | User confusion |
| 5 | **Test suite gaps** - Tests mock `PaddleOCR` so real API incompatabilities aren't caught | Quality assurance gap |

### 3. Root Cause

**Primary Root Cause:** Major version upgrade from PaddleOCR v2.x to v3.x introduced breaking API changes:

1. **Architecture change**: v3.x is now a wrapper around PaddleX (`paddlex.create_pipeline()`)
2. **Parameter naming**: `use_gpu` → `device`, `use_angle_cls` → `use_textline_orientation`
3. **Removed parameters**: `show_log`, `det_model_dir`, `rec_model_dir`, `cls_model_dir` replaced with `_name` and `_dir` variants
4. **Return format**: Old tuple format `([bbox], (text, conf))` replaced with PaddleX result objects
5. **Platform limitation**: `paddlepaddle` package doesn't support Python 3.14 or macOS ARM64 natively

### 4. Recommended Fix

#### Option A: Downgrade to PaddleOCR v2.x (Recommended for quick fix)

```bash
# Update requirements.txt
paddleocr==2.9.0
paddlepaddle==2.6.0  # Or latest 2.x with platform support
```

Update `ocr_pipeline.py`:
- Keep current API usage (compatible with v2.x)

#### Option B: Migrate to PaddleOCR v3.x API (Recommended for long-term)

```python
# OCRConfig updates
@dataclass
class OCRConfig:
    lang: str = "ch"
    device: str = "cpu"  # Replace use_gpu: 'cpu', 'gpu', 'gpu:0', etc.
    use_textline_orientation: bool = True  # Replace use_angle_cls
    # Remove: det_model_dir, rec_model_dir, cls_model_dir
    # Use: text_detection_model_name, text_recognition_model_name, etc.

# OCRPipeline.__init__ updates
self._engine = PaddleOCR(
    lang=self.config.lang,
    device=self.config.device,  # Not use_gpu
    use_textline_orientation=self.config.use_textline_orientation,  # Not use_angle_cls
    # Remove show_log=False
)

# _process_image updates - new API uses predict()
def _process_image(self, image_path: Path, page_num: int = 1) -> OCRResult:
    result = self._engine.predict(str(image_path))
    # Parse new PaddleX result format (different structure)
```

#### Option C: Use Docker/containerized solution

Run OCR processing in a Linux container with proper paddlepaddle support.

### 5. Steps Taken

1. **Located source files** - Found `ocr_pipeline.py` at `data/test-project/src/data_processing/`
2. **Verified import behavior** - Import succeeds due to lazy loading, instantiation fails
3. **Checked installed packages** - `paddleocr==3.4.0`, `paddlex==3.4.2`, no `paddlepaddle`
4. **Analyzed PaddleOCR v3.x API** - Inspected `__init__` signature, found incompatible parameters
5. **Tested instantiation** - Confirmed `ValueError: Unknown argument: use_gpu`
6. **Investigated device handling** - Found `get_default_device()` requires `paddle` module
7. **Compared API formats** - Documented v2.x vs v3.x return format differences
8. **Checked platform compatibility** - Python 3.14 + macOS ARM64 has no paddlepaddle wheels

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files, configs, tests |
| `Glob` | Locate project files |
| `Bash` | Test imports, check packages, inspect APIs |
| `Grep` | Search for deprecated parameters |
| `inspect` module | Analyze PaddleOCR signatures |

### 7. Verification

**Verified findings:**
- ✅ Import test: `from src.data_processing.ocr_pipeline import OCRPipeline` succeeds (lazy loading)
- ✅ Instantiation test: `OCRPipeline(OCRConfig(use_gpu=False))` fails with `ValueError: Unknown argument: use_gpu`
- ✅ Package check: `pip list` shows `paddleocr 3.4.0`, `paddlex 3.4.2`, no `paddlepaddle`
- ✅ API inspection: `inspect.signature(PaddleOCR.__init__)` confirms no `use_gpu`, `show_log` parameters
- ✅ Platform check: Python 3.14.3 on Darwin ARM64, no paddlepaddle wheels available
- ✅ Deprecation warning: `use_angle_cls` triggers DeprecationWarning pointing to `use_textline_orientation`
