"""POST /guardrail/run router — REQ-API-007."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_hybrid_bearer_token
from app.deps import get_db
from app.schemas.guardrail import GuardrailRunRequest, GuardrailRunResponse, FindingOut
from app.services.audit import AuditService
from app.services.guardrail import GuardrailService

router = APIRouter(prefix="/guardrail", tags=["guardrail"])

_audit_service = AuditService()
_guardrail_service = GuardrailService()


@router.post("/run", response_model=GuardrailRunResponse)
async def run_guardrail(
    payload: GuardrailRunRequest,
    tenant: str = Depends(verify_hybrid_bearer_token),
    db: AsyncSession = Depends(get_db),
):
    """Run guardrail rule engine over a document set.

    Returns findings and flags documents with High severity findings.
    """
    result = await _guardrail_service.run_guardrail(
        db=db,
        tenant_id=tenant,
        user_id="system",  # extracted from token in future iteration
        product_id=payload.product_id,
        doc_set_ids=payload.doc_set_ids,
        rule_set_version=payload.rule_set_version,
        audit_service=_audit_service,
    )

    findings_out = [
        FindingOut(
            finding_id=f["finding_id"],
            severity=f["severity"],
            message=f["message"],
            evidence_links=f["evidence_links"],
        )
        for f in result["findings"]
    ]

    return GuardrailRunResponse(
        findings=findings_out,
        run_id=result["run_id"],
        documents_flagged=result["documents_flagged"],
    )
