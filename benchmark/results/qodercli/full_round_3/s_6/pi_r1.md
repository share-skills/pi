# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: pi | Run: 1
## Duration: 37.53s

---

# PI · Debug Report · Chunk Builder Unicode Corruption

## 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **Unicode corruption at chunk boundaries** - `_fixed_size_chunking` cuts text at byte offsets without validating UTF-8 character boundaries | `chunk_builder.py:147-153` | 🔴 Blocker |
| 2 | **Position tracking bug in sentence-aware chunking** - `char_pos` calculation is incorrect, causing wrong `start_pos`/`end_pos` values | `chunk_builder.py:189-191` | 🔴 Blocker |
| 3 | **Infinite loop protection fails** - `pos <= chunks[-1].start_pos` check accesses empty list when first chunk is too small | `chunk_builder.py:162` | 🟡 High |
| 4 | **Overlap can cause backward position movement** - When overlap > chunk size written, `pos` moves backward creating duplicate/infinite processing | `chunk_builder.py:160-163` | 🟡 High |
| 5 | **Sentence splitter loses trailing content** - Trailing text without punctuation appended incorrectly when `parts` length is odd | `chunk_builder.py:215-216` | 🟡 Medium |
| 6 | **Unused import** - `Iterator` imported but not used in type hints properly | `chunk_builder.py:9` | ⚪ Low |

---

## 2. Hidden Issues

| # | Issue | Location | Category |
|---|-------|----------|----------|
| 7 | **Security: Path traversal in source metadata** - `source` parameter used directly in `chunk_id` hash without sanitization | `chunk_builder.py:39` | 🔒 Security |
| 8 | **Resource leak risk** - `build_chunks_from_file` doesn't use context manager properly for exception safety | `chunk_builder.py:227-235` | 🔒 Resource |
| 9 | **Hardcoded encoding default** - File encoding hardcoded to "utf-8" without fallback detection | `chunk_builder.py:227` | ⚙️ Config |
| 10 | **Memory inefficiency** - `build_chunks_streaming` collects all chunks then yields, defeating purpose of streaming | `chunk_builder.py:237-241` | ⚡ Performance |
| 11 | **Missing validation** - No check for negative config values (max_chunk_size, overlap, min_chunk_size) | `chunk_builder.py:53-55` | ✅ Correctness |
| 12 | **Thread safety** - `_stats` dictionary modified without locks in multi-threaded scenarios | `chunk_builder.py:91` | 🧵 Concurrency |
| 13 | **Algorithm bug** - Overlap logic in `_fixed_size_chunking` uses character comparison for byte positions | `chunk_builder.py:162` | ✅ Correctness |

---

## 3. Root Cause

### Primary Root Cause (Issue #1)
**File:** `chunk_builder.py:147-153`

```python
# Line 147-153: The bug
end = min(pos + max_size, len(text_bytes))
chunk_bytes = text_bytes[pos:end]

try:
    chunk_text = chunk_bytes.decode(self.config.encoding)
except UnicodeDecodeError:
    chunk_text = chunk_bytes.decode(self.config.encoding, errors="replace")
```

**Problem:** The code slices `text_bytes` at arbitrary byte offsets (`pos + max_size`). UTF-8 is a variable-length encoding (1-4 bytes per character). A Chinese character typically uses 3 bytes. Cutting at byte boundary can split a multi-byte character:
- Original: `...之 [E4 B9 8B] 不...` 
- Cut at: `...之 [E4 B9 | 8B] 不...`
- Result: `8B` alone is invalid → `\xe4\xb8` corruption

The `errors="replace"` mask hides the error by inserting `` but doesn't fix the underlying data loss.

### Secondary Root Cause (Issue #2)
**File:** `chunk_builder.py:189-191`

```python
# Line 189-191: Incorrect position tracking
current_sentences.append(sentence)
current_size += sentence_size
char_pos += len(sentence)  # BUG: should be += sentence_size or track differently
```

**Problem:** `char_pos` tracks cumulative character count, but `len(sentence)` gives characters, not bytes. When calculating `start_pos`, the math becomes inconsistent with actual byte positions.

---

## 4. Recommended Fix

### Fix 1: UTF-8 Safe Boundary Detection

