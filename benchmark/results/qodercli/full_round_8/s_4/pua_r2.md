# Scenario 4: API Server Response Format Mismatch
## Condition: pua | Run: 2
## Duration: 179.27s

---

## Summary

The OpenAI SDK `ValidationError` is caused by **5 critical format mismatches**:

### Critical Issues (Cause ValidationError)

1. **`finish_reason` not validated** - Code passes arbitrary values from vLLM; SDK only accepts: `"stop"`, `"length"`, `"tool_calls"`, `"content_filter"`, `"function_call"`

2. **`ChatMessage.role` unconstrained** - Should be `Literal["system", "user", "assistant", "tool", "developer"]`

3. **Streaming missing role announcement** - First chunk must have `delta: {role: "assistant"}` before content

4. **Streaming `finish_reason` can be null** - Should be omitted or valid Literal value

5. **Missing `object` in choice** - Streaming choices should include proper structure

### Hidden Issues Found

- **H1**: No authentication enforcement (security risk)
- **H2**: Missing `tool_calls` support (causes ValidationError if model uses tools)
- **H3**: Missing `refusal` field (newer SDK requirement)
- **H4**: Empty choices array not handled
- **H5**: No `logprobs` support

### Root Cause

The Pydantic models are oversimplified and don't match the strict Literal type constraints and required field structure of the official OpenAI SDK schema.
