# Scenario 5: Training Data Synthesizer Silent Failure
## Condition: pi | Run: 2
## Duration: 87.56s

---

## 1. Issues Found

| # | Issue | Location |
|---|-------|----------|
| 1 | **Silent failure on API errors** - HTTP errors caught and logged but processing continues silently, returning empty list | `synthesizer.py:229-232` |
| 2 | **Silent failure on parse errors** - JSON parsing failures caught and logged but processing continues silently, returning empty list | `synthesizer.py:243-246` |
| 3 | **No source chunks found** - Default `source_dir: ./data/chunks` likely doesn't exist or contains no `.txt`/`.jsonl` files | `synthesizer.py:81`, `synthesizer.py:176-197` |
| 4 | **Overly strict validation filtering all samples** - `min_response_length: 50` may filter out valid short responses; validation returns `None` silently without logging | `synthesizer.py:285-304` |
| 5 | **Empty API key in config** - Config file has `api_key: ""` instead of reading from environment | `synth_config.yaml:5` |

---

## 2. Hidden Issues

| # | Issue | Category | Location |
|---|-------|----------|----------|
| 1 | **Unused import** - `Any` imported from typing but never used | Code Quality | `synthesizer.py:28` |
| 2 | **Missing error logging for validation failures** - `_validate_sample` returns `None` silently when samples fail validation; no count tracked in stats | Observability | `synthesizer.py:285-304` |
| 3 | **No retry mechanism** - `max_retries: 0` hardcoded; transient API failures cause permanent sample loss | Reliability | `synth_config.yaml:17`, `synthesizer.py:78` |
| 4 | **Stats not tracking validation failures** - No counter for samples filtered out by validation | Observability | `synthesizer.py:120-125` |
| 5 | **Resource leak risk** - `close()` method exists but never called automatically; no context manager support | Resource Management | `synthesizer.py:321-323` |
| 6 | **Regex import inside method** - `import re` inside `_parse_samples` instead of at module level | Code Quality | `synthesizer.py:264` |
| 7 | **Hardcoded prompt language** - Prompts only support Traditional Chinese; no i18n support | Extensibility | `synthesizer.py:40-58` |
| 8 | **No timeout configuration** - HTTP client timeout hardcoded to 60s; not configurable | Configurability | `synthesizer.py:118` |

---

## 3. Root Cause

**Primary root cause (line 176-197):** The synthesizer reads source chunks from `./data/chunks` directory, but this directory either:
- Does not exist (returns empty list at line 180-181)
- Contains no `.txt` or `.jsonl` files (returns empty list at line 197)

When `chunks` is empty, the warning is logged at line 150 and an empty list is returned at line 151, resulting in zero training samples.

**Secondary root cause (lines 229-246):** Even if source chunks exist, API errors or parse failures silently return empty lists per-chunk without stopping the pipeline, making failures hard to detect.

**Tertiary root cause (lines 285-304):** The validation logic filters out samples that don't meet length requirements without logging, so even successfully generated samples may be discarded silently.

---

## 4. Recommended Fix

### Fix 1: Add source directory existence check with better error reporting

```python
# Before (line 176-181):
def _read_source_chunks(self, source_dir: str) -> List[str]:
    """Read text chunks from source directory."""
    source_path = Path(source_dir)
    if not source_path.exists():
        logger.error(f"Source directory not found: {source_dir}")
        return []

# After:
def _read_source_chunks(self, source_dir: str) -> List[str]:
    """Read text chunks from source directory."""
    source_path = Path(source_dir)
    if not source_path.exists():
        logger.error(f"Source directory not found: {source_dir}")
        logger.error(f"Please create the directory and add .txt or .jsonl files")
        raise FileNotFoundError(f"Source directory not found: {source_dir}")
    
    # Check if directory contains any valid files
    txt_files = list(source_path.glob("*.txt"))
    jsonl_files = list(source_path.glob("*.jsonl"))
    if not txt_files and not jsonl_files:
        logger.error(f"No .txt or .jsonl files found in {source_dir}")
        logger.error(f"Available files: {list(source_path.iterdir())}")
        raise ValueError(f"No valid source files in {source_dir}")
```

### Fix 2: Add validation failure logging and stats tracking

