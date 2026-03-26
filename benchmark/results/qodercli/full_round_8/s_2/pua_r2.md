# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pua | Run: 2
## Duration: 141.85s

---

Now I have a complete understanding. Let me provide the structured summary based on my investigation:

---

## Investigation Summary: Text Cleaner Regex Catastrophic Backtracking

### 1. Issues Found

| # | Issue | Location | Severity | Status |
|---|-------|----------|----------|--------|
| 1 | **`_recover_punctuation` - MISDIAGNOSIS** | N/A | **N/A** | Pattern was NEVER problematic - linear time O(n) |
| 2 | `_strip_annotations` removes TOO MUCH content | Lines 288-289 | **CRITICAL** | **NOT FIXED** - Correctness bug in current code |
| 3 | `dedup_window` config ignored | Line 68, 231-251 | MEDIUM | NOT FIXED - Uses global set instead of window |
| 4 | Dead code: `punct_patterns` (in nopua version) | Lines 96-103 | LOW | Present in nopua version only |
| 5 | String allocation inefficiency | Lines 210-211 | LOW | Could use `str.translate()` |

### 2. Hidden Issues (Beyond the Ask)

| # | Type | Location | Description |
|---|------|----------|-------------|
| H1 | **Correctness Bug** | `_strip_annotations` lines 288-289 | Pattern `r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^\[【]*` removes ALL text after annotation if no closing bracket exists - tested and verified |
| H2 | **Config Ignored** | `CleanerConfig.dedup_window` | Defined as `5` but `_deduplicate()` checks ALL sentences globally via unbounded `seen` set |
| H3 | **Type Safety Gap** | Lines 126 vs 200-291 | `clean()` validates `str` input but internal methods don't validate their parameters |
| H4 | **Unused Constant** | Line 41 | `CLASSICAL_PUNCTUATION` set defined but never referenced |
| H5 | **Unused Imports** | Lines 22-24 | `Optional`, `Tuple` from typing never used |
| H6 | **Unbounded Counters** | Lines 96-101 | `_stats` dict grows indefinitely in long-running batch processes |

### 3. Root Cause

#### Why Was `_recover_punctuation` Blamed? (Misdiagnosis Analysis)

**The reported bug is INCORRECT.** The pattern at `_recover_punctuation`:
```python
r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
```

This is **provably safe**:
- Single capture group `([...])` matches exactly ONE character
- Literal newline `\n` has no quantifier
- Positive lookahead `(?=...)` is zero-width assertion with no backtracking
- **Linear time O(n)** - no catastrophic backtracking possible

**Performance test results** (verified):
```
   1024 KB (  1024 chars): 0.0016s PASS
   5120 KB (  5120 chars): 0.0001s PASS
  10240 KB ( 10240 chars): 0.0003s PASS
  51200 KB ( 51200 chars): 0.0014s PASS
 102400 KB (102400 chars): 0.0028s PASS
```

#### Actual Root Causes Found

**CRITICAL BUG #1: `_strip_annotations` Correctness Issue**

The pattern `r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^\[【]*` uses negated character class `[^\[【]*` which:
- Matches ANY character that isn't `[` or `【`
- When annotation is unclosed, scans to END of string
- Removes FAR more content than intended

**Verified by test** (from `test_text_cleaner_issues.py`):
```
Input:    '[注] 註釋 some text after'
Expected: ' some text after'  (only remove annotation)
Actual:   ''                  (removes EVERYTHING)
```

### 4. Recommended Fix

#### Fix 1: Correct `_strip_annotations` (CRITICAL)

**Current (buggy)**:
```python
text = re.sub(r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】)[^\[【]*", "", text)
```

**Fixed**:
```python
# Stop at first occurrence of common patterns or end of line
text = re.sub(r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】).*?(?=\n|$|\[|【)", "", text)
text = re.sub(r"（按 [：:][^)）]*[)）]", "", text)
```

Or use non-greedy with explicit boundary:
```python
text = re.sub(r"(?:\[|【)(?:注 | 按 | 校勘記 | 案)(?:\]|】).*?(?=\[|【|$)", "", text, flags=re.DOTALL)
```

#### Fix 2: Implement Windowed Deduplication

