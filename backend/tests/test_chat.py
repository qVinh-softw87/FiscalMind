from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.fixture
def mock_groq():
    """Mocks Groq completions call to return stream chunks."""
    with patch("app.services.chat_service.AsyncGroq") as mock_groq_class:
        # Mock instance and choices stream
        mock_client = mock_groq_class.return_value
        
        # Async iterator mock for the stream completions
        async def mock_chunks():
            # Mock objects resembling Groq delta chunks
            class Delta:
                def __init__(self, content):
                    self.content = content

            class Choice:
                def __init__(self, content):
                    self.delta = Delta(content)

            class Chunk:
                def __init__(self, content):
                    self.choices = [Choice(content)]

            yield Chunk("Chào ")
            yield Chunk("bạn, tôi là ")
            yield Chunk("CFO AI.")

        mock_client.chat.completions.create = AsyncMock(return_value=mock_chunks())
        yield mock_client


# ── Test: Conversations CRUD ──────────────────────────────────────────────────

class TestConversations:
    async def test_create_conversation_history_flow(
        self, client: AsyncClient, auth_headers: dict
    ):
        # 1. Get empty history
        list_resp = await client.get("/api/v1/chat/conversations", headers=auth_headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 0

        # Start a stream chat request which creates conversation session automatically
        with patch("app.services.chat_service.RAGPipeline.retrieve_context", new_callable=AsyncMock) as mock_retrieval:
            mock_retrieval.return_value = []
            
            with patch("app.services.chat_service.AsyncGroq") as mock_groq_class:
                mock_client = mock_groq_class.return_value
                # Mock stream return
                async def mock_chunks():
                    class Delta:
                        content = "Chào bạn"
                    class Choice:
                        delta = Delta()
                    class Chunk:
                        choices = [Choice()]
                    yield Chunk()
                mock_client.chat.completions.create = AsyncMock(return_value=mock_chunks())

                # Send request
                response = await client.post(
                    "/api/v1/chat",
                    json={"message": "Xin chào CFO"},
                    headers=auth_headers,
                )
                assert response.status_code == 200
                
                # Check stream content line header
                lines = response.text.split("\n\n")
                first_chunk = json.loads(lines[0].replace("data: ", ""))
                assert "conversation_id" in first_chunk
                assert first_chunk["is_new"] is True


    async def test_get_conversation_not_found(self, client: AsyncClient, auth_headers: dict):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/chat/conversations/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"


# ── Test: Chat API Stream Routing ─────────────────────────────────────────────

class TestChatStreamAPI:
    @patch("app.services.chat_service.RAGPipeline.retrieve_context", new_callable=AsyncMock)
    async def test_chat_stream_success(
        self, mock_retrieval, client: AsyncClient, auth_headers: dict, mock_groq
    ):
        # RAG context return stub
        mock_retrieval.return_value = [
            {
                "clean_text": "Doanh thu năm 2024 đạt 100 tỷ VND",
                "score": 0.95,
                "metadata": {"filename": "bctc.pdf", "document_type": "income_statement", "chunk_index": 1}
            }
        ]

        response = await client.post(
            "/api/v1/chat",
            json={"message": "Doanh thu năm 2024?"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["Content-Type"]

        # Parse SSE structure
        lines = [line for line in response.text.split("\n\n") if line.strip()]
        assert len(lines) >= 3

        # Header payload verify
        header = json.loads(lines[0].replace("data: ", ""))
        assert "conversation_id" in header

        # Tokens stream check
        token_payloads = [json.loads(line.replace("data: ", "")) for line in lines[1:-1]]
        text_joined = "".join([t["text"] for t in token_payloads if "text" in t])
        assert "CFO AI" in text_joined

        # Completion signal payload check
        done_payload = json.loads(lines[-1].replace("data: ", ""))
        assert done_payload["done"] is True
        assert "citations" in done_payload
