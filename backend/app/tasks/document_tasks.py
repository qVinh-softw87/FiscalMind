from __future__ import annotations

import uuid

from app.core.database import db_session_context
from app.core.logging import get_logger
from app.models.document import DocumentStatus
from app.repositories.document_repository import DocumentRepository
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="document.process",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def process_document_task(self, document_id: str) -> dict:
    """
    Background Celery task: process a newly uploaded document.

    This task is the orchestrator for the entire document intelligence pipeline:
    Phase 4 → OCR (if scanned PDF) + Financial Statement Parser
    Phase 5 → Chunking + Embedding → Qdrant vector store

    Why Celery?
    - Document processing takes 10-120 seconds (OCR is slow)
    - HTTP request cannot wait that long (client timeout)
    - Celery runs in a separate worker container → doesn't block API server
    - Failed tasks are retried automatically (max_retries=3)
    - Task status tracked via DocumentStatus in DB → frontend polls /status

    Current status: STUB — updates status to READY immediately.
    Phase 4 will replace this with real OCR + parsing logic.
    """
    import asyncio

    async def _run() -> dict:
        doc_uuid = uuid.UUID(document_id)

        async with db_session_context() as db:
            repo = DocumentRepository(db)
            document = await repo.get_by_id(doc_uuid)

            if not document:
                logger.warning("task_document_not_found", document_id=document_id)
                return {"status": "not_found"}

            if document.is_deleted:
                logger.info("task_document_deleted_skip", document_id=document_id)
                return {"status": "skipped"}

            try:
                # Mark as PROCESSING
                await repo.update_status(document, DocumentStatus.PROCESSING)
                logger.info("document_processing_started", document_id=document_id)

                # Initialize and run FinancialParser
                from app.financial_engine.parser import FinancialParser
                parser = FinancialParser()
                
                parsed_result = await parser.parse_document(
                    file_path=document.file_path,
                    original_filename=document.original_filename,
                    mime_type=document.mime_type,
                )

                # Store extracted data in DB JSONB and mark as READY
                # We save raw_text, tables, and normalized_data in the JSONB column
                # mapped to the database structure.
                await repo.update_parsed_data(
                    document=document,
                    parsed_data={
                        "tables": parsed_result["tables"],
                        "normalized_data": parsed_result["normalized_data"],
                        "raw_text_length": len(parsed_result["raw_text"]),
                    },
                    document_type=parsed_result["document_type"],
                    page_count=None,  # Will be refined in RAG phase
                )

                # Save raw text to disk alongside the uploaded file for RAG chunking
                text_path = f"{document.file_path}.txt"
                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(parsed_result["raw_text"])

                # ── Index parsed text into Qdrant Cloud ───────────────────────
                logger.info("indexing_to_qdrant_cloud_started", document_id=document_id)
                from app.rag.pipeline import RAGPipeline
                rag_pipeline = RAGPipeline()
                await rag_pipeline.index_document(document, parsed_result["raw_text"])

                logger.info(
                    "document_processing_complete",
                    document_id=document_id,
                    detected_type=parsed_result["document_type"].value,
                    status="ready",
                )
                return {"status": "ready", "document_id": document_id}

            except Exception as exc:
                logger.exception(
                    "document_processing_failed",
                    document_id=document_id,
                    error=str(exc),
                )
                await repo.update_status(
                    document,
                    DocumentStatus.FAILED,
                    error_message=str(exc),
                )
                # Retry with exponential backoff
                raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))

    # Celery tasks are synchronous — run async code in event loop
    return asyncio.get_event_loop().run_until_complete(_run())
