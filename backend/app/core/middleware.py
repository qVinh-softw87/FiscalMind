from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every incoming HTTP request with:
    - Method, path, status code
    - Response time in milliseconds
    - Request ID for distributed tracing

    Why middleware?
    - Cross-cutting concern: applies to ALL routes without touching each handler
    - Runs before and after every request lifecycle
    """

    SKIP_PATHS = {"/health", "/metrics", "/favicon.ico"}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()

        # Bind request-scoped context to all log lines in this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.info(
            "http_request",
            status_code=response.status_code,
            duration_ms=elapsed_ms,
        )

        # Expose response time in headers for client-side debugging
        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"

        return response
