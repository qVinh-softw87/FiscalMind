from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel, Field


class DirectionEnum(str, Enum):
    UP = "UP"      # Higher values are better (e.g., roe, margins)
    DOWN = "DOWN"  # Lower values are better (e.g., debt_ratio)


class ThresholdRange(BaseModel):
    """Refers to raw numeric boundaries that classify healthy vs warning values."""

    healthy_boundary: float = Field(..., description="Ngưỡng đạt nhãn HEALTHY")
    warning_boundary: float = Field(..., description="Ngưỡng đạt nhãn WARNING (dưới ngưỡng này sẽ là CRITICAL nếu direction=UP)")
    direction: DirectionEnum = Field(default=DirectionEnum.UP)

    def evaluate(self, value: float | None) -> str:
        """Classifies a ratio into HEALTHY, WARNING, or CRITICAL based on boundaries."""
        if value is None:
            return "UNKNOWN"

        if self.direction == DirectionEnum.UP:
            if value >= self.healthy_boundary:
                return "HEALTHY"
            if value >= self.warning_boundary:
                return "WARNING"
            return "CRITICAL"
        else:
            # For DOWN (lower is better)
            if value <= self.healthy_boundary:
                return "HEALTHY"
            if value <= self.warning_boundary:
                return "WARNING"
            return "CRITICAL"


class ResolvedThreshold(BaseModel):
    """
    Threshold wrapped with context metadata showing where it came from (audit transparency).
    """

    healthy_boundary: float
    warning_boundary: float
    direction: DirectionEnum
    source: str = Field(..., description="Nguồn gốc của ngưỡng (e.g. USER, ORG, INDUSTRY, DEFAULT)")
    industry_average: float | None = Field(default=None, description="Giá trị trung bình ngành (nếu lấy từ nguồn INDUSTRY)")

    def evaluate(self, value: float | None) -> str:
        # Wrap evaluation from threshold range
        tr = ThresholdRange(
            healthy_boundary=self.healthy_boundary,
            warning_boundary=self.warning_boundary,
            direction=self.direction,
        )
        return tr.evaluate(value)


class BaseBenchmarkProvider(ABC):
    """
    Abstract Base Class (Interface) for Benchmark Providers (Strategy Pattern).
    """

    @abstractmethod
    async def get_thresholds(
        self,
        metric: str,
        sector: str,
        user_id: uuid.UUID,
        org_id: uuid.UUID | None = None,
    ) -> ThresholdRange | None:
        """
        Fetches thresholds for a metric.
        Returns ThresholdRange if configured, else None.
        """
        pass
