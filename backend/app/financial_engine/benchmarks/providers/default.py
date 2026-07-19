from __future__ import annotations

import uuid

from app.financial_engine.benchmarks.base import (
    BaseBenchmarkProvider,
    DirectionEnum,
    ThresholdRange,
)


class DefaultBenchmarkProvider(BaseBenchmarkProvider):
    """
    Fallback System Provider.
    Supplies general baseline financial thresholds when no other configuration is present.
    """

    # Static default baseline registry
    DEFAULT_REGISTRY: dict[str, ThresholdRange] = {
        "roe": ThresholdRange(healthy_boundary=0.15, warning_boundary=0.05, direction=DirectionEnum.UP),
        "roa": ThresholdRange(healthy_boundary=0.06, warning_boundary=0.02, direction=DirectionEnum.UP),
        "current_ratio": ThresholdRange(healthy_boundary=1.5, warning_boundary=1.0, direction=DirectionEnum.UP),
        "quick_ratio": ThresholdRange(healthy_boundary=1.0, warning_boundary=0.7, direction=DirectionEnum.UP),
        "debt_ratio": ThresholdRange(healthy_boundary=0.5, warning_boundary=0.7, direction=DirectionEnum.DOWN),
        "debt_to_equity": ThresholdRange(healthy_boundary=1.0, warning_boundary=2.0, direction=DirectionEnum.DOWN),
        "gross_margin": ThresholdRange(healthy_boundary=0.25, warning_boundary=0.15, direction=DirectionEnum.UP),
        "net_margin": ThresholdRange(healthy_boundary=0.10, warning_boundary=0.03, direction=DirectionEnum.UP),
        "operating_margin": ThresholdRange(healthy_boundary=0.12, warning_boundary=0.05, direction=DirectionEnum.UP),
    }

    async def get_thresholds(
        self,
        metric: str,
        sector: str,
        user_id: uuid.UUID,
        org_id: uuid.UUID | None = None,
    ) -> ThresholdRange | None:
        """Returns the fallback general baseline threshold."""
        return self.DEFAULT_REGISTRY.get(metric.lower())
