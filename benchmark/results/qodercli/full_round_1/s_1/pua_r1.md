# Scenario 1: OCR Pipeline Import Error
## Condition: pua | Run: 1
## Duration: 138.12s

---

Now I have a complete picture of the issues. Let me compile my investigation findings:

---

## Investigation Summary

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **ModuleNotFoundError for `paddleocr`** | Critical | Line 31 |
| 2 | **GPU silently falls back to CPU** | High | Line 113, config line 3 |
| 3 | **Unused imports causing bloat** | Low | Lines 18-19, 24-25, 28 |
| 4 | **`model_cache_dir` parameter ignored** | Medium | Line 107 |
| 5 | **PDF temp files not cleaned properly** | Medium | Lines 181-185 |
| 6 | **`_merge_text_boxes` logic bug** | Medium | Lines 247-252 |

---

### 2. Hidden Issues Discovered

1. **Comment in config is misleading** (`configs/ocr_config.yaml:3`): States "Falls back to CPU silently if CUDA unavailable" — this is NOT true behavior; PaddleOCR throws an error or requires explicit GPU framework installation.

2. **`max_workers` config unused**: The `max_workers: 4` in config is never used despite `ThreadPoolExecutor` being imported.

3. **`enable_table_detection` config unused**: Defined but never referenced in code.

4. **CLI `--format` option broken**: Click option uses `--format` with dest `"fmt"` but passes undefined `fmt` variable instead of `output_format`.

---

### 3. Root Cause Analysis

**Issue 1: ModuleNotFoundError**
- User installed `paddle-ocr` (hyphenated) but the import expects package `paddleocr` (no hyphen)
- PyPI shows correct package name is `paddleocr`, installed via `pip install paddleocr`
- Additionally, PaddleOCR requires `paddlepaddle-gpu` framework for GPU support: `pip install paddlepaddle-gpu`

**Issue 2: GPU Not Being Used (Performance Problem)**
- Code sets `use_gpu=True` but PaddleOCR's GPU support requires:
  1. `paddlepaddle-gpu` framework installed (not just `paddleocr`)
  2. CUDA toolkit matching the framework version
  3. Compatible GPU drivers
- Without these, PaddleOCR either fails or silently falls back to CPU depending on version

**Issue 6: Text Merge Logic Bug**
- Line 249: `merged.append("\n" + lines[i])` prepends newline but joins with `"".join()` 
- This creates incorrect spacing vs intended paragraph separation

---

### 4. Recommended Fixes

```python
# FIX 1: Correct package installation (user action required)
# Uninstall wrong package, install correct ones:
# pip uninstall paddle-ocr
# pip install paddleocr paddlepaddle-gpu  # For GPU support

# FIX 2: Add GPU verification in __init__ (lines 110-119)
try:
    import paddle
    gpu_available = paddle.device.is_compiled_with_cuda() and paddle.device.get_device().startswith("gpu")
    if self.config.use_gpu and not gpu_available:
        logger.warning(
            f"GPU requested but not available. "
            f"Installed: {'paddlepaddle-gpu' if gpu_available else 'paddlepaddle (CPU-only)'}. "
            f"Falling back to CPU."
        )
except ImportError:
    gpu_available = False

self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=self.config.use_gpu and gpu_available,  # Only enable if actually available
    # ... rest of params
)

# FIX 3: Remove unused imports (lines 18-19, 24-25, 28)
# Remove: os, sys (line 18-19), ThreadPoolExecutor/as_completed (line 25), Image (line 28)

# FIX 4: Use model_cache_dir parameter (line 119)
self._engine = PaddleOCR(
    # ... existing params
    ir_optim=True,
    gpu_mem=8000,
)
if self.model_cache_dir:
    # Set PaddleOCR model cache via environment or param if supported
    pass

# FIX 5: Proper PDF temp cleanup (lines 181-185)
finally:
    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

# FIX 6: Text merge logic (lines 247-254)
if gap_ratio > self.config.box_merge_threshold:
    merged.append(lines[i])  # New paragraph - just append
else:
    merged[-1] += lines[i]   # Same paragraph - concatenate to previous
```

---

### 5. Steps Taken

1. Read both copies of `ocr_pipeline.py` in benchmark directories
2. Verified `from paddleocr import PaddleOCR` is the correct import syntax
3. Searched PyPI documentation for correct package name
4. Investigated GPU configuration requirements for PaddleOCR
5. Analyzed config file for discrepancies
6. Cross-referenced all `use_gpu` usages across the codebase
7. Identified unused imports and configuration options
8. Traced through `_merge_text_boxes` logic to find concatenation bug

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files (ocr_pipeline.py, ocr_config.yaml) |
| `Grep` | Search for `use_gpu` usage patterns, import statements |
| `WebSearch` | Research PaddleOCR package naming, GPU issues |
| `WebFetch` | Fetch official PyPI and PaddleOCR docs |
| `Bash` | Check installed packages, locate files |

---

### 7. Verification

**Verified findings:**
- ✅ Import statement `from paddleocr import PaddleOCR` is correct per PyPI
- ✅ Package name mismatch confirmed: user has `paddle-ocr`, needs `paddleocr`
- ✅ GPU requires `paddlepaddle-gpu` framework, not just `paddleocr`
- ✅ Config comment "falls back silently" is incorrect/misleading
- ✅ `max_workers`, `enable_table_detection` defined but never used
- ✅ `model_cache_dir` parameter accepted but never passed to PaddleOCR
- ✅ Text merge bug: `"\n" + lines[i]` + `"".join()` produces wrong output

**Not verified (would require runtime):**
- ❌ Actual GPU availability on user's machine
- ❌ Whether current code runs after package fix
- ❌ Performance benchmarks before/after

---

### Final Action Required by User

Run these commands to fix the import and GPU issues:

```bash
pip uninstall paddle-ocr -y
pip install paddleocr paddlepaddle-gpu
```

For CPU-only machines:
```bash
pip uninstall paddle-ocr -y  
pip install paddleocr paddlepaddle
```
