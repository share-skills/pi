#!/usr/bin/env python3
"""Test script to reproduce Unicode boundary corruption."""

import sys
sys.path.insert(0, 'data/test-project/src')

from data_processing.chunk_builder import ChunkBuilder, ChunkConfig

def test_fixed_size_chunking():
    """Test fixed-size chunking with Chinese text."""
    print("=" * 60)
    print("TEST 1: Fixed-Size Chunking (respect_sentences=False)")
    print("=" * 60)

    # Create test text - classical Chinese, all 3-byte UTF-8 chars
    text = "子曰：「學而時習之，不亦說乎？」" * 50
    print(f"Input text: {len(text)} chars, {len(text.encode('utf-8'))} bytes\n")

    config = ChunkConfig(
        max_chunk_size=256,  # bytes
        overlap=32,
        respect_sentences=False,
        min_chunk_size=10,
    )
    builder = ChunkBuilder(config=config)
    chunks = builder.build_chunks(text)

    print(f"Generated {len(chunks)} chunks:\n")
    for i, chunk in enumerate(chunks):
        has_fffd = '\ufffd' in chunk.text
        last_bytes = chunk.text.encode('utf-8')[-10:] if chunk.text else b''
        last_chars = chunk.text[-10:] if len(chunk.text) > 10 else chunk.text

        print(f"Chunk {i}:")
        print(f"  Size: {chunk.size} chars, {chunk.byte_size} bytes")
        print(f"  Byte range: [{chunk.start_pos}:{chunk.end_pos}]")
        print(f"  Last 10 chars: {repr(last_chars)}")
        print(f"  Last 10 bytes: {last_bytes}")
        if has_fffd:
            print(f"  *** CORRUPTED: Contains U+FFFD replacement character!")
        print()

    return chunks


def test_sentence_aware_chunking():
    """Test sentence-aware chunking."""
    print("=" * 60)
    print("TEST 2: Sentence-Aware Chunking (respect_sentences=True)")
    print("=" * 60)

    text = "子曰：「學而時習之，不亦說乎？」有朋自遠方來，不亦樂乎？" * 30
    print(f"Input text: {len(text)} chars, {len(text.encode('utf-8'))} bytes\n")

    config = ChunkConfig(
        max_chunk_size=256,
        overlap=32,
        respect_sentences=True,
        min_chunk_size=10,
    )
    builder = ChunkBuilder(config=config)
    chunks = builder.build_chunks(text)

    print(f"Generated {len(chunks)} chunks:\n")
    for i, chunk in enumerate(chunks):
        has_fffd = '\ufffd' in chunk.text
        last_chars = chunk.text[-15:] if len(chunk.text) > 15 else chunk.text

        print(f"Chunk {i}:")
        print(f"  Size: {chunk.size} chars, {chunk.byte_size} bytes")
        print(f"  Last chars: {repr(last_chars)}")
        if has_fffd:
            print(f"  *** CORRUPTED: Contains U+FFFD!")
        print()

    return chunks


def test_overlap_issue():
    """Test that overlap doesn't cause byte boundary issues."""
    print("=" * 60)
    print("TEST 3: Overlap Boundary Issue")
    print("=" * 60)

    # Text where overlap will land mid-character
    text = "abcdefghij" * 100 + "子曰學而時習之" * 50
    print(f"Input text: {len(text)} chars, {len(text.encode('utf-8'))} bytes")

    config = ChunkConfig(
        max_chunk_size=100,
        overlap=33,  # Will land in middle of Chinese chars
        respect_sentences=False,
        min_chunk_size=5,
    )
    builder = ChunkBuilder(config=config)
    chunks = builder.build_chunks(text)

    print(f"Generated {len(chunks)} chunks:\n")
    corrupted_count = 0
    for i, chunk in enumerate(chunks):
        has_fffd = '\ufffd' in chunk.text
        if has_fffd:
            corrupted_count += 1
            print(f"Chunk {i}: CORRUPTED")
            print(f"  Last 20 chars: {repr(chunk.text[-20:])}")

    print(f"\nTotal corrupted: {corrupted_count}/{len(chunks)}")
    return chunks


if __name__ == "__main__":
    test_fixed_size_chunking()
    test_sentence_aware_chunking()
    test_overlap_issue()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("The _fixed_size_chunking method cuts text at arbitrary BYTE positions.")
    print("When a cut lands in the middle of a multi-byte UTF-8 character:")
    print("  1. UnicodeDecodeError is raised")
    print("  2. errors='replace' masks it with U+FFFD")
    print("  3. The original character bytes are LOST forever")
    print("\nThe fix must ensure cuts happen only at CHARACTER boundaries.")
