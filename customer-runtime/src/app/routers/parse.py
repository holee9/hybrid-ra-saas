"""Parse job router — GET /parse/jobs, GET /parse/jobs/{job_id}, PATCH /parse/{job_id}/corrections."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_tenant, get_db
from app.models.parse_job import ParseJob, ParseJobStatus
from app.schemas.parse import (
    CorrectionsRequest,
    ExtractionStage,
    FieldExtraction,
    IFU_FIELD_NAMES,
    JobSummary,
    ListJobsResponse,
    ParsedFields,
    ParseJobResponse,
)

router = APIRouter(prefix="/parse", tags=["parse"])

# Valid status values for whitelist validation
_VALID_STATUSES: frozenset[str] = frozenset(s.value for s in ParseJobStatus)


def _extract_summary_fields(result_json: dict | None) -> tuple[float | None, bool]:
    """Safely extract overall_confidence and requires_correction from result_json.

    Handles None, missing 'parsed_fields' key, and partial data gracefully.
    Returns (None, False) when data is unavailable (e.g. pending/running jobs).
    """
    if not result_json:
        return None, False
    pf = result_json.get("parsed_fields") or {}
    return pf.get("overall_confidence"), bool(pf.get("requires_correction", False))


# @MX:ANCHOR: [AUTO] list_parse_jobs — public tenant-scoped list API
# @MX:REASON: fan_in >= 3 (QueuePage, useListJobs, test suites). Tenant isolation must not be weakened.
@router.get("/jobs", response_model=ListJobsResponse)
async def list_parse_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    requires_correction: bool | None = Query(None),
    tenant: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated list of parse jobs for the current tenant.

    Query params:
    - skip: offset (default 0)
    - limit: page size (default 50, max 200)
    - status: filter by status — must be one of pending/running/done/failed
    - requires_correction: filter by correction flag (PostgreSQL JSON operator)
    """
    # Validate status whitelist
    if status is not None and status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{status}'. Allowed: {sorted(_VALID_STATUSES)}",
        )

    # Base where clause: tenant scope (mandatory)
    filters = [ParseJob.tenant_id == tenant]
    if status is not None:
        filters.append(ParseJob.status == ParseJobStatus(status))

    # requires_correction filter using PostgreSQL JSON path operator
    if requires_correction is not None:
        # Cast JSON boolean: result_json->'parsed_fields'->'requires_correction'
        json_flag = ParseJob.result_json["parsed_fields"]["requires_correction"].as_boolean()
        if requires_correction:
            filters.append(json_flag.is_(True))
        else:
            filters.append(json_flag.is_(False))

    # Count query (total matching rows, ignoring skip/limit)
    count_stmt = select(func.count()).select_from(ParseJob).where(*filters)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Data query: ordered by created_at desc, paginated
    data_stmt = (
        select(ParseJob)
        .where(*filters)
        .order_by(ParseJob.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(data_stmt)
    jobs = result.scalars().all()

    items = []
    for job in jobs:
        confidence, req_correction = _extract_summary_fields(job.result_json)
        items.append(
            JobSummary(
                job_id=job.job_id,
                doc_id=job.doc_id,
                status=job.status.value,
                overall_confidence=confidence,
                requires_correction=req_correction,
                created_at=job.created_at,
                error=job.error,
            )
        )

    return ListJobsResponse(items=items, total=total, skip=skip, limit=limit)


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


def _apply_correction(parsed_fields: ParsedFields, field: str, new_value: str) -> ParsedFields:
    """Apply a human correction to a single field.

    Sets confidence=1.0, stage=NONE, needs_correction=False for the corrected field.
    Recomputes overall_confidence and requires_correction.
    """
    from app.services.parser_engine.confidence import overall

    # Build updated fields dict
    fields_dict = {name: getattr(parsed_fields, name) for name in IFU_FIELD_NAMES}
    fields_dict[field] = FieldExtraction(
        value=new_value,
        confidence=1.0,
        stage=ExtractionStage.NONE,
        needs_correction=False,
    )

    # Rebuild ParsedFields for overall calculation
    tmp = ParsedFields(
        overall_confidence=0.0,
        **fields_dict,
    )
    new_overall = overall(tmp)
    new_requires_correction = any(
        fields_dict[f].needs_correction for f in IFU_FIELD_NAMES
    )

    return ParsedFields(
        overall_confidence=new_overall,
        requires_correction=new_requires_correction,
        rejected=parsed_fields.rejected,
        **fields_dict,
    )


# @MX:NOTE: [AUTO] PATCH corrections endpoint — applies human review corrections to parsed fields
@router.patch("/{job_id}/corrections", response_model=ParseJobResponse)
async def patch_corrections(
    job_id: str,
    body: CorrectionsRequest,
    tenant: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Apply human corrections to parsed fields of a completed parse job.

    Only IFU_FIELD_NAMES fields are accepted. Unknown fields return 422.
    """
    job = await db.get(ParseJob, job_id)
    if job is None or job.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Parse job not found")

    result_json = job.result_json or {}
    parsed_fields_data = result_json.get("parsed_fields")
    if not parsed_fields_data:
        raise HTTPException(status_code=400, detail="No parsed fields available for this job")

    parsed_fields = ParsedFields.model_validate(parsed_fields_data)

    # Apply each correction sequentially
    for field, new_value in body.corrections.items():
        parsed_fields = _apply_correction(parsed_fields, field, new_value)

    # Persist updated parsed_fields back
    result_json["parsed_fields"] = parsed_fields.model_dump()
    job.result_json = result_json
    await db.commit()
    await db.refresh(job)

    return ParseJobResponse(
        job_id=job.job_id,
        status=job.status.value,
        confidence=parsed_fields.overall_confidence,
        parsed_fields=parsed_fields,
    )
