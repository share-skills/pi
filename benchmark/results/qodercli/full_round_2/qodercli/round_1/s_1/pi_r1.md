# Scenario 1: OCR Pipeline Import Error
## Condition: pi | Run: 1
## Duration: 149.91s

---

## 1. Issues Found

| # | Issue | File:Line |
|---|-------|-----------|
| 1 | **ModuleNotFoundError: No module named 'paddleocr'** - Package not installed in current environment | `ocr_pipeline.py:31` |
| 2 | **GPU acceleration likely not working** - `use_gpu=True` default but PaddlePaddle GPU version may not be installed | `ocr_pipeline.py:40,113` |
| 3 | **Unused import: `field`** - Imported from dataclasses but never used | `ocr_pipeline.py:24` |
| 4 | **Unused import: `os`** - Imported but never referenced in the file | `ocr_pipeline.py:18` |
| 5 | **Unused import: `ThreadPoolExecutor, as_completed`** - Imported for concurrency but `process_directory` uses sequential processing | `ocr_pipeline.py:25` |
| 6 | **Unused import: `Image` from PIL** - Imported but never used | `ocr_pipeline.py:28` |
| 7 | **Hardcoded Unix path `/tmp/guwen_ocr`** - Will fail on Windows | `ocr_pipeline.py:50` |
| 8 | **Resource leak: temp files not cleaned** - PDF conversion creates images but only removes empty directory | `ocr_pipeline.py:182-185` |
| 9 | **Silent exception swallowing** - OSError during cleanup is silently ignored | `ocr_pipeline.py:184-185` |
| 10 | **Missing null check** - `result[0]` accessed without checking if result list is empty first | `ocr_pipeline.py:191` |

---

## 2. Hidden Issues

| # | Category | Issue | File:Line |
|---|----------|-------|-----------|
| 1 | **Performance** | `max_workers=4` configured but `process_directory` processes files sequentially (no ThreadPoolExecutor usage) | `ocr_pipeline.py:46,286-297` |
| 2 | **Cross-platform** | Hardcoded `/tmp/guwen_ocr` fails on Windows; should use `tempfile.gettempdir()` | `ocr_pipeline.py:50` |
| 3 | **Resource Leak** | `_process_pdf` creates temp image files but `rmdir()` fails if files exist; images never deleted | `ocr_pipeline.py:172,182-185` |
| 4 | **Security** | No validation of `config_path` in `_load_config` - potential path traversal | `ocr_pipeline.py:126-130` |
| 5 | **Exception Handling** | Bare `except Exception` in `process_directory` catches all exceptions including `KeyboardInterrupt` | `ocr_pipeline.py:295` |
| 6 | **API Contract** | `_process_image` returns `OCRResult` with `confidence=0.0` when no text detected - callers may not handle this edge case | `ocr_pipeline.py:193` |
| 7 | **Thread Safety** | `self._stats` modified without locks; unsafe if parallel processing ever enabled | `ocr_pipeline.py:176,178,297` |
| 8 | **Configuration** | `model_cache_dir` parameter in `__init__` accepted but never passed to `PaddleOCR` | `ocr_pipeline.py:98,107-119` |
| 9 | **Logic Bug** | `_merge_text_boxes` joins lines with `" "` but sometimes appends `"\n" + line` creating inconsistent separators | `ocr_pipeline.py:249,252,254` |
| 10 | **Memory** | Large PDFs load all pages into memory at once via `convert_from_path()` before processing | `ocr_pipeline.py:163-168` |

---

## 3. Root Cause

### Issue 1: ModuleNotFoundError
**Root Cause**: The package `paddleocr` is listed in `requirements.txt:11` but is **not installed** in the current Python environment. User reports "pip list shows paddle-ocr" but the actual package name is `paddleocr` (no hyphen), and `pip list` shows no paddle-related packages.

**Evidence**: 
```bash
python3 -m pip list | grep -i paddle  # Returns nothing
```

### Issue 2: GPU Not Being Used / Slow Performance
**Root Cause**: `use_gpu=True` is the default (`ocr_pipeline.py:40`), but:
1. PaddlePaddle has separate CPU/GPU packages (`paddlepaddle` vs `paddlepaddle-gpu`)
2. GPU package requires CUDA/cuDNN properly installed
3. No runtime verification that GPU is actually available before initialization

**Evidence**: Line 111-119 passes `use_gpu=self.config.use_gpu` to PaddleOCR without any capability check.

---

## 4. Recommended Fix

### Fix 1: Install Missing Dependencies
```bash
# Install OCR dependencies
pip install -r requirements.txt
# Or specifically:
pip install paddleocr paddlepaddle  # For CPU
# OR
pip install paddleocr paddlepaddle-gpu  # For GPU (requires CUDA)
```

