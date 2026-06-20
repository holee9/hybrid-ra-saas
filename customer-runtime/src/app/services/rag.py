"""RAG service — REQ-API-008, REQ-API-009, REQ-RAG-001 through REQ-RAG-007.

Embeds questions via sentence-transformers, searches pgvector, generates answers via Ollama.
Supports routing_mode: local-only | regula-only | hybrid (default).

# @MX:ANCHOR: [AUTO] RagService.query — public API boundary for RAG retrieval
# @MX:REASON: fan_in >= 3 (router, test_rag, future async job)
# @MX:NOTE: [AUTO] Ollama HTTP call retries up to OLLAMA_MAX_RETRIES times with exponential backoff
# @MX:NOTE: [AUTO] pgvector <=> cosine distance operator requires pgvector extension in PostgreSQL
# @MX:NOTE: [AUTO] Regula RAG endpoint — verify path with ra-med-bot team if changed
"""
import asyncio
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ollama_health import (
    OllamaUnavailableError,
    is_circuit_open,
    record_ollama_failure,
    record_ollama_success,
)

# Lazy import with graceful fallback
try:
    from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)

_EMBEDDING_DIM = 384
_EXECUTOR = ThreadPoolExecutor(max_workers=2)

# Simple in-memory embedding cache (process-local, TTL 1 hour)
# @MX:NOTE: [AUTO] Embedding cache — reduces sentence-transformers CPU load for repeated queries.
# Replace with Redis for multi-instance deployments.
_embedding_cache: dict[str, tuple[list[float], float]] = {}
EMBEDDING_CACHE_TTL = 3600  # 1 hour


def _get_cached_embedding(text: str) -> Optional[list[float]]:
    """Return cached embedding if present and not expired, else None."""
    if text in _embedding_cache:
        embedding, ts = _embedding_cache[text]
        if time.time() - ts < EMBEDDING_CACHE_TTL:
            return embedding
        del _embedding_cache[text]
    return None


def _set_cached_embedding(text: str, embedding: list[float]) -> None:
    """Store embedding in cache with current timestamp."""
    _embedding_cache[text] = (embedding, time.time())

OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
# Request timeout permits slow successful non-streamed responses; retry budget caps total SLA cost.
OLLAMA_TIMEOUT = 25.0
OLLAMA_RETRY_BUDGET = 28.0
OLLAMA_MAX_RETRIES = 3  # max attempts (initial + 2 retries) with exponential backoff

