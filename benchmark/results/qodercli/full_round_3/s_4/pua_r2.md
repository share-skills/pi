# Scenario 4: API Server Response Format Mismatch
## Condition: pua | Run: 2
## Duration: 211.0s

---

---

## Summary Report

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | `created` field type is `str` instead of `int` | Line 97 (model), Line 200, 284 (usage) | **CRITICAL** - Causes ValidationError |
| 2 | Missing `usage` field in response model | Line 89-107 | **CRITICAL** - Required by OpenAI SDK |
| 3 | Response creation doesn't extract usage from vLLM | Line 194-204 | HIGH - Usage data lost |
| 4 | Streaming response uses ISO timestamp | Line 284 | HIGH - Same type mismatch |
| 5 | Tests validated incorrect behavior | tests/test_api_server.py:71-99 | MEDIUM - Masked the bugs |

### 2. Hidden Issues Discovered

- **Test cases were asserting wrong behavior**: The existing tests at lines 71-99 explicitly validated that `created` should be a `str` and that `usage` should NOT exist - this is the opposite of OpenAI's spec
- **vLLM usage data not forwarded**: Even when vLLM returns token usage, it was being discarded

### 3. Root Cause

The response model was designed without verifying against the actual OpenAI SDK Pydantic schema. The developer assumed:
- `created` should be an ISO 8601 string (common in many APIs)
- `usage` was optional/not needed

When OpenAI SDK requires:
- `created: int` (Unix timestamp in seconds)
- `usage: Optional[UsageInfo]` (present in response schema)

### 4. Recommended Fix (APPLIED)

**Changes made to `api_server.py`:**

1. Added `UsageInfo` model (lines 89-93)
2. Changed `created: str` → `created: int` (line 104)
3. Added `usage: Optional[UsageInfo] = None` field (line 107)
4. Extract usage from vLLM response (lines 206-214)
5. Use `int(time.time())` instead of `datetime.now().isoformat()` (line 218)
6. Fixed streaming response timestamp (line 303)

**Changes made to `test_api_server.py`:**

1. Updated `test_created_field_type` to validate `int` type
2. Updated `test_response_fields` to expect `usage` field

### 5. Steps Taken

1. Searched OpenAI API documentation for exact response schema
2. Fetched OpenAI Python SDK source code to verify Pydantic model
3. Read the full `api_server.py` file (345 lines)
4. Identified all locations with the `created` field issue
5. Applied fixes to model definition and response creation
6. Fixed both non-streaming and streaming responses
7. Discovered and updated incorrect test cases
8. Ran all tests - 7/7 passed
9. Validated OpenAI SDK compatibility with explicit checks

### 6. Tools Used

- `WebSearch` - Find OpenAI API specification
- `WebFetch` - Fetch OpenAI SDK source schema
- `Read` - Read source files
- `Edit` - Apply fixes
- `Bash` - Run tests and validation
- `TodoWrite` - Track investigation progress

### 7. Verification

**Evidence of fix:**
```
============================== 7 passed in 0.54s ===============================

Test 1 - Response with all fields:
  created: 1774215183 (type: int)
  usage: prompt_tokens=10 completion_tokens=20 total_tokens=30

Test 2 PASSED: created field is int
Test 3 PASSED: usage field exists
Test 4 PASSED: response serializes correctly

=== All OpenAI compatibility checks PASSED ===
```
