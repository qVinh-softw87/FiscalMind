from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _service(db: DBSession) -> DashboardService:
    """Wires DashboardService with database session."""
    return DashboardService(db=db)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get dashboard overview statistics",
)
async def get_dashboard_summary(
    current_user: CurrentUser,
    db: DBSession,
) -> DashboardSummaryResponse:
    """
    Returns aggregated metrics and recent activity list.

    Provides:
    - Count of documents by status (READY, PENDING, etc.).
    - Total sum of critical ratios across all user's files.
    - Top 5 recent documents.
    - Top 5 recent chat conversations.
    """
    return await _service(db).get_summary(current_user=current_user)
