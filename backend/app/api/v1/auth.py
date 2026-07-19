from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.dependencies import CurrentUser, DBSession, RedisClient
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _service(db: DBSession, redis: RedisClient) -> AuthService:
    """Wires AuthService with its injected dependencies."""
    return AuthService(db=db, redis=redis)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Register a new account",
    responses={
        409: {"description": "Email already registered"},
        422: {"description": "Validation error (password strength, email format)"},
    },
)
async def register(
    payload: RegisterRequest,
    db: DBSession,
    redis: RedisClient,
) -> UserResponse:
    """
    Creates a new user account.

    Password rules: min 8 chars, at least 1 uppercase, 1 lowercase, 1 digit.
    """
    return await _service(db, redis).register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive JWT tokens",
    responses={
        401: {"description": "Invalid credentials"},
        403: {"description": "Account deactivated"},
    },
)
async def login(
    payload: LoginRequest,
    db: DBSession,
    redis: RedisClient,
) -> TokenResponse:
    """
    Authenticates user and returns access + refresh token pair.

    - `access_token` expires in 30 minutes — send in `Authorization: Bearer` header
    - `refresh_token` expires in 7 days — use POST /auth/refresh when access token expires
    """
    return await _service(db, redis).login(payload)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and blacklist current access token",
    responses={401: {"description": "Unauthorized"}},
)
async def logout(
    request: Request,
    current_user: CurrentUser,   # Validates token before blacklisting
    db: DBSession,
    redis: RedisClient,
) -> MessageResponse:
    """
    Invalidates the current access token via Redis blacklist.

    Token remains blacklisted until its natural expiry time.
    Requires: `Authorization: Bearer <access_token>`
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    return await _service(db, redis).logout(token)


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Get a new access token",
    responses={401: {"description": "Invalid or expired refresh token"}},
)
async def refresh_token(
    payload: RefreshTokenRequest,
    db: DBSession,
    redis: RedisClient,
) -> AccessTokenResponse:
    """
    Issues a new access token from a valid refresh token.

    Call this when you receive a 401 on any protected endpoint.
    """
    return await _service(db, redis).refresh(payload.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    responses={401: {"description": "Unauthorized"}},
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    """
    Returns the authenticated user's profile.

    Requires: `Authorization: Bearer <access_token>`
    """
    return UserResponse.model_validate(current_user)
