# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 2
## Duration: 87.53s

---

---

## Summary

**Issues Found: 8 total (2 reported + 6 hidden)**

| # | Issue | Severity | Category |
|---|-------|----------|----------|
| 1 | Wrong package installed (`paddle-ocr` vs `paddleocr`) | Critical | Import Error |
| 2 | No GPU validation - silent CPU fallback | Critical | Performance |
| 3 | 6 unused imports (`os`, `sys`, `field`, `ThreadPoolExecutor`, `as_completed`, `Image`) | Low | Code Quality |
| 4 | No error handling for pdf2image conversion | Medium | Reliability |
| 5 | Hardcoded Unix path `/tmp/guwen_ocr` | Medium | Cross-Platform |
| 6 | Thread-unsafe `_stats` dictionary | Medium | Concurrency |
| 7 | Potential division by zero edge case | Low | Correctness |
| 8 | Click option shadows built-in `format` | Low | Code Quality |

**Root Cause:**
- **ImportError**: User installed `paddle-ocr` (third-party) instead of `paddleocr` (official PyPI package)
- **Slow Performance**: `use_gpu=True` is a request, not auto-detection. PaddleOCR silently falls back to CPU when GPU unavailable. No validation code exists to warn users.

**Recommended Fix:**
```bash
pip uninstall paddle-ocr
pip install paddleocr>=2.7.0 paddlepaddle-gpu>=2.5.0
```

Then add GPU validation in `OCRPipeline.__init__()` before line 111.
