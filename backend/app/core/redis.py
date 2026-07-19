from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Singleton Redis connection pool
_redis_pool: aioredis.Redis | None = None


async def get_redis_client() -> aioredis.Redis:
    """
    Returns the shared Redis client with connection pooling.

    Why connection pooling?
    - Reusing connections is far cheaper than creating new TCP connections
    - Pool manages max_connections to prevent overwhelming Redis
    - decode_responses=True returns str instead of bytes everywhere
    """
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        logger.info("redis_connected", url=settings.REDIS_URL)
    return _redis_pool


async def close_redis() -> None:
    """Gracefully closes the Redis connection pool on app shutdown."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
        logger.info("redis_disconnected")


async def ping_redis() -> bool:
    """Health check: returns True if Redis is reachable."""
    try:
        client = await get_redis_client()
        await client.ping()
        return True
    except Exception as e:
        logger.error("redis_ping_failed", error=str(e))
        return False