```python
# chunk_builder.py:145-165 (replace _fixed_size_chunking)
def _find_utf8_safe_boundary(self, text_bytes: bytes, target_pos: int) -> int:
    """Find a safe cut position that doesn't split UTF-8 characters."""
    if target_pos >= len(text_bytes):
        return len(text_bytes)
    
    # Scan backwards up to 3 bytes to find character start
    for offset in range(4):
        pos = target_pos - offset
        if pos <= 0:
            return 0
        byte = text_bytes[pos]
        # UTF-8 continuation bytes: 10xxxxxx (0x80-0xBF)
        # Character starts with: 0xxxxxxx or 11xxxxxx
        if byte < 0x80 or (byte & 0xC0) == 0xC0:
            return pos
    
    return target_pos - 3  # Fallback: cut 3 bytes back

def _fixed_size_chunking(self, text: str, text_bytes: bytes,
                          source: str) -> List[Chunk]:
    """Simple fixed-size chunking with overlap."""
    chunks = []
    max_size = self.config.max_chunk_size
    overlap = self.config.overlap
    pos = 0
    chunk_idx = 0
    last_end = 0

    while pos < len(text_bytes):
        target_end = min(pos + max_size, len(text_bytes))
        # Find UTF-8 safe boundary
        end = self._find_utf8_safe_boundary(text_bytes, target_end)
        
        if end <= pos:  # Safety: avoid infinite loop
            end = pos + 1
        
        chunk_bytes = text_bytes[pos:end]
        chunk_text = chunk_bytes.decode(self.config.encoding)

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
            last_end = end

        # Move forward with overlap
        next_pos = end - overlap
        if next_pos <= pos:  # Avoid infinite loop
            next_pos = end
        pos = next_pos

    self._update_stats(chunks)
    return chunks
```

### Fix 2: Correct Position Tracking

```python
# chunk_builder.py:175-210 (fix _sentence_aware_chunking)
def _sentence_aware_chunking(self, text: str, text_bytes: bytes,
                              source: str) -> List[Chunk]:
    """Chunk text while respecting sentence boundaries."""
    sentences = self._split_sentences(text)
    chunks = []
    current_sentences = []
    current_size = 0
    chunk_idx = 0
    char_pos = 0  # Track character position, not byte

    for sentence in sentences:
        sentence_size = len(sentence.encode(self.config.encoding))
        sentence_char_len = len(sentence)

        if current_size + sentence_size > self.config.max_chunk_size:
            if current_sentences:
                chunk_text = "".join(current_sentences)
                chunk = Chunk(
                    text=chunk_text,
                    index=chunk_idx,
                    source=source,
                    start_pos=char_pos - len("".join(current_sentences)),
                    end_pos=char_pos,
                )
                chunks.append(chunk)
                chunk_idx += 1

                # Keep last sentence(s) for overlap
                overlap_sentences = []
                overlap_size = 0
                for s in reversed(current_sentences):
                    s_size = len(s.encode(self.config.encoding))
                    if overlap_size + s_size <= self.config.overlap:
                        overlap_sentences.insert(0, s)
                        overlap_size += s_size
                    else:
                        break

                current_sentences = overlap_sentences
                current_size = overlap_size
                # Adjust char_pos to reflect kept sentences
                char_pos -= sum(len(s) for s in current_sentences)

        current_sentences.append(sentence)
        current_size += sentence_size
        char_pos += sentence_char_len

    # Handle remaining sentences
    if current_sentences:
        chunk_text = "".join(current_sentences)
        chunk = Chunk(
            text=chunk_text,
            index=chunk_idx,
            source=source,
            start_pos=char_pos - len(chunk_text),
            end_pos=char_pos,
        )
        chunks.append(chunk)

    self._update_stats(chunks)
    return chunks
```

### Fix 3: Validate Config Values

```python
# Add after __init__ line 90
def __post_init__(self):
    """Validate configuration values."""
    if self.max_chunk_size <= 0:
        raise ValueError("max_chunk_size must be positive")
    if self.min_chunk_size < 0:
        raise ValueError("min_chunk_size cannot be negative")
    if self.overlap < 0:
        raise ValueError("overlap cannot be negative")
    if self.min_chunk_size > self.max_chunk_size:
        raise ValueError("min_chunk_size cannot exceed max_chunk_size")
```

