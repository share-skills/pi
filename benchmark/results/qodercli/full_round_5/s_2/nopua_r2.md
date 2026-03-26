# Scenario 2: Text Cleaner Regex Catastrophic Backtracking
## Condition: nopua | Run: 2
## Duration: 55.73s

---

---

## Final Summary

### The Real Bug Location

Despite the task description pointing to `_recover_punctuation`, the **actual catastrophic backtracking bug** is in **`_strip_annotations()`** at lines 185-186:

```python
# BUGGY - Line 185
text = re.sub(r"[\[【](?:注 | 按 | 校勘記 | 案)[】\]].*?(?=[\[【]|$)", "", text)

# BUGGY - Line 186  
text = re.sub(r"（按 [：:].*?）", "", text)
```

### Why It Hangs

| Pattern Component | Problem |
|------------------|---------|
| `.*?` | Lazy quantifier tries minimal match first, then expands |
| `(?=[\[【]|$)` | Lookahead forces backtracking when no bracket found |
| Combined | On 10KB text with `[` but no annotation keyword → O(2^n) backtracking |

### One-Line Fix

```python
# Replace line 185
text = re.sub(r"[\[【](?:注 | 按 | 校勘記 | 案)[】\][^\[【]*", "", text, flags=re.DOTALL)

# Replace line 186
text = re.sub(r"（按 [：:][^）]*）", "", text)
```

The fix changes from "match anything until we find a bracket" (backtracking hell) to "match anything that isn't a bracket" (single-pass linear scan).
