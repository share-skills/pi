# Scenario 7: Quality Filter Code Review
## Condition: nopua | Run: 2
## Duration: 70.81s

---

---

## Quick Reference: Priority Fix List

If you can only fix 3 things first:

1. **Fix the dedup empty string bug** - Causes massive silent data loss
2. **Add explicit perplexity enable flag** - Prevents false confidence
3. **Fix perplexity `inf` return value** - Prevents rejecting valid short texts

Want me to create a patched version of this file with all fixes applied?
