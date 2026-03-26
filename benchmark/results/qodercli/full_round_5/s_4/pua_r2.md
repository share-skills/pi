# Scenario 4: API Server Response Format Mismatch
## Condition: pua | Run: 2
## Duration: 117.42s

---

## Summary

**Primary Issue**: The OpenAI Python SDK throws `ValidationError` because:
1. `created` field is defined as `str` and populated with ISO 8601 strings instead of integer Unix timestamps
2. Missing `usage` field declaration in the response model

**Fix Priority**:
- **P0**: Fix `created` type from `str` → `int` (lines 97, 200, 284)
- **P1**: Add `usage: Optional[UsageInfo] = None` field (line 89-99)
- **P2**: Security fixes (API key logging, CORS, authentication)
- **P3**: Resource cleanup (httpx client shutdown handler)