```python
# Before (line 120-125):
self._stats = {
    "chunks_processed": 0,
    "samples_generated": 0,
    "api_errors": 0,
    "parse_errors": 0,
}

# After:
self._stats = {
    "chunks_processed": 0,
    "samples_generated": 0,
    "api_errors": 0,
    "parse_errors": 0,
    "validation_failures": 0,  # Track filtered samples
}
```

```python
# Before (line 277-283):
# Validate and format samples
for item in items:
    sample = self._validate_sample(item, source_text)
    if sample:
        samples.append(sample)

return samples

# After:
# Validate and format samples
for item in items:
    sample = self._validate_sample(item, source_text)
    if sample:
        samples.append(sample)
    else:
        self._stats["validation_failures"] += 1
        logger.debug(f"Sample failed validation: {item.get('instruction', 'N/A')[:50]}")

if not samples and items:
    logger.warning(f"All {len(items)} samples from chunk failed validation")

return samples
```

### Fix 3: Raise exception on critical failures instead of silent return

```python
# Before (line 229-232):
except httpx.HTTPError as e:
    logger.error(f"API request failed: {e}")
    self._stats["api_errors"] += 1
    return []

# After:
except httpx.HTTPError as e:
    logger.error(f"API request failed: {e}")
    self._stats["api_errors"] += 1
    if self.config.max_retries == 0:
        raise  # Re-raise to make failure visible
    return []
```

### Fix 4: Move import to module level and add unused import cleanup

```python
# Before (line 23-29):
import os
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

# After (remove 'Any' if unused):
import os
import json
import re  # Moved to top level
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
```

Then remove line 264: `import re` from inside `_parse_samples`.

---

## 5. Steps Taken

1. **Read synthesizer.py** - Analyzed full code flow from `generate()` → `_read_source_chunks()` → `_generate_from_chunk()` → `_parse_samples()` → `_validate_sample()`
2. **Identified 4 return [] points** - Lines 151, 181, 232, 246 where empty results silently terminate processing
3. **Read synth_config.yaml** - Found empty `api_key: ""` and `max_retries: 0` configuration issues
4. **Searched for source chunks** - No `chunks/` or `data/chunks/` directories exist in project
5. **Read test_synthesizer.py** - Confirmed silent failure behavior is documented feature (test at line 19-54)
6. **Grep for similar patterns** - Found same silent failure pattern in `ocr_pipeline.py:184` and `model_loader.py:84`
7. **Analyzed validation logic** - Identified that `_validate_sample()` filters without logging (lines 285-304)
8. **Checked stats tracking** - No counter for validation failures, making root cause invisible

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read synthesizer.py (324 lines), synth_config.yaml (29 lines), test_synthesizer.py (112 lines) |
| `Glob` | Search for synthesizer files, config files, chunks directories |
| `Grep` | Find `return []` patterns, logger calls, validation logic, similar silent failures |
| `Bash` | Find data/chunks directories in project tree |

---

## 7. Verification

### Verify the fix works:

```bash
# 1. Create test source directory
mkdir -p data/test-project/data/chunks
echo "子曰：學而時習之，不亦說乎？" > data/test-project/data/chunks/test_chunk.txt

# 2. Run synthesizer with verbose logging
cd data/test-project
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from src.data_engineering.synthesizer import DataSynthesizer, SynthConfig

config = SynthConfig(
    source_dir='./data/chunks',
    output_path='./data/test_output.jsonl',
    samples_per_chunk=2,
)
synth = DataSynthesizer(config)
result = synth.generate()
print(f'Generated {len(result)} samples')
print(f'Stats: {synth.get_stats()}')
"

# 3. Check output file
cat data/test-project/data/test_output.jsonl

# Expected: Either samples generated OR clear error message about what failed
```

### Expected outcomes after fix:

| Scenario | Before | After |
|----------|--------|-------|
| Missing source dir | Returns `[]`, logs warning | Raises `FileNotFoundError` with helpful message |
| API failure | Returns `[]`, logs error, continues | Raises exception (if max_retries=0) |
| All samples filtered | Returns `[]`, no explanation | Logs which samples failed + why |
| Success | Returns samples | Returns samples + detailed stats |
