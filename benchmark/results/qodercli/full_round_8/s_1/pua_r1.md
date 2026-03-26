# Scenario 1: OCR Pipeline Import Error
## Condition: pua | Run: 1
## Duration: 244.07s

---

## Summary

The OCR pipeline has **two critical reported issues** and **five hidden issues**:

### Reported Issues:
1. **ModuleNotFoundError**: Package `paddle-ocr` is installed but code imports from `paddleocr` (official package). These are different packages.
2. **Slow performance/GPU not used**: Even with `use_gpu=True`, GPU won't activate without `paddlepaddle-gpu` package and proper CUDA setup. Additionally, `show_log=False` hides GPU initialization status.

### Hidden Critical Issue:
**PaddleOCR 3.x API Breaking Change**: The code expects PaddleOCR 2.x return format `[(bbox, (text, conf))]` but version 3.x returns `[{"rec_texts": [...], "rec_scores": [...]}]`. This will cause complete pipeline failure on modern installations.

### Immediate Actions Required:
1. Install correct packages: `pip install "paddleocr>=3.0.0" "paddlepaddle-gpu>=3.0.0"` (or `paddlepaddle` for CPU)
2. Update `_process_image()` method to handle new dict-based result format
3. Set `show_log=True` to verify GPU initialization
4. Implement `model_cache_dir` parameter properly
