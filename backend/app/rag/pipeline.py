from __future__ import annotations

import uuid

from app.core.logging import get_logger
from app.models.document import Document
from app.models.user import User
from app.rag.chunker import DocumentChunker
from app.rag.embedder import VoyageEmbedder
from app.rag.reranker import VoyageReranker
from app.rag.retriever import QdrantRetriever

logger = get_logger(__name__)


class RAGPipeline:
    """
    Unified Orchestrator for the FiscalMind AI Knowledge Base (RAG).

    Coordinates:
    1. Indexing: Split text → Get Voyage Embeddings → Save to Qdrant Cloud.
    2. Retrieval: Embed query → Vector search Qdrant (filtered) → Rerank via Voyage API.
    """

    def __init__(
        self,
        chunker: DocumentChunker | None = None,
        embedder: VoyageEmbedder | None = None,
        retriever: QdrantRetriever | None = None,
        reranker: VoyageReranker | None = None,
    ) -> None:
        self.chunker = chunker or DocumentChunker()
        self.embedder = embedder or VoyageEmbedder()
        self.retriever = retriever or QdrantRetriever(
            vector_dim=self.embedder.vector_dimension
        )
        self.reranker = reranker or VoyageReranker()

    # ── Indexing Flow ─────────────────────────────────────────────────────────

    async def index_document(self, document: Document, raw_text: str) -> None:
        """
        Processes and indexes a document text in Qdrant.
        Called asynchronously inside background Celery worker tasks.
        """
        logger.info("rag_indexing_started", document_id=str(document.id))

        metadata = {
            "filename": document.original_filename,
            "document_type": document.document_type.value,
        }

        # 1. Chunk document
        chunks = self.chunker.split_text(raw_text, document_metadata=metadata)
        if not chunks:
            logger.warning("rag_indexing_empty_text_skip", document_id=str(document.id))
            return

        # 2. Extract plain text strings for the Voyage Embedding API call
        plain_texts = [c["text"] for c in chunks]

        # 3. Generate embeddings via Voyage AI API (uses free tier quota)
        vectors = await self.embedder.embed_documents(plain_texts)

        # 4. Upsert vectors and payloads into Qdrant Cloud (secured by user_id)
        await self.retriever.upsert_chunks(
            document_id=document.id,
            user_id=document.user_id,
            chunks=chunks,
            vectors=vectors,
        )

        logger.info(
            "rag_indexing_complete",
            document_id=str(document.id),
            chunks_indexed=len(chunks),
        )

    # ── Retrieval Flow ────────────────────────────────────────────────────────

    async def retrieve_context(
        self,
        query: str,
        current_user: User,
        document_ids: list[uuid.UUID] | None = None,
        limit: int = 10,
        rerank_top_k: int = 4,
    ) -> list[dict]:
        """
        Retrieves the most semantically relevant text chunks for a query.

        Steps:
        1. Embed the query via Voyage AI.
        2. Vector search in Qdrant with tenant payload filtering.
        3. Rerank the top matching candidates using Voyage Rerank API.
        4. Return top relevance scored contexts.
        """
        logger.info(
            "rag_retrieval_started",
            user_id=str(current_user.id),
            docs_scoped=len(document_ids) if document_ids else "all",
        )

        # 1. Embed user query string
        query_vector = await self.embedder.embed_query(query)

        # 2. Retrieve top similarity candidates from Qdrant Cloud (Tenant isolated)
        candidates = await self.retriever.search(
            query_vector=query_vector,
            user_id=current_user.id,
            document_ids=document_ids,
            limit=limit,
        )

        if not candidates:
            logger.info("rag_retrieval_no_candidates_found")
            return []

        # 3. Re-score and rank candidates using Voyage Rerank API
        ranked_contexts = await self.reranker.rerank(
            query=query,
            documents=candidates,
            top_k=rerank_top_k,
        )

        logger.info(
            "rag_retrieval_complete",
            returned_contexts=len(ranked_contexts),
        )
        return ranked_contexts

    # ── Cleanup Flow ──────────────────────────────────────────────────────────

    async def purge_document_vectors(self, document_id: uuid.UUID) -> None:
        """Deletes all vector coordinates in Qdrant associated with document."""
        await self.retriever.delete_document_vectors(document_id)
