"""arq Redis pool factory and FastAPI dependency injection.

# @MX:ANCHOR: [AUTO] create_arq_pool — called by lifespan, upload endpoint, and worker
# @MX:REASON: fan_in >= 3 (main.py lifespan, documents.py enqueue, worker.py startup)
"""

from __future__ import annotations

from arq import create_pool
from arq.connections import RedisSettings, ArqRedis
from fastapi import Request


async def create_arq_pool(redis_url: str) -> ArqRedis:
    """Create and return an arq Redis pool from a DSN string.

    # @MX:ANCHOR: [AUTO] Public pool factory — injected into app.state.arq_pool
    # @MX:REASON: Central Redis connection point; referenced by lifespan, router, worker
    """
    settings = RedisSettings.from_dsn(redis_url)
    return await create_pool(settings)


def get_arq_pool(request: Request) -> ArqRedis:
    """FastAPI Depends helper — returns pool from app.state.arq_pool."""
    return request.app.state.arq_pool
