# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 1
## Duration: 42.58s

---

---

## Summary

**11 issues identified:**
- 2 critical (package mismatch, GPU not working)
- 1 medium (no parallel processing despite config)
- 8 hidden issues (cleanup leaks, unused code, error handling gaps, logic bugs)

**Root cause of ModuleNotFoundError:** Package name is `paddleocr` (no hyphen), not `paddle-ocr`. User installed the wrong package.

**Root cause of slow performance:** Even if `use_gpu=True`, there's no verification that:
1. PaddlePaddle was compiled with CUDA
2. A GPU is actually available
3. The GPU package (`paddlepaddle-gpu`) was installed vs CPU package
