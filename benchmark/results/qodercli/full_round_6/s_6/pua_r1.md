# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: pua | Run: 1
## Duration: 123.89s

---

Now I have a complete understanding of all the issues. Let me provide the comprehensive analysis:

---

## Investigation Complete

### 1. Issues Found

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| 1 | **UTF-8 Byte Boundary Corruption** | `_fixed_size_chunking()` line 150-158 | Critical |
| 2 | **Overlap Position Also Cuts Mid-Character** | `_fixed_size_chunking()` line 172 | Critical |
| 3 | **Silent Data Loss with `errors='replace'`** | `_fixed_size_chunking()` line 158 | Critical |
| 4 | **Position Tracking Uses Byte Offsets for String Data** | `Chunk.start_pos/end_pos` | High |

### 2. Hidden Issues Discovered

| # | Issue | Impact |
|---|-------|--------|
| 1 | **Sentence splitter regex doesn't handle all classical Chinese punctuation** | Missing `」、︰` etc. |
| 2 | **`_split_sentences()` loses trailing text edge case** | Line 260 logic incorrect |
| 3 | **Overlap calculation in sentence-aware mode uses bytes but iterates chars** | Lines 212-218 may create wrong overlap |
| 4 | **No validation that chunks can be recombined to original text** | Data corruption undetectable |

### 3. Root Cause Analysis

**Primary Root Cause:** The `_fixed_size_chunking()` method slices the UTF-8 encoded byte array at arbitrary byte positions (line 150: `text_bytes[pos:end]`), which cuts multi-byte UTF-8 characters in half. When decoded:
- Bytes like `\xe5\xa4` (partial 天) become invalid
- `errors='replace'` substitutes U+FFFD () 
- Original character data is **permanently lost**

**Why Sentence-Aware Chunking Works:** It operates on Python strings (character level), never slicing raw bytes. The `_split_sentences()` returns完整 sentences as strings, so no UTF-8 boundary violations occur.

**Secondary Issue:** The overlap calculation (`pos = end - overlap` at line 172) also lands at arbitrary byte positions, compounding the corruption.

### 4. Recommended Fix

```python
def _fixed_size_chunking(self, text: str, text_bytes: bytes, source: str) -> List[Chunk]:
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
        chunk_text = chunk_bytes.decode(self.config.encoding)
        
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
```

### 5. Steps Taken

| Step | Action | Tool Used |
|------|--------|-----------|
| 1 | Located actual chunk_builder.py files | Glob search |
| 2 | Read and analyzed full source code | Read tool |
| 3 | Found existing test files | Glob search |
| 4 | Searched for Unicode/decode patterns | Grep search |
| 5 | Ran reproduction test script | Bash execution |
| 6 | Analyzed corruption output (100% chunks corrupted in fixed-size mode) | Output analysis |
| 7 | Created diagnostic test to verify root cause | Write + Bash |
| 8 | Confirmed sentence-aware mode is safe | Code analysis + test |
| 9 | Identified all hidden issues | Code review |

### 6. Tools Used

- **Glob**: Found chunk_builder.py and test files
- **Read**: Full source code analysis
- **Grep**: Searched for decode/error patterns
- **Bash**: Ran test scripts to reproduce issue
- **Write**: Created diagnostic test

### 7. Verification

**Evidence of corruption confirmed:**
```
TEST 1 (Fixed-Size): 12/12 chunks CORRUPTED with U+FFFD
TEST 3 (Overlap):    17/32 chunks CORRUPTED
TEST 2 (Sentence):   0/10 chunks corrupted (SAFE)
```

**Root cause verified:**
```
Cutting at byte 10: e5a4a9e59cb0e78e84e9
With errors='replace': '天地玄'
```

The fix has been validated conceptually - scanning backward to find valid UTF-8 boundaries prevents mid-character cuts.
