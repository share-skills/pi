# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: nopua | Run: 2
## Duration: 92.23s

---

## Investigation Summary

### 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **UTF-8 Byte Boundary Corruption** | Critical | `_fixed_size_chunking()` lines 149-177 |
| 2 | **Position Tracking Inconsistency** | High | `_fixed_size_chunking()` lines 165-166 |
| 3 | **Overlap Logic Breaks UTF-8 Sequences** | High | `_fixed_size_chunking()` lines 172-174 |
| 4 | **Incomplete Chinese Punctuation Set** | Medium | `_split_sentences()` line 248 |

---

### 2. Hidden Issues Discovered

| # | Issue | Impact |
|---|-------|--------|
| 5 | **`errors='replace'` silently masks corruption** | Replacement characters (U+FFFD) inserted but no warning/error raised |
| 6 | **Chunk metadata positions are ambiguous** | `start_pos`/`end_pos` sometimes represent byte offsets, sometimes char offsets - inconsistent |
| 7 | **Overlap calculation doesn't account for UTF-8 boundaries** | Overlap region can start mid-character, causing corruption in overlapping chunks too |
| 8 | **Closing quotation marks treated as sentence starters** | Text like `「學而時習之。」孟子曰` splits incorrectly, leaving `」` at start of next "sentence" |

---

### 3. Root Cause

**Primary Root Cause:** The code slices text at **byte-level** (`text_bytes[pos:end]`) but then tries to use those byte offsets as if they were **character-level** positions for:
- Chunk metadata (`start_pos`, `end_pos`)
- Overlap calculations
- Position advancement

When a byte slice cuts through a multi-byte UTF-8 character (e.g., cutting `e9bb83` at byte 10 leaves `e9` incomplete), decoding fails. Using `errors='replace'` hides the problem by inserting U+FFFD replacement characters instead of raising an error.

**Evidence from tests:**
```
Chunk 0: start_pos=0, end_pos=50
  text preview: '天地玄黃宇宙洪荒日月盈昃辰宿列張'
  Last char: '', bytes: efbfbd  ← U+FFFD replacement character
```

---

### 4. Recommended Fix

**Fix 1: Work at character level, not byte level**

```python
def _fixed_size_chunking(self, text: str, text_bytes: bytes,
                          source: str) -> List[Chunk]:
    chunks = []
    max_chars = self.config.max_chunk_size  # Use character limit
    overlap_chars = self.config.overlap
    pos = 0  # Character position, not byte position
    chunk_idx = 0

    while pos < len(text):
        # Take up to max_chars characters
        chunk_text = text[pos:pos + max_chars]
        chunk_byte_size = len(chunk_text.encode('utf-8'))

        # If chunk is too large in bytes, trim characters
        while chunk_byte_size > self.config.max_chunk_size and len(chunk_text) > 1:
            chunk_text = chunk_text[:-1]
            chunk_byte_size = len(chunk_text.encode('utf-8'))

        if len(chunk_text.strip()) >= self.config.min_chunk_size:
            chunk = Chunk(
                text=chunk_text,
                index=chunk_idx,
                source=source,
                start_pos=pos,
                end_pos=pos + len(chunk_text),
            )
            chunks.append(chunk)
            chunk_idx += 1

        # Move forward by character count, not bytes
        pos += len(chunk_text) - overlap_chars
        if pos <= chunks[-1].start_pos if chunks else 0:
            pos = chunks[-1].start_pos + len(chunks[-1].text)

    self._update_stats(chunks)
    return chunks
```

**Fix 2: Validate UTF-8 boundaries explicitly**

```python
# Instead of errors='replace', validate and fix:
try:
    chunk_text = chunk_bytes.decode(self.config.encoding)
except UnicodeDecodeError:
    # Find the last complete UTF-8 character
    valid_end = len(chunk_bytes)
    while valid_end > 0:
        try:
            chunk_text = chunk_bytes[:valid_end].decode(self.config.encoding)
            break
        except UnicodeDecodeError:
            valid_end -= 1
    else:
        logger.warning(f"Skipping unparseable chunk at position {pos}")
        continue
```

**Fix 3: Expand Chinese punctuation set**

```python
# Line 248: Add closing quotation marks and other CJK punctuation
parts = re.split(
    r"((?:[。！？；!?」』】〉》…‥]+))",
    text
)
```

---

### 5. Steps Taken

1. **Read the source file** (`chunk_builder.py`) - understood the chunking architecture
2. **Read test file** (`test_chunk_builder.py`) - found existing test for byte boundary issue but no assertion
3. **Created debug script** - reproduced the corruption with controlled inputs
4. **Analyzed output** - identified U+FFFD replacement characters in chunks
5. **Created deep investigation script** - isolated each bug:
   - Test 1: Confirmed UTF-8 byte slicing causes corruption
   - Test 2: Sentence-aware chunking works (uses character operations)
   - Test 3: Demonstrated root cause (mid-character byte cut)
   - Test 4: Showed position tracking inconsistency
   - Test 5: Mixed 1-byte/3-byte chars expose overlap bugs
   - Test 6: Missing Chinese punctuation marks
   - Test 7: Verified sentence-aware positions are correct
6. **Cleaned up test files**

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Glob` | Locate chunk_builder.py and test files |
| `Read` | Read source code and tests |
| `Grep` | Search for corruption-related patterns |
| `Bash` | Run Python debug scripts |
| `Write` | Create temporary investigation scripts |

---

### 7. Verification

**Verification Method:** Executed two Python scripts that:
1. Created a `ChunkBuilder` with small `max_chunk_size` to force splits
2. Processed classical Chinese text (all 3-byte UTF-8 characters)
3. Checked each chunk for:
   - Presence of U+FFFD replacement characters
   - Last character's hex bytes (confirmed `efbfbd` = U+FFFD)
   - Position tracking consistency

**Key Evidence:**
```
Chunk 0: text preview: '天地玄黃宇宙洪荒日月盈昃辰宿列張'
  WARNING: Contains replacement character (U+FFFD)
  Last char: '', bytes: efbfbd  ← Confirmed corruption
```

**Sentence-aware chunking verified working:**
```
Chunk 0: text: '子曰：學而時習之，不亦說乎？有朋自遠方來，不亦樂乎？'
  ✓ No corruption (operates on character level, not bytes)
```
