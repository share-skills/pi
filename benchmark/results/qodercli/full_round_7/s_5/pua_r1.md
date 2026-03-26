# Scenario 5: Training Data Synthesizer Silent Failure
## Condition: pua | Run: 1
## Duration: 117.12s

---

Now I have all the evidence I need. Let me compile my comprehensive analysis:

---

## Investigation Complete

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| **1** | **Empty API key causes silent API authentication failure** | Critical | `synthesizer.py:66`, `synth_config.yaml:5` |
| **2** | **API errors are silently swallowed, returning empty list** | High | `synthesizer.py:229-232` |
| **3** | **No pre-flight validation of API key before processing** | High | `synthesizer.py:133-174` |
| **4** | **YAML config empty string overrides environment variable default** | Medium | `synthesizer.py:127-131` |

### 2. Hidden Issues (Beyond the Ask)

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| **H1** | **No retry mechanism** (`max_retries=0`) - transient failures cause permanent data loss | High | `synthesizer.py:78`, `synth_config.yaml:17` |
| **H2** | **`chunks_processed` stat only incremented on success** - masks actual processing count | Medium | `synthesizer.py:239` |
| **H3** | **Empty output file written even when all samples fail** - no indication of failure | Medium | `synthesizer.py:306-315` |
| **H4** | **Config loading from YAML doesn't fallback to env var when api_key is empty string** | Medium | `synthesizer.py:127-131` |

### 3. Root Cause Analysis

**Primary Root Cause:**
The synthesizer produces 0 samples because:

1. **Config file has empty API key**: `configs/synth_config.yaml:5` sets `api_key: ""`
2. **Environment variable not set**: Confirmed `OPENAI_API_KEY` is NOT set in current environment
3. **Default fallback is also empty**: Line 66 defaults to `os.environ.get("OPENAI_API_KEY", "")` which returns `""` when unset
4. **API calls fail with 401 Unauthorized**: Empty API key causes authentication failure
5. **Failures are silently caught**: Lines 229-232 catch `httpx.HTTPError` and return `[]` without raising
6. **Empty results are saved**: `_save_results()` writes an empty file with no warning

**Code Flow:**
```
generate() → _read_source_chunks() → finds test.txt ✓
           → _generate_from_chunk() → API POST with empty Bearer token
           → response.raise_for_status() raises HTTPError (401)
           → except block catches, logs error, returns []
           → all_samples = [] (extended with empty lists)
           → _save_results([]) → writes 0-byte file
```

### 4. Recommended Fix

**Immediate Fix (Priority 1):**
```python
# synthesizer.py: Add pre-flight validation at line 133
def generate(self, source_dir: Optional[str] = None,
             output_path: Optional[str] = None) -> List[Dict]:
    source_dir = source_dir or self.config.source_dir
    output_path = output_path or self.config.output_path

    # CRITICAL: Validate API key before processing
    if not self.config.api_key or not self.config.api_key.strip():
        raise ValueError(
            "API key is empty. Set OPENAI_API_KEY environment variable "
            "or provide api_key in config. Cannot proceed without valid authentication."
        )
```

**Secondary Fix (Priority 2):**
```yaml
# synth_config.yaml: Remove hardcoded empty api_key
synthesis:
  api_base_url: https://api.openai.com/v1
  # api_key: ""  ← DELETE THIS LINE - let it fall back to env var
  model: gpt-4
```

**Tertiary Fix (Priority 3 - Robustness):**
```python
# synthesizer.py:66 - Change default to None for explicit failure
api_key: str = os.environ.get("OPENAI_API_KEY") or ""

# synthesizer.py:127-131 - Don't override env var with empty string
def _load_config(self, config_path: str) -> SynthConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    synth_data = data.get("synthesis", data)
    # Preserve env var if YAML has empty api_key
    if synth_data.get("api_key") == "":
        synth_data["api_key"] = os.environ.get("OPENAI_API_KEY", "")
    
    return SynthConfig(**synth_data)
```

### 5. Steps Taken

1. **Read source code**: Full `synthesizer.py` (324 lines) analyzed
2. **Read config file**: `synth_config.yaml` examined
3. **Verified file system**: Confirmed `data/chunks/test.txt` exists (78 bytes), `data/output.jsonl` is empty (0 bytes)
4. **Checked environment**: Verified `OPENAI_API_KEY` is NOT set
5. **Tested config loading**: Python reproduction confirmed YAML empty string overrides env var default
6. **Reviewed test suite**: `test_synthesizer.py` confirms this is known behavior (test `test_silent_api_failure`)
7. **Analyzed pipeline script**: `run_pipeline.py:98-105` shows synthesis stage calls without validation
8. **Checked iteration logs**: Round 6 log shows S6 scenario had API timeout issues (infrastructure)

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read synthesizer.py, synth_config.yaml, test files, pipeline scripts |
| `Glob` | Locate synthesizer files, config files, output files |
| `Grep` | Search for API key usage patterns across codebase |
| `Bash` | Verify file sizes, check environment variables, run Python tests |

### 7. Verification Evidence

**Confirmed Silent Failure:**
```bash
$ cat data/output.jsonl
# (empty - 0 bytes)

$ echo "OPENAI_API_KEY is set: $([ -n "$OPENAI_API_KEY" ] && echo 'YES' || echo 'NO')"
OPENAI_API_KEY is set: NO
```

**Confirmed Config Issue:**
```python
>>> yaml_data = {'api_key': ''}
>>> SynthConfig(**yaml_data).api_key
''  # Empty string, not env var fallback
```

**Confirmed Error Handling Behavior:**
Lines 229-232 catch ALL `httpx.HTTPError` exceptions and return `[]`:
```python
except httpx.HTTPError as e:
    logger.error(f"API request failed: {e}")
    self._stats["api_errors"] += 1
    return []  # ← Silent failure - no exception raised
```

This means `generate()` returns `[]` on API failure, and `_save_results([])` writes an empty file with no error indication to the user.
