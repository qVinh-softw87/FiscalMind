from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.dependencies import CurrentUser, DBSession
from app.schemas.chat import (
    ChatRequest,
    ConversationDetailResponse,
    ConversationResponse,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["AI Chat"])


def _service(db: DBSession) -> ChatService:
    """Wires ChatService with database session."""
    return ChatService(db=db)


@router.post(
    "",
    response_class=StreamingResponse,
    summary="Submit query and stream assistant response (SSE)",
)
async def chat_stream(
    payload: ChatRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> StreamingResponse:
    """
    Submits a query to the AI financial assistant.

    Returns a Server-Sent Events (SSE) stream (`text/event-stream`):
    - **Header chunk**: `data: {"conversation_id": "...", "is_new": true}`
    - **Token chunks**: `data: {"text": "chunk"}`
    - **Final chunk**: `data: {"done": true, "citations": [...]}`

    Supported custom features:
    - `document_ids`: restrict context search to specified document IDs only.
    - `conversation_id`: pass an existing ID to continue conversation.
    """
    service = _service(db)
    generator = await service.execute_chat_stream(
        payload=payload,
        current_user=current_user,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Prevents Nginx from buffering stream chunks
        },
    )


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
    summary="List all conversations",
)
async def list_conversations(
    current_user: CurrentUser,
    db: DBSession,
) -> list[ConversationResponse]:
    """Returns a list of the user's active conversations sorted by latest activity."""
    return await _service(db).list_conversations(current_user=current_user)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation history",
)
async def get_conversation_history(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ConversationDetailResponse:
    """Returns the full chat history (all messages and citations) for a conversation."""
    return await _service(db).get_conversation_history(
        conversation_id=conversation_id,
        current_user=current_user,
    )


@router.delete(
    "/conversations/{conversation_id}",
    summary="Delete a conversation",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> dict:
    """Permanently deletes a conversation and all its associated messages."""
    return await _service(db).delete_conversation(
        conversation_id=conversation_id,
        current_user=current_user,
    )
