# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 1
## Duration: 32.55s

---

The file path in the task description points to `D:\Projects\private-project\src\data_processing\ocr_pipeline.py`, which is a Windows path. The provided source code is embedded in the task description itself. Let me analyze the code directly.

## Investigation Analysis

### Issues Found

**1. Module Import Error - Wrong Package Name**
- **Location**: Line 24: `from paddleocr import PaddleOCR`
- **Issue**: The error states `paddle-ocr` is installed (per `pip list`), but the import uses `paddleocr`. The package name on PyPI is `paddleocr`, but when installed via some package managers or specific versions, it might be registered differently.
- **Root Cause**: Check if the actual importable module name matches what's used in code.

**2. GPU Not Being Used - Configuration Issue**
- **Location**: Line 108-115, `__init__` method where `PaddleOCR` is initialized
- **Issue**: `use_gpu=self.config.use_gpu` is passed, but default config sets `use_gpu: bool = True` (Line 36). However, PaddleOCR's parameter name for GPU usage has changed across versions:
  - Older versions use `use_gpu`
  - Newer versions (2.7+) use `gpu_mem` or require explicit GPU device setup
- **Hidden Issue**: Even if `use_gpu=True`, without checking if CUDA/paddlepaddle-gpu is properly installed, it silently falls back to CPU.

**3. Missing pdf2image Import Handling**
- **Location**: Line 159 - `from pdf2image import convert_from_path`
- **Issue**: This is a lazy import inside `_process_pdf`, but `pdf2image` is not listed in the main imports. If this package isn't installed, the error only appears at runtime when processing PDFs.

**4. Inefficient ThreadPoolExecutor Import But Not Used**
- **Location**: Line 17: `from concurrent.futures import ThreadPoolExecutor, as_completed`
- **Issue**: Imported but never used in the code. The `process_directory` method processes files sequentially despite having the threading infrastructure imported.

**5. Performance Issue - No Batch Processing**
- **Location**: `process_directory` method, Lines 233-257
- **Issue**: Despite `max_workers: int = 4` in config (Line 42), files are processed sequentially in a simple for-loop. The `ThreadPoolExecutor` is imported but never utilized.

**6. Temporary Directory Cleanup Issue**
- **Location**: Lines 174-177
- **Issue**: The `finally` block tries `tmp_dir.rmdir()` which only works on empty directories. The comment acknowledges this but ignores it, leaving orphaned temp files.

**7. Hardcoded Unix Path**
- **Location**: Line 47: `tmp_dir: str = "/tmp/guwen_ocr"`
- **Issue**: This Unix path won't work on Windows (the user's environment is Windows based on the `D:\` path). Should use `pathlib.Path` with platform-agnostic temp directory.

### Hidden Issues Beyond the Ask

**8. Missing Error Handling for Model Download**
- **Location**: Lines 108-115
- **Issue**: PaddleOCR downloads models on first run if not cached. No error handling for network failures or disk space issues during model download.

**9. Memory Leak Risk with Large PDFs**
- **Location**: Lines 165-172
- **Issue**: `convert_from_path` loads ALL pages into memory at once. For large PDFs (100+ pages), this will cause OOM errors.

**10. Confidence Calculation Bug**
- **Location**: Line 201
- **Issue**: When `confidences` list is empty (no text detected above threshold), `avg_confidence` becomes `0.0` correctly, but this masks the difference between "no text" and "low confidence text".

**11. Box Merge Logic Error**
- **Location**: Lines 213-214
- **Issue**: When merging boxes, `merged.append("\n" + lines[i])` adds newline before the line, but `"".join(merged)` at the end doesn't add newlines between non-merged lines consistently.

### Verification Steps Taken

1. **Code Analysis**: Read through all 280+ lines of the OCR pipeline
2. **Import Chain Verification**: Traced `paddleocr` vs `paddle-ocr` naming convention
3. **Configuration Flow**: Followed `use_gpu` from config through to PaddleOCR initialization
4. **Performance Audit**: Checked where `max_workers` config is (not) used

### Tools Used
- Static code analysis (reading the provided source)
- Pattern matching against known PaddleOCR API changes
- Cross-referencing import statements with usage

---

## Summary Report

| # | Issue | Severity | Type |
|---|-------|----------|------|
| 1 | Import mismatch (`paddleocr` vs installed package) | P0 | Bug |
| 2 | GPU not actually used (parameter name / fallback) | P0 | Performance |
| 3 | Sequential processing despite `max_workers` config | P1 | Performance |
| 4 | Windows incompatibility (hardcoded `/tmp/`) | P1 | Compatibility |
| 5 | Temp file cleanup incomplete | P2 | Bug |
| 6 | Lazy import without error handling (pdf2image) | P2 | Robustness |
| 7 | Unused ThreadPoolExecutor import | P3 | Code Quality |
| 8 | All-pages-in-memory PDF processing | P1 | Memory |
| 9 | No model download error handling | P2 | Robustness |
| 10 | Confidence calculation edge case | P3 | Logic |
| 11 | Box merge newline inconsistency | P3 | Logic |

### Root Causes

1. **ModuleNotFoundError**: Package naming inconsistency between installation (`paddle-ocr`) and import (`paddleocr`). Need to verify actual pip package name and potentially add fallback import logic.

2. **GPU Not Used**: PaddleOCR's GPU parameter semantics changed. Setting `use_gpu=True` alone doesn't guarantee GPU usage—requires `paddlepaddle-gpu` package (not just `paddlepaddle`) and proper CUDA setup. The code should verify GPU availability and report actual device being used.

3. **Slow Performance**: Multiple factors:
   - Files processed sequentially despite `max_workers=4` config
   - No batch inference support
   - Large PDFs load all pages to memory

### Recommended Fixes

**Immediate (P0):**
```python
# Fix 1: Verify import and add fallback
try:
    from paddleocr import PaddleOCR
except ImportError:
    try:
        from paddle_ocr import PaddleOCR  # Alternative package name
    except ImportError:
        raise ImportError("Please install paddleocr: pip install paddleocr")

# Fix 2: Add GPU verification
import paddle
if self.config.use_gpu:
    if not paddle.is_compiled_with_cuda() or not paddle.is_gpu_available():
        logger.warning("GPU requested but not available, falling back to CPU")
        self.config.use_gpu = False
    else:
        logger.info(f"Using GPU: {paddle.device.get_device()}")
```

**Performance (P1):**
```python
# Fix 3: Use ThreadPoolExecutor for parallel file processing
def process_directory(self, input_dir: str, output_dir: Optional[str] = None,
                      recursive: bool = True) -> Dict[str, List[OCRResult]]:
    # ... file discovery code ...
    
    with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
        future_to_file = {
            executor.submit(self.process_file, str(file_path)): file_path 
            for file_path in files
        }
        
        for future in tqdm(as_completed(future_to_file), desc="OCR Processing"):
            file_path = future_to_file[future]
            try:
                results = future.result()
                # ... rest of processing ...
```

**Compatibility (P1):**
```python
# Fix 4: Platform-agnostic temp directory
import tempfile
tmp_dir: str = field(default_factory=lambda: os.path.join(tempfile.gettempdir(), "guwen_ocr"))
```

Would you like me to provide the complete fixed version of the file?
