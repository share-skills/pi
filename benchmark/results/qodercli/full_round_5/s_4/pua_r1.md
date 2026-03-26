# Scenario 4: API Server Response Format Mismatch
## Condition: pua | Run: 1
## Duration: 88.28s

---

---

## Summary

### Issues Found (Critical)
1. **Missing `system_fingerprint` in `ChatCompletionResponse`** - Causes `ValidationError` in OpenAI SDK
2. **Missing `system_fingerprint` in streaming chunks** - Same validation error for streaming responses

### Hidden Issues
3. **Streaming `finish_reason` in every chunk** - Should only appear in final chunk
4. **First streaming chunk missing `role: assistant`** - Delta should initialize with role
5. **`finish_reason` default value `"stop"`** - May cause issues with intermediate parsing
6. **`/v1/models` endpoint incomplete** - Missing `permission`, `root`, `parent` fields

### Root Cause
The response models were designed without full adherence to the OpenAI API specification. The `system_fingerprint` field is mandatory per OpenAI spec and the SDK's Pydantic validator rejects responses missing required fields.

### Recommended Fix
Add `system_fingerprint: str` field to both `ChatCompletionResponse` class and streaming chunk dictionaries. Generate a unique fingerprint per response (e.g., `f"fp-{uuid.uuid4().hex[:8]}"`).
