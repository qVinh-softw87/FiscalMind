from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    analysis,
    auth,
    benchmarks,
    chat,
    comparison,
    dashboard,
    documents,
    health,
    insights,
)

# API v1 router — aggregates all v1 sub-routers
# Adding a new domain module:
#   from app.api.v1 import documents
#   api_router.include_router(documents.router, prefix="/documents")

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(analysis.router)
api_router.include_router(insights.router)
api_router.include_router(dashboard.router)
api_router.include_router(comparison.router)
api_router.include_router(benchmarks.router)
