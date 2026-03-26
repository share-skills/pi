# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 1
## Duration: 211.73s

---

---

## Summary

**Issues Found: 6**
1. Critical: Wrong package name (`paddle-ocr` vs `paddleocr`)
2. High: Missing `paddlepaddle-gpu` for GPU acceleration
3. Medium: Temp directory cleanup fails silently (disk leak)
4. Medium: pdf2image is lazy-imported but not documented
5. Low: Unused imports (`ThreadPoolExecutor`, `as_completed`, `os`)
6. Low: `model_cache_dir` parameter accepted but never used

**Hidden Issues: 5**
1. No GPU fallback warning (fails silently to CPU)
2. Click import inside main() delays error detection
3. Concurrent.futures imported but processing is sequential
4. No verification that GPU is actually being used
5. Temp images accumulate indefinitely

**Root Cause:**
- Package naming confusion + missing GPU-specific paddlepaddle installation
- Incomplete cleanup logic and unused code from refactoring

**Recommended Fix:**
```bash
# Fix package installation
pip uninstall paddle-ocr 2>/dev/null; pip install paddleocr

# For GPU (CUDA 11.8 example)
python -m pip install paddlepaddle-gpu==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/
```
