from __future__ import annotations

import uuid

import redis.asyncio as aioredis
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_ttl,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

logger = get_logger(__name__)

# Redis key prefix for JWT blacklist
# Pattern: "blacklist:{jti}" → "1" with TTL = remaining token lifetime
_BLACKLIST_PREFIX = "blacklist:"


class AuthService:
    """
    Business logic for authentication flows.

    Receives all dependencies via constructor — fully testable without mocking globals.
    Single Responsibility: ONLY handles auth business rules.

    Flows implemented:
    1. register()   → validate → check duplicate → hash password → persist
    2. login()      → verify credentials → generate tokens → record login time
    3. logout()     → blacklist access token in Redis
    4. refresh()    → validate refresh token → issue new access token
    5. get_me()     → fetch and return current user
    """

    def __init__(self, db: AsyncSession, redis: aioredis.Redis) -> None:
        self._db = db
        self._redis = redis
        self._user_repo = UserRepository(db)

    # ── Register ──────────────────────────────────────────────────────────────

    async def register(self, payload: RegisterRequest) -> UserResponse:
        """
        Registers a new user account.

        Steps:
        1. Check email uniqueness (409 if duplicate)
        2. Hash password with bcrypt
        3. Persist to DB
        4. Return safe user response (no hashed_password)
        """
        if await self._user_repo.email_exists(payload.email):
            raise ConflictError("User", "email", payload.email)

        hashed = hash_password(payload.password)
        user = await self._user_repo.create(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hashed,
        )

        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return UserResponse.model_validate(user)

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, payload: LoginRequest) -> TokenResponse:
        """
        Authenticates a user and issues JWT tokens.

        Security:
        - Use constant-time comparison via bcrypt.verify (prevents timing attacks)
        - Return SAME error message for wrong email or wrong password
          (prevents user enumeration: attacker can't tell if email exists)
        - Record last_login_at for audit

        Returns access + refresh tokens.
        """
        user = await self._user_repo.get_by_email(payload.email)

        # Deliberate: same error for wrong email AND wrong password
        if not user or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")

        if not user.is_active:
            raise ForbiddenError("Your account has been deactivated.")

        # Generate token pair
        access_token, _ = create_access_token(user.id)
        refresh_token, _ = create_refresh_token(user.id)

        # Record login time
        await self._user_repo.update_last_login(user)

        logger.info("user_logged_in", user_id=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=60 * 60,  # 60 minutes in seconds (matches ACCESS_TOKEN_EXPIRE_MINUTES * 2 buffer)
        )

    # ── Logout ────────────────────────────────────────────────────────────────

    async def logout(self, access_token: str) -> MessageResponse:
        """
        Invalidates the current access token via Redis blacklist.

        How JWT blacklisting works:
        1. JWT is stateless — we can't "delete" it from the server
        2. Instead: store the token's JTI (unique ID) in Redis
        3. Set Redis TTL = remaining lifetime of the token
        4. On every request, check if jti is blacklisted → reject if yes
        5. Redis auto-expires the key when the token would have expired anyway

        This approach is memory-efficient: only LOGOUT tokens are stored, not all tokens.
        """
        try:
            payload = decode_token(access_token)
        except JWTError:
            # Token already invalid — nothing to blacklist
            return MessageResponse(message="Logged out successfully.")

        ttl = get_token_ttl(payload.exp)
        if ttl > 0:
            blacklist_key = f"{_BLACKLIST_PREFIX}{payload.jti}"
            await self._redis.setex(blacklist_key, ttl, "1")

        logger.info("user_logged_out", jti=payload.jti)
        return MessageResponse(message="Logged out successfully.")

    # ── Refresh Token ─────────────────────────────────────────────────────────

    async def refresh(self, refresh_token: str) -> AccessTokenResponse:
        """
        Issues a new access token using a valid refresh token.

        Validates:
        1. Token signature is valid
        2. Token type is "refresh" (prevents using access token here)
        3. Token is not blacklisted in Redis
        4. User still exists and is active
        """
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise UnauthorizedError("Invalid or expired refresh token.")

        if payload.type != "refresh":
            raise UnauthorizedError("Token type mismatch.")

        # Check if this refresh token was blacklisted (e.g., after logout)
        if await self._is_blacklisted(payload.jti):
            raise UnauthorizedError("Token has been revoked.")

        user = await self._user_repo.get_by_id(uuid.UUID(payload.sub))
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive.")

        new_access_token, _ = create_access_token(user.id)

        logger.info("token_refreshed", user_id=str(user.id))

        return AccessTokenResponse(
            access_token=new_access_token,
            expires_in=60 * 30,  # 30 minutes
        )

    # ── Get Current User ──────────────────────────────────────────────────────

    async def get_current_user_by_token(self, access_token: str) -> User:
        """
        Validates an access token and returns the User model.
        Used internally by the get_current_user dependency.
        """
        try:
            payload = decode_token(access_token)
        except JWTError:
            raise UnauthorizedError("Invalid or expired access token.")

        if payload.type != "access":
            raise UnauthorizedError("Token type mismatch.")

        if await self._is_blacklisted(payload.jti):
            raise UnauthorizedError("Token has been revoked. Please log in again.")

        user = await self._user_repo.get_by_id(uuid.UUID(payload.sub))
        if not user:
            raise UnauthorizedError("User not found.")
        if not user.is_active:
            raise ForbiddenError("Account is deactivated.")

        return user

    # ── Internal Helpers ──────────────────────────────────────────────────────

    async def _is_blacklisted(self, jti: str) -> bool:
        """Checks Redis for the jti blacklist entry."""
        return await self._redis.exists(f"{_BLACKLIST_PREFIX}{jti}") > 0
