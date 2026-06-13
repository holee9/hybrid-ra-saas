"""Checklist generator — creates ChecklistItems from TemplateSections for a pack+product."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applicability_rule import ApplicabilityRule
from app.models.checklist_item import ChecklistItem
from app.models.product_profile import ProductProfile
from app.models.template_document import TemplateDocument
from app.models.template_pack import TemplatePack
from app.models.template_section import TemplateSection
from app.services.applicability import evaluate_rule


async def generate_checklist(
    pack_id: str, product_id: str, db: AsyncSession
) -> dict:
    """Generate checklist items for a (pack_id, product_id) pair.

    Evaluates applicability rules per section.
    Returns: {checklist_id, items[], required_count, blocking_count}
    """
    # Validate pack exists
    pack = await db.get(TemplatePack, pack_id)
    if pack is None:
        return {"error": "pack_not_found"}

    # Validate product exists
    profile = await db.get(ProductProfile, product_id)
    if profile is None:
        return {"error": "product_not_found"}

    # Load all documents for this pack
    doc_result = await db.execute(
        select(TemplateDocument).where(TemplateDocument.pack_id == pack_id)
    )
    doc_ids = [d.document_id for d in doc_result.scalars().all()]

    if not doc_ids:
        return {
            "checklist_id": str(uuid.uuid4()),
            "items": [],
            "required_count": 0,
            "blocking_count": 0,
        }

    # Load all sections
    section_result = await db.execute(
        select(TemplateSection).where(TemplateSection.document_id.in_(doc_ids))
    )
    sections = section_result.scalars().all()

    # Load rules
    rule_ids = [s.applicability_rule_id for s in sections if s.applicability_rule_id]
    rules_map: dict[str, ApplicabilityRule] = {}
    if rule_ids:
        rule_result = await db.execute(
            select(ApplicabilityRule).where(ApplicabilityRule.rule_id.in_(rule_ids))
        )
        rules_map = {r.rule_id: r for r in rule_result.scalars().all()}

    items = []
    for section in sections:
        rule = rules_map.get(section.applicability_rule_id) if section.applicability_rule_id else None
        if not evaluate_rule(rule, profile):
            continue  # excluded — skip

        item = ChecklistItem(
            checklist_item_id=str(uuid.uuid4()),
            section_id=section.section_id,
            status="not_started",
            blocking=section.required,
            evidence_required=bool(section.source_reference_ids),
        )
        items.append(item)

    required_count = sum(1 for i in items if i.blocking)
    blocking_count = sum(1 for i in items if i.blocking)

    return {
        "checklist_id": str(uuid.uuid4()),
        "items": [
            {
                "checklist_item_id": i.checklist_item_id,
                "section_id": i.section_id,
                "status": i.status,
                "blocking": i.blocking,
                "evidence_required": i.evidence_required,
            }
            for i in items
        ],
        "required_count": required_count,
        "blocking_count": blocking_count,
    }
