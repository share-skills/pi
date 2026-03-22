"""Data processing module for OCR ingestion, text cleaning, and chunking.

This module provides the core text processing pipeline:
1. OCRPipeline — Scans PDFs/images and extracts Chinese text
2. TextCleaner — Normalizes and cleans OCR output
3. ChunkBuilder — Splits cleaned text into training-ready chunks
"""

def get_ocr_pipeline():
    """Get OCR pipeline instance (lazy import to avoid heavy deps)."""
    from .ocr_pipeline import OCRPipeline
    return OCRPipeline

def get_text_cleaner():
    """Get text cleaner class."""
    from .text_cleaner import TextCleaner
    return TextCleaner

def get_chunk_builder():
    """Get chunk builder class."""
    from .chunk_builder import ChunkBuilder
    return ChunkBuilder
