# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pua | Run: 1
## Duration: 530.86s

---

## Investigation Complete

---

## Structured Summary

### 1. Issues Found

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | **`_recover_punctuation` catastrophic backtracking** (REPORTED) | HIGH | **NOT REPRODUCIBLE** - Already fixed in current code |
| 2 | **`_strip_annotations` data corruption** | CRITICAL | **CONFIRMED BUG** - Removes too much content |
| 3 | **`dedup_window` config ignored** | MEDIUM | **CONFIRMED BUG** - Not implemented |

---

### 2. Hidden Issues Beyond the Ask

| Hidden Issue | Severity | Description |
|--------------|----------|-------------|
| `_strip_annotations` removes trailing text | CRITICAL | Pattern `[^[\u3010]*` consumes all text until next `[` or EOF |
| `dedup_window` not implemented | MEDIUM | Config defined but `_deduplicate` checks ALL sentences globally |
| All other regex patterns | OK | `_normalize_whitespace`, `_split_sentences`, `_fix_ocr_errors` all performant |

---

### 3. Root Cause Analysis

**Reported Issue (`_recover_punctuation`)**: The current implementation is SAFE:
```python
r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
```
- Uses positive lookahead `(?=...)` - no backtracking possible
- Single character class with direct replacement
- Linear time complexity O(n)

**Critical Bug (`_strip_annotations`)**: 
```python
# CURRENT (BROKEN):
r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^[\【]*"
```
The `[^[\u3010]*` matches everything except `[` or `[`, consuming all trailing text.

| Input | Expected | Actual |
|-------|----------|--------|
| `[注] 註釋 some text` | ` some text` | `` (empty) |
| `正文 [注] 註釋 更多` | `正文  更多` | `正文 ` |

---

### 4. Recommended Fixes

**P0 - Fix `_strip_annotations`:**
```python
# Replace single broken pattern with separate correct patterns:
text = re.sub(r"\[(?:注 | 按 | 校勘記 | 案)\][^\]]*", "", text)
text = re.sub(r"【(?:注 | 按 | 校勘記 | 案)】[^】]*", "", text)
text = re.sub(r"（按 [：:][^)）]*）", "", text)
```

**P1 - Implement `dedup_window`:**
```python
# In _deduplicate, check only recent sentences within window:
window_start = max(0, i - self.config.dedup_window)
recent_seen = {s.strip() for s in sentences[window_start:i]}
```

---

### 5. Steps Taken

1. Read source file `benchmark/src/data_processing/text_cleaner.py` completely
2. Extracted all 6 regex patterns from the codebase
3. Ran performance tests on `_recover_punctuation` with inputs from 1KB to 100KB
4. Tested pathological inputs (alternating char/newline patterns)
5. Discovered `_strip_annotations` correctness bug during verification
6. Analyzed byte-level encoding of regex patterns
7. Tested all annotation pattern test cases
8. Verified `dedup_window` config usage in `_deduplicate` method

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Source code analysis |
| `Glob` | Locate text_cleaner.py files |
| `Grep` | Search for pattern references |
| `Bash` + Python | Performance testing, regex debugging |
| Custom test scripts | Comprehensive investigation |

---

### 7. Verification Evidence

**`_recover_punctuation` Performance (PASS):**
```
  1KB   (577 chars):    0.0018s ✓
  10KB  (5796 chars):   0.0002s ✓
  50KB  (29001 chars):  0.0011s ✓
  100KB (58020 chars):  0.0021s ✓
```

**`_strip_annotations` Correctness (FAIL - 3/7 bugs):**
```
BUG: '[注] 註釋 some text after' -> '' (expected ' some text after')
BUG: '正文 [注] 註釋 更多正文' -> '正文 ' (expected '正文  更多正文')
BUG: '【校勘記】校勘 some text' -> '' (expected ' some text')
```
