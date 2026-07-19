from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """
    User ORM model — maps to the `users` table in PostgreSQL.

    Design decisions:
    - UUID primary key: prevents enumeration attacks (attacker can't guess /users/1, /users/2)
    - `is_active`: soft disable instead of delete (preserve audit trail)
    - `is_verified`: email verification gate (Phase 2 sets to True by default, Phase 12 adds email flow)
    - `server_default=func.now()`: DB generates timestamps, not Python (timezone-safe)
    - `updated_at` onupdate: auto-updates every time the row changes
    """

    __tablename__ = "users"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,   # Index for fast login lookup
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── Auth ──────────────────────────────────────────────────────────────────
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── Status ────────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        "Document",
        back_populates="user",
        lazy="select",
    )
    conversations: Mapped[list["Conversation"]] = relationship(  # noqa: F821
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
