# Scenario 4: API Server Response Format Mismatch
## Condition: pua | Run: 1
## Duration: 211.3s

---

## Summary

**6 primary issues** and **5 hidden issues** were identified in the API server's response format that cause OpenAI SDK `ValidationError`:

### Critical Issues (cause ValidationError):
1. **`finish_reason` defaults to `"stop"`** — Should be `Optional[str]` allowing `null`
2. **Missing `logprobs` field** — Required by OpenAI SDK schema
3. **Streaming missing `role: "assistant"` in first chunk delta** — SDK expects two-phase streaming

### Medium Issues:
4. Missing `system_fingerprint` field (optional but expected)
5. vLLM `finish_reason` values not mapped to OpenAI enum (e.g., `"max_tokens"` → `"length"`)
6. Streaming `finish_reason` not properly nullable

### Hidden Issues:
- H1: No validation of vLLM finish_reason values
- H2: `.strip()` on potentially None content
- H3: Streaming error format non-standard
- H4: Streaming index always 0 (breaks multi-choice)
- H5: Defensive usage info extraction missing

All findings verified against OpenAI Python SDK source code from GitHub.
