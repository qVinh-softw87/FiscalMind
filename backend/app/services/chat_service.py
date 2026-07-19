from __future__ import annotations

import json
import re
import uuid
from collections.abc import AsyncGenerator

from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.logging import get_logger
from app.models.conversation import Conversation
from app.models.user import User
from app.rag.pipeline import RAGPipeline
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import (
    ChatRequest,
    ConversationDetailResponse,
    ConversationResponse,
)

logger = get_logger(__name__)


# ── Financial CFO System Prompt ───────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a Senior AI Architect, CFO, and Chuyên gia Phân tích Tài chính Cấp cao (Senior Financial Analyst) with 15+ years of experience.
Your mission is to help the user analyze financial statements (Balance Sheets, Income Statements, Cash Flow, and Notes) of corporate entities.

Behavior Guidelines:
1. Act like an elite, objective, and precise financial analyst. Avoid generic, vague, or fluffy summaries.
2. Structure your analysis with clean Markdown headers, bullet points, and tables. Highlight key formulas and numeric changes.
3. Always verify calculations (e.g. profit margins, debt ratios) before writing them down.
4. Ground your answers strictly in the provided Context. If the context does not contain the necessary information, state clearly: "Không tìm thấy thông tin này trong tài liệu được cung cấp." Do NOT invent numbers (hallucination is prohibited).
5. When presenting numbers or claims, you MUST cite your source using the exact bracket format: `[Source: filename, Page: X]`.
6. Vietnamese is the primary language for communication. Keep a professional, formal, and authoritative tone.
"""


class ChatService:
    """
    Orchestrates the conversational financial reasoning engine.
    Integrates the RAG pipeline with Groq Llama 3.3.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = ChatRepository(db)
        self._rag = RAGPipeline()

        # Groq client initialization
        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY is not set. Chat will fail at runtime.")
        self._groq = AsyncGroq(api_key=settings.GROQ_API_KEY)

    # ── Chat Execution ────────────────────────────────────────────────────────

    async def execute_chat_stream(
        self,
        payload: ChatRequest,
        current_user: User,
    ) -> AsyncGenerator[str, None]:
        """
        Main execution flow:
        1. Resolve conversation session.
        2. Query Qdrant Cloud for context.
        3. Formulate LLM prompts.
        4. Stream tokens from Groq.
        5. Extract and build citations list.
        6. Persist history, yield JSON chunks.
        """
        # Resolve conversation
        conversation_id = payload.conversation_id
        is_new_conv = False

        if not conversation_id:
            # Create a new conversation automatically if not provided
            # Set temporary title to user's query prefix
            title = payload.message[:40] + ("..." if len(payload.message) > 40 else "")
            conv = await self._repo.create_conversation(
                user_id=current_user.id,
                title=title,
            )
            conversation_id = conv.id
            is_new_conv = True
        else:
            conv = await self._repo.get_conversation(conversation_id, current_user.id)
            if not conv:
                raise NotFoundError("Conversation", conversation_id)

        # ── Step 1: Retrieve context from Qdrant Cloud ────────────────────────
        contexts = await self._rag.retrieve_context(
            query=payload.message,
            current_user=current_user,
            document_ids=payload.document_ids,
            limit=8,
            rerank_top_k=4,
        )

        # Build context prompt
        context_str = ""
        citations_candidates = []
        if contexts:
            context_pieces = []
            for c in contexts:
                filename = c["metadata"].get("filename", "Unknown")
                doc_type = c["metadata"].get("document_type", "Unknown")
                # Clean text chunk
                context_pieces.append(
                    f"--- Source Document: {filename} (Type: {doc_type}) ---\n{c['clean_text']}"
                )
                citations_candidates.append({
                    "filename": filename,
                    "document_type": doc_type,
                    "chunk_index": c["metadata"].get("chunk_index"),
                })
            context_str = "\n\n".join(context_pieces)

        # ── Step 2: Fetch Chat History ──
        history_messages = await self._repo.get_messages(conversation_id)
        llm_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Inject conversation history (last 10 messages to protect tokens window)
        for msg in history_messages[-10:]:
            llm_messages.append({"role": msg.role, "content": msg.content})

        # Format user prompt injecting the retrieved context
        user_prompt = f"""
Here is the retrieved context from the corporate financial statements:
{context_str}

User Question: {payload.message}
"""
        llm_messages.append({"role": "user", "content": user_prompt})

        # Save user message to PostgreSQL
        await self._repo.create_message(
            conversation_id=conversation_id,
            role="user",
            content=payload.message,
        )

        # ── Step 3: Stream from Groq ──────────────────────────────────────────
        full_assistant_response = []
        yield f"data: {json.dumps({'conversation_id': str(conversation_id), 'is_new': is_new_conv})}\n\n"

        try:
            chat_completion = await self._groq.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=llm_messages,  # type: ignore[arg-type]
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                stream=True,
            )

            async for chunk in chat_completion:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_assistant_response.append(delta)
                    # Yield token to SSE stream
                    yield f"data: {json.dumps({'text': delta})}\n\n"

        except Exception as e:
            logger.exception("groq_stream_failed", error=str(e))
            yield f"data: {json.dumps({'error': 'Failed to generate AI response.'})}\n\n"
            return

        final_content = "".join(full_assistant_response)

        # ── Step 4: Parse citations ───────────────────────────────────────────
        # Extract matching filenames cited by Llama in brackets: [Source: file.pdf, Page: X]
        detected_citations = []
        for cand in citations_candidates:
            if cand["filename"] in final_content:
                # Add to verified citations list
                if cand not in detected_citations:
                    detected_citations.append(cand)

        # Save AI assistant message history to PostgreSQL
        await self._repo.create_message(
            conversation_id=conversation_id,
            role="assistant",
            content=final_content,
            citations=detected_citations,
        )

        # Send final citations list and complete signal
        yield f"data: {json.dumps({'done': True, 'citations': detected_citations})}\n\n"

    # ── Conversations Management ──────────────────────────────────────────────

    async def list_conversations(self, current_user: User) -> list[ConversationResponse]:
        """Lists user's conversations."""
        convs = await self._repo.list_conversations(current_user.id)
        return [ConversationResponse.model_validate(c) for c in convs]

    async def get_conversation_history(
        self,
        conversation_id: uuid.UUID,
        current_user: User,
    ) -> ConversationDetailResponse:
        """Fetches full chat history ensuring ownership check."""
        conv = await self._repo.get_conversation(conversation_id, current_user.id)
        if not conv:
            raise NotFoundError("Conversation", conversation_id)
        return ConversationDetailResponse.model_validate(conv)

    async def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        current_user: User,
    ) -> dict:
        """Deletes conversation from DB."""
        conv = await self._repo.get_conversation(conversation_id, current_user.id)
        if not conv:
            raise NotFoundError("Conversation", conversation_id)
        await self._repo.delete_conversation(conv)
        return {"message": "Conversation deleted successfully.", "conversation_id": conversation_id}
