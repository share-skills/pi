"""Tests for RAG pipeline."""

import pytest
from unittest.mock import patch, MagicMock, call
from src.retrieval.rag_pipeline import RAGConfig, EmbeddingModel


class TestRAGConfig:
    def test_default_port(self):
        config = RAGConfig()
        assert config.milvus_port == 19530

    def test_embedding_dim(self):
        from src.retrieval.rag_pipeline import BGE_EMBEDDING_DIM
        assert BGE_EMBEDDING_DIM == 1024
        config = RAGConfig()
        assert config.embedding_dim == BGE_EMBEDDING_DIM

    def test_no_connection_timeout_field(self):
        """Verify there is no connection_timeout parameter on the config."""
        config = RAGConfig()
        assert not hasattr(config, "connection_timeout")


class TestRAGPipeline:
    """Tests that mock Milvus to avoid needing a real instance."""

    @patch("src.retrieval.rag_pipeline.connections")
    @patch("src.retrieval.rag_pipeline.EmbeddingModel")
    def test_connection_uses_default_port(self, mock_embedder, mock_connections):
        """Verify connection uses config port (19530 by default)."""
        from src.retrieval.rag_pipeline import RAGPipeline, RAGConfig
        config = RAGConfig(milvus_port=19530)
        pipeline = RAGPipeline(config)

        mock_connections.connect.assert_called_once_with(
            alias="default",
            host="localhost",
            port=19530,
        )

    @patch("src.retrieval.rag_pipeline.connections")
    @patch("src.retrieval.rag_pipeline.EmbeddingModel")
    def test_connection_refused(self, mock_embedder, mock_connections):
        """Test that a connection failure raises an exception."""
        from src.retrieval.rag_pipeline import RAGPipeline, RAGConfig

        mock_connections.connect.side_effect = Exception("Connection refused")

        with pytest.raises(Exception, match="Connection refused"):
            RAGPipeline(RAGConfig(milvus_port=19530))

    @patch("src.retrieval.rag_pipeline.connections")
    @patch("src.retrieval.rag_pipeline.EmbeddingModel")
    @patch("src.retrieval.rag_pipeline.utility")
    @patch("src.retrieval.rag_pipeline.Collection")
    def test_create_collection_handles_exceptions(
        self, mock_collection, mock_utility, mock_embedder, mock_connections
    ):
        """Verify create_collection handles exceptions gracefully."""
        from src.retrieval.rag_pipeline import RAGPipeline, RAGConfig

        mock_utility.has_collection.return_value = False
        mock_collection.side_effect = Exception("Schema dimension mismatch")
        mock_utility.has_collection.side_effect = [False, True]
        mock_collection.side_effect = [Exception("Schema dimension mismatch"), MagicMock()]

        pipeline = RAGPipeline(RAGConfig())
        pipeline.create_collection()  # Falls through to the fallback

    @patch("src.retrieval.rag_pipeline.connections")
    @patch("src.retrieval.rag_pipeline.EmbeddingModel")
    def test_search_calls_load(self, mock_embedder, mock_connections):
        """Verify collection.load() is called on each search."""
        from src.retrieval.rag_pipeline import RAGPipeline, RAGConfig

        mock_emb_instance = MagicMock()
        mock_emb_instance.encode_query.return_value = [0.0] * 1024
        mock_embedder.return_value = mock_emb_instance

        pipeline = RAGPipeline(RAGConfig())
        mock_col = MagicMock()
        mock_col.search.return_value = [[]]
        pipeline._collection = mock_col

        # Search 3 times
        pipeline.search("天下大同")
        pipeline.search("仁者愛人")
        pipeline.search("學而時習之")

        assert mock_col.load.call_count == 3
