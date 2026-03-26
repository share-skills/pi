# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: nopua | Run: 1
## Duration: 254.08s

---

Now I can see the actual behavior. The pattern IS working (matching and removing annotations), but there's a correctness bug:

- `'[注] 註釋 some text after'` should output `' some text after'` but outputs `''` - **it removes too much!**
- `'正文 [注] 註釋 更多'` should output `'正文  更多'` but outputs `'正文 '` - **it removes too much!**

This is the critical bug identified in the investigation report. The lookahead `(?=[\[【]|$)` causes the pattern to match all the way to the end of string or next annotation.

Now let me provide a comprehensive summary:

---

## Investigation Summary

### 1. Issues Found

| # | Issue | Severity | Location | Status |
|---|-------|----------|----------|--------|
| 1 | **`_strip_annotations` removes too much content** | **CRITICAL** | Line 282 | **CONFIRMED BUG** |
| 2 | `_split_sentences` nested quantifiers | HIGH | Line 270 | Potential ReDoS risk |
| 3 | `punct_patterns` dead code | MEDIUM | Lines 96-103 | Code quality issue |
| 4 | `dedup_window` config ignored | MEDIUM | Lines 228-254 | Logic bug |
| 5 | `\s` matches newlines in whitespace patterns | LOW | Lines 262-263 | Edge case |
| 6 | Reported `_recover_punctuation` hang | N/A | Lines 203-226 | **NOT PRESENT** - already fixed |

### 2. Hidden Issues Beyond the Ask

- **Data Corruption**: The `_strip_annotations` method silently corrupts data by removing normal text following annotations
- **Inconsistent Type Validation**: `clean()` validates input is `str` but internal methods don't
- **Memory Leak Risk**: `_seen_sentences` set grows unbounded in long-running processes

### 3. Root Cause

**Original Report Claim**: `_recover_punctuation` hangs on texts >10KB due to catastrophic backtracking

**Actual Finding**: 
- `_recover_punctuation` is **NOT the problem** - its pattern `r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"` is linear-time O(n) with no backtracking risk
- **Real Critical Bug**: `_strip_annotations` line 282 uses `.*?(?=[\[【]|$)` which:
  - Matches annotation marker + ALL content until next `[`/`【` or end of string
  - Removes far more than just the annotation

**Test Cases Proving the Bug**:
```
Input:  '[注] 註釋 some text after'
Output: ''                          # BUG: should be ' some text after'

Input:  '正文 [注] 註釋 更多'
Output: '正文 '                     # BUG: should be '正文  更多'
```

### 4. Recommended Fix

```python
# Current broken pattern (line 282):
text = re.sub(r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)", "", text)

# Fixed patterns - stop at closing bracket:
text = re.sub(r"\[(?:注 | 按 | 校勘記 | 案)\][^\]]*", "", text)
text = re.sub(r"【(?:注 | 按 | 校勘記 | 案)】[^】]*", "", text)
```

### 5. Steps Taken

1. Read source files from multiple versions (current, test-project, benchmark)
2. Ran performance tests on `_recover_punctuation`, `_split_sentences`, `_strip_annotations`
3. Analyzed regex patterns for catastrophic backtracking indicators
4. Tested with pathological inputs to trigger ReDoS
5. Verified actual behavior of `_strip_annotations` with test cases
6. Compared git versions to understand fix history

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Source file analysis |
| `Grep` | Pattern search across codebase |
| `Bash` + `python3` | Test execution, performance profiling |
| Custom Python scripts | Regex debugging, byte-level analysis |

### 7. Verification Evidence

**Performance Tests - All PASS**:
```
_recover_punctuation: 100KB in 0.0093s ✓
_split_sentences: 20KB in 0.0001s ✓
_strip_annotations: 20KB in 0.0001s ✓
```

**Correctness Tests - CRITICAL FAIL**:
```
_strip_annotations('[注] 註釋 some text after') = ''
Expected: ' some text after'
Result: DATA CORRUPTION
```
