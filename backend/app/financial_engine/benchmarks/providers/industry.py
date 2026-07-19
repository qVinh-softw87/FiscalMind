from __future__ import annotations

import uuid

from app.financial_engine.benchmarks.base import (
    BaseBenchmarkProvider,
    DirectionEnum,
    ThresholdRange,
)


class IndustryBenchmarkProvider(BaseBenchmarkProvider):
    """
    Industry Sector Provider.
    Supplies sector-specific thresholds and averages based on business context.
    """

    # Industry averages baseline (Sector -> Metric -> (ThresholdRange, industry_average))
    SECTOR_REGISTRY: dict[str, dict[str, tuple[ThresholdRange, float]]] = {
        "technology": {
            "roe": (ThresholdRange(healthy_boundary=0.20, warning_boundary=0.10, direction=DirectionEnum.UP), 0.18),
            "roa": (ThresholdRange(healthy_boundary=0.10, warning_boundary=0.04, direction=DirectionEnum.UP), 0.08),
            "current_ratio": (ThresholdRange(healthy_boundary=2.0, warning_boundary=1.5, direction=DirectionEnum.UP), 2.2),
            "quick_ratio": (ThresholdRange(healthy_boundary=1.8, warning_boundary=1.2, direction=DirectionEnum.UP), 1.9),
            "debt_ratio": (ThresholdRange(healthy_boundary=0.3, warning_boundary=0.5, direction=DirectionEnum.DOWN), 0.25),
            "debt_to_equity": (ThresholdRange(healthy_boundary=0.5, warning_boundary=1.0, direction=DirectionEnum.DOWN), 0.40),
            "gross_margin": (ThresholdRange(healthy_boundary=0.45, warning_boundary=0.30, direction=DirectionEnum.UP), 0.50),
            "net_margin": (ThresholdRange(healthy_boundary=0.15, warning_boundary=0.08, direction=DirectionEnum.UP), 0.12),
        },
        "real_estate": {
            # Real Estate operates on high leverage
            "roe": (ThresholdRange(healthy_boundary=0.12, warning_boundary=0.06, direction=DirectionEnum.UP), 0.10),
            "roa": (ThresholdRange(healthy_boundary=0.04, warning_boundary=0.015, direction=DirectionEnum.UP), 0.03),
            "current_ratio": (ThresholdRange(healthy_boundary=1.2, warning_boundary=0.9, direction=DirectionEnum.UP), 1.1),
            "quick_ratio": (ThresholdRange(healthy_boundary=0.6, warning_boundary=0.4, direction=DirectionEnum.UP), 0.5), # Low is normal due to slow land/inv sales
            "debt_ratio": (ThresholdRange(healthy_boundary=0.6, warning_boundary=0.75, direction=DirectionEnum.DOWN), 0.65), # High debt is sector standard
            "debt_to_equity": (ThresholdRange(healthy_boundary=1.5, warning_boundary=2.5, direction=DirectionEnum.DOWN), 1.8),
            "gross_margin": (ThresholdRange(healthy_boundary=0.30, warning_boundary=0.20, direction=DirectionEnum.UP), 0.28),
            "net_margin": (ThresholdRange(healthy_boundary=0.08, warning_boundary=0.03, direction=DirectionEnum.UP), 0.06),
        },
        "retail": {
            # Retail has low margins but high turnover
            "roe": (ThresholdRange(healthy_boundary=0.18, warning_boundary=0.08, direction=DirectionEnum.UP), 0.15),
            "roa": (ThresholdRange(healthy_boundary=0.07, warning_boundary=0.03, direction=DirectionEnum.UP), 0.05),
            "current_ratio": (ThresholdRange(healthy_boundary=1.3, warning_boundary=1.0, direction=DirectionEnum.UP), 1.2),
            "quick_ratio": (ThresholdRange(healthy_boundary=0.7, warning_boundary=0.4, direction=DirectionEnum.UP), 0.5), # Inventory forms bulk of assets
            "debt_ratio": (ThresholdRange(healthy_boundary=0.5, warning_boundary=0.65, direction=DirectionEnum.DOWN), 0.55),
            "debt_to_equity": (ThresholdRange(healthy_boundary=1.0, warning_boundary=1.8, direction=DirectionEnum.DOWN), 1.2),
            "gross_margin": (ThresholdRange(healthy_boundary=0.20, warning_boundary=0.10, direction=DirectionEnum.UP), 0.18),
            "net_margin": (ThresholdRange(healthy_boundary=0.05, warning_boundary=0.02, direction=DirectionEnum.UP), 0.03),
        },
        "manufacturing": {
            # High CapEx fixed assets
            "roe": (ThresholdRange(healthy_boundary=0.14, warning_boundary=0.06, direction=DirectionEnum.UP), 0.11),
            "roa": (ThresholdRange(healthy_boundary=0.05, warning_boundary=0.02, direction=DirectionEnum.UP), 0.04),
            "current_ratio": (ThresholdRange(healthy_boundary=1.5, warning_boundary=1.1, direction=DirectionEnum.UP), 1.4),
            "quick_ratio": (ThresholdRange(healthy_boundary=1.0, warning_boundary=0.7, direction=DirectionEnum.UP), 0.9),
            "debt_ratio": (ThresholdRange(healthy_boundary=0.45, warning_boundary=0.6, direction=DirectionEnum.DOWN), 0.50),
            "debt_to_equity": (ThresholdRange(healthy_boundary=0.8, warning_boundary=1.5, direction=DirectionEnum.DOWN), 1.0),
            "gross_margin": (ThresholdRange(healthy_boundary=0.22, warning_boundary=0.12, direction=DirectionEnum.UP), 0.18),
            "net_margin": (ThresholdRange(healthy_boundary=0.08, warning_boundary=0.03, direction=DirectionEnum.UP), 0.05),
        }
    }

    async def get_thresholds(
        self,
        metric: str,
        sector: str,
        user_id: uuid.UUID,
        org_id: uuid.UUID | None = None,
    ) -> ThresholdRange | None:
        """Returns the specific industry thresholds if sector matches."""
        sec_dict = self.SECTOR_REGISTRY.get(sector.lower())
        if sec_dict:
            res = sec_dict.get(metric.lower())
            if res:
                return res[0] # Return the ThresholdRange
        return None

    def get_industry_average(self, metric: str, sector: str) -> float | None:
        """Returns raw sector average value (e.g. 0.18 for tech ROE) if registered."""
        sec_dict = self.SECTOR_REGISTRY.get(sector.lower())
        if sec_dict:
            res = sec_dict.get(metric.lower())
            if res:
                return res[1] # Return the average float
        return None
