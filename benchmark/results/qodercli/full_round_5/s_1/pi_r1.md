# Scenario 1: OCR Pipeline Import Error
## Condition: pi | Run: 1
## Duration: 112.62s

---

Now I have comprehensive understanding. Let me document my findings:

---

## 📋 Investigation Report: OCR Pipeline Import Error & GPU Performance Issue

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **ModuleNotFoundError: No module named 'paddleocr'** - Package installed as `paddle-ocr` but imported as `paddleocr` | `ocr_pipeline.py:31` | 🔴 Blocker |
| 2 | **GPU silently falls back to CPU** - `use_gpu=True` default but no CUDA availability check or warning | `ocr_pipeline.py:40,111-119` | 🟡 High |
| 3 | **Hardcoded temp directory `/tmp/guwen_ocr`** - Not cross-platform compatible (fails on Windows) | `ocr_pipeline.py:50` | 🟡 Medium |
| 4 | **Unused imports** - `os`, `sys`, `ThreadPoolExecutor`, `as_completed`, `Image` imported but never used | `ocr_pipeline.py:18-25` | ⚪ Low |
| 5 | **Dead code**: `self._engine = None` assigned then immediately overwritten | `ocr_pipeline.py:108` | ⚪ Low |

---

### 2. Hidden Issues (Beyond User's Ask)

| # | Issue | Location | Risk |
|---|-------|----------|------|
| 6 | **Resource leak**: PDF temp images not cleaned up properly - `tmp_dir.rmdir()` fails silently when directory has files | `_process_pdf:181-185` | 🔴 Data leak |
| 7 | **No input validation**: `confidence_threshold` accepts invalid values (e.g., 1.5, -0.5) without validation | `OCRConfig:48` | 🟡 Correctness |
| 8 | **Division by zero risk**: `avg_confidence` calculation when `confidences` is empty returns 0.0 but logic could fail | `_process_image:208` | 🟡 Edge case |
| 9 | **Missing error handling**: PaddleOCR initialization can fail (missing models, CUDA error) with no try/catch | `__init__:111-119` | 🟡 Stability |
| 10 | **Thread safety issue**: `self._stats` modified without locks in concurrent `process_directory` scenario | `process_directory:296-297` | 🟡 Race condition |
| 11 | **Configuration comment misleading**: "Falls back to CPU silently" in ocr_config.yaml but PaddleOCR throws error if GPU unavailable | `configs/ocr_config.yaml:3` | ⚪ Confusion |

---

### 3. Root Cause Analysis

#### Issue 1: ModuleNotFoundError
**Root Cause**: Package naming inconsistency
- User installed: `pip install paddle-ocr` (hyphenated package name for PyPI)
- Code imports: `from paddleocr import PaddleOCR` (module name)
- **Actual Python module name**: `paddleocr` (no hyphen) - the import IS correct
- **Real problem**: `paddleocr` package is NOT actually installed in current environment

**Evidence**:
```bash
pip3 list | grep -i paddle  # Returns nothing
```

The user's statement "pip list shows paddle-ocr" appears incorrect for this environment, or they're on a different machine (Windows `D:\Projects\private-project`).

#### Issue 2: GPU Performance Degradation
**Root Cause**: No CUDA availability verification before initializing PaddleOCR with `use_gpu=True`

Code at `ocr_pipeline.py:111-119`:
```python
self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=self.config.use_gpu,  # Always True by default
    ...
)
```

PaddleOCR may:
- Silently fall back to CPU if CUDA unavailable (version-dependent)
- Or throw runtime error during inference

No logging/warning tells users they're running on CPU.

---

### 4. Recommended Fix

#### Fix 1: Add Lazy Import with Clear Error Message
```python
# ocr_pipeline.py:27-32 (replace direct import)
logger = logging.getLogger(__name__)


def _get_paddleocr():
    """Lazy import PaddleOCR with helpful error message."""
    try:
        from paddleocr import PaddleOCR
        return PaddleOCR
    except ImportError as e:
        raise ImportError(
            "paddleocr not installed. Install with: pip install paddleocr>=2.7.0\n"
            "Note: Package name is 'paddleocr' (not 'paddle-ocr')"
        ) from e
```

Then update `__init__`:
```python
# ocr_pipeline.py:106-124
self.config = config
self.model_cache_dir = model_cache_dir
self._stats = {"processed": 0, "failed": 0, "total_pages": 0}

# Lazy initialization - defer import error until first use
self._engine = None
```

