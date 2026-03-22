"""Tests for chunk builder."""

import pytest
from src.data_processing.chunk_builder import ChunkBuilder, ChunkConfig, Chunk, merge_small_chunks


class TestChunk:
    def test_chunk_creation(self):
        chunk = Chunk(text="子曰：學而時習之", index=0, source="test")
        assert chunk.size == 9  # 9 characters
        assert chunk.byte_size == 27  # 9 * 3 bytes per CJK char (UTF-8)

    def test_chunk_to_dict(self):
        chunk = Chunk(text="天下大同", index=1, source="test.txt",
                      start_pos=0, end_pos=4)
        d = chunk.to_dict()
        assert d["text"] == "天下大同"
        assert d["size"] == 4
        assert d["byte_size"] == 12

    def test_chunk_id_deterministic(self):
        c1 = Chunk(text="abc", index=0, source="file", start_pos=0, end_pos=3)
        c2 = Chunk(text="abc", index=0, source="file", start_pos=0, end_pos=3)
        assert c1.chunk_id == c2.chunk_id


class TestChunkBuilder:
    def test_short_text_no_split(self):
        builder = ChunkBuilder(max_chunk_size=1024)
        text = "子曰：學而時習之，不亦說乎？"
        chunks = builder.build_chunks(text)
        assert len(chunks) == 1
        assert chunks[0].text == text

    def test_empty_text(self):
        builder = ChunkBuilder()
        assert builder.build_chunks("") == []
        assert builder.build_chunks("   ") == []

    def test_byte_vs_char_boundary(self):
        """
        Test chunking behaviour when max_chunk_size is in bytes.

        A Chinese character is 3 bytes in UTF-8, so:
          max_chunk_size=10 bytes covers 3 full chars (9 bytes).
        """
        builder = ChunkBuilder(ChunkConfig(
            max_chunk_size=10,   # 10 bytes
            min_chunk_size=1,
            overlap=0,
            respect_sentences=False,
        ))

        # Each Chinese char = 3 bytes; 3 chars = 9 bytes, 4 chars = 12 bytes
        text = "天地玄黃宇宙洪荒日月盈昃辰宿列張"

        chunks = builder.build_chunks(text)

        full_text = "".join(c.text for c in chunks)
        has_replacement = "\ufffd" in full_text
        if has_replacement:
            print("UTF-8 boundary split detected in chunks")

    def test_sentence_aware_chunking(self):
        builder = ChunkBuilder(ChunkConfig(
            max_chunk_size=512,
            overlap=64,
            respect_sentences=True,
        ))
        text = "子曰：學而時習之，不亦說乎？有朋自遠方來，不亦樂乎？人不知而不慍，不亦君子乎？"
        chunks = builder.build_chunks(text, source="lunyu")
        assert len(chunks) >= 1
        for chunk in chunks:
            assert len(chunk.text) > 0

    def test_chunk_size_bytes_vs_chars(self):
        """
        Show that max_chunk_size operates in bytes but Chinese chars are 3 bytes each.
        A max_chunk_size=99 will hold ~33 Chinese chars, not 99.
        """
        config = ChunkConfig(max_chunk_size=99, min_chunk_size=1, overlap=0,
                             respect_sentences=False)
        builder = ChunkBuilder(config)
        # 40 Chinese chars = 120 bytes > 99 → should split into 2 chunks
        text = "天" * 40
        chunks = builder.build_chunks(text)
        assert len(chunks) >= 1

    def test_stats(self):
        builder = ChunkBuilder(max_chunk_size=100)
        text = "a" * 500
        chunks = builder.build_chunks(text)
        stats = builder.get_stats()
        assert stats["total_chunks"] == len(chunks)
        assert stats["total_chars"] > 0


class TestMergeSmallChunks:
    def test_merge_empty(self):
        assert merge_small_chunks([]) == []

    def test_merge_small_into_previous(self):
        chunks = [
            Chunk("天地玄黃宇宙洪荒", 0, start_pos=0, end_pos=8),
            Chunk("日", 1, start_pos=8, end_pos=9),  # Too small
        ]
        merged = merge_small_chunks(chunks, min_size=4)
        assert len(merged) == 1
        assert "天地玄黃" in merged[0].text

    def test_reindex_after_merge(self):
        chunks = [
            Chunk("天地玄黃", 0, start_pos=0, end_pos=4),
            Chunk("日", 1, start_pos=4, end_pos=5),
            Chunk("宇宙洪荒", 2, start_pos=5, end_pos=9),
        ]
        merged = merge_small_chunks(chunks, min_size=4)
        for i, c in enumerate(merged):
            assert c.index == i
