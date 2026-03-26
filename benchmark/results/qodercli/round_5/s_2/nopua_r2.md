# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: nopua | Run: 2
## Duration: 98.01s

---

## Final Summary

| Category | Count |
|----------|-------|
| **Critical Issues** | 1 (catastrophic backtracking in `_strip_annotations`) |
| **High Severity** | 1 (performance bug in second annotation pattern) |
| **Medium Severity** | 1 (logic bug in `_split_sentences`) |
| **Low Severity** | 1 (stats calculation bug) |
| **Hidden Issues** | 4 (unused code, dedup state leak, thread safety) |

**Root Cause:** The `_strip_annotations()` method uses `.*?(?=[\[【]|$)` which causes O(n²) backtracking on large inputs with many bracket characters. The user misattributed this to `_recover_punctuation` because it's the earlier visible step in the pipeline.

**Fix:** Replace lazy quantifiers with negated character classes: `.*?` → `[^【[]*`