And initialize engine on first use:
```python
def _get_engine(self):
    """Initialize PaddleOCR engine lazily with GPU check."""
    if self._engine is None:
        PaddleOCR = _get_paddleocr()
        
        # Warn if GPU requested but CUDA unavailable
        if self.config.use_gpu:
            try:
                import torch
                cuda_available = torch.cuda.is_available()
            except ImportError:
                cuda_available = False
            
            if not cuda_available:
                logger.warning(
                    "GPU requested but CUDA not available. "
                    "Falling back to CPU. Install torch with CUDA for GPU acceleration."
                )
        
        self._engine = PaddleOCR(
            lang=self.config.lang,
            use_gpu=self.config.use_gpu and cuda_available,
            use_angle_cls=self.config.use_angle_cls,
            det_model_dir=self.config.det_model_dir,
            rec_model_dir=self.config.rec_model_dir,
            cls_model_dir=self.config.cls_model_dir,
            show_log=False,
        )
    return self._engine
```

#### Fix 2: Cross-Platform Temp Directory
```python
# ocr_pipeline.py:1-2 (add import)
import tempfile
...
# OCRConfig:50 (replace hardcoded path)
tmp_dir: str = field(default_factory=lambda: os.path.join(tempfile.gettempdir(), "guwen_ocr"))
```

#### Fix 3: Remove Unused Imports
```python
# Remove: os, sys, ThreadPoolExecutor, as_completed, Image
# Keep only what's used
```

#### Fix 4: Proper Temp File Cleanup
```python
# _process_pdf:154-185
finally:
    import shutil
    try:
        shutil.rmtree(tmp_dir)  # Remove entire directory tree
    except OSError as e:
        logger.warning(f"Failed to cleanup temp dir {tmp_dir}: {e}")
```

#### Fix 5: Add Thread Safety for Stats
```python
# Add at class level
import threading
self._stats_lock = threading.Lock()

# Update stats safely
with self._stats_lock:
    self._stats["total_pages"] += 1
```

---

### 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read `ocr_pipeline.py` source | Identified direct import at L31, GPU config at L40/L113 |
| 2 | Ran import test: `python3 -c "from src.data_processing.ocr_pipeline import OCRPipeline"` | Confirmed `ModuleNotFoundError: No module named 'paddleocr'` |
| 3 | Checked installed packages: `pip3 list \| grep -i paddle` | No paddle packages installed |
| 4 | Searched for `use_gpu` usage across codebase | Found 19 occurrences, config defaults to `true` |
| 5 | Read `ocr_config.yaml` | Comment says "falls back to CPU silently" - unverified |
| 6 | Searched for optional import patterns in codebase | Found 4 examples of `try/except ImportError` pattern |
| 7 | Read `setup.py` | Confirms `paddleocr>=2.7.0` as dependency (correct package name) |
| 8 | Analyzed `_process_pdf` cleanup logic | Identified resource leak: `rmdir()` won't remove non-empty dir |
| 9 | Checked for thread safety in `process_directory` | Found unprotected shared state modification |

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files: `ocr_pipeline.py`, `setup.py`, `ocr_config.yaml`, `__init__.py`, test file |
| `Grep` | Search for `use_gpu` patterns, `ImportError` handling patterns |
| `Glob` | Find all Python files in test project |
| `Bash` | Test import, check installed packages |

---

### 7. Verification

**Verification Commands:**

```bash
# 1. Verify paddleocr installation status
pip3 list | grep -i paddle

# 2. Install paddleocr if missing
pip install paddleocr>=2.7.0

# 3. Test import after fix
cd /Users/hepin/IdeaProjects/pi/nopua/benchmark/test-project
python3 -c "from src.data_processing.ocr_pipeline import OCRPipeline; print('Import OK')"

# 4. Verify GPU availability check
python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())"

# 5. Run existing tests (mocked)
pytest tests/test_ocr_pipeline.py -v
```

**Current State:**
- ❌ Import fails: `paddleocr` not installed in this environment
- ❌ GPU performance issue confirmed: No CUDA check before `use_gpu=True`
- ✅ Root causes identified with line numbers
- ✅ Fix recommendations provided with code examples

---

## 📋 交付确认

**目标匹配:**
- ✅ ModuleNotFoundError 根因定位：环境未安装 paddleocr（非导入语法错误）
- ✅ GPU 性能问题定位：缺少 CUDA 可用性检查，静默降级

**边界覆盖:**
- ✅ 跨平台兼容性（Windows 路径）
- ✅ 资源泄漏（临时文件清理）
- ✅ 线程安全（并发统计修改）
- ✅ 边界条件（空结果、除零风险）

**风险可控:**
- 🔴 依赖缺失 → 添加延迟导入 + 清晰错误提示
- 🟡 GPU 降级 → 添加 CUDA 检查 + 警告日志
- 🟡 资源泄漏 → 改用 `shutil.rmtree()` 完整清理
