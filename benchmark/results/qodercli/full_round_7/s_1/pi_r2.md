# Scenario 1: OCR Pipeline Import Error
## Condition: pi | Run: 2
## Duration: 228.38s

---

Now I have gathered enough information. Let me compile the complete investigation report:

---

## 🧠 PI · Investigation Complete · OCR Pipeline Issues

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **ModuleNotFoundError for paddleocr** - Package not installed in current environment | `ocr_pipeline.py:31` | 🔴 Blocker |
| 2 | **API incompatibility: `use_gpu` parameter removed** - PaddleOCR 3.x uses `device` parameter instead | `ocr_pipeline.py:113` | 🔴 Blocker |
| 3 | **API incompatibility: `show_log` parameter unknown** - Causes ValueError | `ocr_pipeline.py:118` | 🔴 Blocker |
| 4 | **API incompatibility: `use_angle_cls` deprecated** - Renamed to `use_textline_orientation` | `ocr_pipeline.py:114` | 🟡 Warning |
| 5 | **GPU fallback behavior misleading** - Config says "Falls back to CPU silently" but actually crashes | `ocr_config.yaml:3` | 🟡 Warning |
| 6 | **Unused imports** - `os`, `sys`, `ThreadPoolExecutor`, `as_completed`, `Image` imported but never used | `ocr_pipeline.py:18-29` | ⚪ Nit |
| 7 | **Temporary directory cleanup incomplete** - Only removes empty dirs, leaves image files behind | `ocr_pipeline.py:181-185` | 🟡 Suggestion |

### 2. Hidden Issues (Beyond User's Ask)

| # | Issue | Location | Risk |
|---|-------|----------|------|
| H1 | **No graceful degradation when paddle module missing** - Import fails at module level instead of lazy loading | `ocr_pipeline.py:31` | 🔴 Blocks all usage |
| H2 | **Device configuration requires string format** - e.g., `"cpu"` or `"gpu:0"`, not boolean | New API requirement | 🔴 Breaking change |
| H3 | **No validation of device availability** - Code doesn't check if GPU is actually available before requesting it | `ocr_pipeline.py:111-119` | 🟡 May cause runtime errors |
| H4 | **Missing error handling for PDF conversion** - `pdf2image.convert_from_path` can fail without cleanup | `ocr_pipeline.py:163-168` | 🟡 Resource leak risk |
| H5 | **Hardcoded `/tmp/` path** - Not cross-platform compatible (fails on Windows) | `ocr_pipeline.py:50` | 🟡 Portability issue |
| H6 | **No thread safety for `_stats` dictionary** - Concurrent access could corrupt stats | `ocr_pipeline.py:109` | ⚪ Low priority |

### 3. Root Cause

**Primary Root Cause:** PaddleOCR underwent a **major version upgrade from 2.x to 3.x**, which introduced breaking API changes:

1. **`use_gpu` parameter removed** (Line 113): The old API accepted `use_gpu=True/False`. The new API (3.x) uses `device="cpu"` or `device="gpu:0"` passed through `**kwargs` to the underlying `create_pipeline()` function.

2. **`show_log` parameter unknown** (Line 118): This parameter was never part of the official API and causes `ValueError: Unknown argument: show_log`.

3. **`use_angle_cls` deprecated** (Line 114): Now renamed to `use_textline_orientation` per the deprecation mapping in `paddleocr/_pipelines/ocr.py:46`.

**Initially I thought** the issue was just a missing package installation. **Upon closer inspection**, the root cause is actually a **breaking API change** between PaddleOCR 2.x and 3.x. The code was written for 2.x but the environment has 3.4.0 installed.

**Actually**, the problem is more complex: even if you install `paddlepaddle`, the code will still fail because the constructor signature has completely changed.

### 4. Recommended Fix

#### Fix 1: Update PaddleOCR initialization (Lines 111-119)

**Before:**
```python
self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=self.config.use_gpu,
    use_angle_cls=self.config.use_angle_cls,
    det_model_dir=self.config.det_model_dir,
    rec_model_dir=self.config.rec_model_dir,
    cls_model_dir=self.config.cls_model_dir,
    show_log=False,
)
```

**After:**
```python
# Build kwargs for PaddleOCR 3.x compatibility
ocr_kwargs = {
    "lang": self.config.lang,
}

# Map deprecated parameter names to new names
if self.config.det_model_dir:
    ocr_kwargs["text_detection_model_dir"] = self.config.det_model_dir
if self.config.rec_model_dir:
    ocr_kwargs["text_recognition_model_dir"] = self.config.rec_model_dir
if self.config.cls_model_dir:
    ocr_kwargs["textline_orientation_model_dir"] = self.config.cls_model_dir

# Map use_angle_cls to use_textline_orientation
ocr_kwargs["use_textline_orientation"] = self.config.use_angle_cls

# Convert use_gpu boolean to device string
if self.config.use_gpu:
    ocr_kwargs["device"] = "gpu:0"
else:
    ocr_kwargs["device"] = "cpu"

self._engine = PaddleOCR(**ocr_kwargs)
```

