from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.services.comparison_service import ComparisonService

router = APIRouter(prefix="/analysis", tags=["Financial Analysis"])


def _service(db: DBSession) -> ComparisonService:
    """Wires ComparisonService with database session."""
    return ComparisonService(db=db)


@router.post(
    "/compare",
    response_model=ComparisonResponse,
    summary="Compare multiple corporate financial statements side-by-side",
    responses={
        400: {"description": "Validation failed / Too few or too many document IDs"},
        404: {"description": "One or more documents not found"},
        403: {"description": "Access denied to one or more documents"},
        422: {"description": "One or more documents are not processed yet"},
    },
)
async def compare_statements(
    payload: ComparisonRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> ComparisonResponse:
    """
    Triggers side-by-side ratio compilation and AI cross-analysis.

    Inputs:
    - `document_ids`: Array of UUIDs (minimum 2, maximum 5).

    Returns:
    - `compared_entities`: Clean metadata of the files.
    - `comparison_matrix`: Side-by-side mapping for all 10 core metrics.
    - `ai_evaluation`: Direct comparative analysis (CFO Verdict, Profitability, Liquidity, Solvency).

    Requires: `Authorization: Bearer <access_token>`
    """
    return await _service(db).compare_companies(
        payload=payload,
        current_user=current_user,
    )
