# Scenario 4: API Server Response Format Mismatch
## Condition: nopua | Run: 1
## Duration: 77.25s

---

## Summary Table

| # | Issue | Severity | Location | Fix |
|---|-------|----------|----------|-----|
| 1 | `created` field is string, should be int | 🔴 Critical | Lines 97, 200, 284 | Change type to `int`, use `int(time.time())` |
| 2 | Missing `usage` field in response | 🟡 High | Lines 89-100 | Add `usage: Optional[UsageInfo]` |
| 3 | `finish_reason` not validated | 🟡 Medium | Line 86 | Add normalization helper |
| 4 | Stream chunk missing `delta.role` | 🟡 Medium | Lines 286-296 | Add `"role": "assistant"` |
| 5 | Stream `finish_reason` passthrough | 🟡 Medium | Line 294 | Use normalization helper |
| 6 | Missing `system_fingerprint` | 🟢 Low | Lines 89-100 | Add optional field |
| 7 | `/v1/models` missing `permission` | 🟢 Low | Lines 132-145 | Add permission array |
