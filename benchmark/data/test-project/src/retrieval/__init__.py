"""Retrieval module for RAG-augmented inference.

Provides vector-based retrieval using Milvus for classical Chinese texts.
"""

from .rag_pipeline import RAGPipeline, RAGConfig

__all__ = ["RAGPipeline", "RAGConfig"]
