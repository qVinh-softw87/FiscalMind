from __future__ import annotations

import math
import mimetypes
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    DocumentProcessingError,
    ForbiddenError,
    NotFoundError,
    ValidationFailedError,
)
from app.core.logging import get_logger
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    DeleteDocumentResponse,
    DocumentListParams,
    DocumentListResponse,
    DocumentResponse,
    DocumentStatusResponse,
)
from app.storage.base import StorageBackend

logger = get_logger(__name__)


class DocumentService:
    """
    Business logic for document lifecycle management.

    Orchestrates:
    - File validation (type, size)
    - Storage (save to disk/S3)
    - Database persistence
    - Versioning
    - Background task triggering (OCR + parsing + embedding)
    - Deletion (storage + DB soft-delete)

    Dependencies injected via constructor → fully testable.
    """

    def __init__(self, db: AsyncSession, storage: StorageBackend) -> None:
        self._db = db
        self._storage = storage
        self._repo = DocumentRepository(db)

    # ── Upload ────────────────────────────────────────────────────────────────

    async def upload(
        self,
        file: UploadFile,
        current_user: User,
    ) -> DocumentResponse:
        """
        Full document upload pipeline:

        1. Validate file type (MIME + extension double-check)
        2. Validate file size
        3. Read file bytes (streaming for large files)
        4. Detect versioning (same filename → increment version)
        5. Generate safe stored filename (UUID-based)
        6. Save to storage backend
        7. Persist document record to DB (status=PENDING)
        8. Trigger background processing task (Celery)
        9. Return DocumentResponse immediately (202-style: processing async)
        """
        # ── Step 1: Validate file type ─────────────────────────────────────
        await self._validate_file_type(file)

        # ── Step 2: Read content + validate size ──────────────────────────
        content = await self._read_and_validate_size(file)

        # ── Step 3: Detect versioning ─────────────────────────────────────
        version, parent_id = await self._resolve_version(
            user_id=current_user.id,
            original_filename=file.filename or "upload",
        )

        # ── Step 4: Generate safe storage path ────────────────────────────
        stored_filename, file_path = self._build_storage_path(
            user_id=current_user.id,
            original_filename=file.filename or "upload",
        )

        # ── Step 5: Persist to storage ────────────────────────────────────
        try:
            await self._storage.save(file_path, content)
        except Exception as e:
            raise DocumentProcessingError(
                f"Failed to save file to storage: {e}",
                details={"filename": file.filename},
            )

        # ── Step 6: Create DB record ──────────────────────────────────────
        document = await self._repo.create(
            user_id=current_user.id,
            original_filename=file.filename or "upload",
            stored_filename=stored_filename,
            file_path=file_path,
            file_size=len(content),
            mime_type=file.content_type or "application/octet-stream",
            version=version,
            parent_id=parent_id,
        )

        logger.info(
            "document_uploaded",
            document_id=str(document.id),
            user_id=str(current_user.id),
            filename=document.original_filename,
            size=document.file_size,
            version=version,
        )

        # ── Step 7: Trigger background processing ─────────────────────────
        # Phase 4 will implement actual OCR + parsing
        # For now: dispatch to Celery and return immediately
        self._dispatch_processing_task(document_id=document.id)

        return DocumentResponse.model_validate(document)

    # ── List ──────────────────────────────────────────────────────────────────

    async def list_documents(
        self,
        current_user: User,
        params: DocumentListParams,
    ) -> DocumentListResponse:
        """Returns paginated list of documents for the authenticated user."""
        documents, total = await self._repo.list_by_user(
            user_id=current_user.id,
            page=params.page,
            page_size=params.page_size,
            status=params.status,
            document_type=params.document_type,
        )

        return DocumentListResponse(
            items=[DocumentResponse.model_validate(doc) for doc in documents],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=math.ceil(total / params.page_size) if total > 0 else 0,
        )

    # ── Get Single ────────────────────────────────────────────────────────────

    async def get_document(
        self,
        document_id: uuid.UUID,
        current_user: User,
    ) -> DocumentResponse:
        """
        Returns a single document.
        Raises NotFoundError if not found.
        Raises ForbiddenError if document belongs to another user (IDOR prevention).
        """
        document = await self._repo.get_by_id(document_id)

        if not document:
            raise NotFoundError("Document", document_id)

        # Ownership check — never expose other users' documents
        if document.user_id != current_user.id:
            raise ForbiddenError("You do not have access to this document.")

        return DocumentResponse.model_validate(document)

    # ── Status ────────────────────────────────────────────────────────────────

    async def get_status(
        self,
        document_id: uuid.UUID,
        current_user: User,
    ) -> DocumentStatusResponse:
        """Lightweight status check — polled by frontend during processing."""
        document = await self._get_owned_document(document_id, current_user.id)
        return DocumentStatusResponse.model_validate(document)

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete_document(
        self,
        document_id: uuid.UUID,
        current_user: User,
    ) -> DeleteDocumentResponse:
        """
        Deletes a document:
        1. Verify ownership
        2. Remove from storage backend
        3. Soft-delete in DB (preserves audit trail)

        Note: Qdrant vectors for this document are cleaned up separately
        in Phase 5 when the RAG pipeline is implemented.
        """
        document = await self._get_owned_document(document_id, current_user.id)

        # Remove physical file
        try:
            await self._storage.delete(document.file_path)
        except Exception as e:
            logger.warning(
                "storage_delete_failed",
                document_id=str(document_id),
                error=str(e),
            )
            # Don't block DB soft-delete even if file removal fails

        # Remove vector points from Qdrant Cloud
        try:
            from app.rag.pipeline import RAGPipeline
            rag_pipeline = RAGPipeline()
            await rag_pipeline.purge_document_vectors(document_id)
        except Exception as e:
            logger.error(
                "qdrant_vector_delete_failed",
                document_id=str(document_id),
                error=str(e),
            )
            # Proceed to delete from DB anyway

        # Soft-delete in DB
        await self._repo.soft_delete(document)

        logger.info(
            "document_deleted",
            document_id=str(document_id),
            user_id=str(current_user.id),
        )

        return DeleteDocumentResponse(
            message="Document deleted successfully.",
            document_id=document_id,
        )

    # ── Internal Helpers ──────────────────────────────────────────────────────

    async def _validate_file_type(self, file: UploadFile) -> None:
        """
        Double-validation: MIME type + file extension.

        Why double-check?
        - MIME type can be spoofed by the client (set Content-Type header to anything)
        - Extension alone is also unreliable
        - Together they provide stronger validation
        - Phase 4 adds magic bytes validation (reads first bytes of file) for production
        """
        filename = file.filename or ""
        extension = Path(filename).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            raise ValidationFailedError(
                f"File type '{extension}' is not allowed.",
                details={
                    "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
                    "received": extension,
                },
            )

        content_type = file.content_type or ""
        if content_type not in ALLOWED_MIME_TYPES:
            # Try to guess MIME from extension as fallback
            guessed, _ = mimetypes.guess_type(filename)
            if guessed not in ALLOWED_MIME_TYPES:
                raise ValidationFailedError(
                    f"MIME type '{content_type}' is not allowed.",
                    details={"allowed_types": sorted(ALLOWED_MIME_TYPES)},
                )

    async def _read_and_validate_size(self, file: UploadFile) -> bytes:
        """
        Reads file content and validates against MAX_UPLOAD_SIZE_MB.

        Streaming approach: reads in 1MB chunks to avoid holding large files in RAM.
        Raises ValidationFailedError if size exceeds limit.
        """
        max_bytes = settings.max_upload_size_bytes
        chunks: list[bytes] = []
        total_read = 0

        while True:
            chunk = await file.read(1024 * 1024)  # 1MB chunks
            if not chunk:
                break
            total_read += len(chunk)
            if total_read > max_bytes:
                raise ValidationFailedError(
                    f"File size exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit.",
                    details={
                        "max_size_mb": settings.MAX_UPLOAD_SIZE_MB,
                        "received_bytes": total_read,
                    },
                )
            chunks.append(chunk)

        return b"".join(chunks)

    async def _resolve_version(
        self,
        user_id: uuid.UUID,
        original_filename: str,
    ) -> tuple[int, uuid.UUID | None]:
        """
        Determines version number for the uploaded file.

        If a document with the same filename already exists:
        → version = latest.version + 1
        → parent_id = latest.id

        If no prior version exists:
        → version = 1, parent_id = None
        """
        existing = await self._repo.get_latest_version(user_id, original_filename)
        if existing:
            return existing.version + 1, existing.id
        return 1, None

    def _build_storage_path(
        self,
        user_id: uuid.UUID,
        original_filename: str,
    ) -> tuple[str, str]:
        """
        Generates a UUID-based storage filename to prevent:
        - Path traversal attacks
        - Filename collisions
        - Exposing original filenames in storage

        Returns: (stored_filename, relative_file_path)
        Example: ("a1b2c3.pdf", "uploads/user-uuid/a1b2c3.pdf")
        """
        extension = Path(original_filename).suffix.lower()
        stored_filename = f"{uuid.uuid4().hex}{extension}"
        file_path = f"{str(user_id)}/{stored_filename}"
        return stored_filename, file_path

    async def _get_owned_document(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Document:
        """Shared helper: fetch document with ownership check."""
        document = await self._repo.get_by_id_and_user(document_id, user_id)
        if not document:
            raise NotFoundError("Document", document_id)
        return document

    def _dispatch_processing_task(self, document_id: uuid.UUID) -> None:
        """
        Enqueues the document processing task to Celery.

        The task will:
        Phase 4 → OCR + Financial Parser
        Phase 5 → Chunking + Embedding + Qdrant indexing

        Using .delay() (fire-and-forget) — the API returns immediately.
        Task status is tracked via DocumentStatus field in DB.
        """
        try:
            from app.tasks.document_tasks import process_document_task
            process_document_task.delay(str(document_id))
            logger.info("processing_task_dispatched", document_id=str(document_id))
        except Exception as e:
            # Task dispatch failure should not fail the upload
            # Document stays in PENDING status — can be retried via admin
            logger.error(
                "task_dispatch_failed",
                document_id=str(document_id),
                error=str(e),
            )
