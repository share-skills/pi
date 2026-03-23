# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: nopua | Run: 2
## Duration: 46.44s

---

---

## Summary Report

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **UTF-8 byte slicing corrupts multi-byte characters** | `_fixed_size_chunking()` line 150-158 | Critical |
| 2 | **Position tracking mixes character/byte offsets** | `_sentence_aware_chunking()` line 203-204, 234-235 | Medium |
| 3 | **Overlap logic can produce duplicates before correction** | `_fixed_size_chunking()` line 172-174 | Low |

### 2. Hidden Issues

| # | Issue | Location |
|---|-------|----------|
| 1 | Sentence splitter may lose final punctuated sentence | `_split_sentences()` line 260-261 |
| 2 | No validation of UTF-8 validity after decode with `errors='replace'` | Throughout |
| 3 | `merge_small_chunks()` can create overlapping position ranges | Line 320-326 |

### 3. Root Cause

The code slices UTF-8 **encoded bytes** at arbitrary byte positions without checking for multi-byte character boundaries. Chinese characters are 3 bytes each; cutting at byte N when N is not aligned to a character boundary produces incomplete byte sequences that decode to garbled characters like `\xe4\xb8` or ``.

### 4. Recommended Fix

**Switch from byte-level to character-level slicing** in `_fixed_size_chunking()`:
- Use `text[pos:end]` (character indices) instead of `text_bytes[pos:end]` (byte indices)
- Validate byte size after slicing, trim if necessary
- This eliminates UTF-8 corruption entirely

### 5. Steps Taken

1. Read full `chunk_builder.py` file
2. Traced execution flow through `build_chunks()` → `_fixed_size_chunking()` and `_sentence_aware_chunking()`
3. Identified byte-slicing pattern at line 150-151
4. Recognized `errors='replace'` as masking rather than fixing the problem
5. Audited related methods for secondary issues

### 6. Tools Used

- `Read` tool: Read source file
- Manual code analysis: Traced algorithm logic and identified Unicode handling bugs

### 7. Verification

**Evidence of findings**:
- Line 150: `end = min(pos + max_size, len(text_bytes))` — slices at byte boundary
- Line 151: `chunk_bytes = text_bytes[pos:end]` — produces incomplete UTF-8 sequences
- Line 153-158 comment explicitly acknowledges corruption masking with `errors='replace'`
- Chinese characters encode to 3 bytes in UTF-8, making mid-character cuts statistically likely with 512-byte chunks
