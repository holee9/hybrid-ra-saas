"""Async database engine and session factory.

Mirrors customer-runtime/src/app/database.py pattern:
module-level _engine/_session_factory replaced at app startup via init_engine().
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Module-level engine placeholder — replaced at app startup
_engine = None
_session_factory = None


def init_engine(database_url: str) -> None:
    """Initialize module-level engine and session factory.

    # @MX:ANCHOR: [AUTO] Called by lifespan on startup; must be called before any DB access.
    # @MX:REASON: All DB session dependencies (get_async_session) fail if this is not called.
    """
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an AsyncSession.

    Commits on success, rolls back on exception.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_engine() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
