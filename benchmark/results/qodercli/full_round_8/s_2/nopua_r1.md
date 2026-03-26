# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: nopua | Run: 1
## Duration: 450.05s

---

## Investigation Summary

### Issues Found

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | `_split_sentences` catastrophic backtracking `((?:[。！？；]\s*)+)` | CRITICAL | ✅ Fixed in benchmark version |
| 2 | `_strip_annotations` removes excess content (correctness bug) | HIGH | ✅ Fixed in benchmark version |
| 3 | `dedup_window` config defined but never used | MEDIUM | ⚠️ Still present |
| 4 | Dead code `punct_patterns` dictionary | LOW | ✅ Removed in benchmark version |
| 5 | Stats tracking bug (chars vs lines) | LOW | ✅ Fixed in benchmark version |
| 6 | Type validation inconsistency | LOW | ⚠️ Still present |

### Hidden Issues Discovered

1. **Stats tracking bug** - Original code compared character count to line count
2. **Batch dedup documentation mismatch** - Docstring claims "no cross-document dedup" but this limits functionality

### Root Cause

The hanging issue was caused by **nested quantifiers** in regex patterns:
- Pattern `((?:[。！？；]\s*)+)` has outer `+` and inner `\s*` creating O(2^n) backtracking
- Non-greedy `.*?` with unclosed patterns scans to end of string repeatedly

### Recommended Fix

The benchmark version already contains all critical fixes. Remaining work:

```python
# Implement dedup_window or remove the config option
def _deduplicate(self, text: str) -> str:
    sentences = self._split_sentences(text)
    seen = {}  # sentence -> last seen position
    unique = []
    
    for i, sentence in enumerate(sentences):
        normalized = sentence.strip()
        if not normalized:
            unique.append(sentence)
            continue
        
        # Only dedup if seen within window
        if normalized in seen and i - seen[normalized] <= self.config.dedup_window:
            continue
        
        seen[normalized] = i
        unique.append(sentence)
    
    return "".join(unique)
```

### Verification Evidence

All tests pass on the fixed benchmark version:
- 100KB input processes in <0.01s (was hanging indefinitely)
- `_strip_annotations` correctness tests pass
- No catastrophic backtracking detected

Full report saved to: `/Users/hepin/IdeaProjects/pi/INVESTIGATION_REPORT.md`
