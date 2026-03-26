# Scenario 4: API Server Response Format Mismatch
## Condition: nopua | Run: 1
## Duration: 108.18s

---

---

## Final Investigation Report

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | `created` field type wrong - using `str` (ISO format) instead of `int` (Unix timestamp) | Line 97 (model), Line 200 (usage) | **CRITICAL** |
| 2 | `usage` field missing from response model | Line 89-99 | **CRITICAL** |
| 3 | Streaming response `created` field also using ISO string | Line 284 | **CRITICAL** |

### 2. Hidden Issues Discovered

| # | Issue | Impact |
|---|-------|--------|
| 1 | vLLM `usage` info was not being extracted and passed to response | Token usage metrics lost |
| 2 | `datetime` import unused after fix | Minor cleanup needed |

### 3. Root Cause

The OpenAI API specification requires:
- `created`: **integer** Unix timestamp in seconds (e.g., `1711526400`)
- `usage`: **object** with `prompt_tokens`, `completion_tokens`, `total_tokens` (can be null but field must exist)

The code was using `datetime.now().isoformat()` which produces strings like `"2024-03-27T10:00:00"`, causing Pydantic `ValidationError` in the OpenAI SDK.

### 4. Recommended Fixes (Applied)

All fixes have been applied to `/Users/hepin/IdeaProjects/pi/nopua/benchmark/test-project/src/inference/api_server.py`:

1. **Line 97**: Changed `created: str` → `created: int`
2. **Line 100**: Added `usage: Optional[Dict[str, int]] = None`
3. **Lines 199-207**: Added usage extraction from vLLM response
4. **Line 296**: Fixed streaming `created` from `datetime.now().isoformat()` → `int(time.time())`

### 5. Steps Taken

1. Read the api_server.py source file
2. Searched for OpenAI API response format specifications
3. Identified the `created` field type mismatch (str vs int)
4. Identified missing `usage` field
5. Checked streaming endpoint for same issues
6. Applied all fixes
7. Verified syntax with `py_compile`

### 6. Tools Used

- `Read` - File reading
- `WebSearch` - OpenAI API spec research
- `Edit` - Code fixes
- `Bash` - Syntax verification

### 7. Verification

✅ **Syntax check passed**: `python3 -m py_compile src/inference/api_server.py` returns "Syntax OK"

The fixes ensure:
- `created` field now uses `int(time.time())` (Unix timestamp)
- `usage` field is included in responses (extracted from vLLM when available)
- Both non-streaming and streaming endpoints are fixed
