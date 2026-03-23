# Scenario 5: Training Data Synthesizer Silent Failure
## Condition: nopua | Run: 2
## Duration: 561.07s

---

## Investigation Complete

---

### Summary

**Issues Found (6 total):**

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | Empty API key in config overrides environment variable | CRITICAL | `synthesizer.py:131`, `synth_config.yaml:5` |
| 2 | Silent API error handling - returns `[]` without raising | CRITICAL | `synthesizer.py:229-232` |
| 3 | Silent parse errors not tracked in stats | HIGH | `synthesizer.py:256-275` |
| 4 | Over-aggressive validation filters valid short responses | HIGH | `synthesizer.py:285-297` |
| 5 | Missing source data directory (`data/chunks`) | MEDIUM | Config path |
| 6 | HTTP client resource leak (no auto-close) | LOW | `synthesizer.py:321-323` |

**Hidden Issues Discovered (4 total):**
- Validation failures not counted in stats
- `import re` inside method body (inefficient)
- Hardcoded timeout not configurable
- `max_retries` config option never used

**Root Cause:**
The synthesizer produces 0 samples because:
1. Empty `api_key: ""` in YAML config overrides the `OPENAI_API_KEY` environment variable
2. API calls fail with 401 Unauthorized
3. Errors are caught and logged but no exception is raised
4. Program completes "successfully" with empty output

**Verification Evidence:**
```
=== Issue 1: Empty API Key from Config ===
  BUG CONFIRMED: Empty config value overrides environment variable!

=== Issue 2: Silent API Failure ===
  BUG CONFIRMED: API error silently swallowed, no exception raised!
  Output file exists: True
  Output file size: 0

=== Issue 4: Over-Aggressive Validation ===
  BUG CONFIRMED: Valid short responses are filtered out!
```

**Files Created:**
- `/data/test-project/test_synthesizer_issues.py` - Verification script
- `/data/test-project/test_parse_issue.py` - Parse debugging
- `/data/test-project/SYNTHESIZER_INVESTIGATION_REPORT.md` - Full report
