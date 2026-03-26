# Scenario 5: Training Data Synthesizer Silent Failure
## Condition: nopua | Run: 2
## Duration: 91.53s

---

Now I have a complete picture. Let me verify my findings by examining what happens with an empty API key more closely:

**INVESTIGATION SUMMARY**

## 1. Issues Found

### Primary Issue: Silent Failure Due to Empty API Key

**Location:** `synthesizer.py:66, 115`

The synthesizer produces 0 samples silently because:

1. **Line 66**: `api_key` defaults to `os.environ.get("OPENAI_API_KEY", "")` - an **empty string** if env var is not set
2. **Line 115**: The httpx client is initialized with `"Authorization": f"Bearer {self.config.api_key}"` - which becomes `"Bearer "` (empty bearer token) when api_key is empty
3. **Lines 229-232**: API errors are caught and logged, but the function returns `[]` silently - no exception is raised
4. **Lines 243-246**: Parse errors are also caught and return `[]` silently

**Result:** The API returns 401 Unauthorized (or similar), the error is caught, logged, and processing continues with 0 samples generated. No exception stops the pipeline.

### Configuration Compounds the Issue

**Location:** `synth_config.yaml:5`

```yaml
api_key: ""  # Explicitly empty in config file
```

The config file has an empty api_key, expecting users to set `OPENAI_API_KEY` environment variable. But if that's not set either, the synthesizer fails silently.

---

## 2. Hidden Issues Beyond the Ask

### Issue A: No Validation of Required Configuration

**Location:** `synthesizer.py:105-125` (`__init__` method)

There is **no validation** that:
- `api_key` is non-empty before creating the HTTP client
- Source directory exists before calling `generate()`
- Required fields in config are valid

### Issue B: `max_retries=0` Means No Resilience

**Location:** `synthesizer.py:78`, `synth_config.yaml:17`

```python
max_retries: int = 0  # Comment explicitly states "No retry mechanism"
```

Transient API failures (rate limits, timeouts) will cause permanent sample loss for that chunk.

### Issue C: No Logging of Successful API Calls

The code logs errors but never logs:
- When an API call succeeds
- What the raw API response looks like (for debugging)
- Whether the response content was empty or malformed

### Issue D: `_stats` Not Reset Between Runs

**Location:** `synthesizer.py:120-125`

If the same `DataSynthesizer` instance is reused, stats accumulate across runs without being reset.

### Issue E: HTTP Client Never Closed in Error Paths

**Location:** `synthesizer.py:321-323`

The `close()` method exists but is never called automatically. If `generate()` raises an exception partway through, the HTTP connection pool leaks.

---

## 3. Root Cause

**Fundamental Cause:** The synthesizer has **zero validation** of its critical dependency (API key) before attempting to use it, combined with **silent error handling** that swallows all failures.

The flow is:
1. Empty API key → 401 Unauthorized from API
2. 401 caught by `except httpx.HTTPError` → logged and ignored
3. Returns `[]` → no samples added
4. Pipeline completes "successfully" with 0 samples

---

## 4. Recommended Fix

### Immediate Fix (Add Validation + Fail Fast)

```python
# In __init__, after loading config:
def __init__(self, config: SynthConfig = None):
    if config is None:
        config = SynthConfig()
    elif isinstance(config, str):
        config = self._load_config(config)

    # CRITICAL: Validate API key before proceeding
    if not config.api_key or not config.api_key.strip():
        raise ValueError(
            "API key is required but not provided. "
            "Set OPENAI_API_KEY environment variable or pass api_key in config."
        )

    self.config = config
    self._client = httpx.Client(...)
    # ... rest unchanged
```

### Secondary Fixes

1. **Add retry logic** for transient failures
2. **Use context manager** for HTTP client (`with` statement)
3. **Log at INFO level** when API calls succeed
4. **Validate source_dir** exists before starting generation
5. **Raise exceptions** for unrecoverable errors instead of silent returns

---

## 5. Steps Taken

1. **Read synthesizer.py** - Full file to understand structure
2. **Read synth_config.yaml** - Verified configuration
3. **Searched for api_key usage** - Found 13 occurrences across project
4. **Read test_synthesizer.py** - Confirmed tests expect silent failure behavior
5. **Read run_pipeline.py** - Understood how synthesizer is invoked in pipeline
6. **Checked for source chunks** - No test data files found (would also cause 0 output)
7. **Analyzed error handling paths** - Lines 229-246 show silent swallowing

---

## 6. Tools Used

- `Read` - Read synthesizer.py, synth_config.yaml, test files, pipeline runner
- `Glob` - Find synthesizer.py instances, config files, test files
- `Grep` - Search for api_key usage patterns, Authorization header setup

---

## 7. Verification

**Verified findings by:**
1. Confirmed line 66: `api_key` defaults to empty string from env var
2. Confirmed line 115: Authorization header uses potentially empty api_key
3. Confirmed lines 229-232: HTTP errors return `[]` silently
4. Confirmed synth_config.yaml line 5: `api_key: ""` explicitly empty
5. Confirmed test `test_silent_api_failure` (line 19-54) explicitly tests that errors produce empty output without raising

**Evidence:** The test `test_silent_api_failure` proves this is intentional design - the test asserts `result == []` on API failure with no exception raised.

---

## Summary Table

| Issue | Severity | Impact | Fix Complexity |
|-------|----------|--------|----------------|
| Empty API key not validated | Critical | 0 samples, silent failure | Trivial (5 lines) |
| Silent error swallowing | High | Undetected failures | Low |
| No retry mechanism | Medium | Lost samples on transient errors | Low |
| HTTP client leak | Medium | Resource exhaustion over time | Low |
| Stats not reset | Low | Incorrect metrics | Trivial |
