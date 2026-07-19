from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.financial_engine.ratios import FinancialRatioCalculator
from app.models.conversation import Conversation
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.chat import ConversationResponse
from app.schemas.dashboard import DashboardSummaryResponse, DocumentStatusCounts
from app.schemas.document import DocumentResponse


class DashboardService:
    """
    Dashboard Aggregation Engine.
    Queries and merges system activities and financial alerts.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_summary(self, current_user: User) -> DashboardSummaryResponse:
        """
        Gathers and returns dashboard stats.
        """
        user_id = current_user.id

        # ── 1. Count documents grouped by status ──
        status_query = (
            select(Document.status, func.count(Document.id))
            .where(Document.user_id == user_id, Document.is_deleted.is_(False))
            .group_by(Document.status)
        )
        status_results = await self._db.execute(status_query)
        
        status_counts = {
            "ready": 0,
            "processing": 0,
            "pending": 0,
            "failed": 0,
        }
        total_docs = 0
        for status_val, count in status_results.all():
            total_docs += count
            if status_val in status_counts:
                status_counts[status_val] = count

        doc_stats = DocumentStatusCounts(
            total=total_docs,
            ready=status_counts["ready"],
            processing=status_counts["processing"],
            pending=status_counts["pending"],
            failed=status_counts["failed"],
        )

        # ── 2. Scan for CRITICAL warning flags across all READY documents ──
        critical_count = 0
        ready_docs_query = select(Document).where(
            Document.user_id == user_id,
            Document.status == DocumentStatus.READY,
            Document.is_deleted.is_(False),
        )
        ready_docs_result = await self._db.execute(ready_docs_query)
        ready_docs = ready_docs_result.scalars().all()

        for doc in ready_docs:
            p_data = doc.parsed_data or {}
            normalized_data = p_data.get("normalized_data") or {}
            if normalized_data:
                # Compute ratios to determine status flags
                ratios = await FinancialRatioCalculator.calculate_ratios(
                    normalized_data,
                    db=self._db,
                    user_id=user_id,
                    sector=doc.sector,
                )
                # Count occurances of "CRITICAL" in the structured output
                for group in ratios.values():
                    for ratio_item in group.values():
                        if ratio_item.get("status") == "CRITICAL":
                            critical_count += 1

        # ── 3. Fetch top 5 recent documents ──
        recent_docs_query = (
            select(Document)
            .where(Document.user_id == user_id, Document.is_deleted.is_(False))
            .order_by(Document.created_at.desc())
            .limit(5)
        )
        recent_docs_result = await self._db.execute(recent_docs_query)
        recent_docs = recent_docs_result.scalars().all()
        recent_docs_resp = [DocumentResponse.model_validate(d) for d in recent_docs]

        # ── 4. Fetch top 5 recent conversations ──
        recent_convs_query = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .limit(5)
        )
        recent_convs_result = await self._db.execute(recent_convs_query)
        recent_convs = recent_convs_result.scalars().all()
        recent_convs_resp = [ConversationResponse.model_validate(c) for c in recent_convs]

        return DashboardSummaryResponse(
            document_stats=doc_stats,
            total_critical_ratios=critical_count,
            recent_documents=recent_docs_resp,
            recent_conversations=recent_convs_resp,
        )