#### Fix 2: Remove unused imports (Lines 18-29)

**Before:**
```python
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
```

**After:**
```python
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass

import yaml
from tqdm import tqdm

from paddleocr import PaddleOCR
```

#### Fix 3: Improve temporary directory cleanup (Lines 181-185)

**Before:**
```python
finally:
    try:
        tmp_dir.rmdir()
    except OSError:
        pass  # Directory not empty, but we ignore it
```

**After:**
```python
finally:
    # Clean up temporary image files
    try:
        for img_file in tmp_dir.glob("*.png"):
            img_file.unlink()
        tmp_dir.rmdir()
    except OSError:
        logger.warning(f"Failed to clean up temporary directory: {tmp_dir}")
```

#### Fix 4: Make tmp_dir cross-platform (Line 50)

**Before:**
```python
tmp_dir: str = "/tmp/guwen_ocr"
```

**After:**
```python
tmp_dir: str = str(Path.home() / ".cache" / "guwen_ocr")  # Cross-platform temp dir
```

### 5. Steps Taken

1. **Read the source file** (`ocr_pipeline.py`) to understand the current implementation
2. **Tested import** - Confirmed `ModuleNotFoundError: No module named 'paddleocr'` 
3. **Checked pip list** - Found `paddleocr 3.4.0` and `paddlex 3.4.2` installed in venv
4. **Compared API signatures** - Old code uses `use_gpu`, new API requires `device` parameter
5. **Read PaddleOCR 3.x source** (`paddleocr/_pipelines/ocr.py`) to understand new parameter mapping
6. **Identified deprecation mapping** - Found `_DEPRECATED_PARAM_NAME_MAPPING` showing `use_angle_cls` → `use_textline_orientation`
7. **Tested actual instantiation** - Confirmed `ValueError: Unknown argument: use_gpu` and `ValueError: Unknown argument: show_log`
8. **Searched for device parameter** - Found `create_pipeline()` accepts `device: Optional[str] = None`
9. **Cross-referenced config file** - Found `ocr_config.yaml` comment says "Falls back to CPU silently" which is incorrect

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `read_file` | Read source files (ocr_pipeline.py, test files, config) |
| `Bash` | Test imports, check package versions, run Python snippets |
| `grep` | Search for parameter usage patterns |
| `inspect.signature()` | Examine PaddleOCR constructor signature |
| `pip list` | Verify installed packages |

### 7. Verification

**Verification Commands:**

```bash
# 1. Verify paddleocr is installed
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
source .venv/bin/activate
pip show paddleocr | grep Version
# Expected: Version: 3.4.0

# 2. Verify old API fails
python3 -c "
import os
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
from paddleocr import PaddleOCR
try:
    PaddleOCR(lang='ch', use_gpu=True, show_log=False)
except ValueError as e:
    print(f'EXPECTED ERROR: {e}')
"
# Expected: ValueError: Unknown argument: use_gpu OR show_log

# 3. Verify new API works
python3 -c "
import os
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
from paddleocr import PaddleOCR
try:
    ocr = PaddleOCR(lang='ch', device='cpu')
    print('SUCCESS: New API works with device parameter')
except Exception as e:
    print(f'ERROR: {e}')
"
# Expected: SUCCESS message (may still fail if paddle not installed)

# 4. Check parameter mapping
python3 -c "
from paddleocr._pipelines.ocr import _DEPRECATED_PARAM_NAME_MAPPING
print('Deprecated parameter mappings:')
for old, new in _DEPRECATED_PARAM_NAME_MAPPING.items():
    print(f'  {old} -> {new}')
"
```

**Manual Verification Steps:**
- Check `ocr_pipeline.py:111-119` after fix to ensure `device` parameter is used instead of `use_gpu`
- Check `ocr_config.yaml:3` comment should be updated to reflect that GPU must be explicitly available
- Run existing tests: `pytest tests/test_ocr_pipeline.py -v` to ensure backward compatibility

---

### 📋 Delivery Confirmation

□ **目标匹配**: ModuleNotFoundError + GPU slowness → Root cause identified as PaddleOCR 3.x breaking API changes  
□ **边界覆盖**: Import errors, API incompatibility, deprecated parameters, hidden issues (cross-platform, resource cleanup)  
□ **风险可控**: Fix requires code changes; recommend testing in staging environment first; existing tests should be updated
