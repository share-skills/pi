# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: nopua | Run: 1
## Duration: 112.14s

---

Now I have a complete picture. Let me provide the structured summary:

---

## Investigation Summary: Text Cleaner Regex Catastrophic Backtracking

### 1. Issues Found

| # | Issue | Severity | Location | Status |
|---|-------|----------|----------|--------|
| 1 | **`_strip_annotations` removes too much content** | **CRITICAL** | Line 296 | **CONFIRMED BUG** |
| 2 | **`dedup_window` config ignored** | MEDIUM | Lines 228-254 | Logic bug |
| 3 | `_split_sentences` pattern has minor risk | LOW | Line 280 | Already improved |
| 4 | Parenthetical annotation pattern doesn't match | LOW | Line 297 | Partial fix |

#### Issue #1: CRITICAL - `_strip_annotations` Data Corruption

The pattern at line 296:
```python
r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^[\【]*"
```

**Problem**: `[^[\【]*` matches everything except `[` or `【`, consuming ALL text until the next bracket anywhere in the document.

**Test failures**:
- Input: `"[注] 註釋 some text after"` → Expected: `" some text after"` → Actual: `""` (entire tail removed!)
- Input: `"正文 [注] 註釋 更多"` → Expected: `"正文  更多"` → Actual: `"正文 "` (tail removed!)

#### Issue #2: MEDIUM - `dedup_window` Config Ignored

The `config.dedup_window = 5` is defined but never used. The `_deduplicate` method checks ALL previous sentences globally instead of just within the window, causing unbounded memory growth.

---

### 2. Hidden Issues Beyond the Ask

1. **`_recover_punctuation` was NEVER the problem** - The reported hang issue is a **misdiagnosis**. The current regex pattern is O(n) linear time with no backtracking risk. Performance tests confirm it handles 100KB+ inputs in <0.003s.

2. **Parenthetical annotation pattern broken** - Line 297's pattern `r"（按 [：:][^)）]*[)）]"` fails to remove parenthetical annotations when they appear mid-text (test showed input unchanged).

3. **Stats counter overflow risk** - No bounds checking on `_stats` counters for long-running batch processes.

---

### 3. Root Cause

**For the reported issue (`_recover_punctuation` hanging)**:
- The pattern `r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"` uses:
  - Simple character class with no nested quantifiers
  - Positive lookahead (zero-width assertion, no backtracking)
  - Single capture group with direct replacement
- This is **inherently safe** O(n) linear time complexity

**For the actual critical bug (`_strip_annotations`)**:
- The "fix" changed from `.*?(?=[\[【]|$)` to `[^[\【]*` to avoid end-of-string scanning
- But `[^[\【]*` still scans forward until it finds `[` or `【`, removing everything in between
- This corrupts data by deleting normal text following annotations

---

### 4. Recommended Fixes

#### Priority P0: Fix `_strip_annotations` (Data Corruption)

```python
# Current broken line 296:
text = re.sub(r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^[\【]*", "", text)

# Fixed version - separate patterns for each bracket type:
text = re.sub(r"\[(?:注 | 按 | 校勘記 | 案)\][^\]]*", "", text)
text = re.sub(r"【(?:注 | 按 | 校勘記 | 案)】[^】]*", "", text)
text = re.sub(r"（按 [：:][^)）]*）", "", text)
```

#### Priority P1: Fix `dedup_window` Implementation

Modify `_deduplicate` to actually use `self.config.dedup_window` for limiting the seen set scope.

---

### 5. Steps Taken

1. **Read source file** - Analyzed `benchmark/src/data_processing/text_cleaner.py` in full
2. **Searched codebase** - Found related investigation reports and test files
3. **Created test suite** - Wrote `test_text_cleaner_issues.py` with 7 test scenarios
4. **Ran performance tests** - Verified `_recover_punctuation` handles 100KB in 0.0026s
5. **Ran correctness tests** - Identified 4 failing test cases in `_strip_annotations`
6. **Analyzed root cause** - Traced pattern behavior to understand why it removes too much

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Source file analysis |
| `Grep` | Pattern search across codebase |
| `Glob` | Find related test files |
| `Bash` + `python3` | Execute test suite |
| Custom Python script | Isolate and verify bugs |

---

### 7. Verification Evidence

**Performance Test Results** (`_recover_punctuation`):
```
    1 KB:   0.0017s ✓ PASS
    5 KB:   0.0001s ✓ PASS
   10 KB:   0.0003s ✓ PASS
   50 KB:   0.0013s ✓ PASS
  100 KB:   0.0026s ✓ PASS
```

**Correctness Test Results** (`_strip_annotations`):
```
  PASS: Simple annotation only
  FAIL: Annotation followed by normal text (removes too much)
  FAIL: Annotation in middle of text (removes too much)
  PASS: Bracket type annotation only
  FAIL: Bracket annotation in middle (removes too much)
  PASS: Parenthetical annotation only
  FAIL: Parenthetical in middle (doesn't match at all)
```

**Conclusion**: The reported `_recover_punctuation` hang is **NOT PRESENT** in current code. However, `_strip_annotations` has **CRITICAL DATA CORRUPTION BUGS** that require immediate fixing.
