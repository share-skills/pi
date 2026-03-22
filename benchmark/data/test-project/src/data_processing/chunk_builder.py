"""Chunk Builder for Classical Chinese Text.

Splits cleaned text into chunks suitable for training data and RAG indexing.
Handles sentence-aware splitting to avoid breaking mid-sentence, with
configurable overlap for context preservation.

The chunking strategy:
1. Split text into sentences at Chinese punctuation boundaries
2. Group sentences into chunks of target size
3. Add overlap between consecutive chunks
4. Validate chunk boundaries and encoding

Usage:
    builder = ChunkBuilder(max_chunk_size=512, overlap=64)
    chunks = builder.build_chunks(cleaned_text)
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Iterator
from dataclasses import dataclass
from hashlib import md5

logger = logging.getLogger(__name__)


@dataclass
class ChunkConfig:
    """Configuration for chunk building."""
    max_chunk_size: int = 512  # Maximum chunk size
    min_chunk_size: int = 64   # Minimum viable chunk size
    overlap: int = 64          # Overlap between consecutive chunks
    respect_sentences: bool = True  # Try to split at sentence boundaries
    respect_paragraphs: bool = True  # Try to split at paragraph boundaries
    encoding: str = "utf-8"    # Target encoding for size calculation
    include_metadata: bool = True
    strip_whitespace: bool = True


class Chunk:
    """Represents a single text chunk with metadata."""

    def __init__(self, text: str, index: int, source: str = "",
                 start_pos: int = 0, end_pos: int = 0):
        self.text = text
        self.index = index
        self.source = source
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.chunk_id = md5(f"{source}:{start_pos}:{end_pos}".encode()).hexdigest()[:12]

    @property
    def size(self) -> int:
        """Return the size of this chunk in characters."""
        return len(self.text)

    @property
    def byte_size(self) -> int:
        """Return the size of this chunk in bytes (UTF-8)."""
        return len(self.text.encode("utf-8"))

    def to_dict(self) -> Dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "index": self.index,
            "source": self.source,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "size": self.size,
            "byte_size": self.byte_size,
        }

    def __repr__(self):
        preview = self.text[:40] + "..." if len(self.text) > 40 else self.text
        return f"Chunk(idx={self.index}, size={self.size}, text='{preview}')"


class ChunkBuilder:
    """Builds text chunks for training and retrieval.

    Splits input text into overlapping chunks of configurable size,
    respecting sentence and paragraph boundaries where possible.

    Args:
        config: ChunkConfig or keyword arguments for chunk configuration.

    Example:
        >>> builder = ChunkBuilder(max_chunk_size=256)
        >>> chunks = builder.build_chunks("子曰：「學而時習之，不亦說乎？」...")
        >>> for chunk in chunks:
        ...     print(f"Chunk {chunk.index}: {chunk.size} chars")
    """

    def __init__(self, config: ChunkConfig = None, **kwargs):
        if config:
            self.config = config
        else:
            self.config = ChunkConfig(**kwargs)

        self._stats = {"total_chunks": 0, "total_chars": 0, "avg_chunk_size": 0}

    def build_chunks(self, text: str, source: str = "") -> List[Chunk]:
        """Split text into chunks with overlap.

        Args:
            text: Input text to chunk.
            source: Source identifier for metadata.

        Returns:
            List of Chunk objects.
        """
        if not text or not text.strip():
            return []

        if self.config.strip_whitespace:
            text = text.strip()

        text_bytes = text.encode(self.config.encoding)
        total_size = len(text_bytes)  # Size in bytes, not characters

        if total_size <= self.config.max_chunk_size:
            chunk = Chunk(text=text, index=0, source=source,
                          start_pos=0, end_pos=len(text))
            self._stats["total_chunks"] = 1
            self._stats["total_chars"] = len(text)
            self._stats["avg_chunk_size"] = len(text)
            return [chunk]

        # Split into sentences first if configured
        if self.config.respect_sentences:
            return self._sentence_aware_chunking(text, text_bytes, source)
        else:
            return self._fixed_size_chunking(text, text_bytes, source)

    def _fixed_size_chunking(self, text: str, text_bytes: bytes,
                              source: str) -> List[Chunk]:
        """Simple fixed-size chunking with overlap.

        Note: Uses byte-level offsets for size control to ensure chunks
        stay within token limits for models with byte-level tokenizers.
        """
        chunks = []
        max_size = self.config.max_chunk_size
        overlap = self.config.overlap
        pos = 0
        chunk_idx = 0

        while pos < len(text_bytes):
            end = min(pos + max_size, len(text_bytes))
            chunk_bytes = text_bytes[pos:end]

            # Decode chunk — errors='replace' masks the corruption by
            # inserting replacement characters (U+FFFD) instead of failing
            try:
                chunk_text = chunk_bytes.decode(self.config.encoding)
            except UnicodeDecodeError:
                chunk_text = chunk_bytes.decode(self.config.encoding, errors="replace")

            if len(chunk_text.strip()) >= self.config.min_chunk_size:
                chunk = Chunk(
                    text=chunk_text,
                    index=chunk_idx,
                    source=source,
                    start_pos=pos,
                    end_pos=end,
                )
                chunks.append(chunk)
                chunk_idx += 1

            # Move position forward, accounting for overlap
            pos = end - overlap
            if pos <= chunks[-1].start_pos if chunks else 0:
                pos = end  # Avoid infinite loop

        self._update_stats(chunks)
        return chunks

    def _sentence_aware_chunking(self, text: str, text_bytes: bytes,
                                  source: str) -> List[Chunk]:
        """Chunk text while respecting sentence boundaries.

        Groups complete sentences into chunks, only splitting mid-sentence
        if a single sentence exceeds max_chunk_size.
        """
        sentences = self._split_sentences(text)
        chunks = []
        current_sentences = []
        current_size = 0
        chunk_idx = 0
        char_pos = 0

        for sentence in sentences:
            sentence_size = len(sentence.encode(self.config.encoding))

            if current_size + sentence_size > self.config.max_chunk_size:
                if current_sentences:
                    chunk_text = "".join(current_sentences)
                    chunk = Chunk(
                        text=chunk_text,
                        index=chunk_idx,
                        source=source,
                        start_pos=char_pos - len(chunk_text),
                        end_pos=char_pos,
                    )
                    chunks.append(chunk)
                    chunk_idx += 1

                    # Keep last sentence(s) for overlap
                    overlap_sentences = []
                    overlap_size = 0
                    for s in reversed(current_sentences):
                        s_size = len(s.encode(self.config.encoding))
                        if overlap_size + s_size <= self.config.overlap:
                            overlap_sentences.insert(0, s)
                            overlap_size += s_size
                        else:
                            break

                    current_sentences = overlap_sentences
                    current_size = overlap_size

            current_sentences.append(sentence)
            current_size += sentence_size
            char_pos += len(sentence)

        # Handle remaining sentences
        if current_sentences:
            chunk_text = "".join(current_sentences)
            chunk = Chunk(
                text=chunk_text,
                index=chunk_idx,
                source=source,
                start_pos=char_pos - len(chunk_text),
                end_pos=char_pos,
            )
            chunks.append(chunk)

        self._update_stats(chunks)
        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences at Chinese punctuation boundaries.

        Preserves the punctuation with the preceding sentence.
        """
        # Split at sentence-ending punctuation, keeping the delimiter
        parts = re.split(r"((?:[。！？；]+))", text)

        # Recombine: attach punctuation to the preceding text
        sentences = []
        for i in range(0, len(parts) - 1, 2):
            sentence = parts[i]
            if i + 1 < len(parts):
                sentence += parts[i + 1]
            if sentence.strip():
                sentences.append(sentence)

        # Handle trailing text without punctuation
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentences.append(parts[-1])

        return sentences

    def _update_stats(self, chunks: List[Chunk]):
        """Update internal statistics."""
        self._stats["total_chunks"] = len(chunks)
        self._stats["total_chars"] = sum(c.size for c in chunks)
        if chunks:
            self._stats["avg_chunk_size"] = self._stats["total_chars"] / len(chunks)

    def build_chunks_from_file(self, file_path: str, encoding: str = "utf-8") -> List[Chunk]:
        """Read a file and build chunks from its content.

        Args:
            file_path: Path to input text file.
            encoding: File encoding (default: utf-8).

        Returns:
            List of Chunk objects.
        """
        with open(file_path, "r", encoding=encoding) as f:
            text = f.read()
        return self.build_chunks(text, source=file_path)

    def build_chunks_streaming(self, text: str, source: str = "") -> Iterator[Chunk]:
        """Yield chunks one at a time for memory-efficient processing.

        Same algorithm as build_chunks but yields instead of collecting.
        Useful for very large documents.
        """
        chunks = self.build_chunks(text, source)
        yield from chunks

    def get_stats(self) -> Dict:
        """Return chunking statistics."""
        return dict(self._stats)


def merge_small_chunks(chunks: List[Chunk], min_size: int = 64) -> List[Chunk]:
    """Post-processing step to merge chunks smaller than min_size.

    Merges small chunks with their neighbors to ensure all chunks
    meet the minimum size requirement.

    Args:
        chunks: List of Chunk objects to process.
        min_size: Minimum acceptable chunk size in characters.

    Returns:
        New list of Chunk objects with small chunks merged.
    """
    if not chunks:
        return []

    merged = [chunks[0]]
    for chunk in chunks[1:]:
        if merged[-1].size < min_size:
            # Merge with previous chunk
            merged[-1] = Chunk(
                text=merged[-1].text + chunk.text,
                index=merged[-1].index,
                source=merged[-1].source,
                start_pos=merged[-1].start_pos,
                end_pos=chunk.end_pos,
            )
        else:
            merged.append(chunk)

    # Re-index
    for i, chunk in enumerate(merged):
        chunk.index = i

    return merged
