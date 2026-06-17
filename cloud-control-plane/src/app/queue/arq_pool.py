"""arq Redis pool factory and FastAPI dependency for cloud-control-plane.

# @MX:ANCHOR: [AUTO] create_arq_pool — called by lifespan and crawl trigger endpoint
# @MX:REASON: Central Redis connection point for crawl job queue (AC-006)
"""

from __future__ import annotations

from arq import create_pool
from arq.connections import RedisSettings, ArqRedis
from fastapi import Request


async def create_arq_pool(redis_url: str) -> ArqRedis:
    """Create and return an arq Redis pool from a DSN string."""
    settings = RedisSettings.from_dsn(redis_url)
    return await create_pool(settings)


def get_arq_pool(request: Request) -> ArqRedis:
    """FastAPI Depends helper — returns pool from app.state.arq_pool."""
    return request.app.state.arq_pool
