# Scenario 5: Training Data Synthesizer Silent Failure
## Condition: nopua | Run: 2
## Duration: 69.98s

---

---

## Summary Table

| Category | Issue | Location | Severity |
|----------|-------|----------|----------|
| **Root Cause** | Empty `api_key` in config | `synth_config.yaml:5` | Critical |
| **Root Cause** | Source directory missing | `./data/chunks/` doesn't exist | Critical |
| **Design Flaw** | Silent API failure handling | `synthesizer.py:229-232` | High |
| **Design Flaw** | Silent parse failure handling | `synthesizer.py:243-246` | High |
| **Hidden** | No validation rejection logging | `synthesizer.py:285-304` | Medium |
| **Hidden** | Regex extraction fragility | `synthesizer.py:263-275` | Medium |
| **Hidden** | HTTP client leak on early exit | `synthesizer.py:149-151` | Low |

The synthesizer runs without errors but produces 0 samples because: **(1) no API key**, **(2) no source data**, and **(3) all failures are silently swallowed** rather than surfaced to the user.
