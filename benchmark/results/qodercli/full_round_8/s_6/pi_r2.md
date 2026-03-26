# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: pi | Run: 2
## Duration: 366.97s

---

Now I have a complete understanding. Let me provide the structured investigation summary:

---

## Investigation Complete

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **UTF-8 Byte Boundary Corruption** | `_fixed_size_chunking()` lines 149-158 | **CRITICAL** |
| 2 | **Overlap Position Causes Additional Corruption** | `_fixed_size_chunking()` line 172 | **CRITICAL** |
| 3 | **Silent Data Loss with `errors='replace'`** | `_fixed_size_chunking()` line 158 | **CRITICAL** |
| 4 | **Byte/Character Position Mismatch** | `_sentence_aware_chunking()` lines 191, 203-204, 225 | HIGH |
| 5 | **`merge_small_chunks` Logic Backwards** | `merge_small_chunks()` line 318 | MEDIUM |
| 6 | **Dead Configuration Options** | `ChunkConfig` lines 34, 36 | LOW |

---

### 2. Hidden Issues Beyond the Ask

| # | Issue | Category | Impact |
|---|-------|----------|--------|
| H1 | **Position tracking inconsistency** | Logic Bug | `start_pos/end_pos` mean bytes in one method, chars in another |
| H2 | **Sentence splitter incomplete** | Correctness | Missing Chinese punctuation (`」`, `.`, `、`, etc.) |
| H3 | **No round-trip validation** | Data Integrity | No way to detect that chunks don't reconstruct original text |
| H4 | **Repeated encode() calls** | Performance | Lines 194, 213 re-encode same sentences multiple times |
| H5 | **Trailing text edge case bug** | Logic Bug | Line 260 logic incorrect when `parts` has even length |

---

### 3. Root Cause Analysis

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

**Initially I thought** the issue was just about the final cut position. **Upon closer inspection**, the overlap calculation (`pos = end - overlap` at line 172) compounds the problem by creating additional misaligned boundaries for every chunk after the first.

**Why Sentence-Aware Chunking Works:** It operates on Python strings (character level), never slicing raw bytes. The `_split_sentences()` returns complete sentences as strings. However, it has its own issues with position tracking mixing byte and character offsets.

---

### 4. Recommended Fix

```python
def _find_utf8_boundary(self, data: bytes, start: int, target: int) -> int:
    """Find nearest valid UTF-8 boundary at or before target position.
    
    Scans backward from target until finding a position that decodes cleanly.
    """
    if target >= len(data):
        return len(data)
    
    pos = target
    while pos > start:
        try:
            data[start:pos].decode('utf-8')
            return pos  # Valid UTF-8 boundary found
        except UnicodeDecodeError:
            pos -= 1
    
    return start  # Fallback to start position


def _fixed_size_chunking(self, text: str, text_bytes: bytes,
                          source: str) -> List[Chunk]:
    """Simple fixed-size chunking with overlap.
    
    FIXED: Now finds valid UTF-8 character boundaries instead of cutting
    mid-character.
    """
    chunks = []
    max_size = self.config.max_chunk_size
    overlap = self.config.overlap
    pos = 0
    chunk_idx = 0

    while pos < len(text_bytes):
        # Find safe end position (valid UTF-8 boundary)
        target_end = min(pos + max_size, len(text_bytes))
        end = self._find_utf8_boundary(text_bytes, pos, target_end)
        
        if end <= pos:  # No valid boundary found
            break
            
        chunk_bytes = text_bytes[pos:end]
        chunk_text = chunk_bytes.decode(self.config.encoding)  # No errors='replace' needed
        
        if len(chunk_text.strip()) >= self.config.min_chunk_size:
            # Convert byte offsets to character offsets for metadata
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

        # Calculate next position with overlap (also at UTF-8 boundary)
        if end < len(text_bytes):
            overlap_target = end - overlap
            pos = self._find_utf8_boundary(text_bytes, 0, overlap_target)
            if pos >= end:  # Avoid infinite loop
                pos = end
        else:
            break

    self._update_stats(chunks)
    return chunks
```

