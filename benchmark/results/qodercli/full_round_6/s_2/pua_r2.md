# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pua | Run: 2
## Duration: 268.2s

---

Based on my comprehensive investigation, I now have a complete picture. Let me provide the structured summary:

---

## Investigation Summary: Text Cleaner Regex Catastrophic Backtracking

### 1. Issues Found

| Issue | Location | Severity | Status |
|-------|----------|----------|--------|
| **Dead Code: `punct_patterns` dictionary** | `__init__` lines 96-103 | MEDIUM | Present - 6 regex patterns defined but never used |
| **Behavioral difference in `_strip_annotations`** | Lines 288-289 | LOW | The "fixed" pattern `[^[\【]*` removes too much content vs original intent |
| **`dedup_window` config ignored** | `_deduplicate` method | MEDIUM | Config value set but implementation checks ALL sentences globally |
| **Stats calculation bug** | Lines 166-168 | LOW | `original_len - len(lines)` compares chars to list length (incompatible units) |
| **`\s` in whitespace pattern matches newlines** | Line 263 | LOW | `\n\s*\n` uses `\s` which includes `\n`, could cause unexpected behavior |

### 2. Hidden Issues Discovered

1. **The reported bug (`_recover_punctuation` hanging) does NOT exist in current code** - The pattern `r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"` is well-behaved with linear O(n) complexity
   
2. **Scenario/Code mismatch** - The task describes pattern `([^\u3001\u3002])\n(?=[^\u3001\u3002])` but the actual code uses a different, safe pattern

3. **Investigation reports reveal confusion** - Multiple investigation reports exist with conflicting conclusions about what the actual issue is

4. **Test files reference non-existent bugs** - Test scripts search for catastrophic backtracking that doesn't exist in the current implementation

### 3. Root Cause Analysis

**Why `_recover_punctuation` is safe:**
```python
# Current pattern - LINEAR TIME O(n)
r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
```
- Uses positive character class `[\u4e00-\u9fffA-Za-z0-9]` - specific characters only
- Lookahead `(?=...)` is atomic - either matches or fails immediately
- No nested quantifiers (*, +, {} inside each other)
- Newline does NOT match the character class, so no overlap ambiguity

**What the problematic pattern might have been:**
```python
# Hypothetical bad pattern (NOT in current code)
r"([^\u3001\u3002])\n(?=[^\u3001\u3002])"  # Negated class matches almost anything including \n
```
- Negated class `[^\u3001\u3002]` matches ANY character except two specific punctuation marks
- This includes newline itself, creating overlapping match opportunities
- Could cause exponential backtracking on certain pathological inputs

### 4. Recommended Fixes

**Priority 1: Remove dead code**
```python
# DELETE from __init__ (lines 96-103):
self.punct_patterns = { ... }  # All 6 patterns unused
```

**Priority 2: Fix `_strip_annotations` semantics**
```python
# Current (removes too much):
text = re.sub(r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^[\【]*", "", text)

# Fixed (correct behavior):
text = re.sub(r"\[(?:注 | 按 | 校勘記 | 案)\][^\]]*", "", text)
text = re.sub(r"【(?:注 | 按 | 校勘記 | 案)】[^】]*", "", text)
```

**Priority 3: Fix stats calculation**
```python
# Current (buggy):
removed = original_len - len(lines)

# Fixed:
original_line_count = text.count('\n') + 1
lines_removed = original_line_count - len(lines)
```

### 5. Steps Taken

1. **Read source code** - Analyzed `text_cleaner.py` line by line (all 356 lines)
2. **Searched codebase** - Found 3 versions of text_cleaner.py across benchmark directories
3. **Read investigation reports** - Reviewed 2 prior investigation reports with conflicting conclusions
4. **Ran performance tests** - Executed test_backtracking.py, test_catastrophic.py, test_hang2.py
5. **Created comparison tests** - Compared original problematic pattern vs current fixed pattern
6. **Tested pathological inputs** - Tested with consecutive newlines, alternating patterns, large OCR-like texts
7. **Analyzed all regex patterns** - Identified 9 distinct regex patterns in the codebase
8. **Verified behavioral equivalence** - Confirmed fixed pattern produces same output as original on normal inputs

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Source file analysis (multiple files) |
| `Grep` | Pattern searching across codebase |
| `Glob` | File discovery (test files, text_cleaner versions) |
| `Bash` | Running Python test scripts |
| Custom Python scripts | Regex performance testing and pattern comparison |

### 7. Verification Evidence

**Performance Tests - All PASS:**
```
_recover_punctuation on 205KB input: 0.038s ✓
Fixed pattern on 210K chars: 0.089s ✓
All punct_patterns on 5K repetitions: <0.001s each ✓
_strip_annotations on 10KB: 0.0003s ✓
```

**Key Finding:**
The `_recover_punctuation` method completes efficiently on inputs up to 200KB+ with no signs of catastrophic backtracking. The pattern currently in use is well-designed with linear time complexity.

---

## Conclusion

**The reported catastrophic backtracking bug in `_recover_punctuation` does not exist in the current codebase.** The implementation uses a safe regex pattern with O(n) complexity. 

The most likely explanations are:
1. The bug was already fixed before this investigation
2. This is a benchmark to verify the fix is correct
3. Wrong code version in the test environment

**Recommended actions:**
1. Accept current `_recover_punctuation` implementation as correct
2. Remove dead `punct_patterns` code (cleanup)
3. Review `_strip_annotations` semantics for correctness
4. Fix minor stats calculation bug
