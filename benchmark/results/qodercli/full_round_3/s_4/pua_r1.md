# Scenario 4: API Server Response Format Mismatch
## Condition: pua | Run: 1
## Duration: 64.15s

---

---

**Summary**: The primary issue causing `ValidationError` is the `created` field type mismatch (`str` vs `int`). The OpenAI SDK's Pydantic model expects an integer Unix timestamp, but the server returns an ISO format string. Secondary issue is the missing `usage` field which while sometimes optional, is expected by the SDK for token counting.
