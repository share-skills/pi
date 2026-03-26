# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: nopua | Run: 2
## Duration: 171.91s

---

Excellent! Now let me provide the final structured summary:

---

## Investigation Summary

### 1. Issues Found

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | **`_recover_punctuation` Catastrophic Backtracking** (Reported) | HIGH | **NOT PRESENT - Already Fixed** |
| 2 | **`_strip_annotations` Data Corruption** | **CRITICAL** | **PRESENT - Needs Fix** |
| 3 | **`dedup_window` Config Ignored** | MEDIUM | **PRESENT - Needs Fix** |
| 4 | Dead `punct_patterns` Code | LOW | **Already Fixed** |

---

### 2. Hidden Issues Beyond the Ask

**Critical Discovery:** The `_strip_annotations` method has a **data corruption bug** that removes FAR more content than intended:

```python
# Current broken pattern (line 296):
text = re.sub(r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^[\【]*", "", text)
```

**Problem:** The `[^[\【]*` pattern matches everything except `[` or `【`, consuming all text until the next bracket:

| Input | Expected | Actual | Status |
|-------|----------|--------|--------|
| `[注] 這是註釋` | `` | `` | PASS |
| `[注] 註釋 some text` | ` some text` | `` | **FAIL** |
| `正文 [注] 註釋 更多` | `正文  更多` | `正文 ` | **FAIL** |

---

### 3. Root Cause Analysis

**Reported Issue (`_recover_punctuation`):**
- The current implementation uses a **safe, linear-time pattern**:
  ```python
  r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
  ```
- Uses positive character class + lookahead → no nested quantifiers → no backtracking
- Handles 200KB+ inputs in < 0.02s

**Hidden Critical Bug (`_strip_annotations`):**
- Pattern changed from `.*?(?=[\[【]|$)` to `[^[\【]*` to "avoid scanning to end"
- This change **breaks semantics** - removes ALL text after annotation until next bracket
- Result: **Data loss** for any normal text following annotations

---

### 4. Recommended Fixes

**P0 - Fix `_strip_annotations` (CRITICAL):**
```python
# Replace lines 296-297 with:
text = re.sub(r"\[(?:注 | 按 | 校勘記 | 案)\][^\]]*", "", text)
text = re.sub(r"【(?:注 | 按 | 校勘記 | 案)】[^】]*", "", text)
text = re.sub(r"（按 [：:][^)）]*）", "", text)
```

**P1 - Fix `dedup_window` Implementation:**
```python
# In _deduplicate, implement actual sliding window:
window_start = max(0, i - self.config.dedup_window)
recent_seen = {s.strip() for s in sentences[window_start:i]}
```

---

### 5. Steps Taken

1. Read source file `benchmark/src/data_processing/text_cleaner.py`
2. Reviewed prior investigation report (`INVESTIGATION_REPORT.md`)
3. Executed performance tests on `_recover_punctuation` (100-5000 lines)
4. Tested `_strip_annotations` with multiple test cases
5. Verified `dedup_window` behavior
6. Confirmed dead code removal status
7. Validated normal cleaning behavior preservation

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Source code analysis |
| `Grep` | Pattern search across codebase |
| `Bash` + `python3` | Test execution & verification |
| Custom Python scripts | Regex performance/correctness testing |

---

### 7. Verification Evidence

**`_recover_punctuation` Performance (PASS):**
```
100 lines (4,099 chars):    0.0087s ✓
500 lines (20,499 chars):   0.0009s ✓
1000 lines (40,999 chars):  0.0130s ✓
2000 lines (81,999 chars):  0.0044s ✓
5000 lines (204,999 chars): 0.0186s ✓
```

**`_strip_annotations` Correctness (FAIL - 3/5):**
```
✓ Simple annotation
✗ Text after annotation (removes too much)
✗ Text before and after (removes too much)
✗ Fullwidth bracket variant (removes too much)
✓ Parenthesis annotation
```
