# Scenario 4: API Server Response Format Mismatch
## Condition: pua | Run: 2
## Duration: 357.68s

---

## Summary

The OpenAI SDK `ValidationError` is caused by **5 critical format mismatches**:

### Critical Issues (Cause ValidationError):
1. **`created` field is `str` instead of `int`** - Lines 97, 200, 284
2. **Missing `usage` field** - Not defined in `ChatCompletionResponse`
3. **Missing `system_fingerprint` field** - Not defined in `ChatCompletionResponse`

### Hidden Issues Found:
- **Tests validate wrong behavior** - `test_api_server.py:88` and `:99` assert incorrect types/fields
- **Missing `logprobs` support** - Required for full SDK compatibility
- **Message role should be Literal type** - Currently unrestricted `str`
- **Streaming delta incomplete** - Missing `role`, `tool_calls` fields

### Root Cause:
The response models were hand-crafted without referencing the actual OpenAI API specification, resulting in type mismatches and missing fields.

### Fix Priority:
1. Change `created: str` → `created: int` and use `int(time.time())`
2. Add `usage: Optional[CompletionUsage] = None` field
3. Add `system_fingerprint: Optional[str] = None` field
4. Update tests that validate incorrect behavior
