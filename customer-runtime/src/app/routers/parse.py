"""Parse job router — GET /parse/jobs/{job_id} and PATCH /parse/{job_id}/corrections."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_tenant, get_db
from app.models.parse_job import ParseJob
from app.schemas.parse import (
    CorrectionsRequest,
    ExtractionStage,
    FieldExtraction,
    IFU_FIELD_NAMES,
    ParsedFields,
    ParseJobResponse,
)

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
