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


class OrgBenchmarkProvider(BaseBenchmarkProvider):
    """
    Organization Custom Provider.
    Queries PostgreSQL for organization-level customized overrides.
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
        """Fetches custom organization thresholds from DB if set."""
        if not org_id:
            # If org_id is not supplied, skip
            return None

        result = await self._db.execute(
            select(CustomBenchmark).where(
                CustomBenchmark.owner_id == org_id,
                CustomBenchmark.owner_type == "ORGANIZATION",
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
