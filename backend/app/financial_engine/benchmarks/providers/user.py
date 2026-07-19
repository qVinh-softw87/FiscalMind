from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.financial_engine.benchmarks.base import (
    BaseBenchmarkProvider,
    DirectionEnum,
    ThresholdRange,
)
from app.models.benchmark import CustomBenchmark


class UserBenchmarkProvider(BaseBenchmarkProvider):
    """
    User Custom Provider.
    Queries PostgreSQL for user-level customized overrides.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_thresholds(
        self,
        metric: str,
        sector: str,
        user_id: uuid.UUID,
        org_id: uuid.UUID | None = None,
    ) -> ThresholdRange | None:
        """Fetches custom user thresholds from DB if set."""
        result = await self._db.execute(
            select(CustomBenchmark).where(
                CustomBenchmark.owner_id == user_id,
                CustomBenchmark.owner_type == "USER",
                CustomBenchmark.sector == sector.lower(),
                CustomBenchmark.metric == metric.lower(),
            )
        )
        custom = result.scalar_one_or_none()
        if custom:
            return ThresholdRange(
                healthy_boundary=custom.healthy_boundary,
                warning_boundary=custom.warning_boundary,
                direction=DirectionEnum(custom.direction),
            )
        return None
