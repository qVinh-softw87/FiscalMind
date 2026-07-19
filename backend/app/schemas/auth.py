from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Request Schemas (Input) ────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Payload for POST /auth/register"""

    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Enforce basic password strength rules.
        Production-grade: require uppercase, lowercase, digit.
        """
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    """Payload for POST /auth/login"""

    email: EmailStr
    password: str = Field(..., min_length=1)


class RefreshTokenRequest(BaseModel):
    """Payload for POST /auth/refresh"""

    refresh_token: str


# ── Response Schemas (Output) ─────────────────────────────────────────────────

class UserResponse(BaseModel):
    """
    Safe user representation — NEVER expose hashed_password.
    `model_config = {"from_attributes": True}` allows building from ORM model directly.
    """

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Returned after successful login or token refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int   # seconds until access_token expires


class AccessTokenResponse(BaseModel):
    """Returned after a token refresh (only new access_token)."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MessageResponse(BaseModel):
    """Generic success message response."""

    message: str


# ── Internal Token Payload ─────────────────────────────────────────────────────

class TokenPayload(BaseModel):
    """
    Decoded JWT payload.

    Fields:
    - sub: subject (user UUID as string)
    - jti: JWT ID — unique per token, used for blacklisting
    - type: "access" | "refresh" — prevents using refresh token as access token
    - exp: expiration timestamp (Unix)
    """

    sub: str           # user UUID
    jti: str           # JWT unique ID
    type: str          # "access" | "refresh"
    exp: int           # expiry Unix timestamp
