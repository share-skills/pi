#!/usr/bin/env python3
"""Verify chunk builder Unicode boundary corruption."""

import sys
sys.path.insert(0, '/Users/hepin/IdeaProjects/pi/benchmark/data/test-project')

from src.data_processing.chunk_builder import ChunkBuilder, ChunkConfig

# Create text long enough to force multiple chunks
text = "天地玄黃宇宙洪荒日月盈昃辰宿列張寒來暑往秋收冬藏" * 10
print(f"Input text length: {len(text)} chars, {len(text.encode('utf-8'))} bytes")

config = ChunkConfig(
    max_chunk_size=128,  # Force splitting
    min_chunk_size=16,
    overlap=32,
    respect_sentences=False  # Use _fixed_size_chunking
)

builder = ChunkBuilder(config=config)
chunks = builder.build_chunks(text, source="test.txt")

print(f"\nTotal chunks: {len(chunks)}")
corrupted_count = 0
for i, chunk in enumerate(chunks):
    has_replacement = "\ufffd" in chunk.text
    if has_replacement:
        corrupted_count += 1
        print(f"Chunk {i}: CORRUPTED (contains U+FFFD)")
        print(f"  Text repr: {repr(chunk.text[-10:])}")
    else:
        print(f"Chunk {i}: OK ({chunk.size} chars, {chunk.byte_size} bytes)")

print(f"\nCorrupted chunks: {corrupted_count}/{len(chunks)}")

# Also test sentence-aware mode
print("\n" + "=" * 60)
print("Testing sentence-aware mode")
print("=" * 60)

text2 = "子曰：學而時習之，不亦說乎？" * 50
print(f"Input text length: {len(text2)} chars, {len(text2.encode('utf-8'))} bytes")

config2 = ChunkConfig(
    max_chunk_size=256,
    min_chunk_size=32,
    overlap=64,
    respect_sentences=True  # Use _sentence_aware_chunking
)

builder2 = ChunkBuilder(config=config2)
chunks2 = builder2.build_chunks(text2, source="test2.txt")

print(f"\nTotal chunks: {len(chunks2)}")
corrupted_count2 = 0
for i, chunk in enumerate(chunks2):
    has_replacement = "\ufffd" in chunk.text
    if has_replacement:
        corrupted_count2 += 1
        print(f"Chunk {i}: CORRUPTED (contains U+FFFD)")
        print(f"  Text repr: {repr(chunk.text[-10:])}")
    else:
        print(f"Chunk {i}: OK ({chunk.size} chars, {chunk.byte_size} bytes)")

print(f"\nCorrupted chunks: {corrupted_count2}/{len(chunks2)}")
