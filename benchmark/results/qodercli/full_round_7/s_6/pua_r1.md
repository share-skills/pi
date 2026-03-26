# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: pua | Run: 1
## Duration: 51.61s

---

---

## Structured Summary

### 1. Issues Found

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 1 | **CRITICAL** | Byte-level slicing splits multi-byte UTF-8 characters | `_fixed_size_chunking():151` |
| 2 | **CRITICAL** | Error handling masks corruption with `` instead of fixing | Lines 155-158 |
| 3 | **HIGH** | No byte-boundary protection for oversized sentences | `_sentence_aware_chunking():179-240` |
| 4 | **MEDIUM** | Position tracking mixes char/byte offsets inconsistently | Lines 191, 203-204 |
| 5 | **LOW** | Overlap logic untested for sub-sentence splitting | Lines 210-218 |

### 2. Hidden Issues

- **Data integrity loss:** `errors='replace'` causes silent, permanent data loss
- **No validation:** No method to detect `` or encoding errors post-chunking
- **Size calculation confusion:** Mix of `size` (chars) and `byte_size` (bytes)
- **Long sentence vulnerability:** Classical texts without punctuation can create oversized "sentences"

### 3. Root Cause

**Slicing UTF-8 encoded bytes at arbitrary positions without checking character boundaries.** When `text_bytes[pos:end]` cuts through a multi-byte character (e.g., `\xe4\xb8\x80` → `\xe4\xb8`), the resulting bytes are invalid UTF-8. The `errors='replace'` handler hides this by inserting ``, but the original character is lost.

### 4. Recommended Fix

Add `_find_safe_byte_boundary()` helper that scans backward from target position to find valid UTF-8 start byte (not a continuation byte `0x80-0xBF`). Use this before every byte slice operation.

### 5. Steps Taken

- Read full 335-line source file
- Identified byte-slicing pattern in `_fixed_size_chunking()`
- Traced encode→slice→decode data flow
- Analyzed both chunking paths (fixed-size and sentence-aware)
- Checked metadata consistency (char vs byte positions)
- Reviewed UTF-8 encoding specification

### 6. Tools Used

- File read (full source analysis)
- Pattern search (locate decode/slice operations)
- Manual code tracing and UTF-8 spec analysis

### 7. Verification

- Confirmed bug location: line 151 slices bytes directly
- Developer comment (lines 153-154) admits `errors='replace'` "masks corruption"
- UTF-8 spec confirms Chinese chars = 3 bytes typically
- Sentence-aware path safer but still vulnerable for oversized sentences
