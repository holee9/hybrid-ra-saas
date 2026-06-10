"""FastAPI application factory for cloud-control-plane."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings
from app.database import init_engine
from app.routers.crawl import router as crawl_router
from app.routers.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup (REQ-CRAWLER-003, T-003)."""
    settings = Settings()
    init_engine(settings.database_url)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    # @MX:ANCHOR: [AUTO] Public factory used by uvicorn entrypoint and test fixtures.
    # @MX:REASON: Called by entrypoint.sh (uvicorn app.main:app) and conftest.py.
    """
    app = FastAPI(
        title="Cloud Control Plane — RA Crawler",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health_router)
    app.include_router(crawl_router)

    return app


# ASGI entry point
app = create_app()
