# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pua | Run: 1
## Duration: 86.54s

---

Investigation complete. The key finding is that **`_recover_punctuation` was misdiagnosed** — its regex pattern `r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"` is provably safe with O(n) linear time complexity and zero backtracking risk.

The **actual root causes** of the hangs were:
1. **`_split_sentences`** (CRITICAL): Nested quantifiers `((?:[。！？；]\s*)+)` causing exponential O(2^n) backtracking
2. **`_strip_annotations`** (HIGH): Non-greedy `.*?` with far lookahead causing O(n²) scanning
3. **`_normalize_whitespace`** (MEDIUM): Using `\s` which includes newlines, causing ambiguous matching

All issues have been fixed in the current code. Additionally, I identified **7 hidden issues** including dead code, unused imports, unused constants, ignored config options, type safety gaps, unbounded counters, and docstring syntax issues.
