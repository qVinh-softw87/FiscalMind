from __future__ import annotations

import uuid
from pydantic import BaseModel, Field

from app.financial_engine.benchmarks.base import DirectionEnum


# ── Requests ──────────────────────────────────────────────────────────────────

class CustomBenchmarkCreate(BaseModel):
    """Payload to create/update custom threshold values."""

    sector: str = Field(..., description="Ngành áp dụng (e.g. technology, real_estate)")
    metric: str = Field(..., description="Chỉ số tài chính áp dụng (e.g. roe, debt_ratio)")
    healthy_boundary: float = Field(..., description="Ngưỡng đạt nhãn HEALTHY")
    warning_boundary: float = Field(..., description="Ngưỡng đạt nhãn WARNING")
    direction: DirectionEnum = Field(default=DirectionEnum.UP)
    
    # "USER" (personal overrides) or "ORGANIZATION" (org-wide overrides)
    owner_type: str = Field(default="USER")
    org_id: uuid.UUID | None = Field(default=None, description="Chỉ truyền nếu owner_type là ORGANIZATION")


# ── Responses ─────────────────────────────────────────────────────────────────

class ThresholdDetails(BaseModel):
    """Boundaries applied to evaluate the ratio."""

    healthy: float
    warning: float
    direction: DirectionEnum
    industry_average: float | None = None


class RatioBenchmarkComparison(BaseModel):
    """Side-by-side comparison of a single metric against its benchmark."""

    value: float | None
    status: str
    source: str
    thresholds: ThresholdDetails | None
    explanation: str


class GroupBenchmarkComparison(BaseModel):
    """Container grouping metric comparisons (e.g., profitability, liquidity)."""

    metrics: dict[str, RatioBenchmarkComparison]


class DocumentBenchmarkReport(BaseModel):
    """Unified benchmarking report payload."""

    document_id: uuid.UUID
    filename: str
    sector: str
    ratios: dict[str, dict[str, RatioBenchmarkComparison]]
