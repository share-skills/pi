# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: nopua | Run: 1
## Duration: 308.7s

---

Now I have comprehensive evidence. Let me create a detailed summary:

---

## Investigation Summary

### 1. Issues Found

#### **Primary Issue: UTF-8 Byte Boundary Corruption in `_fixed_size_chunking()`**

**Location:** `src/data_processing/chunk_builder.py:136-177`

**Problem:** The method slices text at arbitrary **byte positions** (line 151: `chunk_bytes = text_bytes[pos:end]`), then decodes with `errors='replace'` (line 158). When a slice boundary lands mid-character, the incomplete byte sequence is replaced with U+FFFD (), permanently corrupting the text.

**Evidence from test output:**
```
Chunk 0: byte_range=[0:100], corrupted=True
  Last 5 chars: '宙洪荒天'
  Last 5 bytes: b'\xa4\xa9\xef\xbf\xbd'  # \xef\xbf\xbd = U+FFFD
```

The byte at position 100 cuts through a 3-byte Chinese character. The decoder replaces the incomplete sequence with .

#### **Secondary Issue: Overlap Calculation Exacerbates Corruption**

**Location:** `src/data_processing/chunk_builder.py:172-174`

**Problem:** The overlap mechanism (`pos = end - overlap`) compounds the problem by creating more opportunities for boundaries to land mid-character. Every chunk after the first has TWO potential corruption points (start AND end).

**Evidence:** Test 3 shows 17/32 chunks corrupted when overlap=33 is used.

#### **Hidden Issue: Position Tracking Mismatch in `_sentence_aware_chunking()`**

**Location:** `src/data_processing/chunk_builder.py:191, 203-204, 225`

**Problem:** The method tracks `char_pos` using character counts (line 225: `char_pos += len(sentence)`) but uses it for `start_pos`/`end_pos` metadata. This creates a **character vs byte position mismatch** that could cause issues downstream if consumers expect byte offsets.

```python
char_pos += len(sentence)  # Character count
# ...
start_pos=char_pos - len(chunk_text),  # Mixed with byte-based expectations
end_pos=char_pos,
```

#### **Hidden Issue: Sentence Splitting Regex Incomplete**

**Location:** `src/data_processing/chunk_builder.py:248`

**Problem:** The regex `r"((?:[！？；]+))"` only splits on specific Chinese punctuation. It misses:
- Western punctuation (`.`, `!`, `?`)
- Other Chinese sentence endings (`.`)
- Newlines as paragraph boundaries (despite `respect_paragraphs` config option existing but unused)

---

### 2. Root Cause

**Fundamental Design Flaw:** The code conflates **byte offsets** (for size control) with **character boundaries** (for valid Unicode slicing).

```python
# Line 149-151: Slices bytes directly
while pos < len(text_bytes):
    end = min(pos + max_size, len(text_bytes))
    chunk_bytes = text_bytes[pos:end]  # ← Cuts mid-character

# Line 156-158: Masks errors instead of preventing them
try:
    chunk_text = chunk_bytes.decode(self.config.encoding)
except UnicodeDecodeError:
    chunk_text = chunk_bytes.decode(self.config.encoding, errors="replace")  # ← Hides corruption
```

The comment on line 140-141 acknowledges byte-level sizing for tokenizers, but fails to ensure cuts happen at valid UTF-8 character boundaries.

---

### 3. Recommended Fix

**For `_fixed_size_chunking()`:** After slicing bytes, find the last complete UTF-8 character boundary before `end`:

