# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: pi | Run: 1
## Duration: 274.38s

---

## Investigation Complete

---

## 1. Issues Found

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| 1 | **Unicode boundary corruption** | CRITICAL | `chunk_builder.py:150-158` |
| 2 | **Overlap position causes 100% corruption** | CRITICAL | `chunk_builder.py:172-174` |
| 3 | **Unused logging import** | LOW | `chunk_builder.py:19` |
| 4 | **merge_small_chunks checks wrong chunk** | MEDIUM | `chunk_builder.py:318` |
| 5 | **start_pos/end_pos inconsistent semantics** | LOW | `chunk_builder.py:165-166` vs `203-204` |
| 6 | **Thread safety: self._stats unprotected** | LOW | `chunk_builder.py:101` |
| 7 | **errors='replace' masks corruption silently** | HIGH | `chunk_builder.py:158` |

---

## 2. Hidden Issues (Beyond the Ask)

| # | Category | Issue |
|---|----------|-------|
| H1 | **Code Quality** | Unused `logging` import (line 19) - `logger.` never called |
| H2 | **Correctness** | `merge_small_chunks()` logic backwards - checks `merged[-1]` instead of current chunk |
| H3 | **API Design** | `start_pos/end_pos` means bytes in fixed-size, chars in sentence-aware - inconsistent |
| H4 | **Thread Safety** | `self._stats` modified without locks - race condition in multi-threaded use |
| H5 | **Data Integrity** | `errors='replace'` silently corrupts data with U+FFFD instead of fixing boundaries |
| H6 | **Algorithm** | Overlap calculation (`pos = end - overlap`) ignores UTF-8 boundaries |

---

## 3. Root Cause

### Primary Root Cause (Issues 1, 2, 7)

**`chunk_builder.py:150-151`** slices `text_bytes` at arbitrary byte positions:
```python
end = min(pos + max_size, len(text_bytes))
chunk_bytes = text_bytes[pos:end]  # Cuts mid-character!
```

**`chunk_builder.py:156-158`** uses `errors='replace'` which masks corruption:
```python
try:
    chunk_text = chunk_bytes.decode(self.config.encoding)
except UnicodeDecodeError:
    chunk_text = chunk_bytes.decode(self.config.encoding, errors="replace")  # Inserts U+FFFD
```

**Initially I thought** only the end boundary was problematic. **Upon closer inspection**, the overlap calculation at line 172 (`pos = end - overlap`) also creates misaligned start positions, causing **100% corruption rate** when overlap > 0.

### Secondary Root Cause (Issue 4)

**`chunk_builder.py:318`** checks the wrong chunk:
```python
if merged[-1].size < min_size:  # Checks PREVIOUS chunk, not CURRENT
```

Should check if `chunk.size < min_size` (the chunk being iterated).

---

## 4. Recommended Fix

### Fix 1: UTF-8 Boundary-Aware Slicing

```python
# Add helper method
def _find_utf8_char_boundary(data: bytes, offset: int) -> int:
    """Find nearest UTF-8 character boundary at or before offset."""
    if offset >= len(data):
        return len(data)
    pos = offset
    while pos > 0 and (data[pos] & 0xC0) == 0x80:  # Continuation byte
        pos -= 1
    return pos

# Fix _fixed_size_chunking (lines 149-174)
while pos < len(text_bytes):
    end = min(pos + max_size, len(text_bytes))
    
    # ADJUST: Find character boundaries
    end = self._find_utf8_char_boundary(text_bytes, end)
    if pos < len(text_bytes):
        pos = self._find_utf8_char_boundary(text_bytes, pos)
    
    chunk_bytes = text_bytes[pos:end]
    
    if not chunk_bytes:
        break
    
    # Now safe to decode without errors='replace'
    chunk_text = chunk_bytes.decode(self.config.encoding)
    
    # ... rest of logic
    
    # Move position forward with overlap (also boundary-adjusted)
    next_pos = end - overlap if overlap > 0 else end
    if next_pos <= pos:
        next_pos = end
    pos = self._find_utf8_char_boundary(text_bytes, next_pos)
```

