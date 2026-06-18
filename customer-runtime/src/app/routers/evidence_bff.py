"""Evidence BFF router — Issue #47.

Thin BFF wrapper exposing collect / get / synthesize / export for ra-med-bot.

# @MX:ANCHOR: [AUTO] Evidence BFF public API boundary — 4 endpoints consumed by ra-med-bot.
# @MX:REASON: fan_in >= 3 (ra-med-bot client, test_evidence_bff, future async worker)
"""
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_hybrid_bearer_token
from app.deps import get_db
from app.models.evidence_collect import EvidenceCollect
from app.services.rag import OLLAMA_ENDPOINT, OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_MAX_RETRIES

router = APIRouter(prefix="/evidence", tags=["evidence-bff"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CollectRequest(BaseModel):
    document_ids: list[str]
    query: str
    evidence_type: str
    max_results: int = Field(default=20, ge=1, le=100)


class CollectItem(BaseModel):
    req_id: str
    text: str
    score: float


class CollectResponse(BaseModel):
    collect_id: str
    status: str
    items: list[dict[str, Any]]
    created_at: datetime


class SynthesizeResponse(BaseModel):
    collect_id: str
    synthesis: str
    status: str


class ExportResponse(BaseModel):
    collect_id: str
    items: list[dict[str, Any]]
    synthesis: str | None
    exported_at: datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_collect_or_404(collect_id: str, db: AsyncSession) -> EvidenceCollect:
    result = await db.execute(
        select(EvidenceCollect).where(EvidenceCollect.collect_id == collect_id)
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="collect_id not found")
    return obj


async def _call_ollama_simple(prompt: str) -> str:
    """Call Ollama for synthesis/review. Returns text or raises on failure.

    # @MX:NOTE: [AUTO] Simplified Ollama call without retry budget — BFF endpoints
    #           accept 503 on LLM failure rather than retrying.
    """
    import asyncio

    last_exc: Exception | None = None
    for attempt in range(OLLAMA_MAX_RETRIES):
        if attempt > 0:
            await asyncio.sleep(2 ** (attempt - 1))
        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
                resp = await client.post(
                    f"{OLLAMA_ENDPOINT}/api/generate",
                    json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                )
                resp.raise_for_status()
                return resp.json().get("response", "")
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            last_exc = exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="LLM service error",
            ) from exc
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="LLM service unavailable",
    ) from last_exc


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/collect", response_model=CollectResponse, status_code=status.HTTP_201_CREATED)
async def collect_evidence(
    body: CollectRequest,
    tenant_id: str = Depends(verify_hybrid_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> CollectResponse:
    """Search documents by vector similarity and store results."""
    from app.services.rag import RagService

    svc = RagService()
    # Use RAG similarity search for the query
    rag_result = await svc.query(
        db=db,
        tenant_id=tenant_id,
        question=body.query,
        product_id=None,
        evidence_required=False,
        top_k=body.max_results,
    )

    items = [
        {"req_id": req_id, "text": "", "score": 0.0}
        for req_id in rag_result.get("evidence_links", [])
    ]

    collect = EvidenceCollect(
        collect_id=str(uuid.uuid4()),
        query=body.query,
        evidence_type=body.evidence_type,
        document_ids=body.document_ids,
        items=items,
        status="collected",
    )
    db.add(collect)
    await db.commit()
    await db.refresh(collect)

    return CollectResponse(
        collect_id=collect.collect_id,
        status=collect.status,
        items=collect.items,
        created_at=collect.created_at,
    )


@router.get("/{collect_id}", response_model=CollectResponse)
async def get_collect(
    collect_id: str,
    tenant_id: str = Depends(verify_hybrid_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> CollectResponse:
    """Retrieve stored collect result."""
    obj = await _get_collect_or_404(collect_id, db)
    return CollectResponse(
        collect_id=obj.collect_id,
        status=obj.status,
        items=obj.items,
        created_at=obj.created_at,
    )


@router.post("/{collect_id}/synthesize", response_model=SynthesizeResponse)
async def synthesize_collect(
    collect_id: str,
    tenant_id: str = Depends(verify_hybrid_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> SynthesizeResponse:
    """LLM synthesis of collected items into a summary paragraph."""
    obj = await _get_collect_or_404(collect_id, db)

    if not obj.items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No items to synthesize",
        )

    context_lines = "\n".join(
        item.get("text", item.get("req_id", "")) for item in obj.items
    )
    prompt = (
        f"Evidence type: {obj.evidence_type}\n"
        f"Query: {obj.query}\n\n"
        f"Evidence items:\n{context_lines}\n\n"
        "Write a concise summary paragraph synthesizing the above evidence:"
    )

    synthesis_text = await _call_ollama_simple(prompt)

    obj.synthesis = synthesis_text
    obj.status = "synthesized"
    await db.commit()
    await db.refresh(obj)

    return SynthesizeResponse(
        collect_id=obj.collect_id,
        synthesis=synthesis_text,
        status="synthesized",
    )


@router.get("/{collect_id}/export", response_model=ExportResponse)
async def export_collect(
    collect_id: str,
    tenant_id: str = Depends(verify_hybrid_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> ExportResponse:
    """Export collected evidence as JSON."""
    obj = await _get_collect_or_404(collect_id, db)
    return ExportResponse(
        collect_id=obj.collect_id,
        items=obj.items,
        synthesis=obj.synthesis,
        exported_at=_now(),
    )