### Fix 2: Remove Unused Imports
```python
# BEFORE (lines 18-31):
import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
from PIL import Image
from tqdm import tqdm

from paddleocr import PaddleOCR

# AFTER:
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass

import yaml
from tqdm import tqdm

from paddleocr import PaddleOCR
```

### Fix 3: Cross-Platform Temp Directory
```python
# BEFORE (line 50):
tmp_dir: str = "/tmp/guwen_ocr"

# AFTER:
import tempfile
tmp_dir: str = os.path.join(tempfile.gettempdir(), "guwen_ocr")
```

### Fix 4: Proper Resource Cleanup
```python
# BEFORE (lines 181-185):
finally:
    try:
        tmp_dir.rmdir()
    except OSError:
        pass  # Directory not empty, but we ignore it

# AFTER:
finally:
    # Clean up all temporary image files
    import shutil
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
```

### Fix 5: Add GPU Availability Check
```python
# Add after line 109:
def _check_gpu_available(self) -> bool:
    """Check if GPU is actually available for PaddleOCR."""
    if not self.config.use_gpu:
        return False
    try:
        import paddle
        return paddle.device.is_compiled_with_cuda() and paddle.device.is_gpu_available()
    except ImportError:
        logger.warning("PaddlePaddle not installed, falling back to CPU")
        return False

# Modify __init__ around line 111:
gpu_available = self._check_gpu_available()
if self.config.use_gpu and not gpu_available:
    logger.warning("GPU requested but not available, using CPU instead")

self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=gpu_available,  # Use actual availability, not just config
    ...
)
```

### Fix 6: Enable Parallel Processing
```python
# Replace process_directory loop (lines 286-297):
with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
    future_to_file = {
        executor.submit(self.process_file, str(file_path)): file_path
        for file_path in files
    }
    for future in as_completed(future_to_file):
        file_path = future_to_file[future]
        try:
            results = future.result()
            all_results[str(file_path)] = results
            if output_dir:
                self._save_results(file_path, results, Path(output_dir))
            self._stats["processed"] += 1
        except Exception as e:
            logger.error(f"Failed to process {file_path.name}: {e}")
            self._stats["failed"] += 1
```

---

## 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read full source file `ocr_pipeline.py` (374 lines) | Complete codebase understanding |
| 2 | Reproduced import error with `python3 -c "from src.data_processing.ocr_pipeline import OCRPipeline"` | Confirmed `ModuleNotFoundError: No module named 'paddleocr'` |
| 3 | Checked installed packages with `pip list` | No paddle-related packages found |
| 4 | Read `requirements.txt` | Confirmed `paddleocr>=2.7.0` and `paddlepaddle>=2.5.0` are dependencies |
| 5 | Searched for `use_gpu` usage | Found 6 occurrences; config defaults to True but no capability check |
| 6 | Searched for unused imports | Found 6 unused imports: `os`, `field`, `ThreadPoolExecutor`, `as_completed`, `Image` |
| 7 | Searched for hardcoded paths | Found `/tmp/guwen_ocr` - Windows incompatible |
| 8 | Analyzed exception handling patterns | Found silent `except OSError: pass` and bare `except Exception` |
| 9 | Reviewed resource management in `_process_pdf` | Discovered temp files never cleaned up |
| 10 | Compared imports vs usage | `max_workers` config exists but threading never implemented |

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read full source file (374 lines) |
| `Glob` | Locate `ocr_pipeline.py` and `requirements.txt` |
| `Bash` | Reproduce import error, check Python version, list installed packages |
| `Grep` | Search for specific patterns (imports, GPU config, temp paths, exception handlers) |
| `TodoWrite` | Track investigation progress |

---

## 7. Verification

### Verify Import Works
```bash
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
pip install -r requirements.txt
python3 -c "from src.data_processing.ocr_pipeline import OCRPipeline; print('Import successful')"
```

### Verify GPU Status
```bash
python3 -c "
import paddle
print('CUDA compiled:', paddle.device.is_compiled_with_cuda())
print('GPU available:', paddle.device.is_gpu_available())
if paddle.device.is_gpu_available():
    print('GPU count:', paddle.device.get_device_count())
"
```

### Verify Fixes Applied
```bash
# Check for unused imports
python3 -m py_compile src/data_processing/ocr_pipeline.py && echo "Syntax OK"

# Run a test import and check initialization
python3 -c "
from src.data_processing.ocr_pipeline import OCRPipeline, OCRConfig
config = OCRConfig(use_gpu=False)  # Force CPU for testing
pipeline = OCRPipeline(config)
print('Pipeline initialized successfully')
print('GPU mode:', pipeline.config.use_gpu)
"
```
