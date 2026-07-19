from __future__ import annotations

import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.financial_engine.benchmarks.base import ResolvedThreshold, ThresholdRange
from app.financial_engine.benchmarks.providers.default import DefaultBenchmarkProvider
from app.financial_engine.benchmarks.providers.industry import IndustryBenchmarkProvider
from app.financial_engine.benchmarks.providers.org import OrgBenchmarkProvider
from app.financial_engine.benchmarks.providers.user import UserBenchmarkProvider


class BenchmarkResolver:
    """
    Benchmark Resolver orchestrating the prioritization chain:
    USER -> ORGANIZATION -> INDUSTRY -> DEFAULT.

    Features local in-memory caching to optimize repetitive loops.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        # Instantiating the strategy providers
        self._user_provider = UserBenchmarkProvider(db)
        self._org_provider = OrgBenchmarkProvider(db)
        self._ind_provider = IndustryBenchmarkProvider()
        self._def_provider = DefaultBenchmarkProvider()
        
        # Simple execution cache (key: (metric, sector, user_id, org_id) -> ResolvedThreshold)
        self._cache: dict[tuple, ResolvedThreshold] = {}

    async def resolve_thresholds(
        self,
        metric: str,
        sector: str,
        user_id: uuid.UUID,
        org_id: uuid.UUID | None = None,
    ) -> ResolvedThreshold:
        """
        Traverses the priority providers until a threshold range matches.
        Guarantees fallback to DefaultBenchmarkProvider (so it never returns None).
        """
        cache_key = (metric.lower(), sector.lower(), user_id, org_id)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # ── 1. Check User custom ──
        res = await self._user_provider.get_thresholds(metric, sector, user_id, org_id)
        if res:
            resolved = ResolvedThreshold(
                healthy_boundary=res.healthy_boundary,
                warning_boundary=res.warning_boundary,
                direction=res.direction,
                source="USER",
            )
            self._cache[cache_key] = resolved
            return resolved

        # ── 2. Check Org custom ──
        res = await self._org_provider.get_thresholds(metric, sector, user_id, org_id)
        if res:
            resolved = ResolvedThreshold(
                healthy_boundary=res.healthy_boundary,
                warning_boundary=res.warning_boundary,
                direction=res.direction,
                source="ORGANIZATION",
            )
            self._cache[cache_key] = resolved
            return resolved

        # ── 3. Check Sector/Industry defaults ──
        res = await self._ind_provider.get_thresholds(metric, sector, user_id, org_id)
        ind_avg = self._ind_provider.get_industry_average(metric, sector)
        if res:
            resolved = ResolvedThreshold(
                healthy_boundary=res.healthy_boundary,
                warning_boundary=res.warning_boundary,
                direction=res.direction,
                source="INDUSTRY",
                industry_average=ind_avg,
            )
            self._cache[cache_key] = resolved
            return resolved

        # ── 4. Fallback to System defaults ──
        # Guaranteed to return because DEFAULT_REGISTRY has all metrics
        res_default = await self._def_provider.get_thresholds(metric, sector, user_id, org_id)
        
        # Safe default boundaries fallback
        healthy = res_default.healthy_boundary if res_default else 0.0
        warning = res_default.warning_boundary if res_default else 0.0
        direction = res_default.direction if res_default else "UP"

        resolved = ResolvedThreshold(
            healthy_boundary=healthy,
            warning_boundary=warning,
            direction=direction,
            source="DEFAULT",
        )
        self._cache[cache_key] = resolved
        return resolved
