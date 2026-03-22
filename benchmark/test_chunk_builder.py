#!/usr/bin/env python3
"""Test script to verify ChunkBuilder bugs."""

import sys
sys.path.insert(0, 'data/test-project/src')
from data_processing.chunk_builder import ChunkBuilder

def test_unicode_corruption():
    """Test 1: Unicode corruption in fixed-size chunking."""
    print("=" * 60)
    print("TEST 1: Unicode Corruption in _fixed_size_chunking")
    print("=" * 60)

    text = "子曰：「學而時習之，不亦說乎？」" * 50
    builder = ChunkBuilder(max_chunk_size=512, overlap=64, respect_sentences=False)
    chunks = builder.build_chunks(text, source="test")

    print(f"Input: {len(text)} chars, {len(text.encode('utf-8'))} bytes")
    print(f"Output: {len(chunks)} chunks\n")

    corrupted_count = 0
    for i, chunk in enumerate(chunks):
        has_replacement = chr(0xFFFD) in chunk.text
        if has_replacement:
            corrupted_count += 1
            print(f"Chunk {i}: CORRUPTED (U+FFFD replacement character found)")
            print(f"  End of chunk: {repr(chunk.text[-30:])}")
        else:
            print(f"Chunk {i}: OK ({chunk.size} chars, {chunk.byte_size} bytes)")

    print(f"\nTotal corrupted chunks: {corrupted_count}/{len(chunks)}")
    return corrupted_count > 0


def test_position_tracking():
    """Test 2: Position tracking bug in sentence-aware chunking."""
    print("\n" + "=" * 60)
    print("TEST 2: Position Tracking Bug in _sentence_aware_chunking")
    print("=" * 60)

    text = "子曰。學而時習之。" * 30
    builder = ChunkBuilder(max_chunk_size=256, overlap=32, respect_sentences=True)
    chunks = builder.build_chunks(text, source="test2")

    print(f"Input: {len(text)} chars")
    print(f"Output: {len(chunks2)} chunks\n" if 'chunks2' in dir() else f"Output: {len(chunks)} chunks\n")

    mismatch_count = 0
    for i, chunk in enumerate(chunks):
        extracted = text[chunk.start_pos:chunk.end_pos]
        matches = extracted == chunk.text
        if not matches:
            mismatch_count += 1
            print(f"Chunk {i}: MISMATCH!")
            print(f"  start_pos={chunk.start_pos}, end_pos={chunk.end_pos}")
            print(f"  Expected: {repr(extracted[:40])}...")
            print(f"  Got:      {repr(chunk.text[:40])}...")
        else:
            print(f"Chunk {i}: OK")

    print(f"\nTotal mismatches: {mismatch_count}/{len(chunks)}")
    return mismatch_count > 0


def test_sentence_splitting():
    """Test 3: Regex doesn't match Chinese punctuation."""
    print("\n" + "=" * 60)
    print("TEST 3: Sentence Splitting with Chinese Punctuation")
    print("=" * 60)

    text = "子曰：「學而時習之，不亦說乎？」有朋自遠方來，不亦樂乎？人不知而不慍，不亦君子乎？" * 10
    builder = ChunkBuilder(max_chunk_size=256, respect_sentences=True)
    sentences = builder._split_sentences(text)

    print(f"Input text length: {len(text)} chars")
    print(f"Number of sentences detected: {len(sentences)}")
    print(f"Expected: ~30 sentences (3 per repetition * 10)")

    if len(sentences) < 10:
        print("\nBUG CONFIRMED: Regex fails to split on Chinese punctuation!")
        print(f"First 'sentence' is {len(sentences[0])} chars (should be ~27)")
        return True
    return False


if __name__ == "__main__":
    bug1 = test_unicode_corruption()
    bug2 = test_position_tracking()
    bug3 = test_sentence_splitting()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Bug 1 (Unicode corruption): {'FOUND' if bug1 else 'NOT FOUND'}")
    print(f"Bug 2 (Position tracking):  {'FOUND' if bug2 else 'NOT FOUND'}")
    print(f"Bug 3 (Sentence splitting): {'FOUND' if bug3 else 'NOT FOUND'}")
