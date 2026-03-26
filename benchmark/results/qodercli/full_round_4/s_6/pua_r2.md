# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: pua | Run: 2
## Duration: 791.92s

---

## Summary

The chunk builder produces corrupted text because `_fixed_size_chunking()` slices UTF-8 encoded bytes at arbitrary positions, splitting multi-byte characters. The code masks this with `errors='replace'`, inserting U+FFFD replacement characters instead of preserving the original character data.

**7 issues identified:**
1. **CRITICAL**: UTF-8 byte boundary corruption in fixed-size chunking
2. **HIGH**: Position tracking mixes byte and character offsets
3. **HIGH**: Overlap calculation broken for multi-byte characters
4. **MEDIUM**: min_chunk_size uses characters (biased against CJK)
5. **MEDIUM**: Infinite loop risk when overlap >= max_chunk_size
6. **LOW**: Sentence-aware chunking position tracking inconsistent
7. **LOW**: merge_small_chunks compounds position confusion
