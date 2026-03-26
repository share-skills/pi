# Scenario 1: OCR Pipeline Import Error
## Condition: pi | Run: 1
## Duration: 156.86s

---

---

## 🧠 PI ·  Investigation Complete

### 1. Issues Found

| # | Issue | Location |
|---|-------|----------|
| 1 | **ModuleNotFoundError for paddleocr** - Package name mismatch in requirements.txt | `requirements.txt:11` uses `paddleocr>=2.7.0`, but user reports `pip list shows paddle-ocr` |
| 2 | **GPU not actually used despite use_gpu=True** - No GPU availability verification before initialization | `ocr_pipeline.py:111-119` |
| 3 | **Unused imports** - `os`, `sys`, `ThreadPoolExecutor`, `as_completed`, `field` imported but never used | `ocr_pipeline.py:18-25` |
| 4 | **Hardcoded Unix path** - `/tmp/guwen_ocr` not cross-platform compatible | `ocr_pipeline.py:50` |
| 5 | **Temporary directory cleanup failure** - `rmdir()` silently fails, leaves temp files behind | `ocr_pipeline.py:182-185` |
| 6 | **Missing pdf2image in setup.py** - Required dependency not listed | `setup.py:11-27` |

---

### 2. Hidden Issues

| # | Category | Issue | Location |
|---|----------|-------|----------|
| 1 | 🔒 Security | Hardcoded tmp_dir path could be exploited for symlink attacks on multi-user systems | `ocr_pipeline.py:50` |
| 2 | ⚡ Performance | `max_workers` config defined but never used - no parallel processing implemented | `ocr_pipeline.py:46, 287` |
| 3 | ⚡ Performance | PDF pages saved as PNG (lossless, large) instead of JPG for OCR use case | `ocr_pipeline.py:167` |
| 4 | 📖 Resource Leak | Temporary images not deleted if OCR fails mid-processing (finally block only removes empty dir) | `ocr_pipeline.py:181-185` |
| 5 | ✅ Correctness | No validation that `det_model_dir`, `rec_model_dir`, `cls_model_dir` exist when provided | `ocr_pipeline.py:111-119` |
| 6 | ✅ Correctness | `_merge_text_boxes` returns `"".join(merged)` losing paragraph structure from `"\n"` insertions | `ocr_pipeline.py:249, 254` |
| 7 | ⚠️ Thread Safety | `self._stats` modified without lock protection, unsafe for concurrent use | `ocr_pipeline.py:176, 178, 296-297` |
| 8 | ⚠️ Error Handling | Bare `except Exception` in process_directory swallows all errors including KeyboardInterrupt | `ocr_pipeline.py:295-297` |

---

### 3. Root Cause