**For `merge_small_chunks`:**
```python
def merge_small_chunks(chunks: List[Chunk], min_size: int = 64) -> List[Chunk]:
    """FIXED: Now checks current chunk being iterated, not previous."""
    if not chunks:
        return []

    merged = []
    pending = None
    
    for chunk in chunks:
        if chunk.size < min_size:
            if pending:
                pending = Chunk(
                    text=pending.text + chunk.text,
                    index=pending.index,
                    source=pending.source,
                    start_pos=pending.start_pos,
                    end_pos=chunk.end_pos,
                )
            else:
                pending = chunk
        else:
            if pending:
                merged[-1] = Chunk(
                    text=merged[-1].text + pending.text,
                    index=merged[-1].index,
                    source=merged[-1].source,
                    start_pos=merged[-1].start_pos,
                    end_pos=pending.end_pos,
                ) if merged else pending
                pending = None
            merged.append(chunk)
    
    if pending:
        if merged:
            merged[-1] = Chunk(
                text=merged[-1].text + pending.text,
                index=merged[-1].index,
                source=merged[-1].source,
                start_pos=merged[-1].start_pos,
                end_pos=pending.end_pos,
            )
        else:
            merged.append(pending)

    for i, chunk in enumerate(merged):
        chunk.index = i

    return merged
```

---

### 5. Steps Taken

| Step | Action | Tool Used | Finding |
|------|--------|-----------|---------|
| 1 | Located actual chunk_builder.py files | Glob search | Found 2 copies |
| 2 | Read and analyzed full source code (335 lines) | Read tool | Identified all methods |
| 3 | Found existing test files | Glob search | test_chunk.py, debug_chunk.py |
| 4 | Searched for Unicode/decode patterns | Grep search | Found errors='replace' pattern |
| 5 | Ran reproduction test script | Bash execution | Confirmed 100% corruption in fixed-size mode |
| 6 | Analyzed corruption output | Output analysis | U+FFFD visible in last bytes |
| 7 | Created diagnostic test | Write + Bash | Verified UTF-8 byte boundary root cause |
| 8 | Compared sentence-aware vs fixed-size | Code analysis | Confirmed sentence-aware is safe |
| 9 | Identified hidden issues | Code review | Position tracking mismatch, dead config |
| 10 | Deep byte-level analysis | Bash execution | Demonstrated exact failure mode |

**Assumption Corrections:**
- **Initially I thought** the corruption only happened at chunk boundaries → **Actually** the overlap mechanism causes EVERY chunk (except possibly the last) to have corrupted end AND the next chunk to have corrupted start
- **Initially I thought** sentence-aware mode was completely safe → **Actually** it doesn't corrupt bytes but has position tracking inconsistencies (byte vs char offsets)
- **Initially I thought** `merge_small_chunks` was working correctly → **Actually** the condition checks the wrong chunk

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Glob` | Found chunk_builder.py and test files |
| `Read` | Full source code analysis (335 lines) |
| `Grep` | Searched for decode/error patterns across codebase |
| `Bash` | Ran test scripts to reproduce issue |
| `Write` | Created diagnostic test scripts |
| Manual analysis | Traced execution flow, byte-level debugging |

---

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
With errors='replace': '天地玄'  ← Last character corrupted
```

**Verification Command:**
```bash
cd /Users/hepin/IdeaProjects/pi
python3 benchmark/test_chunk.py
```

---

## Summary Table

| Component | Issue | Severity | Evidence |
|-----------|-------|----------|----------|
| `_fixed_size_chunking()` | UTF-8 boundary corruption | **CRITICAL** | 100% chunks corrupted in tests |
| Overlap logic | Compounds corruption | **CRITICAL** | More boundaries = more corruption |
| `errors='replace'` | Masks silent data loss | **CRITICAL** | Original bytes permanently lost |
| `_sentence_aware_chunking()` | Char/byte position mismatch | HIGH | Metadata inconsistency |
| `merge_small_chunks()` | Checks wrong chunk | MEDIUM | Function doesn't work as intended |
| `respect_paragraphs` | Config exists but unused | LOW | Dead configuration |
