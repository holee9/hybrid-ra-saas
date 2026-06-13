"""Pathway resolver — matches ProductProfile to RegulatoryPathways and TemplatePacks.

# @MX:ANCHOR: [AUTO] Unsupported pathway guard
# @MX:REASON: [AUTO] HARD constraint: no speculative template generation
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applicability_rule import ApplicabilityRule
from app.models.product_profile import ProductProfile
from app.models.regulatory_pathway import RegulatoryPathway
from app.models.source_reference import SourceReference
from app.models.template_document import TemplateDocument
from app.models.template_pack import TemplatePack
from app.models.template_section import TemplateSection
from app.services.applicability import evaluate_rule


async def resolve_pathways(
    product_profile: ProductProfile, db: AsyncSession
) -> dict:
    """Match ProductProfile against RegulatoryPathways and return pack candidates.

    Returns a structured dict with:
    - matched_pathways, pack_candidates, applicable_documents,
      applicable_sections, excluded_sections, source_references

    If no pack exists: {"status": "unsupported", "reason": "No template pack found for pathway"}
    """
    target_markets: list[str] = product_profile.target_market or []

    # --- Find matching pathways ---
    if not target_markets:
        return {
            "status": "unsupported",
            "reason": "No template pack found for pathway",
        }

    pathway_result = await db.execute(
        select(RegulatoryPathway).where(RegulatoryPathway.market.in_(target_markets))
    )
    matched_pathways = pathway_result.scalars().all()

    if not matched_pathways:
        return {
            "status": "unsupported",
            "reason": "No template pack found for pathway",
        }

    pathway_ids = [p.pathway_id for p in matched_pathways]

    # --- Find pack candidates ---
    pack_query = select(TemplatePack).where(
        TemplatePack.pathway_id.in_(pathway_ids),
        TemplatePack.status == "active",
    )
    if product_profile.device_family:
        pack_query = pack_query.where(
            TemplatePack.device_family == product_profile.device_family
        )

    pack_result = await db.execute(pack_query)
    pack_candidates = pack_result.scalars().all()

    if not pack_candidates:
        return {
            "status": "unsupported",
            "reason": "No template pack found for pathway",
        }

    pack_ids = [p.pack_id for p in pack_candidates]

    # --- Load documents and sections for all packs ---
    doc_result = await db.execute(
        select(TemplateDocument).where(TemplateDocument.pack_id.in_(pack_ids))
    )
    all_documents = doc_result.scalars().all()
    doc_ids = [d.document_id for d in all_documents]

    section_result = await db.execute(
        select(TemplateSection).where(TemplateSection.document_id.in_(doc_ids))
    )
    all_sections = section_result.scalars().all()

    # --- Evaluate applicability rules ---
    applicable_sections = []
    excluded_sections = []

    rule_ids = [
        s.applicability_rule_id
        for s in all_sections
        if s.applicability_rule_id is not None
    ]
    rules_map: dict[str, ApplicabilityRule] = {}
    if rule_ids:
        rule_result = await db.execute(
            select(ApplicabilityRule).where(ApplicabilityRule.rule_id.in_(rule_ids))
        )
        rules_map = {r.rule_id: r for r in rule_result.scalars().all()}

    for section in all_sections:
        rule = rules_map.get(section.applicability_rule_id) if section.applicability_rule_id else None
        if evaluate_rule(rule, product_profile):
            applicable_sections.append(section)
        else:
            excluded_sections.append(
                {
                    "section_id": section.section_id,
                    "reason": f"ApplicabilityRule {section.applicability_rule_id} evaluated False",
                }
            )

    # --- Collect source references ---
    all_ref_ids: set[str] = set()
    for section in applicable_sections:
        if section.source_reference_ids:
            all_ref_ids.update(section.source_reference_ids)

    source_references = []
    if all_ref_ids:
        ref_result = await db.execute(
            select(SourceReference).where(SourceReference.ref_id.in_(list(all_ref_ids)))
        )
        source_references = ref_result.scalars().all()

    return {
        "matched_pathways": [
            {"pathway_id": p.pathway_id, "market": p.market, "authority": p.authority}
            for p in matched_pathways
        ],
        "pack_candidates": [
            {
                "pack_id": p.pack_id,
                "pathway_id": p.pathway_id,
                "device_family": p.device_family,
                "version": p.version,
            }
            for p in pack_candidates
        ],
        "applicable_documents": [
            {"document_id": d.document_id, "title": d.title, "doc_type": d.doc_type}
            for d in all_documents
        ],
        "applicable_sections": [
            {
                "section_id": s.section_id,
                "title": s.title,
                "is_internal": s.is_internal,
            }
            for s in applicable_sections
        ],
        "excluded_sections": excluded_sections,
        "source_references": [
            {"ref_id": r.ref_id, "regulation_name": r.regulation_name, "url": r.url}
            for r in source_references
        ],
    }
