# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: pi | Run: 1
## Duration: 194.79s

---

## Summary

**Investigation Complete.** The reported `_recover_punctuation` catastrophic backtracking issue is a **misdiagnosis**. The actual problematic patterns are:

1. **`_split_sentences` line 270** — Nested quantifiers `((?:[.!?;]\s*)+)` create ReDoS vulnerability (HIGH)
2. **`_strip_annotations` line 282** — Non-greedy `.*?` with far lookahead causes quadratic scanning (MEDIUM)
3. **`_normalize_whitespace` line 262** — `\s` includes newlines, ambiguous matching (LOW)

Additional bugs discovered:
- Dead code: `punct_patterns` dict never used (lines 96-103)
- Stats counter bug: mixes character count with line count (lines 169-171)
- Cross-document dedup broken: uses local variable instead of instance variable (lines 235-251)
- Missing type validation in `clean()` method

The `_recover_punctuation` pattern `r"([\u4e00-\u9fffA-Za-z0-9])\n(?=[\u4e00-\u9fffA-Za-z0-9])"` is **provably safe** — linear time O(n) with positive lookahead.
