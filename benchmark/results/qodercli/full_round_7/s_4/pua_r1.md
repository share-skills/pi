# Scenario 4: API Server Response Format Mismatch
## Condition: pua | Run: 1
## Duration: 139.47s

---

## Investigation Summary

**File analyzed:** `nopua/benchmark/test-project/src/inference/api_server.py`

### Key Findings

The OpenAI SDK `ValidationError` is caused primarily by the **`created` field type mismatch**. The code generates ISO 8601 datetime strings, but OpenAI requires Unix timestamp integers.

### Critical Issues (Must Fix)

1. **`created: str` → `created: int`** — Lines 97, 200, 284
2. **Missing `usage` field** — Line 89-99 model definition
3. **Streaming chunk ID changes per chunk** — Line 282 should reuse same ID
4. **Missing role delta in first streaming chunk** — Line 286-296
5. **`finish_reason` type too strict** — Line 86 should be `Optional[str]`

### Hidden Issues Found

- API key logged in plain text (security risk)
- No authentication enforcement on endpoints
- Stream error messages leak internal details
- No validation of vLLM backend response structure

All findings verified against source code and OpenAI API documentation patterns.
