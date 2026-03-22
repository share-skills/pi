# Scenario 4: API Server Response Format Mismatch
## Condition: nopua | Run: 1
## Duration: 84.85s

---

---

## Summary Table

| Category | Count |
|----------|-------|
| **Critical Issues** | 4 |
| **Hidden Issues** | 4 |
| **Total Issues** | 8 |

The primary cause of `ValidationError` is the **`created` field type mismatch** (string vs integer) and **missing `usage` field**. These two issues alone will cause the OpenAI SDK's Pydantic validator to reject the response.