```python
def _fixed_size_chunking(self, text: str, text_bytes: bytes,
                          source: str) -> List[Chunk]:
    chunks = []
    max_size = self.config.max_chunk_size
    overlap = self.config.overlap
    pos = 0
    chunk_idx = 0

    while pos < len(text_bytes):
        end = min(pos + max_size, len(text_bytes))

        # Find the last complete UTF-8 character boundary
        # UTF-8 continuation bytes start with 10xxxxxx (0x80-0xBF)
        adjust = 0
        while end - adjust > pos and (text_bytes[end - adjust - 1] & 0xC0) == 0x80:
            adjust += 1
        end = end - adjust

        chunk_bytes = text_bytes[pos:end]
        chunk_text = chunk_bytes.decode(self.config.encoding)  # No errors='replace' needed

        if len(chunk_text.strip()) >= self.config.min_chunk_size:
            # Calculate character-based positions for Chunk
            char_start = len(text_bytes[:pos].decode(self.config.encoding))
            char_end = len(text_bytes[:end].decode(self.config.encoding))
            chunk = Chunk(
                text=chunk_text,
                index=chunk_idx,
                source=source,
                start_pos=char_start,
                end_pos=char_end,
            )
            chunks.append(chunk)
            chunk_idx += 1

        # Move position forward with overlap
        pos = end - overlap
        if pos <= (chunks[-1].start_pos if chunks else 0):
            pos = end

    self._update_stats(chunks)
    return chunks
```

**Alternative (simpler):** Work entirely in character space, converting to bytes only for size checks:

```python
def _fixed_size_chunking(self, text: str, text_bytes: bytes, source: str) -> List[Chunk]:
    chunks = []
    max_chars = self.config.max_chunk_size // 3  # Conservative estimate
    overlap_chars = self.config.overlap // 3
    pos = 0

    while pos < len(text):
        # Take characters, then check byte size
        chunk_text = text[pos:pos + max_chars]
        while len(chunk_text.encode('utf-8')) > self.config.max_chunk_size:
            chunk_text = chunk_text[:-1]  # Trim until fits

        if len(chunk_text.strip()) >= self.config.min_chunk_size:
            chunk = Chunk(
                text=chunk_text,
                index=len(chunks),
                source=source,
                start_pos=pos,
                end_pos=pos + len(chunk_text),
            )
            chunks.append(chunk)

        pos += len(chunk_text) - overlap_chars

    self._update_stats(chunks)
    return chunks
```

---

### 4. Steps Taken

1. **Read source file** - Analyzed `chunk_builder.py` structure and logic
2. **Found test files** - Located `benchmark/test_chunk.py` and `debug_chunk.py`
3. **Ran reproduction tests** - Executed tests confirming 100% corruption rate in fixed-size mode
4. **Compared methods** - Verified `_sentence_aware_chunking()` avoids corruption (works at string level)
5. **Isolated root cause** - Confirmed byte-slicing + `errors='replace'` pattern causes data loss
6. **Identified hidden issues** - Position tracking mismatch, unused config options, incomplete regex

---

### 5. Tools Used

| Tool | Purpose |
|------|---------|
| `Glob` | Locate chunk_builder.py and test files |
| `Read` | Read source code and test files |
| `Bash` | Run Python reproduction scripts |
| Manual analysis | Trace execution flow, identify patterns |

---

### 6. Verification

**Verification Method:** Ran targeted test with known input, inspected output for U+FFFD characters

**Results:**
- Input: 160 Chinese characters (480 bytes)
- Output: 5 chunks, **ALL 5 corrupted** with  replacement character
- Byte inspection confirms mid-character cuts: `b'\xa4\xa9\xef\xbf\xbd'` (last 2 bytes of char + U+FFFD)

**Sentence-aware mode verification:**
- Same input text produces clean chunks (no corruption)
- Works at string level, never slices raw bytes

---

### Summary Table

| Component | Issue | Severity | Evidence |
|-----------|-------|----------|----------|
| `_fixed_size_chunking()` | UTF-8 boundary corruption | **Critical** | 100% chunks corrupted in tests |
| Overlap logic | Compounds corruption | High | More boundaries = more corruption |
| `_sentence_aware_chunking()` | Char/byte position mismatch | Medium | Metadata inconsistency |
| `_split_sentences()` | Incomplete punctuation set | Low | Misses some sentence types |
| `respect_paragraphs` | Config exists but unused | Low | Dead configuration |
