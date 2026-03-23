# Scenario 1: OCR Pipeline Import Error
## Condition: pua | Run: 2
## Duration: 342.38s

---

---

## Summary

**Primary Issues:**
1. **ModuleNotFoundError**: Wrong package name - should be `paddleocr` not `paddle-ocr`
2. **GPU Performance**: `use_gpu=True` doesn't guarantee GPU usage - no detection/fallback logic, causing silent CPU fallback with overhead

**Hidden Critical Issues:**
- Thread safety risk with shared PaddleOCR engine
- Memory leak from temporary image cleanup failure
- Windows incompatibility (hardcoded `/tmp` path)
- Unused imports that may cause import errors
- Confidence extraction may fail depending on PaddleOCR version

**Root Cause**: Package naming confusion + missing GPU availability validation before initialization
