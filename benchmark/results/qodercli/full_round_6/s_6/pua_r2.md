# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: pua | Run: 2
## Duration: 128.9s

---

## Summary Table

| Issue | Severity | Location | Fix Complexity |
|-------|----------|----------|----------------|
| Unicode boundary corruption | CRITICAL | `_fixed_size_chunking:151` | Medium (add boundary finder) |
| Position tracking bug | HIGH | `_sentence_aware_chunking:203-204,225` | Medium (track both char+byte) |
| Incomplete sentence regex | MEDIUM | `_split_sentences:248` | Low (extend regex pattern) |
| Overlap logic inconsistency | MEDIUM | `_fixed_size_chunking:171-174` | Low (use consistent position type) |
| Chunk ID collision risk | LOW | `Chunk.__init__:50` | Low (fix after position bug fixed) |
| No decode validation | LOW | `_fixed_size_chunking:156-158` | Low (add validation check) |
| Size calculation confusion | LOW | `build_chunks:120-122` | Low (clarify docs or unify) |
