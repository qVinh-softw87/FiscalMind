from __future__ import annotations

import voyageai

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VoyageEmbedder:
    """
    Client wrapper for Voyage AI Embeddings API.

    Uses `voyage-multilingual-2` by default — optimized for high-performance
    multilingual semantic search (ideal for Vietnamese and English financial text).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.VOYAGE_API_KEY
        self.model_name = model_name or settings.VOYAGE_EMBEDDING_MODEL
        self.local_mode = False

        if not self.api_key:
            # Fallback to local offline embedding using FastEmbed (zero cost/API keys)
            logger.warning(
                "voyage_api_key_missing_fallback_to_local_fastembed",
                fallback_model="BAAI/bge-small-en-v1.5",
            )
            from fastembed import TextEmbedding
            self._local_embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            self.local_mode = True
        else:
            # Initialize Voyage Client
            self.client = voyageai.Client(api_key=self.api_key)

    async def embed_query(self, text: str) -> list[float]:
        """
        Generates embedding vector for a single query string.
        Typically returns a 1024-dimension vector.
        """
        if self.local_mode:
            # FastEmbed outputs generator, convert to list.
            # BAAI/bge-small-en-v1.5 has 384 dimensions.
            embeddings = list(self._local_embedder.embed([text]))
            return [float(x) for x in embeddings[0]]

        try:
            # Voyage AI API requires input as list, we wrap the string
            # input_type="query" prepares the model for query-style indexing
            response = self.client.embed(
                texts=[text],
                model=self.model_name,
                input_type="query",
            )
            return response.embeddings[0]
        except Exception as e:
            logger.error("voyage_query_embedding_failed", error=str(e))
            raise

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Generates embedding vectors for a list of document chunks.
        Performs batching automatically under the hood.
        """
        if not texts:
            return []

        if self.local_mode:
            embeddings = list(self._local_embedder.embed(texts))
            return [[float(x) for x in emb] for emb in embeddings]

        try:
            # input_type="document" optimizes retrieval indexing
            response = self.client.embed(
                texts=texts,
                model=self.model_name,
                input_type="document",
            )
            return response.embeddings
        except Exception as e:
            logger.error("voyage_batch_document_embedding_failed", error=str(e))
            raise

    @property
    def vector_dimension(self) -> int:
        """
        Returns vector dimension length.
        `voyage-multilingual-2` yields 1024-dimensional vectors.
        `bge-small-en-v1.5` yields 384 dimensions.
        """
        if self.local_mode:
            return 384
        if "multilingual" in self.model_name:
            return 1024
        return 1024  # Default Voyage-3 dimension is also 1024
