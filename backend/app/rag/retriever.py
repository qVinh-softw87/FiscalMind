from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Standard collection name for financial statement vectors
COLLECTION_NAME = "financial_documents"


class QdrantRetriever:
    """
    Data access layer for the Qdrant Vector database.
    Supports both local Docker (HTTP) and Qdrant Cloud (HTTPS + API Key).

    Implements strict security payload filters (user_id) to prevent data leakages
    between tenant spaces (multi-tenancy security model).
    """

    def __init__(self, vector_dim: int = 1024) -> None:
        self.vector_dim = vector_dim

        # ── 1. Connect Client ──────────────────────────────────────────────────
        # If QDRANT_URL is present, we connect to Qdrant Cloud (HTTPS)
        if settings.QDRANT_URL:
            logger.info("connecting_to_qdrant_cloud", url=settings.QDRANT_URL)
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
        else:
            # Fallback to local Docker setup
            url = f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
            logger.info("connecting_to_qdrant_local", url=url)
            self.client = QdrantClient(url=url)

        # ── 2. Bootstrap Collection ────────────────────────────────────────────
        self._ensure_collection_exists()

    def _ensure_collection_exists(self) -> None:
        """Bootstraps the Qdrant collection if not yet created."""
        try:
            exists = self.client.collection_exists(collection_name=COLLECTION_NAME)
            if not exists:
                logger.info("creating_qdrant_collection", collection=COLLECTION_NAME, dim=self.vector_dim)
                self.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=qmodels.VectorParams(
                        size=self.vector_dim,
                        distance=qmodels.Distance.COSINE,  # Cosine distance for text embeddings
                    )
                )
        except UnexpectedResponse as e:
            logger.error("qdrant_collection_bootstrap_failed", error=str(e))
            # Try parsing legacy error formats or re-raise
            raise

    # ── Upsert / Indexing ─────────────────────────────────────────────────────

    async def upsert_chunks(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        chunks: list[dict],
        vectors: list[list[float]],
    ) -> None:
        """
        Indexes text chunks and their corresponding embedding vectors into Qdrant.
        Stores critical metadata (user_id, document_id) in payload for filtering.
        """
        if not chunks or not vectors:
            return

        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            # Generate deterministic UUID for each chunk based on document_id and index
            point_id = str(uuid.uuid5(document_id, f"chunk_{idx}"))

            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "text": chunk["text"],
                        "clean_text": chunk["clean_text"],
                        "user_id": str(user_id),
                        "document_id": str(document_id),
                        "chunk_index": chunk["metadata"]["chunk_index"],
                        "filename": chunk["metadata"].get("filename", ""),
                        "document_type": chunk["metadata"].get("document_type", ""),
                    }
                )
            )

        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,  # Block until indexed for consistency
        )
        logger.info(
            "qdrant_indexed_chunks",
            document_id=str(document_id),
            chunks_count=len(points),
        )

    # ── Search ────────────────────────────────────────────────────────────────

    async def search(
        self,
        query_vector: list[float],
        user_id: uuid.UUID,
        document_ids: list[uuid.UUID] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Performs vector similarity search in Qdrant.

        Security Pattern:
        Applies strict payload filter matching `user_id == current_user.id`.
        Optionally narrows down search to a specific list of `document_ids`.
        """
        # Strict user boundary filter
        must_filters = [
            qmodels.FieldCondition(
                key="user_id",
                match=qmodels.MatchValue(value=str(user_id)),
            )
        ]

        # Scope filter: restrict search to specific documents
        if document_ids:
            must_filters.append(
                qmodels.FieldCondition(
                    key="document_id",
                    match=qmodels.MatchAny(any=[str(doc_id) for doc_id in document_ids]),
                )
            )

        filter_condition = qmodels.Filter(must=must_filters)

        results = self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=filter_condition,
            limit=limit,
            with_payload=True,
        )

        output = []
        for res in results:
            payload = res.payload or {}
            output.append({
                "text": payload.get("text", ""),
                "clean_text": payload.get("clean_text", ""),
                "score": float(res.score),
                "metadata": {
                    "document_id": payload.get("document_id"),
                    "user_id": payload.get("user_id"),
                    "chunk_index": payload.get("chunk_index"),
                    "filename": payload.get("filename"),
                    "document_type": payload.get("document_type"),
                }
            })

        return output

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete_document_vectors(self, document_id: uuid.UUID) -> None:
        """Removes all vector points associated with a specific document."""
        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
            wait=True,
        )
        logger.info("qdrant_deleted_document_vectors", document_id=str(document_id))
