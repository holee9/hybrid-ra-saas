"""FastAPI application factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.database import init_engine
from app.routers.health import router as health_router
from app.routers.documents import router as documents_router
from app.routers.parse import router as parse_router
from app.routers.guardrail import router as guardrail_router
from app.routers.rag import router as rag_router
from app.routers.audit import router as audit_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    settings = Settings()
    init_engine(settings.database_url)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = Settings()

    app = FastAPI(
        title="RA Customer Runtime",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(parse_router)
    app.include_router(guardrail_router)
    app.include_router(rag_router)
    app.include_router(audit_router)

    return app


# ASGI entry point
app = create_app()
