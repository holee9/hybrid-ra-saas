"""FastAPI application factory for cloud-control-plane."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.database import init_engine
from app.routers.crawl import router as crawl_router
from app.routers.health import router as health_router
from app.routers.product_profiles import router as product_profiles_router
from app.routers.template_packs import router as template_packs_router


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
    settings = Settings()

    app = FastAPI(
        title="Cloud Control Plane — RA Crawler",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS (GAP-01): allow Regula SaaS UI
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(crawl_router)
    app.include_router(product_profiles_router)
    app.include_router(template_packs_router)

    return app


# ASGI entry point
app = create_app()
