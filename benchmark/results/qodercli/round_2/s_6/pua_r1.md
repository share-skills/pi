# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: pua | Run: 1
## Duration: 83.81s

---

Now I have a complete understanding of the issue. Let me provide the comprehensive structured summary:

---

## Investigation Complete

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **UTF-8 Byte Boundary Corruption** | `_fixed_size_chunking()` lines 149-158 | Critical |
| 2 | **Overlap Position Also Cuts Mid-Character** | `_fixed_size_chunking()` line 172 | Critical |
| 3 | **Silent Data Loss with `errors='replace'`** | `_fixed_size_chunking()` line 158 | Critical |
| 4 | **Position Tracking Uses Byte Offsets for String Data** | `Chunk.start_pos/end_pos` | High |

### 2. Hidden Issues Discovered

| # | Issue | Impact |
|---|-------|--------|
| H1 | **Sentence splitter regex incomplete** | Missing Chinese punctuation like `」、︰` etc. |
| H2 | **`_split_sentences()` trailing text edge case** | Line 260 logic incorrect for even-length parts |
| H3 | **Overlap calculation in sentence-aware mode** | Lines 212-218 may create wrong overlap size |
| H4 | **No validation that chunks reconstruct original text** | Data corruption undetectable |
| H5 | **`respect_paragraphs` config exists but never used** | Dead configuration (line 34) |
| H6 | **`include_metadata` config exists but never used** | Dead configuration (line 36) |
| H7 | **Repeated encode() calls for sentence sizes** | Performance issue - lines 194, 213 |

### 3. Root Cause

**Primary Root Cause:** The `_fixed_size_chunking()` method slices the UTF-8 encoded byte array at arbitrary byte positions (line 150: `text_bytes[pos:end]`), which cuts multi-byte UTF-8 characters in half.

**Evidence from test run:**
```
TEST 1 (Fixed-Size): 12/12 chunks CORRUPTED with U+FFFD
TEST 3 (Overlap):    17/32 chunks CORRUPTED
TEST 2 (Sentence):   0/10 chunks corrupted (SAFE)
```

**Why it happens:**
- Chinese characters are typically 3 bytes in UTF-8 (e.g., `天` = `e5a4a9`)
- When `end = pos + max_size` lands at byte 256, and 256 is not divisible by 3, the cut lands mid-character
- Example: cutting `e5a4a9e59cb0e78e84e9` at byte 10 leaves `e9` (incomplete `黃` character)
- `UnicodeDecodeError` is raised
- `errors='replace'` substitutes U+FFFD () — **original data is permanently lost**

**Why Sentence-Aware Chunking Works:** It operates on Python strings (character level), never slicing raw bytes. The `_split_sentences()` returns complete sentences as strings.

### 4. Recommended Fix

```python
def _find_utf8_boundary(self, data: bytes, start: int, target: int) -> int:
    """Find nearest valid UTF-8 boundary at or before target position."""
    if target >= len(data):
        return len(data)
    
    pos = target
    while pos > start:
        try:
            data[start:pos].decode('utf-8')
            return pos
        except UnicodeDecodeError:
            pos -= 1
    
    return start


def _fixed_size_chunking(self, text: str, text_bytes: bytes, source: str) -> List[Chunk]:
    """FIXED: Now finds valid UTF-8 character boundaries."""
    chunks = []
    max_size = self.config.max_chunk_size
    overlap = self.config.overlap
    pos = 0
    chunk_idx = 0

    while pos < len(text_bytes):
        target_end = min(pos + max_size, len(text_bytes))
        end = self._find_utf8_boundary(text_bytes, pos, target_end)
        
        if end <= pos:
            break
            
        chunk_bytes = text_bytes[pos:end]
        chunk_text = chunk_bytes.decode(self.config.encoding)  # No errors='replace' needed
        
        if len(chunk_text.strip()) >= self.config.min_chunk_size:
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
        
        if end < len(text_bytes):
            overlap_target = end - overlap
            pos = self._find_utf8_boundary(text_bytes, 0, overlap_target)
            if pos >= end:
                pos = end
        else:
            break

    self._update_stats(chunks)
    return chunks
```

### 5. Steps Taken

| Step | Action | Tool Used |
|------|--------|-----------|
| 1 | Located actual chunk_builder.py files | Glob search |
| 2 | Read and analyzed full source code (335 lines) | Read tool |
| 3 | Found existing test files | Glob search |
| 4 | Searched for Unicode/decode patterns | Grep search |
| 5 | Ran reproduction test script | Bash execution |
| 6 | Analyzed corruption output (100% chunks corrupted in fixed-size mode) | Output analysis |
| 7 | Created diagnostic test to verify root cause | Write + Bash |
| 8 | Confirmed sentence-aware mode is safe | Code analysis + test |
| 9 | Identified all hidden issues | Code review |
| 10 | Deep UTF-8 byte boundary analysis | Bash execution |

### 6. Tools Used

- **Glob**: Found chunk_builder.py and test files
- **Read**: Full source code analysis
- **Grep**: Searched for decode/error patterns across codebase
- **Bash**: Ran test scripts to reproduce issue
- **Write**: Created diagnostic test

### 7. Verification

**Verification Method:** Executed test script that:
1. Created a `ChunkBuilder` with small `max_chunk_size` to force splits
2. Processed classical Chinese text (all 3-byte UTF-8 characters)
3. Checked each chunk for U+FFFD replacement characters

**Key Evidence:**
```
============================================================
TEST 1: Fixed-Size Chunking (respect_sentences=False)
============================================================
Input text: 800 chars, 2400 bytes
Generated 12 chunks: ALL CORRUPTED

Chunk 0:
  Size: 86 chars, 258 bytes
  Byte range: [0:256]
  Last 10 chars: '說乎？」子曰：「學'  ← U+FFFD visible
  Last 10 bytes: b'\x9a\xe3\x80\x8c\xe5\xad\xb8\xef\xbf\xbd'  ← efbfbd = U+FFFD

============================================================
TEST 2: Sentence-Aware Chunking (respect_sentences=True)  
============================================================
Generated 10 chunks: ALL CLEAN (0 corrupted)
```

**Root cause verified with byte-level analysis:**
```
Text: '天地玄黃'
Bytes: e5a4a9e59cb0e78e84e9bb83 (12 bytes total)
Char 2 "玄": e78e84 (3 bytes)

Cutting at byte 10: e5a4a9e59cb0e78e84e9
With errors='replace': '天地玄'
```

The fix has been validated conceptually — scanning backward to find valid UTF-8 boundaries prevents mid-character cuts.
