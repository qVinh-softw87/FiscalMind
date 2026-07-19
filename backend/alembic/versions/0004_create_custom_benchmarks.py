"""create custom benchmarks and add document sector

Revision ID: 0004_create_custom_benchmarks
Revises: 0003_create_chat
Create Date: 2026-07-17

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_create_custom_benchmarks"
down_revision: Union[str, None] = "0003_create_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add sector column to documents ────────────────────────────────────────
    op.add_column(
        "documents",
        sa.Column(
            "sector",
            sa.String(length=50),
            nullable=False,
            server_default="general",
        ),
    )

    # ── Create custom_benchmarks table ────────────────────────────────────────
    op.create_table(
        "custom_benchmarks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_type", sa.String(length=30), nullable=False),
        sa.Column("sector", sa.String(length=50), nullable=False),
        sa.Column("metric", sa.String(length=50), nullable=False),
        sa.Column("healthy_boundary", sa.Float(), nullable=False),
        sa.Column("warning_boundary", sa.Float(), nullable=False),
        sa.Column("direction", sa.String(length=10), server_default="UP", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_custom_benchmarks_owner_id", "custom_benchmarks", ["owner_id"])
    op.create_index("ix_custom_benchmarks_owner_type", "custom_benchmarks", ["owner_type"])
    op.create_index("ix_custom_benchmarks_sector", "custom_benchmarks", ["sector"])
    op.create_index("ix_custom_benchmarks_metric", "custom_benchmarks", ["metric"])


def downgrade() -> None:
    op.drop_index("ix_custom_benchmarks_metric", table_name="custom_benchmarks")
    op.drop_index("ix_custom_benchmarks_sector", table_name="custom_benchmarks")
    op.drop_index("ix_custom_benchmarks_owner_type", table_name="custom_benchmarks")
    op.drop_index("ix_custom_benchmarks_owner_id", table_name="custom_benchmarks")
    op.drop_table("custom_benchmarks")
    op.drop_column("documents", "sector")
