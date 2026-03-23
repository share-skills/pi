"""Comprehensive verification of all chunk_builder.py issues"""
import sys
sys.path.insert(0, 'data/test-project/src')

from data_processing.chunk_builder import ChunkBuilder, ChunkConfig, Chunk, merge_small_chunks

print("=" * 70)
print("COMPREHENSIVE CHUNK BUILDER ISSUE VERIFICATION")
print("=" * 70)

# ============================================================================
# ISSUE 1: Unicode Boundary Corruption in Fixed-Size Chunking (CRITICAL)
# ============================================================================
print("\n" + "=" * 70)
print("ISSUE 1: Unicode Boundary Corruption in Fixed-Size Chunking")
print("Severity: CRITICAL - Data corruption")
print("=" * 70)

config = ChunkConfig(
    max_chunk_size=50,
    min_chunk_size=1,
    overlap=0,
    respect_sentences=False,
)
builder = ChunkBuilder(config)

text = "子曰學而時習之不亦說乎有朋自遠方來不亦樂乎人不知而不慍不亦君子乎" * 5
chunks = builder.build_chunks(text)

corrupted = [c for c in chunks if "\ufffd" in c.text]
print(f"\nTest: Fixed-size chunking with Chinese text")
print(f"Input: {len(text)} chars, {len(text.encode('utf-8'))} bytes")
print(f"Generated: {len(chunks)} chunks")
print(f"Corrupted: {len(corrupted)} chunks ({len(corrupted)/len(chunks)*100:.0f}%)")

if corrupted:
    print("\n*** VERIFIED: Unicode boundary corruption confirmed ***")
    print(f"Example corrupted chunk: {repr(corrupted[0].text)}")

# Root cause explanation
print("\nRoot Cause:")
print("1. Line 150-151: Slices text_bytes at arbitrary byte positions")
print("2. Line 156-158: Uses errors='replace' which MASKS corruption with U+FFFD")
print("3. No validation that byte boundaries align with UTF-8 character boundaries")

# ============================================================================
# ISSUE 2: Overlap Position Also Causes Corruption (CRITICAL)
# ============================================================================
print("\n" + "=" * 70)
print("ISSUE 2: Overlap Position Calculation Causes Corruption")
print("Severity: CRITICAL - Affects ALL chunks when overlap is used")
print("=" * 70)

config2 = ChunkConfig(
    max_chunk_size=50,
    min_chunk_size=1,
    overlap=10,
    respect_sentences=False,
)
builder2 = ChunkBuilder(config2)

chunks2 = builder2.build_chunks(text)
corrupted2 = [c for c in chunks2 if "\ufffd" in c.text]

print(f"\nTest: Fixed-size chunking with overlap={config2.overlap}")
print(f"Generated: {len(chunks2)} chunks")
print(f"Corrupted: {len(corrupted2)} chunks ({len(corrupted2)/len(chunks2)*100:.0f}%)")

if len(corrupted2) == len(chunks2):
    print("\n*** VERIFIED: 100% corruption rate with overlap ***")
    print("The overlap calculation (pos = end - overlap) creates misaligned boundaries")

# ============================================================================
# ISSUE 3: Byte/Character Position Mismatch in Sentence-Aware Chunking
# ============================================================================
print("\n" + "=" * 70)
print("ISSUE 3: Byte/Character Position Mismatch (Sentence-Aware)")
print("Severity: MEDIUM - Incorrect size calculations")
print("=" * 70)

config3 = ChunkConfig(
    max_chunk_size=100,  # bytes
    min_chunk_size=1,
    overlap=30,
    respect_sentences=True,
)
builder3 = ChunkBuilder(config3)

text3 = "子曰：「學而時習之，不亦說乎？」" * 10
chunks3 = builder3.build_chunks(text3)

print(f"\nTest: Sentence-aware chunking (max_chunk_size=100 bytes)")
print(f"Input: {len(text3)} chars, {len(text3.encode('utf-8'))} bytes")

for i, chunk in enumerate(chunks3[:3]):
    actual_byte_size = len(chunk.text.encode('utf-8'))
    print(f"Chunk {i}: {chunk.size} chars, {actual_byte_size} bytes (expected ~100 bytes max)")

print("\nProblem:")
print("- Size check uses bytes: len(sentence.encode(...))")
print("- Position tracking uses chars: char_pos += len(sentence)")
print("- This creates inconsistency for non-ASCII text")

