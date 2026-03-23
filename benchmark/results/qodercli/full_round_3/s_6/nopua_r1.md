# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: nopua | Run: 1
## Duration: 360.58s

---

Now I have a complete picture. Let me summarize my findings:

---

## Investigation Summary

### 1. Issues Found

**Primary Issue: Unicode Corruption in `_fixed_size_chunking()` (lines 136-177)**

The function slices text at byte boundaries without respecting UTF-8 character boundaries:

```python
# Line 150-158
end = min(pos + max_size, len(text_bytes))
chunk_bytes = text_bytes[pos:end]

try:
    chunk_text = chunk_bytes.decode(self.config.encoding)
except UnicodeDecodeError:
    chunk_text = chunk_bytes.decode(self.config.encoding, errors="replace")  # BUG!
```

**Problem:** When `end` falls in the middle of a multi-byte UTF-8 character:
- The last character bytes are truncated (e.g., `\xe4\xb8` instead of `\xe4\xb8\x8d`)
- Using `errors='replace'` masks the error by inserting U+FFFD () 
- **The original character is permanently lost** - this is data corruption

**Evidence:**
```
Chunk 0: 86 chars, 258 bytes [CORRUPTED - contains U+FFFD]
Last 20 chars: '：「學而時習之，不亦說乎？」子曰：「學'
```

---

### 2. Hidden Issues Discovered

**Issue A: Inconsistent position metadata semantics**
- `_fixed_size_chunking()`: `start_pos`/`end_pos` are **byte offsets** into the encoded bytes
- `_sentence_aware_chunking()`: `start_pos`/`end_pos` are **character offsets** into the string
- This inconsistency will cause bugs when consumers use these positions to reference back to the source text

**Issue B: Overlap logic doesn't account for UTF-8 boundaries**
Even if the decode succeeds, the overlap calculation (`pos = end - overlap`) can start at a misaligned byte position, propagating corruption to subsequent chunks.

**Issue C: `_split_sentences()` drops trailing punctuation-less text in edge cases**
Line 260-261 only handles trailing text when `len(parts)` is odd. If the text ends with punctuation that was split, some content could be lost.

---

### 3. Root Cause

The fundamental problem is a **category error**: the code treats UTF-8 encoded bytes as if they were ASCII bytes where any position is a valid cut point. 

UTF-8 encoding rules:
- ASCII (0x00-0x7F): 1 byte
- Most CJK characters: 3 bytes (pattern: `1110xxxx 10xxxxxx 10xxxxxx`)

Cutting at an arbitrary byte position within a multi-byte sequence produces invalid UTF-8. The `errors='replace'` "fix" actually makes it worse by silently corrupting data instead of failing visibly.

---

### 4. Recommended Fix

**For `_fixed_size_chunking()`:**

Replace the naive byte slicing with boundary-aware logic:

```python
def _find_utf8_boundary(data: bytes, max_len: int) -> int:
    """Find the largest valid UTF-8 boundary <= max_len."""
    if max_len >= len(data):
        return len(data)
    
    # Back up from max_len until we find a valid boundary
    for i in range(max_len, max(0, max_len - 4), -1):
        try:
            data[:i].decode('utf-8')
            return i
        except UnicodeDecodeError:
            continue
    return 0

# In _fixed_size_chunking():
end = min(pos + max_size, len(text_bytes))
end = self._find_utf8_boundary(text_bytes[pos:], max_size) + pos  # Find safe boundary
chunk_bytes = text_bytes[pos:end]
chunk_text = chunk_bytes.decode(self.config.encoding)  # No errors='replace' needed
```

**For metadata consistency:**
Document and standardize whether positions are byte or character offsets. Recommend using **character offsets** consistently since that's what Python strings use natively.

---

### 5. Steps Taken

1. Read the source file to understand the chunking logic
2. Created reproduction scripts to trigger the corruption
3. Identified that `_fixed_size_chunking()` cuts at arbitrary byte positions
4. Verified that `errors='replace'` causes silent data corruption (U+FFFD insertion)
5. Confirmed `_sentence_aware_chunking()` avoids this issue by working with complete sentences
6. Discovered metadata inconsistency between the two chunking methods
7. Tested with actual Chinese text to confirm corruption patterns

---

### 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source file `chunk_builder.py` and test file |
| `Bash` (Python) | Reproduce corruption, verify hypotheses, test fixes |
| `Glob` | Find related test files |
| `Grep` | Search for usage patterns |

---

### 7. Verification

**Reproduced the bug:**
```
Test text: 800 chars, 2400 bytes
Fixed-size chunking: 12 chunks generated
Corrupted chunks: 12/12 (100% contain U+FFFD replacement characters)
```

**Verified sentence-aware path is safe:**
```
Sentence-aware chunking: 10 chunks generated  
Corrupted chunks: 0/10 (no corruption)
```

**Confirmed root cause:**
- Cutting UTF-8 bytes at position 100 produced `\xe4\xb8` (incomplete 3-byte char)
- `errors='replace'` converted this to `` (U+FFFD)
- Original character data is irrecoverably lost