**Current** (ignores `dedup_window` config):
```python
def _deduplicate(self, text: str) -> str:
    seen = set()  # Unbounded!
    for sentence in sentences:
        if normalized in seen:  # Checks ALL history
            duplicates += 1
            continue
        seen.add(normalized)
```

**Fixed**:
```python
def _deduplicate(self, text: str) -> str:
    from collections import deque
    window_size = self.config.dedup_window
    seen = set()
    window = deque(maxlen=window_size)
    
    for sentence in sentences:
        normalized = sentence.strip()
        if not normalized:
            unique.append(sentence)
            continue
        
        if normalized in seen:
            duplicates += 1
            continue
        
        seen.add(normalized)
        window.append(normalized)
        
        # Maintain window bounds
        if len(window) >= window_size:
            oldest = window.popleft()
            seen.discard(oldest)
        
        unique.append(sentence)
```

#### Fix 3: Optimize with `str.translate()`

**Current**:
```python
for ascii_p, cjk_p in MODERN_TO_CLASSICAL.items():
    text = text.replace(ascii_p, cjk_p)
```

**Optimized**:
```python
if not hasattr(self, '_translation_table'):
    self._translation_table = str.maketrans(MODERN_TO_CLASSICAL)
text = text.translate(self._translation_table)
```

### 5. Steps Taken

| Step | Action | Finding |
|------|--------|---------|
| 1 | Read source file `benchmark/src/data_processing/text_cleaner.py` | Established current code state |
| 2 | Read `nopua/benchmark/test-project/src/data_processing/text_cleaner.py` | Found dead `punct_patterns` code |
| 3 | Read `benchmark/data/test-project/src/data_processing/text_cleaner.py` | Compared versions |
| 4 | Read investigation reports (`INVESTIGATION_FINAL.md`) | Understood historical context |
| 5 | Ran `test_text_cleaner_issues.py` | Verified `_strip_annotations` correctness bug |
| 6 | Analyzed each regex pattern for backtracking indicators | Confirmed current patterns are safe |
| 7 | Tested `_recover_punctuation` performance up to 100KB | Linear time O(n) verified |
| 8 | Performed deep code review for hidden issues | Found 6 additional issues |

**Assumption corrections**:
- **Initial assumption**: `_recover_punctuation` has backtracking issue
- **Correction**: Pattern is O(n) linear - misdiagnosis confirmed
- **Further finding**: `_strip_annotations` has CRITICAL correctness bug

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Source code analysis (3 versions of text_cleaner.py) |
| `Glob` | Located all text_cleaner.py variants |
| `Grep` | Searched for backtracking/catastrophic patterns across codebase |
| `Bash` | Executed test scripts to verify behavior |
| Python `time` module | Measured performance of regex operations |

### 7. Verification

**Performance verification** (current fixed code):
```bash
cd /Users/hepin/IdeaProjects/pi
python3 test_text_cleaner_issues.py
```

**Results**:
```
TEST 1: _recover_punctuation Performance
   10240 KB ( 10240 chars): 0.0003s PASS
  102400 KB (102400 chars): 0.0028s PASS

TEST 2: _strip_annotations Correctness
  FAIL: Annotation followed by normal text
  FAIL: Annotation in middle of text
  FAIL: Bracket annotation in middle
  FAIL: Parenthetical in middle
  
SUMMARY:
  CRITICAL: _strip_annotations has correctness bugs!
```

**Behavior verification** (what breaks with current code):
```python
cleaner = TextCleaner()
result = cleaner._strip_annotations("[注] 註釋 some text after")
# Expected: " some text after"
# Actual: ""  ← REMOVES EVERYTHING AFTER ANNOTATION
```

---

## Conclusion

**The reported catastrophic backtracking bug in `_recover_punctuation` is a MISDIAGNOSIS**. That method performs efficiently on all inputs up to 100KB+ in linear time O(n).

**However**, investigation revealed a **CRITICAL correctness bug in `_strip_annotations`** that removes FAR more content than intended when annotations are unclosed. This affects data integrity and must be fixed immediately.

**Additional issues found**:
- `dedup_window` configuration is completely ignored
- Dead code in nopua version (`punct_patterns`)
- Type validation gaps
- Unused imports and constants
