from __future__ import annotations

import pytest
from httpx import AsyncClient


# ── Test: Register ─────────────────────────────────────────────────────────────

class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "SecurePass1",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert "hashed_password" not in data  # Never expose this

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {
            "email": "duplicate@example.com",
            "full_name": "User One",
            "password": "SecurePass1",
        }
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONFLICT"

    async def test_register_weak_password(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "full_name": "Weak User",
            "password": "weakpassword",  # No uppercase, no digit
        })
        assert response.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "full_name": "Bad Email",
            "password": "SecurePass1",
        })
        assert response.status_code == 422


# ── Test: Login ────────────────────────────────────────────────────────────────

class TestLogin:
    async def test_login_success(self, client: AsyncClient, registered_user: dict):
        response = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["plain_password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, registered_user: dict):
        response = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": "WrongPassword1",
        })
        assert response.status_code == 401

    async def test_login_wrong_email(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "SomePass1",
        })
        # Same error as wrong password — prevents user enumeration
        assert response.status_code == 401


# ── Test: Get /me ─────────────────────────────────────────────────────────────

class TestGetMe:
    async def test_get_me_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert "email" in response.json()

    async def test_get_me_no_token(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


# ── Test: Refresh ─────────────────────────────────────────────────────────────

class TestRefresh:
    async def test_refresh_success(self, client: AsyncClient, registered_user: dict):
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["plain_password"],
        })
        refresh_token = login_resp.json()["refresh_token"]

        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_refresh_with_access_token_fails(
        self, client: AsyncClient, registered_user: dict
    ):
        """Access token must not be usable as a refresh token."""
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["plain_password"],
        })
        access_token = login_resp.json()["access_token"]

        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": access_token,  # Wrong type
        })
        assert response.status_code == 401


# ── Test: Logout ──────────────────────────────────────────────────────────────

class TestLogout:
    async def test_logout_blacklists_token(
        self, client: AsyncClient, registered_user: dict
    ):
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["plain_password"],
        })
        access_token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Logout
        logout_resp = await client.post("/api/v1/auth/logout", headers=headers)
        assert logout_resp.status_code == 200

        # Token should now be blacklisted → 401 on /me
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 401
