"""Test script to reproduce Unicode boundary split issue."""

import sys
sys.path.insert(0, '/Users/hepin/IdeaProjects/pi/benchmark/data/test-project')

from src.data_processing.chunk_builder import ChunkBuilder, ChunkConfig

# Test with classical Chinese text that has multi-byte characters
test_text = """
子曰：「學而時習之，不亦說乎？有朋自遠方來，不亦樂乎？人不知而不慍，不亦君子乎？」
有子曰：「其為人也孝弟，而好犯上者，鮮矣；不好犯上，而好作亂者，未之有也。君子務本，本立而道生。孝弟也者，其為仁之本與！」
子曰：「巧言令色，鮮矣仁！」
曾子曰：「吾日三省吾身：為人謀而不忠乎？與朋友交而不信乎？傳不習乎？」
子曰：「道千乘之國，敬事而信，節用而愛人，使民以時。」
子曰：「弟子入則孝，出則弟，謹而信，汎愛眾，而親仁。行有餘力，則以學文。」
子夏曰：「賢賢易色；事父母，能竭其力；事君，能致其身；與朋友交，言而有信。雖曰未學，吾必謂之學矣。」
子曰：「君子不重則不威；學則不固。主忠信。無友不如己者；過則勿憚改。」
曾子曰：「慎終追遠，民德歸厚矣。」
子禽問於子貢曰：「夫子至於是邦也，必聞其政，求之與？抑與之與？」子貢曰：「夫子溫、良、恭、儉、讓以得之。夫子之求之也，其諸異乎人之求之與！」
子曰：「父在，觀其志；父沒，觀其行；三年無改於父之道，可謂孝矣。」
有子曰：「禮之用，和為貴。先王之道，斯為美。小大由之，有所不行。知和而和，不以禮節之，亦不可行也。」
"""

print("=" * 80)
print("Testing ChunkBuilder with classical Chinese text")
print("=" * 80)

# Test with smaller chunk size to force splitting
config = ChunkConfig(
    max_chunk_size=256,  # bytes
    min_chunk_size=32,
    overlap=64,
    respect_sentences=True
)

builder = ChunkBuilder(config=config)
chunks = builder.build_chunks(test_text, source="test_analects.txt")

print(f"\nTotal chunks: {len(chunks)}")
print(f"Statistics: {builder.get_stats()}")

for i, chunk in enumerate(chunks):
    print(f"\n--- Chunk {i} ---")
    print(f"Size: {chunk.size} chars, Byte size: {chunk.byte_size} bytes")
    print(f"Position: {chunk.start_pos} - {chunk.end_pos}")

    # Check for corruption indicators
    text_bytes = chunk.text.encode('utf-8')

    # Check for replacement character (U+FFFD) - indicates decode error was masked
    if '\ufffd' in chunk.text:
        print(f"⚠️  WARNING: Contains replacement character (U+FFFD) - decode error masked!")

    # Check for incomplete multi-byte sequences at end
    last_char = chunk.text[-1] if chunk.text else ''
    last_char_bytes = last_char.encode('utf-8')

    # Valid UTF-8 lead bytes: 0x00-0x7F (ASCII), 0xC0-0xDF (2-byte), 0xE0-0xEF (3-byte), 0xF0-0xF7 (4-byte)
    # Valid UTF-8 continuation bytes: 0x80-0xBF
    if last_char_bytes:
        last_byte = last_char_bytes[-1]
        if 0x80 <= last_byte <= 0xBF:
            print(f"⚠️  WARNING: Last char ends with continuation byte 0x{last_byte:02x} - potential truncation!")

    # Show last 10 chars as repr to see any hidden issues
    print(f"Last 10 chars (repr): {repr(chunk.text[-10:])}")

    # Show raw bytes of last 5 chars
    last_5_bytes = chunk.text[-5:].encode('utf-8') if len(chunk.text) >= 5 else chunk.text.encode('utf-8')
    print(f"Last 5 chars as bytes: {' '.join(f'{b:02x}' for b in last_5_bytes)}")

# Now test fixed-size chunking (non-sentence-aware) which is more likely to show the issue
print("\n" + "=" * 80)
print("Testing FIXED-SIZE chunking (more likely to corrupt)")
print("=" * 80)

config2 = ChunkConfig(
    max_chunk_size=128,  # Even smaller to force mid-character splits
    min_chunk_size=16,
    overlap=32,
    respect_sentences=False  # This will use _fixed_size_chunking
)

builder2 = ChunkBuilder(config=config2)
chunks2 = builder2.build_chunks(test_text, source="test_analects_fixed.txt")

print(f"\nTotal chunks: {len(chunks2)}")

for i, chunk in enumerate(chunks2):
    print(f"\n--- Chunk {i} ---")
    print(f"Size: {chunk.size} chars, Byte size: {chunk.byte_size} bytes")

    # Check for corruption
    if '\ufffd' in chunk.text:
        print(f"⚠️  WARNING: Contains replacement character (U+FFFD)!")

    # Check last bytes
    if chunk.text:
        last_char = chunk.text[-1]
        last_char_bytes = last_char.encode('utf-8')
        if last_char_bytes:
            last_byte = last_char_bytes[-1]
            if 0x80 <= last_byte <= 0xBF:
                print(f"⚠️  CRITICAL: Ends with UTF-8 continuation byte 0x{last_byte:02x}!")

    print(f"Text preview: {repr(chunk.text[:50])}...")
    print(f"Last 20 bytes: {' '.join(f'{b:02x}' for b in chunk.text[-10:].encode('utf-8'))}")
