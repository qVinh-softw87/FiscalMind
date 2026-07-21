from __future__ import annotations

from typing import Annotated, Optional

import redis.asyncio as aioredis
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.redis import get_redis_client

# ── Infrastructure Dependencies ───────────────────────────────────────────────
# Typed aliases for cleaner route signatures:
#   async def my_route(db: DBSession, cache: RedisClient): ...

DBSession = Annotated[AsyncSession, Depends(get_db_session)]
RedisClient = Annotated[aioredis.Redis, Depends(get_redis_client)]

# ── Auth Bearer Scheme ────────────────────────────────────────────────────────
# HTTPBearer extracts the token from "Authorization: Bearer <token>" header
# auto_error=False: we raise our own UnauthorizedError instead of FastAPI's default
_bearer_scheme = HTTPBearer(auto_error=False)
BearerToken = Annotated[
    Optional[HTTPAuthorizationCredentials],
    Depends(_bearer_scheme),
]


# ── Authenticated User Dependency ─────────────────────────────────────────────

async def get_current_user(
    credentials: BearerToken,
    db: DBSession,
    redis: RedisClient,
):
    """
    FastAPI dependency that validates the JWT and returns the current User.

    Usage in routes:
        async def get_profile(current_user: CurrentUser):
            return current_user

    Flow:
    1. Extract token from Authorization header
    2. Validate JWT signature + expiry
    3. Check token not blacklisted in Redis
    4. Load user from DB
    5. Return User model (or raise UnauthorizedError)
    """
    from app.core.exceptions import UnauthorizedError
    from app.services.auth_service import AuthService

    if not credentials:
        raise UnauthorizedError("Authorization header missing.")

    service = AuthService(db=db, redis=redis)
    return await service.get_current_user_by_token(credentials.credentials)


# ── Typed Aliases ─────────────────────────────────────────────────────────────
from app.models.user import User  # noqa: E402

CurrentUser = Annotated[User, Depends(get_current_user)]
