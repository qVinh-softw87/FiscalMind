from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.comparison import ComparisonRequest, ComparisonResponse


class TestComparisonSchemas:
    def test_validation_insufficient_ids_fails(self):
        # 1. Fewer than 2 IDs should raise Pydantic validation error
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ComparisonRequest(document_ids=[uuid.uuid4()])

    def test_validation_excess_ids_fails(self):
        # 2. More than 5 IDs should raise Pydantic validation error
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ComparisonRequest(document_ids=[uuid.uuid4() for _ in range(6)])


class TestComparisonService:
    @patch("app.services.comparison_service.AsyncGroq")
    async def test_compare_companies_mock_success(self, mock_groq_class):
        # Mock Groq returns comparative JSON
        mock_client = mock_groq_class.return_value
        
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "profitability_comparison": "A có ROE cao hơn B.",
            "leverage_comparison": "B có nợ nhiều hơn A.",
            "liquidity_comparison": "Cả hai đều có thanh khoản tốt.",
            "cfo_verdict": "Tổng kết A khoẻ mạnh hơn."
        })
        
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        from app.services.comparison_service import ComparisonService
        from app.models.user import User
        from app.models.document import Document, DocumentStatus, DocumentType
        
        fake_user = User(id=uuid.uuid4(), email="user@example.com")
        
        doc_a = Document(
            id=uuid.uuid4(),
            user_id=fake_user.id,
            original_filename="company_a.pdf",
            status=DocumentStatus.READY,
            document_type=DocumentType.OTHER,
            parsed_data={"normalized_data": {"net_revenue": 100, "net_profit": 20, "equity": 100}}
        )
        
        doc_b = Document(
            id=uuid.uuid4(),
            user_id=fake_user.id,
            original_filename="company_b.pdf",
            status=DocumentStatus.READY,
            document_type=DocumentType.OTHER,
            parsed_data={"normalized_data": {"net_revenue": 100, "net_profit": 10, "equity": 100}}
        )

        db_mock = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [doc_a, doc_b]
        result_mock.scalar_one_or_none.return_value = None
        db_mock.execute = AsyncMock(return_value=result_mock)

        service = ComparisonService(db=db_mock)
        request = ComparisonRequest(document_ids=[doc_a.id, doc_b.id])
        
        report = await service.compare_companies(request, fake_user)
        
        # Verify matrix format
        assert "roe" in report.comparison_matrix
        assert len(report.compared_entities) == 2
        assert report.ai_evaluation.cfo_verdict == "Tổng kết A khoẻ mạnh hơn."
        
        # Verify JSON Mode options were passed
        mock_client.chat.completions.create.assert_called_once()
        called_args = mock_client.chat.completions.create.call_args[1]
        assert called_args["response_format"] == {"type": "json_object"}