**Issue 1: ModuleNotFoundError**
- **Initially I thought**: The package name was inconsistent between `paddleocr` (PyPI) and `paddle-ocr` (user's pip list)
- **Upon closer inspection**: PyPI shows the package is `paddleocr` (https://pypi.org/project/paddleocr/), import is `from paddleocr import PaddleOCR`. If user sees `paddle-ocr` in pip list, they may have installed a different/old package or there's a typo in their environment
- **Actually**: The code at line 31 is correct (`from paddleocr import PaddleOCR`), but requirements.txt line 11 uses `paddleocr>=2.7.0` - user needs to run `pip install paddleocr` not `paddle-ocr`

**Issue 2: GPU Not Used**
- **Root cause**: PaddleOCR's `use_gpu=True` parameter silently falls back to CPU if:
  1. GPU version of PaddlePaddle not installed (only CPU version)
  2. CUDA drivers not available/incompatible
  3. GPU memory insufficient
- **Code evidence**: `ocr_pipeline.py:111-119` passes `use_gpu=self.config.use_gpu` but never verifies GPU is actually available
- **PaddlePaddle diagnostic**: Should use `paddle.is_compiled_with_cuda()` and `paddle.device.is_gpu_available()` before initialization

---

### 4. Recommended Fix

#### Fix 1: Add GPU Verification (ocr_pipeline.py:109-124)
```python
# Before (lines 109-124):
self._engine = None
self._stats = {"processed": 0, "failed": 0, "total_pages": 0}

self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=self.config.use_gpu,
    ...
)

# After:
self._engine = None
self._stats = {"processed": 0, "failed": 0, "total_pages": 0}

# Verify GPU availability if requested
if self.config.use_gpu:
    try:
        import paddle
        if not paddle.is_compiled_with_cuda():
            logger.warning("PaddlePaddle not compiled with CUDA, falling back to CPU")
            self.config.use_gpu = False
        elif not paddle.device.is_gpu_available():
            logger.warning("No GPU available, falling back to CPU")
            self.config.use_gpu = False
    except ImportError:
        logger.warning("Cannot import paddle, assuming CPU-only mode")
        self.config.use_gpu = False

self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=self.config.use_gpu,
    ...
)
```

#### Fix 2: Cross-Platform Temp Directory (ocr_pipeline.py:50)
```python
# Before:
tmp_dir: str = "/tmp/guwen_ocr"

# After:
tmp_dir: str = os.path.join(tempfile.gettempdir(), "guwen_ocr")
```

Add import: `import tempfile` (line 18)

#### Fix 3: Proper Temp Cleanup (ocr_pipeline.py:181-185)
```python
# Before:
finally:
    try:
        tmp_dir.rmdir()
    except OSError:
        pass  # Directory not empty, but we ignore it

# After:
finally:
    import shutil
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Failed to clean up temp directory {tmp_dir}: {e}")
```

#### Fix 4: Remove Unused Imports (ocr_pipeline.py:18-25)
```python
# Remove: import os, import sys, from concurrent.futures import ThreadPoolExecutor, as_completed
# Keep only used imports
```

#### Fix 5: Add pdf2image to setup.py (setup.py:11-27)
```python
install_requires=[
    ...
    "paddleocr>=2.7.0",
    "pdf2image>=1.16.0",  # ADD THIS
    ...
]
```

---

### 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read ocr_pipeline.py fully | Identified import structure, GPU config, temp file handling |
| 2 | **Initially hypothesized**: Package name mismatch causing ModuleNotFoundError | Requirements.txt says `paddleocr`, user has `paddle-ocr` |
| 3 | Searched PyPI documentation for paddleocr | Confirmed package name IS `paddleocr`, import IS `from paddleocr import PaddleOCR` |
| 4 | **Hypothesis修正**: User installed wrong package or environment issue, not code bug |
| 5 | Searched PaddleOCR GitHub issues for GPU problems | Found multiple issues where `use_gpu=True` silently falls back to CPU |
| 6 | Read PaddlePaddle API docs for GPU verification | Discovered `paddle.is_compiled_with_cuda()` and `paddle.device.is_gpu_available()` |
| 7 | **Expanded scope**: Scanned entire file for hidden issues using 逐函数检查清单 | Found 8 additional issues beyond the 2 reported |
| 8 | Checked setup.py vs requirements.txt consistency | Found pdf2image missing from setup.py |
| 9 | Verified import usage across file | Found 5 unused imports |

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `read_file` | Read ocr_pipeline.py, requirements.txt, setup.py, test file |
| `grep` | Search for use_gpu usage patterns, temp directory handling |
| `web_search` | PaddleOCR package naming, GPU troubleshooting, CUDA compatibility |
| `web_fetch` | PyPI page for exact package/import name verification |

---

### 7. Verification

Run these commands to verify findings:

```bash
# 1. Verify paddleocr import works (if installed correctly)
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
python -c "from paddleocr import PaddleOCR; print('Import OK')"

# 2. Check if paddle-ocr vs paddleocr is installed
pip list | grep -i paddle

# 3. Verify GPU availability check
python -c "import paddle; print('CUDA compiled:', paddle.is_compiled_with_cuda()); print('GPU available:', paddle.device.is_gpu_available())"

# 4. Check unused imports
python -m py_compile src/data_processing/ocr_pipeline.py && echo "Syntax OK"

# 5. Verify temp directory issue exists
grep -n "rmdir()" src/data_processing/ocr_pipeline.py

# 6. Check pdf2image in setup.py
grep "pdf2image" setup.py || echo "MISSING - not found"
```

**Expected output demonstrating issues:**
```
# Command 2: Shows paddle-ocr (wrong) instead of paddleocr
paddle-ocr       2.x.x

# Command 5: Shows problematic rmdir()
183:                tmp_dir.rmdir()

# Command 6: Shows missing dependency
MISSING - not found
```

---

## 📋 交付确认

□ **目标匹配**: ModuleNotFoundError → 包名验证 + GPU 性能问题 → GPU 可用性检测  
□ **边界覆盖**: 跨平台路径、资源清理、线程安全、异常处理均已检查  
□ **风险可控**: 安全隐患 (symlink 攻击)、性能隐患 (未并行)、正确性隐患 (统计竞争) 已标注
