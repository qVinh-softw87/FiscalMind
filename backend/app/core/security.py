from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.auth import TokenPayload

logger = get_logger(__name__)

# ── Password Hashing ──────────────────────────────────────────────────────────
# CryptContext manages hashing schemes + auto-upgrades
# bcrypt: industry standard for password hashing
# - Adaptive: work factor can be increased as hardware gets faster
# - Built-in salt: every hash is unique even for same password
# - Slow by design: brute-force attacks are impractical
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.

    Example:
        hash_password("MyPass123") → "$2b$12$abc123..."
    The same password hashed twice produces DIFFERENT results (salt).
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a bcrypt hash.
    Returns True if match, False otherwise.
    Never compares the strings directly — uses bcrypt's verify.
    """
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Token Operations ──────────────────────────────────────────────────────

def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
) -> tuple[str, str]:
    """
    Internal factory: creates a signed JWT token.

    Returns (encoded_jwt, jti) where jti is the unique token ID.

    Payload structure:
    {
        "sub": "user-uuid",      ← Subject (who this token is for)
        "jti": "unique-uuid",    ← JWT ID (used for blacklisting)
        "type": "access",        ← Token type guard
        "iat": 1234567890,       ← Issued at
        "exp": 1234569690,       ← Expires at
    }
    """
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": subject,
        "jti": jti,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    encoded = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded, jti


def create_access_token(user_id: uuid.UUID) -> tuple[str, str]:
    """
    Creates a short-lived JWT access token.
    Returns (token, jti).

    Lifetime: ACCESS_TOKEN_EXPIRE_MINUTES (default: 30 min)
    Used in: Authorization: Bearer <token> header on every request
    """
    return _create_token(
        subject=str(user_id),
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, str]:
    """
    Creates a long-lived JWT refresh token.
    Returns (token, jti).

    Lifetime: REFRESH_TOKEN_EXPIRE_DAYS (default: 7 days)
    Used in: POST /auth/refresh to get a new access token
    """
    return _create_token(
        subject=str(user_id),
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> TokenPayload:
    """
    Decodes and validates a JWT token.

    Raises JWTError if:
    - Signature is invalid (tampered)
    - Token has expired
    - Required claims are missing
    """
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
    return TokenPayload(**payload)


def get_token_ttl(exp: int) -> int:
    """
    Returns remaining seconds until token expires.
    Used to set Redis blacklist TTL on logout.
    """
    now = int(datetime.now(timezone.utc).timestamp())
    return max(0, exp - now)
