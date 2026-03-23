# Scenario 1: OCR Pipeline Import Error
## Condition: pua | Run: 1
## Duration: 258.01s

---

## Structured Summary

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **`use_gpu` parameter removed in PaddleOCR 3.x** | Critical | `ocr_pipeline.py:111-119` |
| 2 | **Package name discrepancy** | Critical | User environment |
| 3 | **`paddlepaddle` core engine not installed** | Critical | User environment |
| 4 | **Unused imports** | Low | `ocr_pipeline.py:18-28` |
| 5 | **Temp directory cleanup bug** | Medium | `ocr_pipeline.py:182-185` |
| 6 | **`_merge_text_boxes` newline logic error** | Medium | `ocr_pipeline.py:249` |
| 7 | **`pdf2image` not installed** | Medium | User environment |
| 8 | **Poppler not installed** | Medium | System dependency |

---

### 2. Hidden Issues (Beyond the Ask)

1. **API Breaking Change**: PaddleOCR 3.x completely removed the `use_gpu` parameter. The code will crash with `ValueError: Unknown argument: use_gpu` when initializing `PaddleOCR`.

2. **Missing Core Engine**: Only `paddleocr` and `paddlex` are installed. The `paddlepaddle` package (the core deep learning engine) is missing, making GPU acceleration impossible even if the parameter worked.

3. **PDF Processing Will Fail**: Neither `pdf2image` Python package nor the `poppler` system utility are installed. Any attempt to process PDF files will fail.

4. **Resource Leak**: The temp directory cleanup in `_process_pdf()` uses `rmdir()` which silently fails on non-empty directories, leaving orphaned image files on disk.

5. **Text Formatting Bug**: The `_merge_text_boxes` method prepends newlines to paragraphs (`"\n" + lines[i]`) instead of appending them, causing incorrect paragraph formatting.

6. **Six Unused Imports**: `os`, `sys`, `ThreadPoolExecutor`, `as_completed`, `field`, and `Image` are imported but never used, adding unnecessary dependencies.

---

### 3. Root Cause

**Primary Issue (ModuleNotFoundError):**
The user reports installing `paddle-ocr` (with hyphen), but the correct PyPI package name is `paddleocr` (no hyphen). These are different packages. The import statement `from paddleocr import PaddleOCR` requires the correctly named package.

**Secondary Issue (GPU Not Working):**
Two-fold problem:
1. The code uses `use_gpu=True` which was removed in PaddleOCR 3.x (the installed version is 3.4.0)
2. Even if the parameter worked, `paddlepaddle` (the core engine with CUDA support) is not installed

---

### 4. Recommended Fix

#### Immediate Fixes (Code Changes):

```python
# 1. Remove unused imports (line 18-25)
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass

import yaml
from tqdm import tqdm

from paddleocr import PaddleOCR

# 2. Fix PaddleOCR initialization for 3.x API (line 111-119)
self._engine = PaddleOCR(
    lang=self.config.lang,
    device='gpu' if self.config.use_gpu else 'cpu',  # Changed from use_gpu to device
    use_angle_cls=self.config.use_angle_cls,
    det_model_dir=self.config.det_model_dir,
    rec_model_dir=self.config.rec_model_dir,
    cls_model_dir=self.config.cls_model_dir,
    show_log=False,
)

# 3. Fix temp directory cleanup (line 182-185)
finally:
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)  # Use rmtree instead of rmdir

# 4. Fix _merge_text_boxes newline logic (line 249)
if gap_ratio > self.config.box_merge_threshold:
    merged.append(lines[i])  # Don't prepend newline
    merged.append('\n')      # Add newline as separate element or handle differently
else:
    merged.append(lines[i])
# Then join properly: result = ''.join(merged)
```

#### Environment Fixes:

```bash
# Uninstall wrong package if installed
pip uninstall paddle-ocr

# Install correct packages
pip install paddleocr paddlepaddle-gpu  # For GPU support
# OR
pip install paddleocr paddlepaddle      # For CPU only

# Install PDF processing dependencies
pip install pdf2image
# Also install poppler system package:
# macOS: brew install poppler
# Ubuntu: apt-get install poppler-utils
# Windows: download from https://github.com/oschwartz10612/poppler-windows/releases
```

---

### 5. Steps Taken

1. **Read the source code** - Analyzed all 374 lines of `ocr_pipeline.py`
2. **Checked requirements.txt and setup.py** - Verified dependency specifications
3. **Searched PyPI and GitHub** - Confirmed correct package name is `paddleocr`
4. **Tested import in virtualenv** - Confirmed import works with correct package
5. **Inspected PaddleOCR 3.x API** - Discovered `use_gpu` parameter was removed
6. **Checked installed packages** - Found `paddlepaddle` missing, only `paddleocr` and `paddlex` present
7. **Verified PDF dependencies** - Confirmed `pdf2image` and `poppler` both missing
8. **Analyzed unused imports** - Used AST parsing to identify 6 unused imports
9. **Traced temp file cleanup** - Identified `rmdir()` failure on non-empty directories
10. **Simulated merge logic** - Confirmed newline placement bug in `_merge_text_boxes`

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Source code analysis |
| `Glob` | File discovery |
| `Grep` | Pattern searching |
| `WebSearch` | Package documentation lookup |
| `WebFetch` | PyPI and GitHub documentation |
| `Bash` | Import testing, package inspection, dependency verification |
| AST parsing | Unused import detection |

---

### 7. Verification

**Evidence collected:**

1. **Import test passed** in venv with correct package:
   ```
   Exit code 0 (success)
   ```

2. **PaddleOCR 3.x API confirmed** - `use_gpu` rejected:
   ```
   ValueError: Unknown argument: use_gpu
   ```

3. **Package inventory** - Missing core engine:
   ```
   paddleocr     3.4.0
   paddlex       3.4.2
   paddlepaddle  NOT INSTALLED
   ```

4. **PDF dependencies missing**:
   ```
   pdf2image: NOT INSTALLED
   poppler (pdftoppm): NOT FOUND
   ```

5. **Merge bug verified** - Output shows incorrect newline placement:
   ```
   'First lineSecond line\nThird line'
   ```
