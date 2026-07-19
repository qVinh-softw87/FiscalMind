from __future__ import annotations

import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus, DocumentType


class DocumentRepository:
    """
    Data access layer for the Document domain.

    All DB operations for documents live here — zero business logic.
    Injected via constructor for easy mocking in tests.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        """Fetch document by ID. Returns None if not found or soft-deleted."""
        result = await self._db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_user(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Document | None:
        """
        Fetch document ensuring it belongs to the requesting user.
        Prevents IDOR (Insecure Direct Object Reference) attacks.
        """
        result = await self._db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
                Document.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: DocumentStatus | None = None,
        document_type: DocumentType | None = None,
    ) -> tuple[list[Document], int]:
        """
        Returns (documents, total_count) for a given user with optional filters.
        Uses OFFSET pagination — suitable for the document volumes expected.
        """
        base_query = select(Document).where(
            Document.user_id == user_id,
            Document.is_deleted.is_(False),
        )

        if status:
            base_query = base_query.where(Document.status == status)
        if document_type:
            base_query = base_query.where(Document.document_type == document_type)

        # Count total matching documents
        count_result = await self._db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        # Fetch page
        paginated = base_query.order_by(Document.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)

        result = await self._db.execute(paginated)
        documents = list(result.scalars().all())

        return documents, total

    async def get_latest_version(
        self,
        user_id: uuid.UUID,
        original_filename: str,
    ) -> Document | None:
        """Finds the most recent non-deleted version of a file by original name."""
        result = await self._db.execute(
            select(Document)
            .where(
                Document.user_id == user_id,
                Document.original_filename == original_filename,
                Document.is_deleted.is_(False),
            )
            .order_by(Document.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create(
        self,
        user_id: uuid.UUID,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        file_size: int,
        mime_type: str,
        version: int = 1,
        parent_id: uuid.UUID | None = None,
    ) -> Document:
        """Inserts a new document record with PENDING status."""
        document = Document(
            user_id=user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            version=version,
            parent_id=parent_id,
        )
        self._db.add(document)
        await self._db.flush()
        await self._db.refresh(document)
        return document

    async def update_status(
        self,
        document: Document,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> Document:
        """Updates processing status (called by Celery worker)."""
        document.status = status
        if error_message is not None:
            document.error_message = error_message
        await self._db.flush()
        return document

    async def update_parsed_data(
        self,
        document: Document,
        parsed_data: dict,
        document_type: DocumentType,
        page_count: int | None = None,
    ) -> Document:
        """Stores extracted financial data after parsing (Phase 4)."""
        document.parsed_data = parsed_data
        document.document_type = document_type
        document.page_count = page_count
        document.status = DocumentStatus.READY
        await self._db.flush()
        return document

    async def soft_delete(self, document: Document) -> Document:
        """Marks document as deleted — data preserved for audit."""
        document.is_deleted = True
        await self._db.flush()
        return document

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        """Returns total active documents for a user."""
        result = await self._db.execute(
            select(func.count(Document.id)).where(
                Document.user_id == user_id,
                Document.is_deleted.is_(False),
            )
        )
        return result.scalar_one()
