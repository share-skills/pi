# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: pua | Run: 1
## Duration: 324.85s

---

## Investigation Summary

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Unicode Boundary Corruption** - `_fixed_size_chunking()` cuts text at arbitrary byte positions, splitting multi-byte UTF-8 characters in half. When decoded with `errors='replace'`, corrupted bytes become U+FFFD replacement characters, losing original data. | Critical | Lines 136-177 |
| 2 | **Overlap Position Bug** - Same root cause as #1. The overlap calculation `pos = end - overlap` (line 172) can land in the middle of a multi-byte character, causing corruption in subsequent chunks. | Critical | Line 172 |
| 3 | **Empty Sentence from Leading Punctuation** - `_split_sentences()` produces an empty sentence `['。']` when text starts with Chinese punctuation. This creates meaningless chunks. | Minor | Lines 242-263 |
| 4 | **Mixed Script Limitation** - `_split_sentences()` only recognizes Chinese punctuation `[。！？；]`, not ASCII punctuation like `!?.`. Mixed Chinese/English text may not split correctly. | Minor | Line 248 |

### 2. Hidden Issues Discovered

| # | Issue | Impact |
|---|-------|--------|
| H1 | **Sentence-aware chunking is safe** - Only `_fixed_size_chunking()` has the Unicode bug. `_sentence_aware_chunking()` works at character level and doesn't corrupt text. | Good news: default config (`respect_sentences=True`) avoids corruption |
| H2 | **Position tracking verified** - Despite initial suspicion, `char_pos` tracking in `_sentence_aware_chunking()` correctly handles overlap. All chunk positions map back to original text accurately. | No additional bug here |
| H3 | **`merge_small_chunks()` propagates corruption** - If input chunks contain U+FFFD, merging preserves and propagates the corruption. Not a root cause but amplifies the problem. | Secondary concern |

### 3. Root Cause

**Primary Root Cause:** In `_fixed_size_chunking()` (lines 149-158):

```python
while pos < len(text_bytes):
    end = min(pos + max_size, len(text_bytes))
    chunk_bytes = text_bytes[pos:end]  # <-- Cuts at arbitrary BYTE position
    
    try:
        chunk_text = chunk_bytes.decode(self.config.encoding)
    except UnicodeDecodeError:
        chunk_text = chunk_bytes.decode(self.config.encoding, errors="replace")  # <-- Masks corruption
```

The code:
1. Slices `text_bytes` at byte offsets without regard for UTF-8 character boundaries
2. Uses `errors='replace'` which silently replaces invalid byte sequences with U+FFFD
3. The original character bytes are **lost forever** - this is data corruption, not just display issues

**Why it happens:** Chinese characters are 3 bytes each in UTF-8. With `max_chunk_size=256` and `overlap=32`:
- Chunk ends at byte 256, but 256 ÷ 3 = 85.33, so byte 256 is in the middle of a character
- Next chunk starts at byte 256 - 32 = 224, also potentially mid-character

### 4. Recommended Fix

**Fix for `_fixed_size_chunking()`:** After slicing bytes, find the last complete UTF-8 character boundary:

```python
def _fixed_size_chunking(self, text: str, text_bytes: bytes, source: str) -> List[Chunk]:
    chunks = []
    max_size = self.config.max_chunk_size
    overlap = self.config.overlap
    pos = 0
    chunk_idx = 0

    while pos < len(text_bytes):
        end = min(pos + max_size, len(text_bytes))
        
        # FIX: Ensure we don't cut in the middle of a multi-byte UTF-8 character
        # UTF-8 continuation bytes are 10xxxxxx (0x80-0xBF)
        while end > pos and (text_bytes[end - 1] & 0xC0) == 0x80:
            end -= 1
        
        if end <= pos:  # Safety check
            break
            
        chunk_bytes = text_bytes[pos:end]
        chunk_text = chunk_bytes.decode(self.config.encoding)  # No need for errors='replace'

        if len(chunk_text.strip()) >= self.config.min_chunk_size:
            chunk = Chunk(
                text=chunk_text,
                index=chunk_idx,
                source=source,
                start_pos=pos,  # Note: these are now BYTE positions, not char positions
                end_pos=end,
            )
            chunks.append(chunk)
            chunk_idx += 1

        # Move position forward with overlap
        next_pos = end - overlap
        
        # FIX: Also adjust overlap position to character boundary
        while next_pos > pos and (text_bytes[next_pos - 1] & 0xC0) == 0x80:
            next_pos -= 1
        
        if next_pos <= pos:
            next_pos = end  # Avoid infinite loop
        
        pos = next_pos

    self._update_stats(chunks)
    return chunks
```

**Alternative approach:** Work entirely at the character level, then convert to bytes for size checking:

```python
def _fixed_size_chunking(self, text: str, text_bytes: bytes, source: str) -> List[Chunk]:
    chunks = []
    max_chars = self.config.max_chunk_size // 3  # Conservative estimate
    overlap_chars = self.config.overlap // 3
    pos = 0
    chunk_idx = 0

    while pos < len(text):
        # Estimate end position, then verify byte size
        end = min(pos + max_chars, len(text))
        chunk_text = text[pos:end]
        
        # Adjust if byte size exceeds limit
        while len(chunk_text.encode(self.config.encoding)) > self.config.max_chunk_size and len(chunk_text) > 1:
            chunk_text = chunk_text[:-1]
            end -= 1
        
        if len(chunk_text.strip()) >= self.config.min_chunk_size:
            chunk = Chunk(
                text=chunk_text,
                index=chunk_idx,
                source=source,
                start_pos=pos,
                end_pos=end,
            )
            chunks.append(chunk)
            chunk_idx += 1

        # Calculate overlap at character level
        overlap_text = chunk_text[-overlap_chars:] if len(chunk_text) > overlap_chars else chunk_text
        pos = end - len(overlap_text)
        
        if pos <= chunks[-1].start_pos if chunks else 0:
            pos = end

    self._update_stats(chunks)
    return chunks
```

### 5. Steps Taken

1. **Read source code** - Analyzed all 335 lines of `chunk_builder.py`
2. **Located test files** - Found existing tests that demonstrate the bug
3. **Reproduced corruption** - Ran tests confirming 100% corruption rate in fixed-size mode
4. **Isolated root cause** - Traced to byte-level slicing without UTF-8 boundary checks
5. **Verified sentence-aware mode** - Confirmed it's unaffected (works at character level)
6. **Tested edge cases** - Sentence splitter, overlap logic, position tracking
7. **Checked related functions** - `merge_small_chunks()`, `_split_sentences()`

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files |
| `Glob` | Find chunk_builder.py instances |
| `Grep` | Search for related test files |
| `Bash` | Run Python tests, reproduce bugs, verify findings |

### 7. Verification Evidence

```
BUG 1 - Fixed-Size Corruption:
  Input: 800 chars (2400 bytes)
  Output: 12 chunks, ALL 12 corrupted with U+FFFD
  
BUG 2 - Overlap Corruption:  
  Input: 1350 chars (2050 bytes)
  Output: 32 chunks, 17 corrupted

Sentence-Aware Mode:
  Multiple tests with various configs
  Result: 0 corruption (works at character level)
```

### Additional Notes

- The comment on lines 153-154 acknowledges the issue but treats `errors='replace'` as acceptable: "masks the corruption by inserting replacement characters". This is incorrect - it loses data.
- Default configuration uses `respect_sentences=True`, which avoids this bug. Users who enable `respect_sentences=False` for performance or other reasons will encounter 100% corruption with Chinese text.
