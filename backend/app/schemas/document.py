from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.document import DocumentStatus, DocumentType

# ── Allowed file types ─────────────────────────────────────────────────────────
ALLOWED_MIME_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",                                            # .xls
    "text/csv",
    "text/plain",
})

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf", ".xlsx", ".xls", ".csv", ".txt"
})


# ── Response Schemas ──────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    """Full document metadata — returned after upload and on GET /documents/{id}."""

    id: uuid.UUID
    user_id: uuid.UUID
    original_filename: str
    file_size: int
    mime_type: str
    document_type: DocumentType
    sector: str = "general"
    status: DocumentStatus
    version: int
    parent_id: uuid.UUID | None
    page_count: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @property
    def file_size_mb(self) -> float:
        return round(self.file_size / (1024 * 1024), 2)


class DocumentStatusResponse(BaseModel):
    """Lightweight status check — polled by frontend during processing."""

    id: uuid.UUID
    status: DocumentStatus
    document_type: DocumentType
    error_message: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Paginated list of user's documents."""

    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DeleteDocumentResponse(BaseModel):
    """Returned after successful deletion."""

    message: str
    document_id: uuid.UUID


# ── Query Params ──────────────────────────────────────────────────────────────

class DocumentListParams(BaseModel):
    """Query parameters for GET /documents."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: DocumentStatus | None = None
    document_type: DocumentType | None = None
