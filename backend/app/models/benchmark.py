from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CustomBenchmark(Base):
    """
    CustomBenchmark ORM model — represents custom user or organization specific ratio thresholds.

    Priority rules:
    - owner_type = "USER" (overrides sector defaults for this specific user)
    - owner_type = "ORGANIZATION" (overrides sector defaults for the entire org)
    """

    __tablename__ = "custom_benchmarks"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────
    # Can be a User UUID or an Organization UUID
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    owner_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,  # "USER" or "ORGANIZATION"
    )

    # ── Target parameters ─────────────────────────────────────────────────────
    sector: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # "technology", "real_estate", etc.
    metric: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # "roe", "debt_ratio", etc.

    # ── Threshold Values ──────────────────────────────────────────────────────
    healthy_boundary: Mapped[float] = mapped_column(Float, nullable=False)
    warning_boundary: Mapped[float] = mapped_column(Float, nullable=False)
    
    # "UP" (higher is better, e.g. roe) or "DOWN" (lower is better, e.g. debt_ratio)
    direction: Mapped[str] = mapped_column(String(10), default="UP", nullable=False)

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

    def __repr__(self) -> str:
        return f"<CustomBenchmark id={self.id} owner={self.owner_type}:{self.owner_id} metric={self.metric}>"
