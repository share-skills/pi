# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pua | Run: 1
## Duration: 405.57s

---

Now let me provide the complete structured summary:

---

## Structured Investigation Summary

### 1. Issues Found

| # | Issue | Severity | Location | Status |
|---|-------|----------|----------|--------|
| 1 | `_recover_punctuation` catastrophic backtracking | **REPORTED** | Line 219-224 | **NOT PRESENT** (already fixed) |
| 2 | `_strip_annotations` removes too much content (data corruption) | **CRITICAL** | Line 296-297 | **CONFIRMED BUG** |
| 3 | `punct_patterns` defined but never used (dead code) | MEDIUM | Lines 96-103 (nopua version) | CONFIRMED |
| 4 | `dedup_window` config parameter ignored | MEDIUM | `_deduplicate` method | CONFIRMED BUG |
| 5 | Stats counter counts chars instead of lines removed | LOW | `clean` method line 169 (nopua) | FIXED in benchmark/src |
| 6 | Missing type validation on internal methods | LOW | Throughout | Minor API issue |

### 2. Hidden Issues Beyond the Ask

| Hidden Issue | Severity | Description |
|-------------|----------|-------------|
| `_strip_annotations` semantic bug | **CRITICAL** | Pattern `[^[\【]*` consumes ALL text until next bracket, deleting normal content |
| Dead `punct_patterns` code | MEDIUM | 6 regex patterns allocated but never called |
| `dedup_window` not implemented | MEDIUM | Config says window=5 but checks ALL sentences globally |
| Inconsistent stats counting | LOW | Some versions count chars, others count lines |

### 3. Root Cause Analysis

#### Issue #1: `_recover_punctuation` Hanging (REPORTED - Already Fixed)

**Current implementation uses a safe pattern:**
```python
r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
```

This pattern is **linear-time** with no backtracking risk because:
- Simple character class with no nested quantifiers
- Positive lookahead `(?=...)` doesn't consume characters
- Single capture group with direct replacement

**Performance verified:**
- 1KB: 0.0016s ✓
- 10KB: 0.0006s ✓
- 50KB: 0.0033s ✓
- 100KB: 0.0065s ✓

#### Issue #2: `_strip_annotations` Data Corruption (CRITICAL BUG)

**Root cause:** The "fixed" pattern uses `[^[\【]*` which was intended to avoid scanning to end-of-string, but has **broken semantics**:

```python
# Current buggy pattern (line 296)
text = re.sub(r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^[\【]*", "", text)
```

**Problem:** `[^[\【]*` matches any character EXCEPT `[` or `【`, so after matching `[注]`, it consumes ALL subsequent text until the next opening bracket or end of string.

**Example:**
- Input: `"正文 [注] 註釋 some text after 更多"`
- Expected: `"正文  更多"`  
- Actual: `"正文 "` ← **"some text after 更多" incorrectly deleted!**

### 4. Recommended Fix

#### Priority 1: Fix `_strip_annotations` (CRITICAL)

```python
# Replace lines 296-297:

# CURRENT (BUGGY):
text = re.sub(r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^[\【]*", "", text)
text = re.sub(r"（按 [：:][^) ）]*[) ）]", "", text)

# FIXED:
text = re.sub(r"\[(?:注 | 按 | 校勘記 | 案)\][^\]]*", "", text)
text = re.sub(r"【(?:注 | 按 | 校勘記 | 案)】[^】]*", "", text)
text = re.sub(r"（按 [：:][^) ）]*）", "", text)
```

The fix changes the negated class from `[^[\【]*` (not opening bracket) to `[^\]]*` (not closing bracket), so annotation content stops at the matching closing delimiter.

#### Priority 2: Remove Dead Code (nopua version only)

Remove lines 96-103 defining unused `punct_patterns`.

#### Priority 3: Implement `dedup_window` Properly

Modify `_deduplicate` to only check sentences within the configured window size instead of global deduplication.

### 5. Steps Taken

1. **Read all three versions** of `text_cleaner.py` (benchmark/src, benchmark/data, nopua/benchmark)
2. **Compared versions** using `diff` to identify differences
3. **Created performance tests** for `_recover_punctuation` with inputs up to 200KB+
4. **Tested `_strip_annotations`** with multiple test cases revealing data corruption
5. **Analyzed regex patterns** byte-by-byte to debug matching issues
6. **Verified actual function behavior** by importing and running the real code
7. **Checked related investigation reports** (`INVESTIGATION_REPORT.md`, `test_backtracking.py`)
8. **Validated all findings** with reproducible test cases

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Source file analysis |
| `Glob` | Finding all text_cleaner.py versions |
| `Grep` | Searching for patterns across codebase |
| `Bash` + Python | Test execution and regex debugging |
| `diff` | Comparing file versions |
| Custom Python scripts | Performance testing, pattern analysis |

### 7. Verification Evidence

**`_recover_punctuation` Performance (PASS):**
```
   1024 chars: 0.0016s ✓
  10240 chars: 0.0006s ✓
  51200 chars: 0.0033s ✓
 102400 chars: 0.0065s ✓
```

**`_strip_annotations` Correctness (FAIL - 3/5 bugs):**
```
✓ '[注] 這是註釋' → ''
✗ '[注] 註釋 some text' → '' (expected ' some text')
✗ '正文 [注] 註釋 更多' → '正文 ' (expected '正文  更多')  
✓ '【注】測試' → ''
✗ 'A[注]X B【案】Y C' → 'A' (expected 'A B C')
```
