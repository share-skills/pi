# Scenario 5: Training Data Synthesizer Silent Failure
## Condition: nopua | Run: 2
## Duration: 73.58s

---

Now I understand the issue. Let me trace through the code flow carefully:

## Investigation Summary

After systematically analyzing the `synthesizer.py` code, I've identified the root cause of the silent failure producing 0 training samples.

---

### 1. Issues Found

**Primary Issue: Validation Logic Bug in `_validate_sample()` (line 285-304)**

The validation logic at line 288-290 checks if `required_fields` exist and are non-empty AFTER stripping:

```python
for field_name in self.config.required_fields:
    if field_name not in item or not item[field_name].strip():
        return None
```

However, the config's `required_fields` default is `["instruction", "output"]`, but the LLM response parsing at line 256-275 may produce items that don't have these exact fields depending on how the LLM responds. The prompt asks for `"instruction"` and `"output"` but the LLM might return different field names or nested structures.

**Secondary Issue: Silent API Key Not Set**

Looking at `synth_config.yaml` line 5:
```yaml
api_key: ""
```

The API key is empty in the config file. The comment says "Set OPENAI_API_KEY environment variable instead" but if the env var isn't set either, the HTTP client will send requests with an empty Authorization header (`Bearer `), which will fail silently (caught at line 229-232, returns `[]`).

---

### 2. Hidden Issues

1. **No logging when samples are filtered out**: When `_validate_sample()` returns `None`, there's no log explaining why (too short? missing field?). This makes debugging impossible.

2. **`_parse_samples()` regex doesn't handle markdown variations**: The regex at line 265 `r"```json?\s*(.*?)```"` only matches lowercase ```json or ```. Many LLMs output ```JSON or other variations.

3. **API error swallowed completely**: Line 229-232 catches `httpx.HTTPError` but just logs and returns `[]`. No indication to the caller that ALL chunks failed vs some succeeded.

4. **No fallback if LLM returns non-JSON prose**: If the API returns text that's not JSON and not in code blocks, `_parse_samples()` returns empty list with no warning.

5. **`max_retries: 0` means transient failures kill everything**: Config explicitly sets no retries. A single 429/503 error means that chunk is lost forever.

---

### 3. Root Cause

The fundamental cause is **multiple silent failure points stacked together**:

1. **Empty API key** → API calls fail with 401 → caught silently → returns `[]` per chunk
2. **Even if API succeeds**, the LLM might return JSON with different field names than expected → validation fails → samples dropped silently
3. **No visibility** into which step failed because all errors are caught and suppressed

The most likely scenario given "logs show it starts generating but output file is empty":
- API key is empty/invalid → all API calls return 401 → `api_errors` counter increments but loop continues → 0 samples written

---

### 4. Recommended Fix

**Fix 1: Add validation logging**
```python
def _validate_sample(self, item: Dict, source_text: str) -> Optional[Dict]:
    for field_name in self.config.required_fields:
        if field_name not in item:
            logger.debug(f"Sample missing field '{field_name}': {item.keys()}")
            return None
        if not item[field_name].strip():
            logger.debug(f"Sample field '{field_name}' is empty")
            return None
    
    output_len = len(item.get("output", ""))
    if output_len < self.config.min_response_length:
        logger.debug(f"Sample output too short: {output_len} < {self.config.min_response_length}")
        return None
    if output_len > self.config.max_response_length:
        logger.debug(f"Sample output too long: {output_len} > {self.config.max_response_length}")
        return None
    # ... rest unchanged
```

**Fix 2: Check API key validity upfront**
```python
def __init__(self, config: SynthConfig = None):
    # ... existing config loading ...
    
    if not self.config.api_key:
        raise ValueError("API key is required. Set via config or OPENAI_API_KEY env var.")
    
    # ... rest of init
```

**Fix 3: Report final stats including parse errors**
```python
logger.info(
    f"Generation complete. "
    f"Chunks: {self._stats['chunks_processed']}, "
    f"Samples: {self._stats['samples_generated']}, "
    f"API Errors: {self._stats['api_errors']}, "
    f"Parse Errors: {self._stats['parse_errors']}"
)
```

---

### 5. Steps Taken

1. Read the full `synthesizer.py` source code
2. Examined `synth_config.yaml` configuration
3. Checked test chunk file (`test.txt`)
4. Reviewed test file to understand expected behavior
5. Searched for error handling patterns and stats tracking
6. Traced data flow: `_read_source_chunks()` → `_generate_from_chunk()` → `_parse_samples()` → `_validate_sample()`
7. Identified all silent failure points in the pipeline

---

### 6. Tools Used

- `Read` - Read synthesizer.py, synth_config.yaml, test files
- `Glob` - Located project files and configs
- `Grep` - Searched for error handling patterns, stats tracking, required_fields usage

---

### 7. Verification

**To verify this diagnosis:**

1. **Check if API key is set:**
   ```bash
   echo $OPENAI_API_KEY
   # Should not be empty
   ```

2. **Add debug logging and re-run:**
   ```python
   # In synthesizer.py, add after line 237:
   logger.info(f"API response content: {content[:200]}...")
   
   # Add after line 279:
   logger.info(f"Parsed {len(items)} items, validated {len(samples)} samples")
   ```

3. **Check the actual API response:**
   Run with a valid API key and inspect what the LLM actually returns vs what the parser expects.

4. **Verify stats output:**
   After running, check `get_stats()` output:
   ```python
   synth = DataSynthesizer(config)
   samples = synth.generate()
   print(synth.get_stats())
   # Will show: api_errors, parse_errors, chunks_processed, samples_generated
   ```

If `api_errors > 0`: API key/auth issue  
If `parse_errors > 0`: Response format issue  
If both are 0 but `samples_generated == 0`: Validation filtering issue
