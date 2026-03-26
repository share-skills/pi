# Scenario 4: API Server Response Format Mismatch
## Condition: pua | Run: 1
## Duration: 170.57s

---

Investigation complete. The API server has **8 format mismatches** that cause OpenAI SDK `ValidationError`:

## Quick Reference: Issues & Fixes

| # | Issue | Fix |
|---|-------|-----|
| 1 | `finish_reason: str` should be `Literal[...]` | Add type + normalization function |
| 2 | Streaming delta missing `role: "assistant"` | Add role on first chunk |
| 3 | Streaming `finish_reason` always present | Only include when non-null |
| 4 | `content: str` should be `Optional[str]` | Change field type |
| 5 | Chunk ID regenerated per chunk | Generate once, reuse |
| 6 | vLLM finish_reason not normalized | Add mapping function |
| 7 | Missing `system_fingerprint` | Add optional field |
| 8 | Empty choices not validated | Add validation |

The two **CRITICAL** issues (#1 and #2) are sufficient to cause the reported `ValidationError` from the OpenAI SDK.
