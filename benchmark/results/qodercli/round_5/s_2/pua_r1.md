# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pua | Run: 1
## Duration: 457.36s

---

## Investigation Complete

### Summary

**Task**: Debug `_recover_punctuation` method hanging on texts >10KB

### Key Findings

#### 1. `_recover_punctuation` is SAFE (No Catastrophic Backtracking)

The pattern `r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"` is **linear time O(n)**:
- Character class `[...]` matches exactly 1 character - no quantifier
- Literal `\n` - no ambiguity
- Lookahead `(?=...)` - zero-width assertion, no backtracking possible

**Performance verified:**
| Input Size | Time |
|------------|------|
| 10 KB | 0.0023s |
| 50 KB | 0.0034s |
| 100 KB | 0.0067s |

#### 2. CRITICAL BUG in `_strip_annotations` (line 296)

**Buggy pattern:**
```python
r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^[\【]*"
#                    ^^^^
#       SPACES around | are LITERAL characters!
```

**Problem:** The spaces around `|` in the alternation are treated as literal characters, so the pattern tries to match `"注 "` (with trailing space) or `" 按"` (with leading space) instead of `"注"` or `"按"`.

**Impact:** Annotation removal **never works** - patterns never match any input.

**Test Results:**
| Input | Expected | Actual | Status |
|-------|----------|--------|--------|
| `[注] 這是註釋` | `` | `[注] 這是註釋` | FAIL |
| `[注] 註釋 some text` | `` | `[注] 註釋 some text` | FAIL |
| `正文 [注] 註釋 更多` | `正文` | `正文 [注] 註釋 更多` | FAIL |

#### 3. Additional Issues Found

1. **Dead Code**: `punct_patterns` (lines 96-103) defined but never used
2. **Config Ignored**: `dedup_window = 5` not implemented - checks ALL sentences globally
3. **Inconsistent Validation**: `clean()` validates type, internal methods don't

### Recommended Fixes

**Priority 1 (CRITICAL):** Fix `_strip_annotations`
```python
# Replace line 296
# FROM: r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^[\【]*"
# TO:   r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】).*?(?=\[|【|$)"
```

**Priority 2 (MEDIUM):** Remove dead `punct_patterns` code (lines 96-103)

**Priority 3 (MEDIUM):** Fix `dedup_window` implementation

### Files Analyzed
- `benchmark/src/data_processing/text_cleaner.py`
- `benchmark/data/test-project/src/data_processing/text_cleaner.py`
- `nopua/benchmark/test-project/src/data_processing/text_cleaner.py`
- `benchmark/INVESTIGATION_REPORT.md`
- `benchmark/test_backtracking.py`
- `benchmark/test_pathological.py`

### Tools Used
- Read tool (source file analysis)
- Grep tool (pattern search)
- Bash + Python (regex performance testing)
- Custom test scripts (verification)
