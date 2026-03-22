"""RAG Pipeline with Milvus Vector Database.

Provides retrieval-augmented generation for classical Chinese texts using
Milvus as the vector store and BGE embeddings for semantic search.

Architecture:
    1. Text chunks are embedded using BGE-large-zh-v1.5
    2. Embeddings are stored in Milvus collections
    3. At query time, the query is embedded and searched against the collection
    4. Top-k results are returned with relevance scores

Usage:
    rag = RAGPipeline(RAGConfig(collection_name="guwen_chunks"))
    rag.index_chunks(chunks)
    results = rag.search("何為仁？", top_k=5)

Requirements:
    - Milvus 2.3+ running (via Docker or standalone)
    - sentence-transformers or FlagEmbedding
"""

import os
import time
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

import numpy as np
from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)

logger = logging.getLogger(__name__)


# BGE-large-zh-v1.5 embedding dimension
BGE_EMBEDDING_DIM = 1024


@dataclass
class RAGConfig:
    """Configuration for the RAG pipeline."""
    # Milvus connection
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_alias: str = "default"

    # Collection settings
    collection_name: str = "guwen_chunks"
    embedding_dim: int = BGE_EMBEDDING_DIM
    index_type: str = "IVF_FLAT"
    metric_type: str = "COSINE"
    nlist: int = 128
    nprobe: int = 16

    # Embedding model
    embedding_model: str = "BAAI/bge-large-zh-v1.5"
    embedding_batch_size: int = 32
    normalize_embeddings: bool = True

    # Search settings
    top_k: int = 5
    score_threshold: float = 0.5
    rerank: bool = False
    rerank_model: Optional[str] = None

    # Index settings
    max_text_length: int = 4096
    auto_flush: bool = True
    flush_interval: int = 1000