### Fix 2: merge_small_chunks Logic

```python
# Fix line 318
for chunk in chunks[1:]:
    if chunk.size < min_size:  # Check CURRENT chunk, not previous
        # Merge with previous chunk
        merged[-1] = Chunk(
            text=merged[-1].text + chunk.text,
            # ...
        )
    else:
        merged.append(chunk)
```

### Fix 3: Remove Unused Import

```python
# Remove line 19
import logging  # DELETE - never used
```

---

## 5. Steps Taken

| Step | Action | Discovery |
|------|--------|-----------|
| 1 | Read `chunk_builder.py` source | Understood chunking architecture |
| 2 | Ran test script to reproduce corruption | Confirmed `\ufffd` replacement characters |
| 3 | Analyzed UTF-8 byte structure | Chinese chars = 3 bytes each |
| 4 | Traced `_fixed_size_chunking` execution | Line 150 cuts at arbitrary bytes |
| 5 | Tested overlap behavior | 100% corruption with overlap > 0 |
| 6 | Compared sentence-aware vs fixed-size | Sentence-aware works correctly (char-level) |
| 7 | Checked import usage | `logging` imported but never used |
| 8 | Tested `merge_small_chunks()` | Logic checks wrong chunk |
| 9 | Verified position tracking | Inconsistent byte vs char semantics |
| 10 | Checked thread safety | `self._stats` unprotected |

**Assumption修正**: Initially I thought the issue was only about end boundaries. **Upon closer inspection**, the overlap calculation creates misaligned START positions too, making corruption unavoidable with the current algorithm.

---

## 6. Tools Used

| Tool | Purpose |
|------|---------|
| `Read` | Read source files |
| `Grep` | Search for patterns across codebase |
| `Glob` | Find related test files |
| `Bash` (python3) | Run verification tests, demonstrate bugs |
| `Bash` (grep) | Check import usage |

---

## 7. Verification

```bash
# Verify Issue 1: Unicode corruption
cd /Users/hepin/IdeaProjects/pi/benchmark/data/test-project
python3 -c "
import sys; sys.path.insert(0, 'src')
from data_processing.chunk_builder import ChunkBuilder, ChunkConfig
config = ChunkConfig(max_chunk_size=50, overlap=10, respect_sentences=False)
chunks = ChunkBuilder(config).build_chunks('子曰學而時習之' * 10)
corrupted = sum(1 for c in chunks if chr(0xFFFD) in c.text)
print(f'Corrupted: {corrupted}/{len(chunks)}')
"
# Expected: corrupted > 0

# Verify Issue 3: Unused logging
grep -c 'logger\.' src/data_processing/chunk_builder.py
# Expected: 0

# Verify Issue 4: merge_small_chunks bug
python3 -c "
import sys; sys.path.insert(0, 'src')
from data_processing.chunk_builder import Chunk, merge_small_chunks
chunks = [Chunk('abcd', 0), Chunk('x', 1)]
merged = merge_small_chunks(chunks, min_size=4)
print(f'Merged count: {len(merged)} (expected: 1)')
"
# Expected: 2 (bug confirmed)

# Verify fix approach
python3 -c "
text_bytes = '子曰'.encode('utf-8')
# Test boundary detection
def find_boundary(data, offset):
    while offset > 0 and (data[offset] & 0xC0) == 0x80:
        offset -= 1
    return offset
print(f'Boundary at 4: {find_boundary(text_bytes, 4)}')  # Should be 3
print(f'Boundary at 5: {find_boundary(text_bytes, 5)}')  # Should be 3
"
```

---

## Delivery Confirmation

```
📋 交付確認
□ 目標匹配: Unicode boundary split 問題已定位，根因為 byte-level slicing 無視 UTF-8 邊界
□ 邊界覆蓋: 發現 7 個問題（2 個 Critical, 1 個 High, 1 個 Medium, 3 個 Low）
□ 風險可控: 提供驗證命令與修復代碼範例
```
