"""RAG schemas — request/response models for POST /rag/query."""
from pydantic import BaseModel, Field


class RagQueryRequest(BaseModel):
    question: str
    product_id: str | None = None
    evidence_required: bool = False
    top_k: int = Field(default=5, ge=1, le=20)


class RagQueryResponse(BaseModel):
    answer: str
    evidence_links: list[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    submit_safe: bool