---

## 5. Steps Taken

1. **Read the entire file** `chunk_builder.py` to understand the chunking architecture
2. **Identified byte vs character confusion** - Noted `text_bytes` used for size but positions mixed
3. **Analyzed `_fixed_size_chunking`** - Found direct byte slicing without UTF-8 validation (line 147-153)
4. **Traced corruption pattern** - Confirmed `\xe4\xb8` pattern matches truncated 3-byte UTF-8 sequences
5. **Examined `_sentence_aware_chunking`** - Discovered `char_pos` tracking inconsistency (line 189-191)
6. **Reviewed overlap logic** - Found potential infinite loop when `overlap >= chunk_size` (line 162)
7. **Checked sentence splitter** - Identified edge case with trailing unpunctuated text (line 215-216)
8. **Searched for similar patterns** - Scanned entire file for other byte-slicing operations
9. **Verified imports** - Found unused `Iterator` import and missing validation

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| `read_file` | Read full `chunk_builder.py` source code |
| Manual code analysis | Trace execution flow, identify byte/character boundary issues |
| Pattern matching | Recognize `\xe4\xb8` as truncated UTF-8 sequence |
| Static analysis | Check imports, type hints, resource management |

---

## 7. Verification

### Verification Commands

```bash
# Test UTF-8 boundary handling
python3 -c "
from src.data_processing.chunk_builder import ChunkBuilder, ChunkConfig

# Test with classical Chinese text containing multi-byte characters
test_text = '子曰：「學而時習之，不亦說乎？有朋自遠方來，不亦樂乎？' * 50

builder = ChunkBuilder(max_chunk_size=128, overlap=32)
chunks = builder.build_chunks(test_text)

# Check for corruption markers
for chunk in chunks:
    if '\ufffd' in chunk.text:  # Replacement character
        print(f'CORRUPTION in chunk {chunk.index}: {repr(chunk.text[-20:])}')
    # Check for truncated UTF-8 patterns
    try:
        chunk.text.encode('utf-8').decode('utf-8')
    except:
        print(f'INVALID UTF-8 in chunk {chunk.index}')

print(f'Total chunks: {len(chunks)}')
print('Verification: PASS' if all('\ufffd' not in c.text for c in chunks) else 'FAIL')
"

# Verify position tracking
python3 -c "
from src.data_processing.chunk_builder import ChunkBuilder

test_text = '天地玄黃，宇宙洪荒。日月盈昃，辰宿列張。' * 20
builder = ChunkBuilder(max_chunk_size=100)
chunks = builder.build_chunks(test_text)

# Verify positions are consistent
for i, chunk in enumerate(chunks):
    extracted = test_text[chunk.start_pos:chunk.end_pos]
    if extracted != chunk.text:
        print(f'MISMATCH chunk {i}: expected {repr(extracted[:20])}, got {repr(chunk.text[:20])}')
    print(f'Chunk {i}: pos={chunk.start_pos}-{chunk.end_pos}, len={len(chunk.text)}')
"
```

### Expected Output After Fix

```
Total chunks: N
Verification: PASS
Chunk 0: pos=0-95, len=95
Chunk 1: pos=63-158, len=95
...
```

### Regression Test to Add

```python
# tests/test_chunk_builder.py
def test_utf8_boundary_split():
    """Ensure chunks don't split UTF-8 characters mid-sequence."""
    builder = ChunkBuilder(max_chunk_size=64)
    # Text with many 3-byte Chinese characters
    text = "abcdefghij" + "天地玄黃宇宙洪荒" * 20
    chunks = builder.build_chunks(text)
    
    for chunk in chunks:
        # Should not contain replacement characters
        assert '\ufffd' not in chunk.text
        # Should be valid UTF-8
        chunk.text.encode('utf-8').decode('utf-8')

def test_position_tracking():
    """Verify start_pos/end_pos correctly map to original text."""
    text = "子曰：「學而時習之」" * 30
    builder = ChunkBuilder(max_chunk_size=50)
    chunks = builder.build_chunks(text, source="test")
    
    for chunk in chunks:
        extracted = text[chunk.start_pos:chunk.end_pos]
        assert extracted == chunk.text, f"Position mismatch at chunk {chunk.index}"
```