# ============================================================================
# ISSUE 4: start_pos/end_pos Use Byte Offsets But Should Be Character Offsets
# ============================================================================
print("\n" + "=" * 70)
print("ISSUE 4: start_pos/end_pos Semantics Are Ambiguous")
print("Severity: LOW - Metadata inconsistency")
print("=" * 70)

print("\nIn _fixed_size_chunking (lines 165-166):")
print("  start_pos=pos, end_pos=end  # These are BYTE offsets")
print("\nIn _sentence_aware_chunking (lines 203-204, 234-235):")
print("  start_pos=char_pos - len(chunk_text), end_pos=char_pos  # CHARACTER offsets")
print("\nThis inconsistency means start_pos/end_pos have different meanings")
print("depending on which chunking method is used!")

# Demonstrate
config4a = ChunkConfig(max_chunk_size=50, respect_sentences=False)
builder4a = ChunkBuilder(config4a)
chunks4a = builder4a.build_chunks("abcdefg" * 20)
print(f"\nFixed-size: start_pos={chunks4a[0].start_pos}, end_pos={chunks4a[0].end_pos}")
print(f"  These are BYTE positions")

config4b = ChunkConfig(max_chunk_size=50, respect_sentences=True)
builder4b = ChunkBuilder(config4b)
chunks4b = builder4b.build_chunks("abcdefg。" * 20)
print(f"Sentence-aware: start_pos={chunks4b[0].start_pos}, end_pos={chunks4b[0].end_pos}")
print(f"  These are CHARACTER positions")

# ============================================================================
# ISSUE 5: merge_small_chunks Logic Is Backwards
# ============================================================================
print("\n" + "=" * 70)
print("ISSUE 5: merge_small_chunks Checks Wrong Chunk")
print("Severity: MEDIUM - Function doesn't work as intended")
print("=" * 70)

chunks5 = [
    Chunk("天地玄黃宇宙洪荒", 0, start_pos=0, end_pos=8),  # size=8
    Chunk("日", 1, start_pos=8, end_pos=9),  # size=1, too small
]

print(f"\nInput: Chunk 0 (size=8), Chunk 1 (size=1)")
print(f"min_size=4")

merged5 = merge_small_chunks(chunks5, min_size=4)
print(f"Output: {len(merged5)} chunks (expected: 1 merged chunk)")

print("\nProblem in code (line 318):")
print("  if merged[-1].size < min_size:")
print("This checks if the PREVIOUS chunk is small, but chunk 0 has size 8 >= 4")
print("Should check if CURRENT chunk (chunk being iterated) is small")

# ============================================================================
# ISSUE 6: errors='replace' Masks Corruption Instead of Fixing It
# ============================================================================
print("\n" + "=" * 70)
print("ISSUE 6: errors='replace' Masks Corruption")
print("Severity: HIGH - Silent data corruption")
print("=" * 70)

text_bytes = text.encode('utf-8')
bad_chunk = text_bytes[0:50]  # Cuts mid-character

try:
    bad_chunk.decode('utf-8', errors='strict')
except UnicodeDecodeError as e:
    print(f"\nStrict decoding fails: {e}")

masked = bad_chunk.decode('utf-8', errors='replace')
print(f"With errors='replace': {repr(masked)}")
print(f"Contains replacement char: {'\ufffd' in masked}")

print("\n*** The code uses errors='replace' which hides the problem ***")
print("*** instead of fixing the byte boundary alignment ***")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("SUMMARY OF ISSUES FOUND")
print("=" * 70)

issues = [
    ("Unicode boundary corruption", "CRITICAL", "Fixed-size chunking splits mid-character"),
    ("Overlap position corruption", "CRITICAL", "100% corruption when overlap > 0"),
    ("Byte/char position mismatch", "MEDIUM", "Sentence-aware chunking inconsistent"),
    ("start_pos/end_pos ambiguity", "LOW", "Different semantics per method"),
    ("merge_small_chunks logic", "MEDIUM", "Checks wrong chunk for size"),
    ("errors='replace' masks issue", "HIGH", "Silent data corruption"),
]

print("\n| # | Issue                          | Severity | Description                        |")
print("|---|--------------------------------|----------|------------------------------------|")
for i, (name, severity, desc) in enumerate(issues, 1):
    print(f"| {i} | {name:<30} | {severity:<8} | {desc:<34} |")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
