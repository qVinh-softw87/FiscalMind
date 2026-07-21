from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db_session
from app.core.redis import get_redis_client
from app.main import app

# ── Test Database (SQLite in-memory) ──────────────────────────────────────────
# Using SQLite for tests:
# - No Docker required → tests run in CI without infrastructure
# - In-memory → each test session starts clean
# - aiosqlite: async SQLite driver

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Single event loop shared across the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Creates all tables before tests, drops them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fresh DB session per test, rolled back after each test."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()
        # Clean up all table contents to prevent cross-test DB pollution
        from sqlalchemy import text
        try:
            await session.execute(text("DELETE FROM messages;"))
            await session.execute(text("DELETE FROM conversations;"))
            await session.execute(text("DELETE FROM custom_benchmarks;"))
            await session.execute(text("DELETE FROM documents;"))
            await session.execute(text("DELETE FROM users;"))
            await session.commit()
        except Exception:
            pass


@pytest_asyncio.fixture
async def mock_redis():
    """In-memory fake Redis using fakeredis."""
    try:
        import fakeredis.aioredis as fakeredis
        redis = fakeredis.FakeRedis(decode_responses=True)
        yield redis
    except ImportError:
        # If fakeredis not installed, use a simple dict mock
        class FakeRedis:
            def __init__(self):
                self._store = {}

            async def setex(self, key, ttl, value):
                self._store[key] = value

            async def exists(self, key):
                return 1 if key in self._store else 0

            async def ping(self):
                return True

        yield FakeRedis()


@pytest_asyncio.fixture
async def client(db_session, mock_redis) -> AsyncGenerator[AsyncClient, None]:
    """
    Test HTTP client with overridden dependencies.
    - Uses SQLite in-memory DB instead of PostgreSQL
    - Uses fake Redis instead of real Redis
    """
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict:
    """Creates a test user and returns credentials."""
    payload = {
        "email": "fixture@example.com",
        "full_name": "Fixture User",
        "password": "SecurePass1",
    }
    await client.post("/api/v1/auth/register", json=payload)
    return {**payload, "plain_password": payload["password"]}


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, registered_user: dict) -> dict:
    """Returns auth headers for an authenticated test user."""
    response = await client.post("/api/v1/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["plain_password"],
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
