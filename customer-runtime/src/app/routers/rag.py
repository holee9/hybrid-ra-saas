"""POST /rag/query router — REQ-API-008, REQ-API-009."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_tenant, get_db
from app.schemas.rag import RagQueryRequest, RagQueryResponse
from app.services.rag import RagService

router = APIRouter(prefix="/rag", tags=["rag"])

_rag_service = RagService()


@router.post("/query", response_model=RagQueryResponse)
async def rag_query(
    payload: RagQueryRequest,
    tenant: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve and generate answer from requirements corpus.

    REQ-API-009: First response within 30 seconds (Ollama timeout = 25s).
    """
    result = await _rag_service.query(
        db=db,
        tenant_id=tenant,
        question=payload.question,
        product_id=payload.product_id,
        evidence_required=payload.evidence_required,
        top_k=payload.top_k,
    )
    return RagQueryResponse(**result)
