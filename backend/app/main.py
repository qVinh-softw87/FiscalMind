from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import (
    FiscalMindException,
    fiscalmind_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestLoggingMiddleware
from app.core.redis import close_redis, get_redis_client

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    Controls startup and shutdown:
    - STARTUP: Initialize connections, warm up caches, validate config
    - SHUTDOWN: Gracefully close connections, flush logs

    Using lifespan instead of deprecated on_event decorators (FastAPI >= 0.93).
    """
    # ── STARTUP ───────────────────────────────────────────────────────────────
    configure_logging(debug=settings.DEBUG)
    logger.info(
        "fiscalmind_starting",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )

    # Warm up database connection pool
    async with engine.connect() as conn:
        await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    logger.info("database_connected")

    # Warm up Redis connection pool
    await get_redis_client()
    logger.info("redis_connected")

    logger.info("fiscalmind_ready", docs_url=f"{settings.API_PREFIX}/docs")

    yield  # Application is running

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    logger.info("fiscalmind_shutting_down")
    await engine.dispose()
    await close_redis()
    logger.info("fiscalmind_stopped")


def create_application() -> FastAPI:
    """
    Application factory pattern.

    Why a factory?
    - Makes the app testable: tests create their own app instance with overrides
    - Avoids module-level side effects at import time
    - Clean separation between app creation and app running
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered assistant for enterprise financial statement analysis.",
        version=settings.APP_VERSION,
        docs_url=f"{settings.API_PREFIX}/docs" if settings.DEBUG else None,
        redoc_url=f"{settings.API_PREFIX}/redoc" if settings.DEBUG else None,
        openapi_url=f"{settings.API_PREFIX}/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    _register_middleware(app)
    _register_exception_handlers(app)
    _register_routers(app)

    return app


def _register_middleware(app: FastAPI) -> None:
    """
    Middleware registration order matters — middleware executes in reverse order.
    Last added = first to process the request.
    """
    # GZip: compresses responses > 1000 bytes (reduces bandwidth ~70%)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS: allow frontend origins to call the API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging: logs every request with timing
    app.add_middleware(RequestLoggingMiddleware)


def _register_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers for consistent error responses."""
    app.add_exception_handler(FiscalMindException, fiscalmind_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


def _register_routers(app: FastAPI) -> None:
    """Mounts all API routers under the versioned prefix."""
    app.include_router(api_router, prefix=settings.API_PREFIX)


# Application instance — imported by uvicorn
app = create_application()
