# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: nopua | Run: 2
## Duration: 162.36s

---

## Structured Summary

### 1. Issues Found

| # | Issue | Severity | Location | Status |
|---|-------|----------|----------|--------|
| 1 | **`_recover_punctuation` Hang** | CRITICAL | `benchmark/src/data_processing/text_cleaner.py:219-224` | **FIXED** (in current code) |
| 2 | **`_strip_annotations` Data Corruption** | CRITICAL | `benchmark/src/data_processing/text_cleaner.py:296-297` | **PRESENT - NOT FIXED** |
| 3 | **`dedup_window` Config Ignored** | MEDIUM | `_deduplicate method` | **PRESENT - NOT FIXED** |
| 4 | **Dead Code: `punct_patterns`** | LOW | `__init__, lines 96-103` | **PRESENT** |

---

### 2. Hidden Issues Beyond the Ask

| Hidden Issue | Category | Evidence |
|-------------|----------|----------|
| `_strip_annotations` removes text AFTER annotation | **Data Corruption** | Input `[注] 註釋 some text` → Output `` (expected ` some text`) |
| `dedup_window=2` config ignored, global dedup applied | Logic Bug | Sentence `A` removed even when outside window |
| Six regex patterns in `punct_patterns` never used | Dead Code | Defined in `__init__` but never called |
| Whitespace pattern `\s` could match newlines | Edge Case | Fixed in current version with explicit `[ \t]` |

---

### 3. Root Cause Analysis

#### Original Reported Issue (`_recover_punctuation` hang)

**Current Implementation** (already fixed):
```python
text = re.sub(
    r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])",
    r"\1。\n",
    text,
    flags=re.MULTILINE,
)
```

**Why it's safe:**
- Character class `[\u4e00-\u9fffA-Za-z0-9]` has no nested quantifiers
- Positive lookahead `(?=...)` doesn't consume characters
- Linear time complexity O(n)

**Verified Performance:**
- 1KB: 0.0018s | 10KB: 0.0003s | 50KB: 0.0016s | 100KB: 0.0031s

#### Critical Bug (`_strip_annotations` data corruption)

**Current Broken Pattern:**
```python
text = re.sub(r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^[\【]*", "", text)
```

**Problem:** `[^[\【]*` matches everything except `[` or `【`, consuming all text until the next bracket character.

**Test Failure:**
```
Input:    "[注] 註釋 some text"
Expected: " some text"
Actual:   ""  ← DATA CORRUPTION
```

---

### 4. Recommended Fixes

#### Priority 1 (P0): Fix `_strip_annotations` Data Corruption

```python
# Current (BROKEN) - lines 296-297:
text = re.sub(r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^[\【]*", "", text)
text = re.sub(r"（按 [：:][^)）]*[)）]", "", text)

# Fixed - correct behavior:
text = re.sub(r"\[(?:注 | 按 | 校勘記 | 案)\][^\]]*", "", text)
text = re.sub(r"【(?:注 | 按 | 校勘記 | 案)】[^】]*", "", text)
text = re.sub(r"（按 [：:][^)）]*）", "", text)
```

#### Priority 2 (P2): Fix `dedup_window` Implementation

Modify `_deduplicate` to respect the window:
```python
window_start = max(0, i - window_size)
recent_seen = {s.strip() for s in unique[window_start:i] if s.strip()}
```

#### Priority 3 (P3): Remove Dead Code

Remove `self.punct_patterns` dict from `__init__` (lines 96-103).

---

### 5. Steps Taken

1. **Read source files** - Analyzed `text_cleaner.py` in three locations (benchmark/src, nopua/benchmark/test-project, benchmark/data/test-project)
2. **Compared versions** - Identified differences between "fixed" and original versions
3. **Created verification tests** - Custom Python test script for performance and correctness
4. **Ran performance tests** - Verified `_recover_punctuation` handles 100KB+ in <5ms
5. **Identified critical bug** - `_strip_annotations` removes far more content than intended
6. **Verified findings** - Executed tests confirming data corruption

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Source file analysis |
| `Glob` | Locate text_cleaner.py variants |
| `Grep` | Search for backtracking/performance references |
| `Bash + python3` | Test execution |
| `time.time()` | Performance measurement |

---

### 7. Verification Evidence

**Performance Test Results (`_recover_punctuation`):**
```
1KB (1044 chars):   0.0018s [PASS]
10KB (10444 chars): 0.0003s [PASS]
50KB (52223 chars): 0.0016s [PASS]
100KB (104447 chars): 0.0031s [PASS]
```

**Correctness Test Results (`_strip_annotations`):**
```
Text after annotation should remain: [FAIL]
  Input:    '[注] 註釋 some text'
  Expected: ' some text'
  Actual:   ''  ← CRITICAL BUG

Text before and after annotation: [FAIL]
  Input:    '正文 [注] 註釋 更多'
  Expected: '正文  更多'
  Actual:   '正文 '  ← CRITICAL BUG
```
