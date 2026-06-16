"""Async database engine and session factory."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine_from_url(database_url: str):
    """Create an async SQLAlchemy engine from a URL."""
    return create_async_engine(database_url, echo=False, pool_pre_ping=True)


# Module-level engine placeholder — replaced at app startup
_engine = None
_session_factory = None


def init_engine(database_url: str) -> None:
    """Initialize module-level engine and session factory."""
    global _engine, _session_factory
    _engine = create_engine_from_url(database_url)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    from app.db.tenant_filter import register_tenant_filter
    register_tenant_filter(_session_factory)


@asynccontextmanager
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager yielding an AsyncSession."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_engine() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields AsyncSession."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_engine() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
