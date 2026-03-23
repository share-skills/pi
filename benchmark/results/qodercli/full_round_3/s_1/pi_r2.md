# Scenario 1: OCR Pipeline Import Error
## Condition: pi | Run: 2
## Duration: 265.96s

---

Now I have a complete picture. Let me provide the structured summary:

---

## 🧠 PI · 调查完成 · 肃阵

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **Missing `paddlepaddle` package** - requirements.txt specifies `paddlepaddle>=2.5.0` but it's not installed | requirements.txt:12, environment | 🔴 blocker |
| 2 | **API incompatibility: `use_gpu` parameter removed** - PaddleOCR 3.x uses `device` parameter instead of `use_gpu` | ocr_pipeline.py:40,113 | 🔴 blocker |
| 3 | **API incompatibility: `show_log` parameter removed** - No longer supported in PaddleOCR 3.x | ocr_pipeline.py:118 | 🔴 blocker |
| 4 | **Deprecated parameter names** - `use_angle_cls`, `det_model_dir`, `rec_model_dir`, `cls_model_dir` need updating to new names | ocr_pipeline.py:114-117 | 🟡 warning |

### 2. Hidden Issues

| # | Issue | Location | Risk |
|---|-------|----------|------|
| 5 | **GPU never used on macOS** - This is Apple Silicon (no CUDA), `use_gpu=True` silently falls back to CPU causing slow performance | configs/ocr_config.yaml:3 | ⚡ performance |
| 6 | **No paddlepaddle GPU package** - Even on Linux with GPU, `paddlepaddle` (CPU) is in requirements, not `paddlepaddle-gpu` | requirements.txt:12 | ⚡ performance |
| 7 | **Temporary directory cleanup failure** - `_process_pdf()` ignores OSError when tmp_dir has files, leaving orphaned files | ocr_pipeline.py:182-185 | 🗑️ resource leak |
| 8 | **Hardcoded tmp path** - `/tmp/guwen_ocr` doesn't work on Windows (config file and code) | ocr_pipeline.py:50, ocr_config.yaml:10 | 🪟 cross-platform |
| 9 | **Unused imports** - `os`, `sys`, `field`, `ThreadPoolExecutor`, `as_completed`, `Image` are imported but never used | ocr_pipeline.py:18-25 | 📖 code quality |
| 10 | **Silent exception swallowing** - `process_directory()` catches all exceptions but only logs, no recovery or retry | ocr_pipeline.py:295-297 | ⚠️ error handling |

### 3. Root Cause

**Primary Issue (Import Error):**
- **Line 31**: `from paddleocr import PaddleOCR` succeeds because `paddleocr==3.4.0` is installed
- **Line 111-119**: `PaddleOCR(...)` constructor fails because:
  1. `use_gpu` is not a valid parameter in PaddleOCR 3.x (replaced by `device`)
  2. `show_log` is not a valid parameter in PaddleOCR 3.x
  3. `paddlepaddle` base package is missing (required dependency)

**Evidence:**
```
ValueError: Unknown argument: use_gpu     [tested via python -c]
ValueError: Unknown argument: show_log    [tested via python -c]
ModuleNotFoundError: No module named 'paddle'  [when trying device='gpu']
```

**Secondary Issue (Performance):**
- Platform is macOS (Darwin 25.3.0) with Apple Silicon - no CUDA support
- Config sets `use_gpu: true` but this always falls back to CPU
- No Metal acceleration configured for PaddlePaddle

### 4. Recommended Fix

#### Fix 1: Update requirements.txt
```diff
# OCR
-paddleocr>=2.7.0
-paddlepaddle>=2.5.0
+paddleocr>=3.4.0
+paddlepaddle>=3.0.0  # Or paddlepaddle-gpu on Linux with CUDA
```

#### Fix 2: Update OCRConfig dataclass (ocr_pipeline.py:36-53)
```diff
@dataclass
class OCRConfig:
    lang: str = "ch"
-   use_gpu: bool = True
+   device: str = "cpu"  # New PaddleOCR 3.x API: "cpu", "gpu", "gpu:0", etc.
    det_model_dir: Optional[str] = None
    rec_model_dir: Optional[str] = None
    cls_model_dir: Optional[str] = None
-   use_angle_cls: bool = True
+   use_textline_orientation: bool = True  # Renamed parameter
    output_format: str = "txt"
    max_workers: int = 4
    dpi: int = 300
    confidence_threshold: float = 0.6
    page_separator: str = "\n---PAGE_BREAK---\n"
-   tmp_dir: str = "/tmp/guwen_ocr"
+   tmp_dir: str = None  # Use tempfile.gettempdir() for cross-platform
    enable_table_detection: bool = False
    merge_boxes: bool = True
    box_merge_threshold: float = 0.5
    
    def __post_init__(self):
        if self.tmp_dir is None:
            import tempfile
            self.tmp_dir = Path(tempfile.gettempdir()) / "guwen_ocr"
```

