"""Test script to reproduce Unicode boundary split issue."""

import sys
sys.path.insert(0, 'src')

from data_processing.chunk_builder import ChunkBuilder, ChunkConfig

# Test with classical Chinese text that has multi-byte characters
test_text = """子曰：「學而時習之，不亦說乎？有朋自遠方來，不亦樂乎？人不知而不慍，不亦君子乎？」
有子曰：「其為人也孝弟，而好犯上者，鮮矣；不好犯上，而好作亂者，未之有也。君子務本，本立而道生。孝弟也者，其為仁之本與！」
子曰：「巧言令色，鮮矣仁！」
曾子曰：「吾日三省吾身：為人謀而不忠乎？與朋友交而不信乎？傳不習乎？」
子曰：「道千乘之國，敬事而信，節用而愛人，使民以時。」
子曰：「弟子入則孝，出則弟，謹而信，汎愛眾，而親仁。行有餘力，則以學文。」
子夏曰：「賢賢易色；事父母，能竭其力；事君，能致其身；與朋友交，言而有信。雖曰未學，吾必謂之學矣。」
子曰：「君子不重則不威；學則不固。主忠信。無友不如己者；過則勿憚改。」
曾子曰：「慎終追遠，民德歸厚矣。」
子禽問於子貢曰：「夫子至於是邦也，必聞其政，求之與，抑與之與？」子貢曰：「夫子溫、良、恭、儉、讓以得之。夫子之求之也，其諸異乎人之求之與？」
子曰：「父在，觀其志；父沒，觀其行；三年無改於父之道，可謂孝矣。」
有子曰：「禮之用，和為貴。先王之道，斯為美。小大由之，有所不行。知和而和，不以禮節之，亦不可行也。」
有子曰：「信近於義，言可復也。恭近於禮，遠恥辱也。因不失其親，亦可宗也。」
子曰：「君子食無求飽，居無求安，敏於事而慎於言，就有道而正焉。可謂好學也已。」
子貢曰：「貧而無諂，富而無驕，何如？」子曰：「可也。未若貧而樂，富而好禮者也。」子貢曰：「《詩》云：『如切如磋！如琢如磨』，其斯之謂與？」子曰：「賜也！始可與言《詩》已矣，告諸往而知來者。」
子曰：「不患人之不己知，患不知人也。」"""

# Create builder with small chunk size to force splitting
builder = ChunkBuilder(max_chunk_size=256, overlap=32, min_chunk_size=32)
chunks = builder.build_chunks(test_text, source="test_analects")

print(f"Total chunks: {len(chunks)}")
print("=" * 80)

for i, chunk in enumerate(chunks):
    print(f"\nChunk {i}: {chunk.size} chars, {chunk.byte_size} bytes")
    print(f"  Start: {chunk.start_pos}, End: {chunk.end_pos}")

    # Check for garbled characters at end
    last_10_chars = chunk.text[-10:] if len(chunk.text) >= 10 else chunk.text
    last_10_bytes = last_10_chars.encode('utf-8')

    # Check if chunk ends with incomplete multi-byte sequence
    try:
        # Try to decode the last few bytes
        test_decode = chunk.text.encode('utf-8')
        print(f"  Last 10 chars (repr): {repr(last_10_chars)}")
        print(f"  Last 10 bytes (hex): {last_10_bytes.hex()}")

        # Check for replacement characters (sign of corruption)
        if '\ufffd' in chunk.text:
            print(f"  WARNING: Contains replacement character (U+FFFD)!")

        # Check if text ends mid-character by looking at last bytes
        if len(last_10_bytes) > 0:
            last_byte = last_10_bytes[-1]
            # UTF-8 continuation bytes are 0x80-0xBF
            if 0x80 <= last_byte <= 0xBF:
                print(f"  WARNING: Chunk ends with continuation byte 0x{last_byte:02x}!")

    except Exception as e:
        print(f"  ERROR checking chunk: {e}")

    # Print preview
    preview = chunk.text[:50].replace('\n', '\\n')
    print(f"  Preview: {preview}...")

# Now test fixed-size chunking which is more likely to have the issue
print("\n" + "=" * 80)
print("Testing FIXED-SIZE chunking (more likely to corrupt):")
print("=" * 80)

builder_no_sentences = ChunkBuilder(max_chunk_size=128, overlap=16,
                                     min_chunk_size=32, respect_sentences=False)
chunks_fixed = builder_no_sentences.build_chunks(test_text, source="test_fixed")

print(f"Total chunks: {len(chunks_fixed)}")

for i, chunk in enumerate(chunks_fixed):
    print(f"\nChunk {i}: {chunk.size} chars, {chunk.byte_size} bytes")

    # Check for garbled characters at end
    last_10_chars = chunk.text[-10:] if len(chunk.text) >= 10 else chunk.text
    last_10_bytes = last_10_chars.encode('utf-8')

    try:
        print(f"  Last 10 chars (repr): {repr(last_10_chars)}")
        print(f"  Last 10 bytes (hex): {last_10_bytes.hex()}")

        if '\ufffd' in chunk.text:
            print(f"  WARNING: Contains replacement character (U+FFFD)!")

        # Check if chunk text when re-encoded matches original byte slice
        # This detects if decoding lost information
        reencoded = chunk.text.encode('utf-8')
        original_bytes = test_text.encode('utf-8')[chunk.start_pos:chunk.end_pos]

        if reencoded != original_bytes:
            print(f"  WARNING: Re-encoded bytes don't match original!")
            print(f"    Original bytes length: {len(original_bytes)}")
            print(f"    Re-encoded bytes length: {len(reencoded)}")

        # Check if text ends mid-character
        if len(last_10_bytes) > 0:
            last_byte = last_10_bytes[-1]
            if 0x80 <= last_byte <= 0xBF:
                print(f"  WARNING: Chunk ends with continuation byte 0x{last_byte:02x}!")

    except Exception as e:
        print(f"  ERROR checking chunk: {e}")

    preview = chunk.text[:50].replace('\n', '\\n')
    print(f"  Preview: {preview}...")
