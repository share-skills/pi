# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: nopua | Run: 1
## Duration: 218.84s

---

## Investigation Report: Chunk Builder Unicode Boundary Corruption

### 1. Issues Found

#### Issue #1: Critical - UTF-8 Byte Boundary Corruption in `_fixed_size_chunking` (Lines 136-177)

**Location:** `benchmark/data/test-project/src/data_processing/chunk_builder.py:150-158`

**Problem:** The code slices text at arbitrary **byte positions**, then uses `errors='replace'` to handle UnicodeDecodeError. This masks the corruption by inserting U+FFFD replacement characters and **permanently loses the original character data**.

```python
# Line 150-158: Cuts at byte boundary
end = min(pos + max_size, len(text_bytes))
chunk_bytes = text_bytes[pos:end]

# Line 155-158: Masks corruption instead of fixing it
try:
    chunk_text = chunk_bytes.decode(self.config.encoding)
except UnicodeDecodeError:
    chunk_text = chunk_bytes.decode(self.config.encoding, errors="replace")  # BUG!
```

**Evidence:** Test output shows `\xef\xbf\xbd` (U+FFFD bytes) in chunk endings:
```
Chunk 0: Last 10 bytes: b'\x9a\xe3\x80\x8c\xe5\xad\xb8\xef\xbf\xbd'
         Last 10 chars: '說乎？」子曰：「學'  ← U+FFFD corruption
```

---

#### Issue #2: Position Tracking Mismatch - Byte Offsets vs Character Indices (Lines 165-166, 172-174)

**Location:** Lines 165-166, 172-174

**Problem:** `start_pos` and `end_pos` are stored as **byte offsets**, but they should represent **character indices** for proper text slicing. This creates a fundamental inconsistency where `text[start_pos:end_pos]` doesn't match `chunk.text`.

**Evidence:**
```
Chunk 0: start=0, end=150, actual_text_len=50
  MISMATCH! slice len=150, chunk text len=50
Chunk 4: start=480, end=630, actual_text_len=50
  MISMATCH! slice len=0, chunk text len=50  ← Completely wrong!
```

---

#### Issue #3: Overlap Calculation Lands on Byte Boundaries (Line 172)

**Location:** Line 172

**Problem:** `pos = end - overlap` moves the position backward by overlap bytes, but this often lands in the middle of a multi-byte UTF-8 character, causing the corruption described in Issue #1.

**Evidence:** With `overlap=50` bytes, the cut point frequently falls within 3-byte Chinese characters.

---

#### Issue #4: Missing Long Sentence Splitting in `_sentence_aware_chunking` (Lines 179-240)

**Location:** Lines 179-240

**Problem:** When a single sentence exceeds `max_chunk_size`, the code doesn't split it. It just creates one oversized chunk, defeating the purpose of chunking for training data with strict size limits.

**Evidence:**
```
Text: 221 chars, 663 bytes
max_chunk_size: 100 bytes
Generated 1 chunks: 663 bytes  ← Should be 7+ chunks!
```

---

#### Issue #5: Overlap Logic Doesn't Preserve Full Sentences (Lines 209-221)

**Location:** Lines 209-221

**Problem:** The overlap logic keeps partial sentences based on byte size, not complete sentences. This breaks the "sentence-aware" guarantee and causes awkward context cuts.

**Evidence:**
```
Chunk 0 ends: ...亦說乎？」子曰：「學而時習之，不亦說乎？
Chunk 1 starts: 」子曰：「學而時習之，不亦說乎？」子曰：...
← Overlap starts with closing quotation mark, not full sentence
```

---

### 2. Hidden Issues Discovered

#### Hidden Issue #1: `_split_sentences` Regex Incomplete (Lines 242-263)

The regex `r"((?:[]]+))"` doesn't handle all classical Chinese punctuation:
- Missing: `」``【】` (brackets)
- Missing: `:` `` (Western-style colons/commas common in modern texts)
- Edge case: Consecutive punctuation like `?!` or `!!` may not group correctly

#### Hidden Issue #2: `merge_small_chunks` Creates Invalid Positions (Lines 300-334)

When merging chunks, the merged chunk's `end_pos` is taken from the last chunk, but there's no validation that the resulting text actually spans from `start_pos` to `end_pos` in the original text.

#### Hidden Issue #3: No Validation After Chunk Creation

No method validates that:
- All chunks decode without U+FFFD characters
- Concatenating all chunks reproduces the original text
- `chunk.byte_size` matches expected size from `start_pos`/`end_pos`

---

### 3. Root Cause

**Fundamental Design Flaw:** The code conflates **byte offsets** (for size control) with **character indices** (for text manipulation). 

