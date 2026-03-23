# Scenario 5: Training Data Synthesizer Silent Failure
## Condition: nopua | Run: 1
## Duration: 239.64s

---

Now I have a complete understanding of the issue. Let me provide the structured summary:

---

## Investigation Summary

### 1. Issues Found

**Primary Issue: Missing Source Data Directory**

The synthesizer produces 0 training samples because the **source directory does not exist**:

- Config file (`configs/synth_config.yaml:20`) specifies: `source_dir: ./data/chunks`
- The `data/` directory **does not exist** in the project root
- When `_read_source_chunks()` is called, it logs an error and returns `[]`
- With no chunks to process, the main loop never executes
- Result: 0 samples generated, but no visible error (just a warning log)

**Code flow:**
```python
# synthesizer.py:148-151
chunks = self._read_source_chunks(source_dir)
if not chunks:
    logger.warning(f"No source chunks found in {source_dir}")
    return []  # ← Silent exit, no exception
```

### 2. Hidden Issues Discovered

**Issue A: Silent Failure on API Errors**
- `_generate_from_chunk()` catches all HTTP errors and returns `[]` silently (line 229-232)
- No exception is raised, just a logged error
- Combined with `max_retries: 0`, any API failure means permanent silent loss of that chunk

**Issue B: No Retry Mechanism**
- `max_retries: 0` in config means zero retries on transient failures
- Common issues like rate limits (429), timeouts, or temporary network glitches cause permanent data loss

**Issue C: Validation May Filter All Results**
- `_validate_sample()` requires both `instruction` and `output` fields
- Minimum response length is 50 characters
- If the LLM returns malformed JSON or short responses, all samples get filtered to `[]`

**Issue D: Path Resolution Ambiguity**
- Default paths are relative (`./data/chunks`, `./data/synthetic_training.jsonl`)
- Behavior depends on current working directory when script runs
- This creates inconsistent behavior between local runs, CI, and production

### 3. Root Cause

**Immediate root cause:** The `data/chunks/` directory referenced in the config does not exist.

**Systemic root cause:** The synthesizer is designed to fail silently:
1. Missing directory → returns `[]` with only a warning log
2. API errors → caught and logged, returns `[]` per chunk
3. Parse errors → caught and logged, returns `[]` per chunk
4. No exceptions propagate to alert the user

This design choice prioritizes "pipeline continues" over "fail fast with clear error."

### 4. Recommended Fix

**Immediate fix:**
```bash
# Create the missing directory and add source chunks
mkdir -p data/chunks
# Add your classical Chinese text files to data/chunks/
```

**Or update the config to point to existing data:**
```yaml
# configs/synth_config.yaml
synthesis:
  source_dir: /absolute/path/to/your/existing/chunks  # Use absolute path
```

**Long-term improvements:**
1. **Fail-fast mode**: Add a config option `fail_on_missing_source: true` that raises an exception instead of returning `[]`
2. **Pre-flight validation**: Check source directory exists before starting generation
3. **Absolute paths**: Use absolute paths in config or resolve relative to config file location
4. **Better error reporting**: Log at ERROR level when 0 samples are produced after claiming to process N chunks

### 5. Steps Taken

1. Read the synthesizer source code to understand the pipeline flow
2. Located and read the config file (`synth_config.yaml`)
3. Searched for `chunks` directory - found none exist
4. Verified `data/` directory doesn't exist in test-project
5. Traced code path: `generate()` → `_read_source_chunks()` → returns `[]` when dir missing
6. Reviewed test file to understand expected behavior and failure modes
7. Ran Python verification script to confirm path resolution behavior

### 6. Tools Used

- `Read` - Read synthesizer.py, synth_config.yaml, test_synthesizer.py, run_pipeline.py
- `Glob` - Searched for chunk files and config files
- `Bash` - Listed directories, tested path resolution
- `Grep` - Searched for references to synthesizer and source_dir

### 7. Verification

**Verified findings:**
```
Path("./data/chunks").exists() → False
```

The directory specified in config simply does not exist. The synthesizer handles this gracefully by:
1. Logging `ERROR: Source directory not found: ./data/chunks`
2. Returning empty list `[]`
3. Logging `WARNING: No source chunks found in ./data/chunks`
4. Completing with 0 samples

**Evidence from code** (`synthesizer.py:176-181`):
```python
def _read_source_chunks(self, source_dir: str) -> List[str]:
    source_path = Path(source_dir)
    if not source_path.exists():
        logger.error(f"Source directory not found: {source_dir}")
        return []  # ← Silent return, no exception
```
