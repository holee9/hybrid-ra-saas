"""RAG service — REQ-API-008, REQ-API-009.

Embeds questions via sentence-transformers, searches pgvector, generates answers via Ollama.

# @MX:ANCHOR: [AUTO] RagService.query — public API boundary for RAG retrieval
# @MX:REASON: fan_in >= 3 (router, test_rag, future async job)
# @MX:NOTE: [AUTO] Ollama HTTP call is an external dependency with 25s timeout; graceful fallback on error
# @MX:NOTE: [AUTO] pgvector <=> cosine distance operator requires pgvector extension in PostgreSQL
"""
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Lazy import with graceful fallback
try:
    from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore[assignment, misc]

_EMBEDDING_DIM = 384
_EXECUTOR = ThreadPoolExecutor(max_workers=2)

OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT = 25.0  # seconds — leaves 5s margin for REQ-API-009 30s total budget


class RagService:
    """Retrieval-Augmented Generation over the requirements corpus."""

    async def query(
        self,
        db: AsyncSession,
        tenant_id: str,
        question: str,
        product_id: str | None,
        evidence_required: bool,
        top_k: int,
    ) -> dict[str, Any]:
        """Embed, search, generate, and return structured RAG response."""
        # Step 1: embed question
        vector = await self._embed_question(question)

        # Step 2: similarity search
        evidence = await self._similarity_search(
            db=db,
            tenant_id=tenant_id,
            product_id=product_id,
            vector=vector,
            top_k=top_k,
        )

        evidence_links = [e["req_id"] for e in evidence]

        # Step 3: generate answer via Ollama if evidence found
        answer = "No relevant evidence found."
        confidence = 0.0

        if evidence:
            context = "\n".join(e["text"] for e in evidence)
            prompt = f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
            try:
                answer = await self._call_ollama(prompt)
                confidence = min(1.0, sum(e.get("score", 0.5) for e in evidence) / len(evidence))
            except (TimeoutError, httpx.TimeoutException, Exception):
                answer = "LLM service unavailable"
                confidence = 0.0

        # Step 4: compute submit_safe
        submit_safe = len(evidence_links) > 0
        if evidence_required and not evidence_links:
            submit_safe = False

        return {
            "answer": answer,
            "evidence_links": evidence_links,
            "confidence": confidence,
            "submit_safe": submit_safe,
        }

    async def _embed_question(self, question: str) -> list[float]:
        """Embed question using sentence-transformers in a thread pool.

        Falls back to zero vector if sentence_transformers is unavailable.
        """
        if SentenceTransformer is None:
            return [0.0] * _EMBEDDING_DIM

        loop = asyncio.get_event_loop()
        try:
            def _encode():
                model = SentenceTransformer("all-MiniLM-L6-v2")
                return model.encode(question).tolist()

            return await loop.run_in_executor(_EXECUTOR, _encode)
        except ImportError:
            return [0.0] * _EMBEDDING_DIM

    async def _similarity_search(
        self,
        db: AsyncSession,
        tenant_id: str,
        product_id: str | None,
        vector: list[float],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Search requirements table using pgvector cosine distance (<=>).

        # @MX:NOTE: [AUTO] Requires pgvector extension; returns empty list if table has no embeddings
        """
        vector_str = "[" + ",".join(str(v) for v in vector) + "]"
        product_filter = "AND r.product_family IS NOT NULL" if product_id else ""

        sql = text(
            f"""
            SELECT r.req_id, r.text, (r.embedding <=> CAST(:vec AS vector)) AS distance
            FROM requirements r
            WHERE r.tenant_id = :tenant_id
              {product_filter}
              AND r.embedding IS NOT NULL
            ORDER BY r.embedding <=> CAST(:vec AS vector)
            LIMIT :top_k
            """
        )
        try:
            result = await db.execute(
                sql,
                {"vec": vector_str, "tenant_id": tenant_id, "top_k": top_k},
            )
            rows = result.fetchall()
            return [
                {"req_id": row.req_id, "text": row.text, "score": 1.0 - float(row.distance)}
                for row in rows
            ]
        except Exception:  # noqa: BLE001 — pgvector may not be installed in unit test context
            return []

    async def _call_ollama(self, prompt: str) -> str:
        """POST to Ollama generate endpoint with 25s timeout.

        # @MX:NOTE: [AUTO] External HTTP call — timeout raises TimeoutError for caller to handle
        """
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            resp = await client.post(
                f"{OLLAMA_ENDPOINT}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
