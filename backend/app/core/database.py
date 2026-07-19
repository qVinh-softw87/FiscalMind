from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """
    Shared SQLAlchemy declarative base.
    All ORM models must inherit from this class.

    Using a single Base ensures Alembic can discover all models
    and generate migrations correctly via `metadata.create_all()`.
    """
    pass


def _create_engine() -> AsyncEngine:
    """
    Creates the async SQLAlchemy engine with production-grade pool settings.

    Pool Configuration:
    - pool_size: max number of persistent connections
    - max_overflow: temporary connections beyond pool_size (burst capacity)
    - pool_timeout: seconds to wait for a connection before raising
    - pool_pre_ping: validates connections before use (handles DB restarts)
    """
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_pre_ping=True,          # Detects stale connections automatically
        echo=settings.DEBUG,         # Log SQL queries only in development
    )


# Singleton engine — one engine per application lifecycle
engine: AsyncEngine = _create_engine()

# Session factory — creates sessions bound to our engine
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,    # Prevent lazy-loading errors after commit
    autoflush=False,           # Manual control over when SQL is sent
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.

    Lifecycle per request:
    1. Open a new session
    2. Yield it to the route handler
    3. Commit on success, rollback on exception
    4. Always close the session (returns connection to pool)

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def db_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions outside of FastAPI request scope.
    Used in Celery tasks, background jobs, and startup scripts.

    Usage:
        async with db_session_context() as db:
            result = await db.execute(select(User))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
