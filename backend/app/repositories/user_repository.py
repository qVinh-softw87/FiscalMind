from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """
    Data access layer for the User domain.

    Responsibilities:
    - All DB queries related to User live HERE, nowhere else
    - No business logic — only read/write operations
    - Receives AsyncSession via constructor (Dependency Injection)

    Why Repository Pattern?
    - Decouples business logic from DB implementation
    - Easy to mock in tests: replace UserRepository with a fake
    - If we switch from PostgreSQL to MongoDB, only this file changes
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch user by primary key. Returns None if not found."""
        result = await self._db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """
        Fetch user by email address.
        Used in: login (check credentials), register (check duplicate).
        Indexed column → O(log n) lookup.
        """
        result = await self._db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        full_name: str,
        hashed_password: str,
    ) -> User:
        """
        Inserts a new user record.

        Note: session.commit() is handled by the caller (service layer)
        or by the get_db_session dependency automatically.
        This keeps the repository focused on DB operations only.
        """
        user = User(
            email=email.lower().strip(),
            full_name=full_name.strip(),
            hashed_password=hashed_password,
        )
        self._db.add(user)
        await self._db.flush()   # Flush to get auto-generated id without full commit
        await self._db.refresh(user)
        return user

    async def update_last_login(self, user: User) -> User:
        """Records the timestamp of a successful login."""
        from datetime import datetime, timezone
        user.last_login_at = datetime.now(timezone.utc)
        await self._db.flush()
        return user

    async def email_exists(self, email: str) -> bool:
        """Efficient existence check without fetching full user object."""
        result = await self._db.execute(
            select(User.id).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none() is not None
