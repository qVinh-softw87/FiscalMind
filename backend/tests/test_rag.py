from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.rag.chunker import DocumentChunker
from app.rag.embedder import VoyageEmbedder
from app.rag.reranker import VoyageReranker
from app.rag.retriever import QdrantRetriever


class TestChunker:
    def test_chunker_basic_split(self):
        chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
        text = (
            "Paragraph one is a fairly short paragraph. "
            "Paragraph two is another section of the document that is somewhat longer."
        )
        metadata = {"filename": "report.pdf", "document_type": "balance_sheet"}
        chunks = chunker.split_text(text, document_metadata=metadata)

        assert len(chunks) > 0
        assert "report.pdf" in chunks[0]["text"]
        assert "balance_sheet" in chunks[0]["text"]
        assert chunks[0]["index"] == 0
        assert chunks[0]["metadata"]["chunk_index"] == 0

    def test_chunker_empty_text(self):
        chunker = DocumentChunker()
        assert chunker.split_text("") == []


class TestVoyageEmbedder:
    @patch("voyageai.Client")
    def test_embedder_dimensions(self, mock_client):
        # Mock client initialization
        embedder = VoyageEmbedder(api_key="fake-key", model_name="voyage-multilingual-2")
        assert embedder.vector_dimension == 1024


class TestVoyageReranker:
    @patch("voyageai.Client")
    async def test_reranker_fallback_on_error(self, mock_client):
        # Mock client to throw error during reranking
        mock_instance = mock_client.return_value
        mock_instance.rerank.side_effect = Exception("API Error")

        reranker = VoyageReranker(api_key="fake-key", model_name="rerank-2.5")
        docs = [
            {"text": "doc1", "score": 0.9},
            {"text": "doc2", "score": 0.8},
        ]
        
        # Should gracefully return original list with score copied to rerank_score
        results = await reranker.rerank("some query", docs, top_k=2)
        assert len(results) == 2
        assert results[0]["rerank_score"] == 0.9
        assert results[1]["rerank_score"] == 0.8


class TestQdrantRetriever:
    @patch("app.rag.retriever.QdrantClient")
    def test_retriever_cloud_initialization(self, mock_qdrant_client):
        # Set settings mock values via patch or config overrides
        with patch("app.core.config.settings.QDRANT_URL", "https://fake-cluster.qdrant.io"):
            with patch("app.core.config.settings.QDRANT_API_KEY", "fake-key"):
                retriever = QdrantRetriever(vector_dim=1024)
                # Verify QdrantClient was instantiated with cloud args
                mock_qdrant_client.assert_called_with(
                    url="https://fake-cluster.qdrant.io",
                    api_key="fake-key",
                )
