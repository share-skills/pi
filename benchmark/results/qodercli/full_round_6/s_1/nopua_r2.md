# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 2
## Duration: 248.3s

---

---

**Summary**: I found **2 reported issues** (ModuleNotFoundError, GPU performance) and **5 hidden issues** (Poppler dependency, temp file leak, no CUDA verification, unused imports, incomplete error handling). The root cause of the import error is a package name mismatch (`paddle-ocr` vs `paddleocr`). The performance issue stems from either missing GPU package or silent CPU fallback without notification.
