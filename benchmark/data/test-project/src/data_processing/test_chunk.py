#!/usr/bin/env python3
"""Test script to reproduce Unicode boundary corruption."""

from chunk_builder import ChunkBuilder, ChunkConfig

def test_fixed_size_chunking():
    """Test fixed-size chunking with multi-byte characters."""
    # Classical Chinese text with many multi-byte characters
    test_text = '子曰：「學而時習之，不亦說乎？」' * 50
    
    # Force fixed-size chunking (no sentence awareness)
    config = ChunkConfig(max_chunk_size=256, overlap=32, respect_sentences=False)
    builder = ChunkBuilder(config=config)
    chunks = builder.build_chunks(test_text)
    
    print('=== Fixed-Size Chunking Test ===')
    print(f'Total chunks: {len(chunks)}')
    print()
    
    for i, chunk in enumerate(chunks):
        print(f'Chunk {i}:')
        print(f'  Size: {chunk.size} chars, {chunk.byte_size} bytes')
        
        # Check last bytes for corruption
        encoded = chunk.text.encode('utf-8')
        last_bytes = encoded[-10:] if len(encoded) >= 10 else encoded
        print(f'  Last bytes (hex): {last_bytes.hex()}')
        print(f'  Ends with: {repr(chunk.text[-10:])}')
        
        # Check for corruption indicators
        if '\ufffd' in chunk.text:
            print(f'  ⚠️ CORRUPTION: Contains replacement character (U+FFFD)!')
        
        # Check for incomplete multi-byte sequence at end
        if len(encoded) > 0:
            last_byte = encoded[-1]
            # UTF-8 continuation bytes start with 10xxxxxx (0x80-0xBF)
            # If last byte is 0x80-0xBF, the sequence is incomplete
            if 0x80 <= last_byte <= 0xBF:
                print(f'  ⚠️ CORRUPTION: Incomplete multi-byte sequence! Last byte: 0x{last_byte:02x}')
        print()
    
    return chunks


def test_sentence_aware_chunking():
    """Test sentence-aware chunking."""
    test_text = '子曰：「學而時習之，不亦說乎？」有朋自遠方來，不亦樂乎？' * 30
    
    config = ChunkConfig(max_chunk_size=256, overlap=32, respect_sentences=True)
    builder = ChunkBuilder(config=config)
    chunks = builder.build_chunks(test_text)
    
    print('=== Sentence-Aware Chunking Test ===')
    print(f'Total chunks: {len(chunks)}')
    print()
    
    for i, chunk in enumerate(chunks):
        print(f'Chunk {i}:')
        print(f'  Size: {chunk.size} chars, {chunk.byte_size} bytes')
        print(f'  Ends with: {repr(chunk.text[-20:])}')
        
        # Check for corruption
        encoded = chunk.text.encode('utf-8')
        if len(encoded) > 0:
            last_byte = encoded[-1]
            if 0x80 <= last_byte <= 0xBF:
                print(f'  ⚠️ CORRUPTION: Incomplete multi-byte sequence!')
        print()
    
    return chunks


if __name__ == '__main__':
    print('Testing Chunk Builder Unicode Boundary Handling\n')
    print('=' * 60)
    print()
    
    fixed_chunks = test_fixed_size_chunking()
    print()
    print('=' * 60)
    print()
    sentence_chunks = test_sentence_aware_chunking()
