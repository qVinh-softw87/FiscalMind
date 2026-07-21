from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.insight import FinancialInsightReport, PriorityEnum


class TestInsightSchemas:
    def test_valid_insight_json_load(self):
        raw_json = """
        {
          "summary": "Doanh nghiệp ổn định.",
          "strengths": [
            {"metric": "ROE", "value": "20%", "analysis": "Tốt"}
          ],
          "weaknesses": [
            {"metric": "Hệ số nợ", "value": "75%", "analysis": "Cảnh báo"}
          ],
          "recommendations": [
            {"action": "Cơ cấu nợ", "priority": "HIGH", "detail": "Nhanh chóng chuyển đổi nợ ngắn hạn"}
          ]
        }
        """
        report = FinancialInsightReport.model_validate_json(raw_json)
        assert report.summary == "Doanh nghiệp ổn định."
        assert len(report.strengths) == 1
        assert report.recommendations[0].priority == PriorityEnum.HIGH

    def test_invalid_insight_priority_fails(self):
        raw_json = """
        {
          "summary": "Doanh nghiệp ổn định.",
          "recommendations": [
            {"action": "Cơ cấu nợ", "priority": "IMMEDIATE", "detail": "Invalid priority"}
          ]
        }
        """
        # Should raise validation error because IMMEDIATE is not in HIGH/MEDIUM/LOW
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FinancialInsightReport.model_validate_json(raw_json)


class TestInsightService:
    @patch("app.services.insight_service.AsyncGroq")
    async def test_insights_generation_mock_success(self, mock_groq_class):
        # Mock the Groq client to return standard structured JSON payload
        mock_client = mock_groq_class.return_value
        
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "summary": "Mô phỏng báo cáo tổng quan.",
            "strengths": [{"metric": "ROE", "value": "18%", "analysis": "Hiệu suất sinh lời cao"}],
            "weaknesses": [],
            "recommendations": []
        })
        
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        from app.services.insight_service import InsightService
        from app.models.user import User
        from app.models.document import Document
        
        fake_user = User(id=uuid.uuid4(), email="user@example.com")
        fake_doc = Document(
            id=uuid.uuid4(),
            user_id=fake_user.id,
            original_filename="bctc.pdf",
            parsed_data={"normalized_data": {"net_revenue": 100, "net_profit": 20, "equity": 100}}
        )

        db_mock = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db_mock.execute = AsyncMock(return_value=result_mock)
        
        with patch("app.services.insight_service.DocumentRepository") as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_by_id = AsyncMock(return_value=fake_doc)
            
            service = InsightService(db=db_mock)
            report = await service.generate_insights(fake_doc.id, fake_user)
            
            assert report.summary == "Mô phỏng báo cáo tổng quan."
            assert len(report.strengths) == 1
            assert report.strengths[0].metric == "ROE"
            
            # Verify JSON Mode options were passed
            mock_client.chat.completions.create.assert_called_once()
            called_args = mock_client.chat.completions.create.call_args[1]
            assert called_args["response_format"] == {"type": "json_object"}
import uuid
from unittest.mock import MagicMock
