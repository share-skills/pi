# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pua | Run: 2
## Duration: 160.91s

---

## Structured Summary

### 1. Issues Found

| # | Issue | Severity | Location | Description |
|---|-------|----------|----------|-------------|
| 1 | **Dead Code** | MEDIUM | `text_cleaner.py:96-103` | `punct_patterns` dictionary (6 regex patterns) defined but never used anywhere |
| 2 | **Config Ignored** | MEDIUM | `text_cleaner.py:228-254` | `dedup_window=5` config defined but `_deduplicate()` uses global seen set, not window-limited |
| 3 | **Stats Calculation Bug** | LOW | `text_cleaner.py:169-171` | Calculates `original_len - len(lines)` mixing character count with list length |
| 4 | **Whitespace Pattern Issue** | LOW | `text_cleaner.py:262` | `\n\s*\n` uses `\s` which includes `\n`, may match more than intended |
| 5 | **Unbounded Non-Greedy Match** | LOW | `text_cleaner.py:282` | `.*?` in `_strip_annotations` scans to end of string on unclosed markers |

### 2. Hidden Issues Beyond the Ask

| Hidden Issue | Category | Impact |
|--------------|----------|--------|
| `punct_patterns` dead code | Code Quality | Memory waste, confusing API, suggests incomplete implementation |
| `dedup_window` ignored | Logic Bug | Memory grows unbounded; performance degradation on long documents |
| Inconsistent type validation | API Design | `clean()` validates str, internal methods don't |
| Docstring contradictions | Documentation | `clean_batch()` says "no cross-document dedup" but name implies shared state |
| Integer overflow risk | Edge Case | Stats counters never checked for overflow |

### 3. Root Cause Analysis

**The reported catastrophic backtracking issue does NOT exist in the current implementation.**

The current `_recover_punctuation` pattern:
```python
r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"
```

This is **safe** because:
- Uses positive character classes (not negated)
- Newline does NOT match the character class (no overlap)
- Single lookahead assertion doesn't consume characters
- Linear O(n) complexity regardless of input

**Performance verification:**
- 1KB: 0.0000s
- 10KB: 0.0001s
- 50KB: 0.0006s
- 100KB: 0.0012s

### 4. Recommended Fixes

**Priority 1 - Remove Dead Code:**
```python
# Delete lines 96-103: self.punct_patterns = {...}
```

**Priority 2 - Fix dedup_window Implementation:**
```python
def _deduplicate(self, text: str) -> str:
    sentences = self._split_sentences(text)
    seen = set()
    unique = []
    duplicates = 0
    window_size = self.config.dedup_window
    
    for i, sentence in enumerate(sentences):
        normalized = sentence.strip()
        if not normalized:
            unique.append(sentence)
            continue
        
        # Only check recent sentences within window
        window_start = max(0, i - window_size)
        recent_seen = {s.strip() for s in sentences[window_start:i] if s.strip()}
        
        if normalized in recent_seen:
            duplicates += 1
            continue
        
        seen.add(normalized)
        unique.append(sentence)
    
    self._stats["duplicates_removed"] += duplicates
    return "".join(unique)
```

**Priority 3 - Fix Stats Calculation:**
```python
original_line_count = text.count('\n') + 1
lines = [l for l in text.split("\n") if len(l.strip()) >= self.config.min_line_length or not l.strip()]
removed_lines = original_line_count - len(lines)
if removed_lines > 0:
    self._stats["lines_removed"] += removed_lines
```

### 5. Steps Taken

1. Read source files (`text_cleaner.py` in multiple locations)
2. Searched codebase for related issues, tests, and investigation reports
3. Created and ran performance tests with inputs from 1KB to 250KB
4. Tested pathological inputs designed to trigger catastrophic backtracking
5. Analyzed all 9 regex patterns in the codebase
6. Identified dead code paths and unused configurations
7. Verified behavioral correctness of cleaning pipeline
8. Compared findings against existing investigation reports

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Source code analysis |
| `Grep` | Pattern/search across codebase |
| `Glob` | File discovery |
| `Bash` + `python3` | Test execution |
| Custom Python scripts | Regex performance testing |
| `time.time()` | Performance measurement |

### 7. Verification Evidence

**All tests passed:**
```
✓ _recover_punctuation (15KB in 0.0024s)
✓ _recover_punctuation pathological (30KB in 0.0003s)
✓ Full pipeline (62KB in 0.0040s)
✓ Full pipeline (227KB in 0.0152s)
✓ _strip_annotations worst case (50KB in 0.0003s)
✓ All punct_patterns patterns (14KB each in <0.0003s)
```

**Conclusion:** The `_recover_punctuation` method is performant and does not exhibit catastrophic backtracking. The most significant issues are dead code removal and the ignored `dedup_window` configuration.
