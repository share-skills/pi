# Scenario 5: Training Data Synthesizer Silent Failure
## Condition: pua | Run: 2
## Duration: 78.25s

---

Now I have a complete picture. Let me provide the structured summary:

---

## Investigation Complete

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Empty API key in config overrides environment variable** | CRITICAL | `synthesizer.py:66,131`, `synth_config.yaml:5` |
| 2 | **Silent API error handling** - returns `[]` without raising | CRITICAL | `synthesizer.py:229-232` |
| 3 | **Silent parse failures** - malformed JSON not tracked in stats | HIGH | `synthesizer.py:256-275` |
| 4 | **Over-aggressive validation** - `min_response_length=50` filters valid Chinese Q&A | HIGH | `synthesizer.py:285-297` |
| 5 | **HTTP client resource leak** - `close()` never called automatically | LOW | `synthesizer.py:321-323` |

### 2. Hidden Issues Discovered

| # | Hidden Issue | Impact |
|---|--------------|--------|
| H1 | **Validation failures not tracked** - no counter for samples rejected by `_validate_sample()` | Zero visibility into why samples are discarded |
| H2 | **`max_retries` config ignored** - defined but no retry logic exists | Transient API failures cause permanent sample loss |
| H3 | **Regex imported inside method** - `import re` on every parse failure (line 264) | Minor inefficiency |
| H4 | **Timeout hardcoded** - 60s timeout not configurable (line 118) | Inflexible for varying API latencies |

### 3. Root Cause

The synthesizer exhibits a **"pyramid of silence"**:

```
Empty api_key in YAML → 401 Unauthorized 
    ↓ (caught silently, line 229-232)
Returns [] from _generate_from_chunk()
    ↓ (extended to all_samples, line 158)
Empty list saved to output file
    ↓ (no exception ever propagates)
User sees: "Completed" with 0 samples
```

**Why config breaks env var**: Python dataclass defaults only apply when fields are omitted. Loading `api_key: ""` from YAML explicitly passes empty string to constructor, overriding the default `os.environ.get("OPENAI_API_KEY", "")`.

### 4. Recommended Fixes (Priority Order)

**P0 - Fix API Key Loading** (`synthesizer.py:127-131`):
```python
def _load_config(self, config_path: str) -> SynthConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    config_data = data.get("synthesis", data)
    
    # Don't let empty string override environment
    if config_data.get("api_key") == "":
        config_data["api_key"] = os.environ.get("OPENAI_API_KEY", "")
    
    return SynthConfig(**config_data)
```

**P0 - Raise on API Error** (`synthesizer.py:229-232`):
```python
except httpx.HTTPError as e:
    logger.error(f"API request failed: {e}")
    self._stats["api_errors"] += 1
    raise RuntimeError(f"API request failed: {e}") from e  # FAIL FAST
```

**P1 - Track Parse/Validation Failures**:
- Add `parse_failures` and `validation_failures` counters
- Log when LLM returns unparseable content

**P2 - Reduce Validation Aggressiveness**:
- Lower `min_response_length` from 50 to 20 for CJK text
- Or add language-aware detection

### 5. Steps Taken

1. Read `synthesizer.py` source code (324 lines)
2. Read `synth_config.yaml` configuration
3. Searched project structure for data directories
4. Reviewed existing test files (`test_synthesizer.py`, `test_synthesizer_issues.py`)
5. Ran verification script confirming all 5 major issues
6. Ran parse debug script confirming parse failures aren't tracked

### 6. Tools Used

| Tool | Usage |
|------|-------|
| `Read` | Source code, config, test files |
| `Glob` | File discovery (synthesizer.py, configs) |
| `Grep` | Pattern search across codebase |
| `Bash` | Executed verification scripts |

### 7. Verification

**All findings verified with automated tests:**

```
Issue 1 (Empty API Key):     BUG CONFIRMED
Issue 2 (Silent API Error):  BUG CONFIRMED  
Issue 3 (Silent Parse):      CONFIRMED (not tracked in stats)
Issue 4 (Over-validation):   BUG CONFIRMED
Issue 5 (Resource Leak):     POTENTIAL ISSUE CONFIRMED

Hidden Issues:
- Validation failures: 0 counters exist
- max_retries: unused in codebase
- import re inside method: confirmed line 264
```

**Evidence**: Test output shows:
- Empty config `api_key` overrides env var
- API errors caught, logged, return `[]` silently
- Parse failures produce `[]` with no stats increment
- 9-character Chinese responses filtered by 50-char minimum
