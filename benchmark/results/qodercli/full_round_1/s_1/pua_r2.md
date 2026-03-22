# Scenario 1: OCR Pipeline Import Error
## Condition: pua | Run: 2
## Duration: 138.35s

---

Now I have completed the investigation. Let me provide the structured summary:

---

## Structured Investigation Summary

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **`use_gpu` parameter removed in PaddleOCR 3.x** | Critical | `ocr_pipeline.py:113` |
| 2 | **`show_log` parameter removed in PaddleOCR 3.x** | Critical | `ocr_pipeline.py:118` |
| 3 | **`det_model_dir`, `rec_model_dir`, `cls_model_dir` parameters renamed** | Critical | `ocr_pipeline.py:115-117` |
| 4 | **`use_angle_cls` parameter renamed to `use_textline_orientation`** | High | `ocr_pipeline.py:114` |
| 5 | **Missing `paddlepaddle` core package** - only `paddleocr` and `paddlex` installed | Critical | Environment |
| 6 | **Missing poppler-utils system dependency** for `pdf2image` | High | System/requirements |
| 7 | **GPU cannot be used** - `paddlepaddle-gpu` not installed, API changed to `device` parameter | High | Config + Environment |

### 2. Hidden Issues Discovered

| # | Issue | Impact |
|---|-------|--------|
| H1 | **requirements.txt specifies `paddleocr>=2.7.0` but v3.4.0 is installed** - major breaking API changes between v2.x and v3.x | Pipeline completely broken |
| H2 | **`tmp_dir.rmdir()` cleanup silently fails** - line 183-185 ignores OSError, leaving temp files behind | Disk space leak |
| H3 | **No lazy initialization of PaddleOCR engine** - engine created in `__init__` even if never used | Wasted resources, slow startup |
| H4 | **Unused imports**: `os`, `sys`, `field`, `ThreadPoolExecutor`, `as_completed`, `Image` | Code cleanliness |
| H5 | **`model_cache_dir` parameter defined but never used** | Unused configuration |
| H6 | **`enable_table_detection` config option defined but never implemented** | False feature expectation |

### 3. Root Cause

**Primary Root Cause:** The code was written for **PaddleOCR 2.x API**, but the environment has **PaddleOCR 3.4.0** installed which has a completely different API:

- **Old API (2.x):** `PaddleOCR(lang='ch', use_gpu=True, show_log=False, ...)`
- **New API (3.x):** `PaddleOCR(lang='ch', device='gpu', text_detection_model_dir=..., ...)`

The `use_gpu` boolean flag was replaced with a `device` string parameter (e.g., `'cpu'`, `'gpu'`, `'gpu:0'`, `'npu'`).

**Secondary Root Cause:** The `requirements.txt` specifies `paddlepaddle>=2.5.0` but this package is **not installed** in the virtual environment. Only `paddleocr` and `paddlex` are present, but `paddlex` requires `paddlepaddle` as a core dependency.

### 4. Recommended Fix

#### Option A: Downgrade to PaddleOCR 2.x (Minimal Code Changes)

```bash
pip install 'paddleocr<3.0' 'paddlepaddle>=2.5.0'
```

Keep existing code, only fix missing dependencies.

#### Option B: Update Code for PaddleOCR 3.x (Recommended Long-term)

Update `ocr_pipeline.py`:

```python
# OCRConfig - change use_gpu to device
@dataclass
class OCRConfig:
    lang: str = "ch"
    device: str = "cpu"  # Changed from use_gpu: bool = True
    text_detection_model_dir: Optional[str] = None  # Renamed from det_model_dir
    text_recognition_model_dir: Optional[str] = None  # Renamed from rec_model_dir
    textline_orientation_model_dir: Optional[str] = None  # Renamed from cls_model_dir
    use_textline_orientation: bool = True  # Renamed from use_angle_cls
    # ... rest unchanged

# OCRPipeline.__init__ - update PaddleOCR initialization
self._engine = PaddleOCR(
    lang=self.config.lang,
    device=self.config.device,  # Changed from use_gpu
    text_detection_model_dir=self.config.text_detection_model_dir,
    text_recognition_model_dir=self.config.text_recognition_model_dir,
    textline_orientation_model_dir=self.config.textline_orientation_model_dir,
    use_textline_orientation=self.config.use_textline_orientation,
)
```

#### Additional Fixes Required:

1. **Install missing dependencies:**
   ```bash
   pip install paddlepaddle  # or paddlepaddle-gpu for GPU support
   # On macOS: brew install poppler
   # On Ubuntu: apt-get install poppler-utils
   ```

2. **Fix temp directory cleanup** (line 182-185):
   ```python
   import shutil
   # Replace: tmp_dir.rmdir()
   # With: shutil.rmtree(tmp_dir, ignore_errors=True)
   ```

3. **Remove unused imports:** `os`, `sys`, `field`, `ThreadPoolExecutor`, `as_completed`, `Image`

4. **Add lazy initialization** for `_engine` to avoid creating PaddleOCR on import

### 5. Steps Taken

1. **Reproduced the import error** - Ran `python3 -c "from src.data_processing.ocr_pipeline import OCRPipeline"` 
2. **Checked installed packages** - `pip list | grep paddle` showed `paddleocr 3.4.0` and `paddlex 3.4.2`, but NO `paddlepaddle`
3. **Tested PaddleOCR with old API** - Confirmed `use_gpu` parameter causes `ValueError: Unknown argument: use_gpu`
4. **Read PaddleOCR 3.x source code** - Analyzed `_common_args.py` and `_pipelines/ocr.py` to understand new API
5. **Discovered `device` parameter replacement** - New API uses `device='cpu'` or `device='gpu'` instead of `use_gpu=True`
6. **Checked system dependencies** - Verified `poppler-utils` is not installed (`pdftoppm` not found)
7. **Compared requirements.txt vs installed** - Found version mismatch and missing packages
8. **Analyzed test file** - Tests use mocks so they pass despite broken real implementation

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Bash` | Run Python commands, check packages, verify errors |
| `Read` | Read source files (ocr_pipeline.py, requirements.txt, tests) |
| `Glob` | Locate ocr_pipeline.py files in project |
| `Grep` | Search for `use_gpu`, `device`, parameter definitions in PaddleOCR source |

### 7. Verification

**Verified findings:**
- ✅ Import error reproduced: `ModuleNotFoundError: No module named 'yaml'` (without venv), then `ValueError: Unknown argument: use_gpu` (with venv)
- ✅ PaddleOCR 3.x API confirmed by reading `/Users/hepin/IdeaProjects/pi/benchmark/data/test-project/.venv/lib/python3.14/site-packages/paddleocr/_pipelines/ocr.py`
- ✅ Missing `paddlepaddle` confirmed: `pip list` shows only `paddleocr` and `paddlex`
- ✅ Missing poppler confirmed: `which pdftoppm` returns nothing
- ✅ Test passes with mocks but would fail with real PaddleOCR due to API incompatibility

**Not yet verified (would require actual fixes):**
- ❌ Pipeline functionality after applying fixes
- ❌ GPU acceleration after installing `paddlepaddle-gpu`
- ❌ PDF processing after installing poppler

---

**Summary:** The OCR pipeline is completely broken due to PaddleOCR 3.x API changes. The code needs significant updates OR the environment needs to downgrade to PaddleOCR 2.x. Additionally, critical system dependencies (poppler) and Python packages (paddlepaddle) are missing.
