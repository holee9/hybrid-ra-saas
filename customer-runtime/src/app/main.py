"""FastAPI application factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import Settings
from app.core.ratelimit import limiter, rate_limit_exceeded_handler
from app.database import init_engine
from app.routers.audit import router as audit_router
from app.routers.authoring import router as authoring_router
from app.routers.checklist import router as checklist_router
from app.routers.audit_decisions import router as audit_decisions_router
from app.routers.evidence import router as evidence_router
from app.routers.auth import router as auth_router
from app.routers.documents import router as documents_router
from app.routers.guardrail import router as guardrail_router
from app.routers.health import router as health_router
from app.routers.parse import router as parse_router
from app.routers.rag import router as rag_router
from app.routers.review_items import router as review_items_router
from app.routers.sync import router as sync_router
from app.routers.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    settings = Settings()
    init_engine(settings.database_url)
    # Tenant filter is registered in init_engine via database.py → register_tenant_filter
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = Settings()

    app = FastAPI(
        title="RA Customer Runtime",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Rate limiting (REQ-API-014): 100 req/min per tenant
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

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
    app.include_router(sync_router)
    # SPEC-PERMISSION-001: user auth + RBAC
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(review_items_router)
    app.include_router(audit_decisions_router)
    # SPEC-AUTHORING-001: Guided Authoring Workspace
    app.include_router(authoring_router)
    # SPEC-CHECKLIST-001: Checklist & Gap Engine
    app.include_router(checklist_router, prefix="/api/v1", tags=["checklists"])
    # SPEC-EVIDENCE-001: Evidence Binder
    app.include_router(evidence_router, prefix="/api/v1", tags=["evidence"])
    # SPEC-TRACEABILITY-001: Cross-Document Consistency Guardrail & Traceability Graph
    from app.routers.traceability import router as traceability_router
    app.include_router(traceability_router, prefix="/api/v1", tags=["traceability"])

    return app


# ASGI entry point
app = create_app()
