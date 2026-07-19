from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession
from app.schemas.insight import FinancialInsightReport
from app.services.insight_service import InsightService

# We merge this endpoint under the "analysis" tag group
router = APIRouter(prefix="/analysis", tags=["Financial Analysis"])


def _service(db: DBSession) -> InsightService:
    """Wires InsightService with database session."""
    return InsightService(db=db)


@router.get(
    "/documents/{document_id}/insights",
    response_model=FinancialInsightReport,
    summary="Generate AI CFO insights and recommendations",
    responses={
        404: {"description": "Document not found"},
        403: {"description": "Access denied"},
        422: {"description": "Insufficient financial data for analysis"},
    },
)
async def generate_document_insights(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> FinancialInsightReport:
    """
    Triggers the AI CFO reasoning engine.

    The AI reads the computed financial ratios (ROE, ROA, Debt Ratio, Liquidity etc.)
    and outputs a structured report containing:
    - Overall summary
    - Key Strengths
    - Risk Warnings (Weaknesses)
    - Actionable Recommendations (prioritized: HIGH, MEDIUM, LOW)

    Requires: `Authorization: Bearer <access_token>`
    """
    return await _service(db).generate_insights(
        document_id=document_id,
        current_user=current_user,
    )