class EmbeddingModel:
    """Wrapper for BGE embedding model.

    Provides text-to-vector encoding with batching support.
    """

    def __init__(self, model_name: str, normalize: bool = True):
        self.model_name = model_name
        self.normalize = normalize
        self._model = None
        self._load_model()

    def _load_model(self):
        """Load the embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode texts to embeddings.

        Args:
            texts: List of text strings to encode.
            batch_size: Batch size for encoding.

        Returns:
            numpy array of shape (len(texts), embedding_dim).
        """
        if not texts:
            return np.array([])

        # Add query instruction prefix for BGE models
        prefixed = [f"为这个句子生成表示以用于检索中文文档: {t}" for t in texts]

        embeddings = self._model.encode(
            prefixed,
            batch_size=batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=len(texts) > 100,
        )

        return embeddings

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a single query string."""
        return self.encode([query], batch_size=1)[0]


class RAGPipeline:
    """RAG pipeline for classical Chinese text retrieval.

    Manages vector indexing and semantic search using Milvus as the
    backend vector store with BGE embeddings.

    Args:
        config: RAGConfig instance with connection and model settings.

    Example:
        >>> config = RAGConfig(collection_name="guwen", milvus_port=19530)
        >>> rag = RAGPipeline(config)
        >>> rag.index_chunks([{"text": "子曰學而時習之", "source": "論語"}])
        >>> results = rag.search("何為學？")
    """

    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        self._collection = None
        self._embedder = None
        self._connected = False

        self._connect()
        self._init_embedder()

    def _connect(self):
        """Establish connection to Milvus."""
        try:
            connections.connect(
                alias=self.config.milvus_alias,
                host=self.config.milvus_host,
                port=self.config.milvus_port,
            )
            self._connected = True
            logger.info(
                f"Connected to Milvus at "
                f"{self.config.milvus_host}:{self.config.milvus_port}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise

    def _init_embedder(self):
        """Initialize the embedding model."""
        self._embedder = EmbeddingModel(
            model_name=self.config.embedding_model,
            normalize=self.config.normalize_embeddings,
        )

    def create_collection(self):
        """Create or get the Milvus collection.

        Sets up the schema with text, source, and embedding fields.
        Creates an IVF index on the embedding field.
        """
        try:
            if utility.has_collection(self.config.collection_name):
                self._collection = Collection(self.config.collection_name)
                logger.info(f"Using existing collection: {self.config.collection_name}")
                return

            # Define collection schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64,
                            is_primary=True, auto_id=True),
                FieldSchema(name="text", dtype=DataType.VARCHAR,
                            max_length=self.config.max_text_length),
                FieldSchema(name="source", dtype=DataType.VARCHAR,
                            max_length=512),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR,
                            dim=self.config.embedding_dim),
            ]

            schema = CollectionSchema(
                fields=fields,
                description="Classical Chinese text chunks for RAG",
            )

            self._collection = Collection(
                name=self.config.collection_name,
                schema=schema,
            )

            # Create index
            index_params = {
                "metric_type": self.config.metric_type,
                "index_type": self.config.index_type,
                "params": {"nlist": self.config.nlist},
            }
            self._collection.create_index(
                field_name="embedding",
                index_params=index_params,
            )

            logger.info(f"Created collection: {self.config.collection_name}")

        except Exception as e:
            logger.warning(f"Collection setup issue: {e}")
            # Fall through — collection might already exist
            if utility.has_collection(self.config.collection_name):
                self._collection = Collection(self.config.collection_name)

    def index_chunks(self, chunks: List[Dict[str, Any]],
                     batch_size: Optional[int] = None) -> int:
        """Index text chunks into the Milvus collection.

        Args:
            chunks: List of dicts with 'text', 'source', and optionally
                    'chunk_index' keys.
            batch_size: Override default embedding batch size.

        Returns:
            Number of chunks successfully indexed.
        """
        if not self._collection:
            self.create_collection()

        batch_size = batch_size or self.config.embedding_batch_size
        indexed = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c["text"] for c in batch]
            sources = [c.get("source", "") for c in batch]
            indices = [c.get("chunk_index", i + j) for j, c in enumerate(batch)]

            # Generate embeddings
            embeddings = self._embedder.encode(texts, batch_size=batch_size)

            # Prepare data for insertion
            data = [
                texts,
                sources,
                indices,
                embeddings.tolist(),
            ]

            try:
                self._collection.insert(data)
                indexed += len(batch)

                if self.config.auto_flush and indexed % self.config.flush_interval == 0:
                    self._collection.flush()
                    logger.debug(f"Flushed at {indexed} chunks")

            except Exception as e:
                logger.error(f"Failed to insert batch at offset {i}: {e}")

        # Final flush
        if self.config.auto_flush:
            self._collection.flush()

        logger.info(f"Indexed {indexed}/{len(chunks)} chunks")
        return indexed

    def search(self, query: str, top_k: Optional[int] = None,
               filter_expr: Optional[str] = None) -> List[Dict]:
        """Search for relevant chunks using semantic similarity.

        Args:
            query: Search query string.
            top_k: Number of results to return (default: config.top_k).
            filter_expr: Optional Milvus filter expression.

        Returns:
            List of result dicts with 'text', 'source', 'score' keys.
        """
        if not self._collection:
            self.create_collection()

        top_k = top_k or self.config.top_k

        self._collection.load()

        # Encode query
        query_embedding = self._embedder.encode_query(query)

        # Search
        search_params = {
            "metric_type": self.config.metric_type,
            "params": {"nprobe": self.config.nprobe},
        }

        results = self._collection.search(
            data=[query_embedding.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=filter_expr,
            output_fields=["text", "source", "chunk_index"],
        )

        # Format results
        formatted = []
        for hits in results:
            for hit in hits:
                score = hit.score
                if score >= self.config.score_threshold:
                    formatted.append({
                        "text": hit.entity.get("text"),
                        "source": hit.entity.get("source"),
                        "chunk_index": hit.entity.get("chunk_index"),
                        "score": score,
                    })

        # Optional reranking
        if self.config.rerank and self.config.rerank_model:
            formatted = self._rerank(query, formatted)

        return formatted

    def _rerank(self, query: str, results: List[Dict]) -> List[Dict]:
        """Rerank search results using a cross-encoder model."""
        try:
            from sentence_transformers import CrossEncoder
            reranker = CrossEncoder(self.config.rerank_model)

            pairs = [(query, r["text"]) for r in results]
            scores = reranker.predict(pairs)

            for result, score in zip(results, scores):
                result["rerank_score"] = float(score)

            results.sort(key=lambda x: x["rerank_score"], reverse=True)

        except Exception as e:
            logger.warning(f"Reranking failed: {e}")

        return results

    def delete_collection(self):
        """Delete the current collection."""
        if utility.has_collection(self.config.collection_name):
            utility.drop_collection(self.config.collection_name)
            logger.info(f"Deleted collection: {self.config.collection_name}")
            self._collection = None

    def get_collection_stats(self) -> Dict:
        """Return statistics about the current collection."""
        if not self._collection:
            return {"status": "not initialized"}

        self._collection.flush()
        return {
            "name": self.config.collection_name,
            "num_entities": self._collection.num_entities,
            "schema": str(self._collection.schema),
        }

    def close(self):
        """Close the Milvus connection."""
        if self._connected:
            connections.disconnect(self.config.milvus_alias)
            self._connected = False
            logger.info("Disconnected from Milvus")
