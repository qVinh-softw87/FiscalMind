from __future__ import annotations

import voyageai

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VoyageReranker:
    """
    Client wrapper for Voyage AI Reranking API.

    Uses `rerank-2.5` by default — a state-of-the-art multilingual
    reranker capable of processing up to 32K context windows.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.VOYAGE_API_KEY
        self.model_name = model_name or settings.VOYAGE_RERANK_MODEL
        self.local_mode = False

        if not self.api_key:
            logger.warning(
                "voyage_api_key_missing_bypass_reranking",
                message="Reranking will be bypassed and raw Qdrant scores will be used."
            )
            self.local_mode = True
        else:
            self.client = voyageai.Client(api_key=self.api_key)

    async def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Re-scores and re-ranks retrieval results.

        Args:
            query: The user search query.
            documents: List of retrieved chunk dicts: [{"text": "...", "metadata": {...}}]
            top_k: Number of ranked results to return.

        Returns:
            Sorted list of documents with updated score and relevance values.
        """
        if not documents:
            return []

        # Bypass reranking if API key is missing
        if self.local_mode:
            for doc in documents:
                doc["rerank_score"] = doc.get("score", 0.5)
            return documents[:top_k]

        # If we have only 1 document, no need to call API for rerank
        if len(documents) == 1:
            documents[0]["rerank_score"] = 1.0
            return documents[:top_k]

        try:
            # Extract plain text content for the API call
            texts = [doc["text"] for doc in documents]

            response = self.client.rerank(
                query=query,
                documents=texts,
                model=self.model_name,
                top_k=top_k,
            )

            ranked_results = []
            for result in response.results:
                orig_idx = result.index
                score = result.relevance_score

                # Clone original document and attach score
                doc_copy = dict(documents[orig_idx])
                doc_copy["rerank_score"] = float(score)
                ranked_results.append(doc_copy)

            logger.info(
                "voyage_rerank_complete",
                candidates_in=len(documents),
                candidates_out=len(ranked_results),
            )
            return ranked_results

        except Exception as e:
            logger.error("voyage_rerank_failed", error=str(e))
            # Graceful fallback: return original documents sorted by original score/index
            for doc in documents:
                doc["rerank_score"] = doc.get("score", 0.5)
            return documents[:top_k]
