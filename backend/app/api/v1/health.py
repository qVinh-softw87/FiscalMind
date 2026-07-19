from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import engine
from app.core.redis import ping_redis

router = APIRouter(tags=["Health"])


class ServiceStatus(BaseModel):
    status: str        # "ok" | "degraded" | "down"
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    timestamp: str
    services: dict[str, ServiceStatus]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
    description="Returns status of all critical infrastructure services.",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint — used by:
    - Docker HEALTHCHECK directive
    - Load balancers (AWS ALB, Nginx)
    - Monitoring systems (Datadog, Prometheus)
    - CI/CD pipelines to verify deploy success

    Returns degraded status (not 500) when a non-critical service is down,
    so the app stays in the load balancer rotation and alerts are triggered separately.
    """
    import time

    services: dict[str, ServiceStatus] = {}

    # ── Check PostgreSQL ───────────────────────────────────────────────────────
    try:
        t0 = time.perf_counter()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_latency = round((time.perf_counter() - t0) * 1000, 2)
        services["database"] = ServiceStatus(status="ok", latency_ms=db_latency)
    except Exception as e:
        services["database"] = ServiceStatus(status="down", detail=str(e))

    # ── Check Redis ────────────────────────────────────────────────────────────
    try:
        t0 = time.perf_counter()
        redis_ok = await ping_redis()
        redis_latency = round((time.perf_counter() - t0) * 1000, 2)
        services["redis"] = ServiceStatus(
            status="ok" if redis_ok else "down",
            latency_ms=redis_latency,
        )
    except Exception as e:
        services["redis"] = ServiceStatus(status="down", detail=str(e))

    # Determine overall status
    all_ok = all(s.status == "ok" for s in services.values())
    overall = "ok" if all_ok else "degraded"

    return HealthResponse(
        status=overall,
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        timestamp=datetime.now(timezone.utc).isoformat(),
        services=services,
    )
