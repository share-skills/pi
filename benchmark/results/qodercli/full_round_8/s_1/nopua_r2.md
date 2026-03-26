# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 2
## Duration: 257.18s

---

---

## Quick Reference: Commands to Fix

```bash
# 1. Fix package installation
pip uninstall paddle-ocr paddleocr -y
pip install paddleocr

# 2. For GPU support (NVIDIA)
pip install paddlepaddle-gpu  # Or specific version with CUDA

# 3. Verify installation
python -c "from paddleocr import PaddleOCR; print('OK')"

# 4. Check GPU availability
python -c "import paddle; print('GPU:', paddle.device.is_compiled_with_cuda())"
```