UTF-8 encoding means:
- 1 ASCII character = 1 byte
- 1 Chinese character = 3 bytes (typically)

Cutting at byte N doesn't equal cutting at character N. The fix requires:
1. Always cut at **character boundaries**
2. Track both byte size AND character count separately
3. Adjust cut points backward to the last complete character when needed

---

### 4. Recommended Fix

#### For `_fixed_size_chunking`:

```python
def _fixed_size_chunking(self, text: str, text_bytes: bytes, source: str) -> List[Chunk]:
    """Fixed: Cut at character boundaries, not byte boundaries."""
    chunks = []
    max_size = self.config.max_chunk_size
    overlap_chars = self.config.overlap  # Convert to character-based
    char_pos = 0
    chunk_idx = 0
    
    while char_pos < len(text):
        # Estimate ending character position based on average byte/char ratio
        # Then adjust to stay within byte limit
        remaining_bytes = len(text[char_pos:].encode(self.config.encoding))
        
        if remaining_bytes <= max_size:
            # Take all remaining text
            chunk_text = text[char_pos:]
            chunk = Chunk(
                text=chunk_text,
                index=chunk_idx,
                source=source,
                start_pos=char_pos,
                end_pos=len(text),
            )
            chunks.append(chunk)
            break
        
        # Binary search for the right character count that fits in max_size bytes
        low, high = 1, len(text) - char_pos
        best_char_count = 1
        
        while low <= high:
            mid = (low + high) // 2
            candidate = text[char_pos:char_pos + mid]
            candidate_bytes = len(candidate.encode(self.config.encoding))
            
            if candidate_bytes <= max_size:
                best_char_count = mid
                low = mid + 1
            else:
                high = mid - 1
        
        chunk_text = text[char_pos:char_pos + best_char_count]
        
        # Validate: ensure no corruption
        try:
            chunk_text.encode(self.config.encoding).decode(self.config.encoding)
        except UnicodeDecodeError:
            # Should never happen now, but fail loudly if it does
            logger.error(f"Unicode corruption detected at char_pos={char_pos}")
            raise
        
        chunk = Chunk(
            text=chunk_text,
            index=chunk_idx,
            source=source,
            start_pos=char_pos,
            end_pos=char_pos + best_char_count,
        )
        chunks.append(chunk)
        chunk_idx += 1
        
        # Move forward with character-based overlap
        overlap_chars_count = min(len(chunk_text), overlap_chars // 3 + 1)  # Estimate
        char_pos = char_pos + best_char_count - overlap_chars_count
        
        if char_pos <= chunks[-1].start_pos:
            char_pos = chunks[-1].end_pos  # Avoid infinite loop
    
    self._update_stats(chunks)
    return chunks
```

#### For `_sentence_aware_chunking`:

Add handling for oversized sentences:

```python
# Inside the for sentence in sentences loop, after line 196:
if sentence_size > self.config.max_chunk_size:
    # Single sentence exceeds limit - must split mid-sentence
    # Use character-based splitting from _fixed_size_chunking
    sub_chunks = self._split_oversized_sentence(sentence, char_pos, chunk_idx, source)
    chunks.extend(sub_chunks)
    chunk_idx += len(sub_chunks)
    char_pos += len(sentence)
    continue
```

---

### 5. Steps Taken

| Step | Tool/Method | Finding |
|------|-------------|---------|
| 1 | Read source file | Understood chunking architecture |
| 2 | Read test files | Identified expected behavior |
| 3 | Ran `test_chunk.py` | Reproduced U+FFFD corruption in fixed-size mode |
| 4 | Tested sentence-aware mode | Found missing long-sentence handling |
| 5 | Tested overlap boundaries | Confirmed overlap causes byte-boundary cuts |
| 6 | Verified position tracking | Found byte/char index mismatch |
| 7 | Analyzed overlap continuity | Found partial sentence overlaps |

---

### 6. Tools Used

- **Read tool**: Source code analysis
- **Glob tool**: Located test files  
- **Bash tool**: Ran reproduction tests with Python
- **Manual analysis**: Traced execution flow and identified root causes

---

### 7. Verification

**Verification Method:** Executed `benchmark/test_chunk.py` which demonstrates:

1. **Fixed-size chunking corruption rate:** 12/12 chunks corrupted (100%)
   ```
   Chunk 0-11: All contain U+FFFD replacement characters
   ```

2. **Sentence-aware chunking:** Works for normal sentences, but:
   - Silent failure on oversized sentences (no splitting)
   - Partial sentence overlaps break context preservation

3. **Overlap boundary test:** 17/32 chunks corrupted (53%)
   ```
   Total corrupted: 17/32
   ```

**Confidence Level:** HIGH - Direct evidence from test output confirms all identified issues.
