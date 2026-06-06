"""GET /parse/jobs/{job_id} endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_tenant, get_db
from app.models.parse_job import ParseJob
from app.schemas.parse import ParseJobResponse

router = APIRouter(prefix="/parse", tags=["parse"])


@router.get("/jobs/{job_id}", response_model=ParseJobResponse)
async def get_parse_job(
    job_id: str,
    tenant: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Return the status and result of a parse job."""
    job = await db.get(ParseJob, job_id)
    if job is None or job.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Parse job not found")

    result = job.result_json or {}
    return ParseJobResponse(
        job_id=job.job_id,
        status=job.status.value,
        field_candidates=result.get("field_candidates"),
        confidence=result.get("confidence"),
        required_missing=result.get("required_missing"),
    )
