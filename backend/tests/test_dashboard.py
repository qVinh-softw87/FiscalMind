from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.document import Document, DocumentStatus
from app.models.user import User


class TestDashboardAPI:
    async def test_get_dashboard_summary_success(
        self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        # Fetch current user from database to use as foreign key
        # User is seeded in fixture (registered_user has fixtures email)
        from sqlalchemy import select
        result = await db_session.execute(
            select(User).where(User.email == "fixture@example.com")
        )
        user = result.scalar_one()

        # Seed 1 READY document with critical ratios
        # Current Ratio: 200 / 800 = 0.25 (Critical)
        doc1 = Document(
            user_id=user.id,
            original_filename="report_2023.pdf",
            stored_filename="abcdefg.pdf",
            file_path="uploads/abcdefg.pdf",
            file_size=1024,
            mime_type="application/pdf",
            status=DocumentStatus.READY,
            parsed_data={
                "normalized_data": {
                    "short_term_assets": 200.0,
                    "short_term_liabilities": 800.0,
                }
            }
        )

        # Seed 1 PENDING document
        doc2 = Document(
            user_id=user.id,
            original_filename="report_2024.pdf",
            stored_filename="xyz.pdf",
            file_path="uploads/xyz.pdf",
            file_size=2048,
            mime_type="application/pdf",
            status=DocumentStatus.PENDING,
        )

        # Seed 1 Conversation session
        conv = Conversation(
            user_id=user.id,
            title="Cuộc trò chuyện thử nghiệm",
        )

        db_session.add_all([doc1, doc2, conv])
        await db_session.commit()

        # Request dashboard API
        response = await client.get("/api/v1/dashboard/summary", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "document_stats" in data
        assert data["document_stats"]["total"] == 2
        assert data["document_stats"]["ready"] == 1
        assert data["document_stats"]["pending"] == 1

        # Verify critical ratio scan counted the 1 critical ratio from doc1
        assert data["total_critical_ratios"] > 0
        
        # Verify lists were returned
        assert len(data["recent_documents"]) > 0
        assert len(data["recent_conversations"]) > 0
        assert data["recent_conversations"][0]["title"] == "Cuộc trò chuyện thử nghiệm"
