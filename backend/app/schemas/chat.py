from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Requests (Input) ──────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    """Payload to start a conversation manually (optional)."""
    title: str = Field(default="New Conversation", max_length=255)


class ChatRequest(BaseModel):
    """
    Payload for POST /chat (submitting a query).
    """

    message: str = Field(..., min_length=1)

    # Optional: scope the chat context to a subset of uploaded documents
    document_ids: list[uuid.UUID] | None = Field(default=None)

    # If conversation_id is missing, the service creates a new session automatically
    conversation_id: uuid.UUID | None = Field(default=None)


# ── Responses (Output) ─────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """Safe representation of a chat message."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations: list[dict] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    """Overview of a conversation session."""

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(ConversationResponse):
    """Full detail of a conversation, including all its messages."""

    messages: list[MessageResponse]

    model_config = {"from_attributes": True}