# Regula RAG API — REQ-RAG-003, REQ-RAG-006
REGULA_BASE_URL = os.environ.get("REGULA_BASE_URL", "https://regula.abyz-lab.work")
REGULA_API_KEY = os.environ.get("REGULA_API_KEY", "")
# @MX:NOTE: [AUTO] Regula RAG endpoint path — verify with ra-med-bot team if integration changes
REGULA_RAG_PATH = "/api/rag/query"
REGULA_TIMEOUT = 20.0  # REQ-RAG-006: 20s timeout


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
        routing_mode: str = "hybrid",
    ) -> dict[str, Any]:
        """Embed, search, generate, and return structured RAG response.

        REQ-RAG-001: routing_mode controls which backend serves the request.
        REQ-RAG-004: hybrid tries local first; falls back to Regula if confidence < 0.5.
        """
        if routing_mode == "regula-only":
            return await self._route_regula_only(question, top_k)

        if routing_mode == "local-only":
            return await self._route_local_only(
                db=db,
                tenant_id=tenant_id,
                question=question,
                product_id=product_id,
                evidence_required=evidence_required,
                top_k=top_k,
            )

        # hybrid (default)
        return await self._route_hybrid(
            db=db,
            tenant_id=tenant_id,
            question=question,
            product_id=product_id,
            evidence_required=evidence_required,
            top_k=top_k,
        )

    async def _route_local_only(
        self,
        db: AsyncSession,
        tenant_id: str,
        question: str,
        product_id: str | None,
        evidence_required: bool,
        top_k: int,
    ) -> dict[str, Any]:
        """REQ-RAG-002: local pgvector + Ollama only. routing_used='local'."""
        result = await self._local_query(
            db=db,
            tenant_id=tenant_id,
            question=question,
            product_id=product_id,
            evidence_required=evidence_required,
            top_k=top_k,
        )
        result["routing_used"] = "local"
        result["sources"] = result.get("evidence_links", [])
        return result

    async def _route_regula_only(self, question: str, top_k: int) -> dict[str, Any]:
        """REQ-RAG-003: Regula RAG API only. routing_used='regula' or 'degraded'."""
        regula = await self._call_regula_rag(question, top_k)
        if regula is None:
            # REQ-RAG-006: timeout/error -> degraded
            return {
                "answer": "Regula RAG service unavailable.",
                "evidence_links": [],
                "confidence": 0.0,
                "submit_safe": False,
                "routing_used": "degraded",
                "sources": [],
            }
        return {
            "answer": regula["answer"],
            "evidence_links": regula.get("sources", []),
            "confidence": regula["confidence"],
            "submit_safe": regula["confidence"] >= 0.5,
            "routing_used": "regula",
            "sources": regula.get("sources", []),
        }

    async def _route_hybrid(
        self,
        db: AsyncSession,
        tenant_id: str,
        question: str,
        product_id: str | None,
        evidence_required: bool,
        top_k: int,
    ) -> dict[str, Any]:
        """REQ-RAG-004: Try local first; fall back to Regula if confidence < 0.5.

        # @MX:WARN: [AUTO] Hybrid routing has 8 branches — confidence threshold controls fallback
        # @MX:REASON: REQ-RAG-004 requires conditional fallback; complexity is inherent in routing logic
        """
        local_ok = True
        try:
            local = await self._local_query(
                db=db,
                tenant_id=tenant_id,
                question=question,
                product_id=product_id,
                evidence_required=evidence_required,
                top_k=top_k,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Local RAG failed in hybrid mode: %s", exc)
            local_ok = False
            local = {"confidence": 0.0, "answer": "", "evidence_links": [], "submit_safe": False}

        if local_ok and local["confidence"] >= 0.5:
            local["routing_used"] = "hybrid-local"
            local["sources"] = local.get("evidence_links", [])
            return local

        # Attempt Regula fallback
        regula = await self._call_regula_rag(question, top_k)
        if regula is not None:
            return {
                "answer": regula["answer"],
                "evidence_links": regula.get("sources", []),
                "confidence": regula["confidence"],
                "submit_safe": regula["confidence"] >= 0.5,
                "routing_used": "hybrid-regula",
                "sources": regula.get("sources", []),
            }

        # Both failed — REQ-RAG-007
        if not local_ok:
            return {"all_failed": True, "answer": "", "evidence_links": [], "confidence": 0.0,
                    "submit_safe": False, "routing_used": "degraded", "sources": []}

        # Local had low confidence and Regula failed: return degraded local result
        local["routing_used"] = "hybrid-local"
        local["sources"] = local.get("evidence_links", [])
        return local

    async def _local_query(
        self,
        db: AsyncSession,
        tenant_id: str,
        question: str,
        product_id: str | None,
        evidence_required: bool,
        top_k: int,
    ) -> dict[str, Any]:
        """Core local RAG: embed → pgvector search → Ollama generation."""
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
        llm_available = False

        if evidence:
            context = "\n".join(e["text"] for e in evidence)
            prompt = f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
            try:
                answer = await self._call_ollama(prompt)
                confidence = min(1.0, sum(e.get("score", 0.5) for e in evidence) / len(evidence))
                llm_available = True
            except OllamaUnavailableError as exc:
                logger.warning("Ollama circuit open — skipping LLM call: %s", exc)
                req_ids = ", ".join(evidence_links)
                answer = f"LLM service unavailable (circuit open). Relevant evidence: {req_ids}"
                confidence = 0.0
            except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                logger.warning("Ollama unavailable after %d attempts: %s", OLLAMA_MAX_RETRIES, exc)
                req_ids = ", ".join(evidence_links)
                answer = f"LLM service unavailable. Relevant evidence: {req_ids}"
                confidence = 0.0
            except Exception as exc:  # noqa: BLE001
                logger.error("Unexpected Ollama error: %s", exc)
                answer = "LLM service unavailable"
                confidence = 0.0

        # Step 4: compute submit_safe — False when no evidence or LLM failed
        submit_safe = len(evidence_links) > 0 and llm_available
        if evidence_required and not evidence_links:
            submit_safe = False

        return {
            "answer": answer,
            "evidence_links": evidence_links,
            "confidence": confidence,
            "submit_safe": submit_safe,
        }

    async def _call_regula_rag(
        self,
        question: str,
        top_k: int,
    ) -> dict[str, Any] | None:
        """POST to Regula RAG API. Returns None on timeout or error (non-fatal).

        REQ-RAG-003, REQ-RAG-006: 20s timeout; non-blocking on failure.
        # @MX:NOTE: [AUTO] Regula RAG endpoint — verify path with ra-med-bot team
        """
        url = f"{REGULA_BASE_URL}{REGULA_RAG_PATH}"
        headers: dict[str, str] = {}
        if REGULA_API_KEY:
            headers["Authorization"] = f"Bearer {REGULA_API_KEY}"
        try:
            async with httpx.AsyncClient(timeout=REGULA_TIMEOUT) as client:
                resp = await client.post(
                    url,
                    json={"question": question, "top_k": top_k},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "answer": data.get("answer", ""),
                    "sources": data.get("sources", data.get("doc_ids", [])),
                    "confidence": float(data.get("confidence", 0.5)),
                }
        except httpx.TimeoutException:
            logger.warning("Regula RAG timeout after %.0fs for question: %.50s", REGULA_TIMEOUT, question)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Regula RAG call failed: %s", exc)
            return None

    async def _embed_question(self, question: str) -> list[float]:
        """Embed question using sentence-transformers in a thread pool.

        Checks in-memory cache first; falls back to zero vector if
        sentence_transformers is unavailable.
        """
        cached = _get_cached_embedding(question)
        if cached is not None:
            return cached

        if SentenceTransformer is None:
            return [0.0] * _EMBEDDING_DIM

        loop = asyncio.get_event_loop()
        try:
            def _encode():
                model = SentenceTransformer("all-MiniLM-L6-v2")
                return model.encode(question).tolist()

            embedding = await loop.run_in_executor(_EXECUTOR, _encode)
            _set_cached_embedding(question, embedding)
            return embedding
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
        """POST to Ollama generate endpoint with retry, exponential backoff, and circuit breaker.

        Checks circuit breaker before each attempt. Records failures/successes to update state.
        Retries on timeout and 5xx errors. Raises on 4xx or after OLLAMA_MAX_RETRIES exhausted.

        # @MX:ANCHOR: [AUTO] Ollama retry entrypoint — callers expect TimeoutException or HTTPStatusError on exhaustion
        # @MX:REASON: fan_in >= 2 (query method, tests); retry contract must be stable
        """
        # Fast-fail: circuit open means Ollama is presumed down
        if is_circuit_open():
            raise OllamaUnavailableError("Ollama circuit breaker is open — skipping call")

        last_exc: Exception | None = None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + OLLAMA_RETRY_BUDGET

        for attempt in range(OLLAMA_MAX_RETRIES):
            if attempt > 0:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    break
                await asyncio.sleep(min(2 ** (attempt - 1), remaining))  # 1s, 2s backoff

            remaining = deadline - loop.time()
            if remaining <= 0:
                break

            try:
                async with httpx.AsyncClient(timeout=min(OLLAMA_TIMEOUT, remaining)) as client:
                    resp = await client.post(
                        f"{OLLAMA_ENDPOINT}/api/generate",
                        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                    )
                    resp.raise_for_status()
                    record_ollama_success()
                    return resp.json().get("response", "")
            except httpx.TimeoutException as exc:
                logger.warning("Ollama timeout (attempt %d/%d)", attempt + 1, OLLAMA_MAX_RETRIES)
                record_ollama_failure()
                last_exc = exc
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500:
                    logger.warning(
                        "Ollama %d error (attempt %d/%d)",
                        exc.response.status_code, attempt + 1, OLLAMA_MAX_RETRIES,
                    )
                    record_ollama_failure()
                    last_exc = exc
                else:
                    raise  # 4xx — not retryable
        if last_exc is not None:
            raise last_exc
        raise httpx.TimeoutException("Ollama retry budget exhausted")
