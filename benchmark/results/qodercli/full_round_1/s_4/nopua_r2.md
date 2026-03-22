# Scenario 4: API Server Response Format Mismatch
## Condition: nopua | Run: 2
## Duration: 169.34s

---

---

## Summary

**Primary causes of ValidationError:**

1. **`created: str` should be `created: int`** - The OpenAI SDK expects a Unix timestamp (integer), but the code sends an ISO datetime string
2. **Missing `usage` field** - The response model doesn't include token usage statistics that the SDK expects

**Secondary issues:**

3. Streaming chunks have the same `created` type issue
4. Streaming delta doesn't include `role: assistant` in the first chunk
5. `finish_reason` should be a proper Literal type

**Fix priority:** Fix items 1 and 2 first - these are the direct causes of the ValidationError.
