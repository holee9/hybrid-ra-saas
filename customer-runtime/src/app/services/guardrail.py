"""Guardrail service — REQ-API-007 rule engine and endpoint logic.

# @MX:ANCHOR: [AUTO] GuardrailService.run_guardrail — public API boundary called by router, tests, and future scheduling agents
# @MX:REASON: fan_in >= 3 (router, test_guardrail, future scheduler)
"""
import uuid
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.finding import Finding
from app.models.base import new_id


async def evaluate_document_rules(
    doc_id: str,
    requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Apply MVP rule set to a single document's requirement graph.

    Rules (placeholder — real NLP analysis is SPEC-PARSER-001 scope):
    - No requirements linked -> Medium finding
    - Requirements with no risk linkage -> High finding

    Returns list of finding dicts with severity, message, doc_id.
    """
    findings: list[dict[str, Any]] = []

    if not requirements:
        findings.append(
            {
                "severity": "Medium",
                "message": "Document has no linked requirements",
                "doc_id": doc_id,
                "evidence_links": [],
            }
        )
        return findings

    for req in requirements:
        if not req.get("risks"):
            findings.append(
                {
                    "severity": "High",
                    "message": "Requirement gap: no risk linkage",
                    "doc_id": doc_id,
                    "evidence_links": [],
                }
            )

    return findings


class GuardrailService:
    """Orchestrates guardrail rule evaluation across a document set."""

    async def run_guardrail(
        self,
        db: AsyncSession,
        tenant_id: str,
        user_id: str,
        product_id: str,
        doc_set_ids: list[str],
        rule_set_version: str,
        audit_service: Any,
    ) -> dict[str, Any]:
        """Run guardrail rules for doc_set_ids and return structured result.

        # @MX:NOTE: [AUTO] Persists Finding rows and triggers document status transition on High severity
        """
        run_id = str(uuid.uuid4())
        all_findings: list[dict[str, Any]] = []
        documents_flagged: list[str] = []

        # Load requirement graph for each document
        reqs_map = await self._load_documents_with_requirements(
            db=db,
            tenant_id=tenant_id,
            doc_set_ids=doc_set_ids,
        )

        for doc_id in doc_set_ids:
            reqs = reqs_map.get(doc_id, [])
            doc_findings = await evaluate_document_rules(doc_id=doc_id, requirements=reqs)

            # Persist Finding records
            for f in doc_findings:
                finding = Finding(
                    finding_id=new_id(),
                    tenant_id=tenant_id,
                    product_id=product_id,
                    severity=f["severity"],
                    message=f["message"],
                    evidence_links=f["evidence_links"],
                )
                db.add(finding)
                all_findings.append(
                    {
                        "finding_id": finding.finding_id,
                        "severity": f["severity"],
                        "message": f["message"],
                        "evidence_links": f["evidence_links"],
                    }
                )

            # High severity -> flag document
            has_high = any(f["severity"] == "High" for f in doc_findings)
            if has_high:
                await self._update_document_status_to_finding_open(
                    db=db,
                    doc_id=doc_id,
                    tenant_id=tenant_id,
                )
                documents_flagged.append(doc_id)

        # Record audit event
        await audit_service.record(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            action="guardrail.run",
        )

        await db.flush()

        return {
            "findings": all_findings,
            "run_id": run_id,
            "documents_flagged": documents_flagged,
        }

    async def _load_documents_with_requirements(
        self,
        db: AsyncSession,
        tenant_id: str,
        doc_set_ids: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        """Return mapping doc_id -> list of requirement dicts (with risk linkage).

        # @MX:NOTE: [AUTO] MVP returns empty requirements for all docs — real join is SPEC-PARSER-001 scope
        """
        # MVP: real requirement-risk join requires SPEC-PARSER-001 migration
        # Return empty for all requested docs so rule engine applies "no requirements" rule
        return {doc_id: [] for doc_id in doc_set_ids}

    async def _update_document_status_to_finding_open(
        self,
        db: AsyncSession,
        doc_id: str,
        tenant_id: str,
    ) -> None:
        """Set Document.status to finding_open for the given doc.

        # @MX:NOTE: [AUTO] finding_open is not in DocumentStatus enum — uses string to allow extension without migration
        """
        stmt = (
            update(Document)
            .where(Document.doc_id == doc_id, Document.tenant_id == tenant_id)
            .values(status="finding_open")  # type: ignore[arg-type]
        )
        await db.execute(stmt)
