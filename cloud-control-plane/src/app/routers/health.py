"""Health check endpoint — no authentication required (REQ-CRAWLER-014, AC-007)."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health", include_in_schema=True)
async def health() -> JSONResponse:
    """Return 200 OK with status: ok.

    Used by Container Apps liveness probe and deployment smoke tests.
    """
    return JSONResponse(content={"status": "ok"})
