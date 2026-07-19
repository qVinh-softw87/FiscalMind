from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentStatus(str, Enum):
    """
    Lifecycle states of a document.

    PENDING     → uploaded, waiting for Celery worker to pick up
    PROCESSING  → worker is running OCR + parsing + embedding
    READY       → fully processed, available for AI chat
    FAILED      → processing failed (error_message contains reason)
    """
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentType(str, Enum):
    """
    Type of financial statement detected during parsing (Phase 4).
    UNKNOWN = not yet analyzed.
    """
    UNKNOWN = "unknown"
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    CASH_FLOW = "cash_flow"
    ANNUAL_REPORT = "annual_report"
    NOTES = "notes"
    OTHER = "other"


class Document(Base):
    """
    Document ORM model — represents a financial statement uploaded by a user.

    Design decisions:
    - `stored_filename`: UUID-based name on disk (prevents path traversal, name collisions)
    - `original_filename`: preserved for display purposes only
    - `version` + `parent_id`: allows versioning — uploading a new version of the same
      document creates a new row with parent_id pointing to the previous version
    - `parsed_data` JSONB: flexible schema for extracted financial tables (Phase 4)
    - Soft-delete via `is_deleted`: keeps audit trail, Celery doesn't process deleted docs
    """

    __tablename__ = "documents"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── File Metadata ─────────────────────────────────────────────────────────
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)  # bytes
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # ── Classification ────────────────────────────────────────────────────────
    document_type: Mapped[DocumentType] = mapped_column(
        String(50),
        default=DocumentType.UNKNOWN,
        nullable=False,
    )
    sector: Mapped[str] = mapped_column(
        String(50),
        default="general",
        server_default="general",
        nullable=False,
    )

    # ── Processing State ──────────────────────────────────────────────────────
    status: Mapped[DocumentStatus] = mapped_column(
        String(20),
        default=DocumentStatus.PENDING,
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Versioning ────────────────────────────────────────────────────────────
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── AI / Parsed Data (populated in Phase 4) ───────────────────────────────
    parsed_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Soft Delete ───────────────────────────────────────────────────────────
    is_deleted: Mapped[bool] = mapped_column(
        default=False, nullable=False, index=True
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(__import__("datetime").timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="documents", lazy="select")  # noqa: F821
    versions: Mapped[list["Document"]] = relationship(
        "Document",
        foreign_keys=[parent_id],
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} name={self.original_filename} status={self.status}>"