#### Fix 3: Update PaddleOCR initialization (ocr_pipeline.py:111-119)
```diff
self._engine = PaddleOCR(
-   lang=self.config.lang,
-   use_gpu=self.config.use_gpu,
-   use_angle_cls=self.config.use_angle_cls,
-   det_model_dir=self.config.det_model_dir,
-   rec_model_dir=self.config.rec_model_dir,
-   cls_model_dir=self.config.cls_model_dir,
-   show_log=False,
+   lang=self.config.lang,
+   device=self.config.device,
+   use_textline_orientation=self.config.use_textline_orientation,
+   text_detection_model_dir=self.config.det_model_dir,
+   text_recognition_model_dir=self.config.rec_model_dir,
+   textline_orientation_model_dir=self.config.cls_model_dir,
)
```

#### Fix 4: Update config file (configs/ocr_config.yaml)
```diff
ocr:
-  lang: ch
-  use_gpu: true
+  lang: ch
+  device: cpu  # Use "gpu" on Linux with CUDA, "cpu" otherwise
-  use_angle_cls: true
+  use_textline_orientation: true
   output_format: json
   max_workers: 4
   dpi: 300
   confidence_threshold: 0.6
   page_separator: "\n---PAGE_BREAK---\n"
-  tmp_dir: /tmp/guwen_ocr
+  tmp_dir: null  # Auto-detect platform-appropriate temp dir
   enable_table_detection: false
   merge_boxes: true
   box_merge_threshold: 0.5
```

### 5. Steps Taken

| Step | Action | Discovery |
|------|--------|-----------|
| 1 | Read ocr_pipeline.py source | Found `use_gpu`, `show_log` parameters at lines 113, 118 |
| 2 | Reproduced import error | `python -c "from src.data_processing.ocr_pipeline import OCRPipeline"` succeeded but warned about model check |
| 3 | Checked installed packages | `paddleocr==3.4.0`, `paddlex==3.4.2`, but `paddlepaddle` NOT installed |
| 4 | Tested PaddleOCR constructor | `ValueError: Unknown argument: use_gpu` - API changed in 3.x |
| 5 | Inspected PaddleOCR 3.x source | New signature uses `device` param, not `use_gpu`; `show_log` removed |
| 6 | Checked deprecated param mapping | `use_angle_cls` → `use_textline_orientation`, `*_model_dir` → `text_*_model_dir` |
| 7 | Verified platform | macOS Darwin 25.3.0 (Apple Silicon) - no CUDA, GPU acceleration unavailable |
| 8 | Searched codebase for similar patterns | Found 7 occurrences of `use_gpu` in ocr_pipeline.py |
| 9 | Reviewed test file | Tests mock PaddleOCR, so they pass even with broken real implementation |
| 10 | Audited for hidden issues | Found resource leak, hardcoded paths, unused imports |

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read ocr_pipeline.py, requirements.txt, test file, config files |
| `Bash` | Test imports, check package versions, verify PaddleOCR API |
| `Grep` | Search for `use_gpu`, `paddlepaddle` patterns across codebase |
| `Glob` | Locate Python files, config files |
| `inspect` (Python) | Examine PaddleOCR 3.x source code and signatures |

### 7. Verification

**Current State (Broken):**
```bash
$ cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
$ source .venv/bin/activate
$ python -c "from src.data_processing.ocr_pipeline import OCRPipeline; p = OCRPipeline()"
# Result: ValueError: Unknown argument: use_gpu
```

**Verification Commands (After Fix):**
```bash
# 1. Verify import works
python -c "from src.data_processing.ocr_pipeline import OCRPipeline; print('✓ Import OK')"

# 2. Verify pipeline initialization
python -c "from src.data_processing.ocr_pipeline import OCRPipeline, OCRConfig; p = OCRPipeline(OCRConfig(device='cpu')); print('✓ Init OK')"

# 3. Verify paddlepaddle is installed
pip show paddlepaddle | grep Version

# 4. Verify correct parameters
python -c "
from paddleocr import PaddleOCR
ocr = PaddleOCR(lang='ch', device='cpu')
print('✓ PaddleOCR 3.x API compatible')
"
```

---

## Summary

**Two independent issues:**
1. **Package name confusion**: User reported `pip list shows paddle-ocr` but actual package is `paddleocr`. The real issue is `paddlepaddle` (the ML framework) is NOT installed despite being in requirements.txt.
2. **API version mismatch**: Code written for PaddleOCR 2.x, but environment has PaddleOCR 3.4.0 with breaking API changes (`use_gpu` → `device`, `show_log` removed, parameter renames).

**Performance issue root cause**: Running on macOS with Apple Silicon - no CUDA GPU available. Even if `use_gpu` worked, it would fall back to CPU. For macOS GPU acceleration, would need PaddlePaddle with Metal support (if available).
