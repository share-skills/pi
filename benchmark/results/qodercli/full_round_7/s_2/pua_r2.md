# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pua | Run: 2
## Duration: 409.76s

---

Now I have a complete picture. The `nopua/benchmark/test-project` version has the `punct_patterns` dead code, while the other two versions don't. Let me provide the final comprehensive investigation report:

---

## Final Investigation Report: Text Cleaner Regex Catastrophic Backtracking

### Executive Summary

The originally reported issue (`_recover_punctuation` hangs on >10KB OCR outputs) **has already been fixed** in the current codebase. However, the investigation revealed **a critical data corruption bug** in `_strip_annotations` that silently removes far more content than intended.

---

### 1. Issues Found

| # | Issue | Severity | Status | Location |
|---|-------|----------|--------|----------|
| 1 | **`_recover_punctuation` hang** | CRITICAL | ✅ FIXED | Line 220-225 |
| 2 | **`_strip_annotations` data corruption** | **CRITICAL** | ⚠️ PRESENT | Line 288 |
| 3 | **Dead code: `punct_patterns`** | MEDIUM | ⚠️ PRESENT (nopua version only) | Lines 96-103 |
| 4 | **`dedup_window` config ignored** | MEDIUM | ⚠️ PRESENT | Line 68 |

**Issue Details:**

1. **`_recover_punctuation` (FIXED)**: Current pattern `r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"` is safe with linear time complexity. Verified: 80KB processes in 0.006s.

2. **`_strip_annotations` (CRITICAL BUG)**: Pattern `r"(?:\[|【)(?:注 | 按|校勘記 | 案)(?:\]|】)[^\[【]*"` consumes ALL text after annotation until next `[` or `[`, causing massive data loss.

3. **`punct_patterns` (DEAD CODE)**: Six regex patterns defined in `__init__` but never used anywhere in the codebase.

4. **`dedup_window` (LOGIC BUG)**: Config value `dedup_window=5` is defined but implementation checks ALL previous sentences globally instead of within window.

---

### 2. Hidden Issues Beyond the Ask

| Hidden Issue | Category | Impact |
|--------------|----------|--------|
| `_strip_annotations` removes text after annotations | **Data Corruption** | Normal text following annotation markers is incorrectly deleted |
| Dead `punct_patterns` code | Code Quality | Wasted memory, unnecessary regex compilation overhead |
| `dedup_window` not implemented | Logic Bug | Memory grows unbounded on long documents |
| Type validation inconsistent | API Design | `clean()` validates type but internal methods don't |

---

### 3. Root Cause Analysis

#### Original Issue (Already Fixed)

The reported `_recover_punctuation` hang was caused by a previous regex pattern with catastrophic backtracking. The **current implementation is safe**:

```python
# Current pattern (SAFE):
r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
```

- Simple character class with no nested quantifiers
- Positive lookahead doesn't consume characters
- Linear time O(n)

#### Critical Bug: `_strip_annotations` Data Corruption

```python
# BROKEN pattern at line 288:
r"(?:\[|【)(?:注 | 按|校勘記 | 案)(?:\]|】)[^\[【]*"
```

**Pattern breakdown:**
| Component | Meaning |
|-----------|---------|
| `(?:\[|【)` | Opening bracket |
| `(?:注 | 按|校勘記 | 案)` | Annotation keyword |
| `(?:\]|】)` | Closing bracket |
| `[^\[【]*` | **Everything except `[` or `[` (GREEDY)** |

**The bug:** After matching `[注]`, the character class `[^\[【]*` matches ALL remaining text until end of string (or next `[`), consuming normal content that should be preserved.

**Test evidence:**
```
Input:    '[注] 註釋 some text'
Expected: ' some text'  (only annotation removed)
Got:      ''            (ALL content removed!)
```

---

### 4. Recommended Fix

#### Priority P0: Fix `_strip_annotations` Data Corruption

```python
def _strip_annotations(self, text: str) -> str:
    """Remove annotation markers and inline notes."""
    # Match each bracket type separately, stopping at closing bracket
    text = re.sub(r"\[(?:注 | 按|校勘記 | 案)\][^\]]*", "", text)
    text = re.sub(r"【(?:注 | 按|校勘記 | 案)】[^】]*", "", text)
    text = re.sub(r"（按 [：:][^)）]*）", "", text)
    return text
```

#### Priority P1: Remove Dead Code

Delete lines 96-103 (`self.punct_patterns = {...}`)

#### Priority P2: Fix `dedup_window` Implementation

Implement actual windowed deduplication instead of global tracking.

---

### 5. Steps Taken

1. **Read source files** - Analyzed all three `text_cleaner.py` variants
2. **Compared versions** - Identified differences between versions  
3. **Searched codebase** - Found test files, prior investigations, analysis reports
4. **Reviewed prior work** - Read `benchmark/INVESTIGATION_REPORT.md` and related docs
5. **Executed performance tests** - Verified `_recover_punctuation` handles 80KB in 0.006s
6. **Executed correctness tests** - Confirmed `_strip_annotations` data corruption
7. **Regex pattern analysis** - Byte-level debugging of pattern encoding
8. **Created debug scripts** - Multiple Python test files to isolate issues

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Source file analysis |
| `Glob` | Finding test files |
| `Grep` | Pattern search across codebase |
| `Bash` + `python3` | Performance and correctness testing |
| Custom Python scripts | Regex pattern debugging |

---

### 7. Verification Evidence

**Performance Test** (`_recover_punctuation`):
```
Input: 81,999 chars (80.1 KB)
Result: 0.006s ✓ PASS - No hang detected
```

**Correctness Test** (`_strip_annotations`):
```
Test: Text after annotation should remain
  Input:    '[注] 註釋 some text'
  Expected: ' some text'
  Got:      ''  ✗ DATA CORRUPTION

Test: Text before and after should remain  
  Input:    '正文 [注] 註釋 更多'
  Expected: '正文  更多'
  Got:      '正文 '  ✗ DATA CORRUPTION
```

---

**Conclusion**: The reported catastrophic backtracking is fixed, but a critical data corruption bug in `_strip_annotations` requires immediate attention. This bug silently deletes user content, which is equally severe as a hang.
