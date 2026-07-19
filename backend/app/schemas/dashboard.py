from __future__ import annotations

from pydantic import BaseModel

from app.schemas.chat import ConversationResponse
from app.schemas.document import DocumentResponse


class DocumentStatusCounts(BaseModel):
    """Counts of documents grouped by their lifecycle status."""

    total: int = 0
    ready: int = 0
    processing: int = 0
    pending: int = 0
    failed: int = 0


class DashboardSummaryResponse(BaseModel):
    """
    Unified payload providing the overview statistics
    displayed on the user's dashboard landing page.
    """

    document_stats: DocumentStatusCounts
    total_critical_ratios: int = 0
    recent_documents: list[DocumentResponse] = []
    recent_conversations: list[ConversationResponse] = []
