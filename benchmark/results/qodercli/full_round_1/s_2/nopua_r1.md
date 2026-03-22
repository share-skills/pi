# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: nopua | Run: 1
## Duration: 285.48s

---

## Investigation Complete

### Summary

**The reported catastrophic backtracking issue in `_recover_punctuation` has already been FIXED** in the current codebase. The pattern now uses positive character classes `[\u4e00-\u9fffA-Za-z0-9]` instead of negated classes, which eliminates the backtracking risk.

---

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Dead Code** - `punct_patterns` dictionary defined but never used | Medium | `__init__`, lines 96-103 |
| 2 | **Inconsistent Input Validation** - `clean()` validates str, internal methods don't | Low | All `_-*` methods |
| 3 | **Statistics Calculation Bug** - Compares chars vs list length | Low | `clean()`, line 169 |
| 4 | **Dedup State Leakage** - `_seen_sentences` persists across `clean()` calls | Medium | `_deduplicate()` |
| 5 | **Silent Failure** - opencc ImportError logged but `_converter` stays None | Medium | `__init__`, lines 113-119 |
| 6 | **Unclear Output Format** - `_split_sentences` returns delimiters + empty strings | Low | `_split_sentences()` |

---

### 2. Hidden Issues Beyond the Ask

1. **`_strip_annotations` regex risk** (HIGH): Pattern `.*?(?=\[|【|$)` with non-greedy quantifier + lookahead could backtrack on pathological inputs
2. **`_normalize_whitespace` edge case**: `\n\s*\n` where `\s*` can match newlines may cause unexpected behavior
3. **No type safety**: Internal methods accept any type, could crash if called directly

---

### 3. Root Cause (Original Bug)

The scenario described a pattern like:
```python
r"([^\u3001\u3002\uff01...])\n(?=[^\u3001\u3002...])"  # BUGGY - negated class
```

This creates O(2^n) complexity because:
- Negated character classes match almost everything
- Combined with multiline and lookahead forces re-evaluation at each position
- Large inputs (>10KB) with many newlines trigger exponential backtracking

**Current fix uses positive classes:**
```python
r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"  # SAFE
```

---

### 4. Recommended Fixes

```python
# Fix #1: Remove dead code (lines 96-103)
# Delete self.punct_patterns = {...}

# Fix #3: Correct stats calculation (line 169)
removed = original_len - len(text.replace("\n", ""))  # Compare chars

# Fix #4: Reset dedup state at start of clean()
self._seen_sentences.clear()  # Add after line 135

# Fix #5: Validate _converter before use (line 160)
if self._converter:  # Already guarded, but add else warning
    text = self._converter.convert(text)
else:
    logger.warning("convert_traditional=True but opencc not available")
```

---

### 5. Steps Taken

1. Read all 3 versions of `text_cleaner.py` in the codebase
2. Analyzed each regex pattern for catastrophic backtracking potential
3. Created stress tests with inputs up to 50KB / 5000 lines
4. Ran performance benchmarks on all methods
5. Identified 6 hidden issues beyond the reported bug

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files |
| `Grep` | Search for patterns across codebase |
| `Glob` | Find all text_cleaner.py versions |
| `Write` | Create test scripts |
| `Bash` | Run Python tests |
| `TodoWrite` | Track investigation progress |

---

### 7. Verification Evidence

```
STRESS TESTS Results:
  5000 lines: PASS (0.0014s)
  50KB whitespace: PASS (0.0054s)
  5000 annotations: PASS (0.0011s)

FULL PIPELINE TEST:
  Full clean() pipeline (500 iterations): 0.0019s
  Input length: 24499 chars
  Output length: 25998 chars
```

**All tests passed without hanging.** The current implementation is safe from catastrophic backtracking.
