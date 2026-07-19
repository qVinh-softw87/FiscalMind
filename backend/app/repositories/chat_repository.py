from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message


class ChatRepository:
    """
    Data access layer for Conversations and Messages (Repository Pattern).
    All database operations for the chat module live here.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Conversations ─────────────────────────────────────────────────────────

    async def get_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Conversation | None:
        """
        Fetch a conversation by ID, checking ownership to prevent IDOR attacks.
        Eagerly loads message records using selectinload.
        """
        result = await self._db.execute(
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Conversation]:
        """Lists user's conversations sorted by latest activity."""
        result = await self._db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def create_conversation(
        self,
        user_id: uuid.UUID,
        title: str = "New Conversation",
    ) -> Conversation:
        """Creates and saves a new conversation session."""
        conversation = Conversation(
            user_id=user_id,
            title=title[:255],  # Guard size boundary
        )
        self._db.add(conversation)
        await self._db.flush()
        await self._db.refresh(conversation)
        return conversation

    async def update_title(
        self,
        conversation: Conversation,
        title: str,
    ) -> Conversation:
        """Updates conversation title (usually based on user's first query)."""
        conversation.title = title[:255]
        await self._db.flush()
        return conversation

    async def delete_conversation(
        self,
        conversation: Conversation,
    ) -> None:
        """Deletes conversation — cascades and deletes orphan messages automatically."""
        await self._db.delete(conversation)
        await self._db.flush()

    # ── Messages ──────────────────────────────────────────────────────────────

    async def create_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        citations: list[dict] | None = None,
    ) -> Message:
        """Inserts and returns a chat message record."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations,
        )
        self._db.add(message)
        await self._db.flush()
        await self._db.refresh(message)
        return message

    async def get_messages(self, conversation_id: uuid.UUID) -> Sequence[Message]:
        """Fetches history for a conversation sorted by date."""
        result = await self._db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return result.scalars().all()
