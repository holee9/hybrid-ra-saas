"""Template packs router — SPEC-TEMPLATE-001 pack registry endpoints.

# @MX:ANCHOR: [AUTO] POST /template-packs source_reference validation gate
# @MX:REASON: [AUTO] HARD constraint: regulatory sections without SourceRef must be rejected at registration
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.applicability_rule import ApplicabilityRule
from app.models.product_profile import ProductProfile
from app.models.regulatory_pathway import RegulatoryPathway
from app.models.source_reference import SourceReference
from app.models.template_document import TemplateDocument
from app.models.template_pack import TemplatePack
from app.models.template_section import TemplateSection
from app.schemas.checklist import ChecklistOut, ChecklistItemOut
from app.schemas.template_pack import (
    DocumentOut,
    PackDetail,
    PackSummary,
    ResolveRequest,
    SectionOut,
    SourceReferenceOut,
    TemplatePackCreate,
    TemplatePackCreateResponse,
)
from app.services.checklist_generator import generate_checklist
from app.services.pathway_resolver import resolve_pathways

router = APIRouter(prefix="/template-packs", tags=["template-packs"])


@router.post("/resolve")
async def resolve_template_packs(
    body: ResolveRequest,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Resolve applicable template packs for a product profile.

    # @MX:ANCHOR: [AUTO] Unsupported pathway guard
    # @MX:REASON: [AUTO] HARD constraint: no speculative template generation
    """
    profile: ProductProfile | None = None

    if body.product_id:
        profile = await db.get(ProductProfile, body.product_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="ProductProfile not found")
    elif body.product_profile:
        pp = body.product_profile
        import uuid
        profile = ProductProfile(
            product_id=str(uuid.uuid4()),
            device_name=pp.device_name,
            classification=pp.classification,
            intended_use=pp.intended_use,
            target_market=pp.target_market,
            technology_type=pp.technology_type,
            device_family=pp.device_family,
            software_in_device=pp.software_in_device,
        )
    else:
        raise HTTPException(status_code=400, detail="Either product_id or product_profile required")

    return await resolve_pathways(profile, db)


@router.get("", response_model=dict)
async def list_template_packs(
    market: str | None = Query(None),
    pathway_id: str | None = Query(None),
    device_family: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """List template packs with optional filters."""
    query = select(TemplatePack)

    if pathway_id:
        query = query.where(TemplatePack.pathway_id == pathway_id)
    if device_family:
        query = query.where(TemplatePack.device_family == device_family)
    if status:
        query = query.where(TemplatePack.status == status)

    if market:
        # Join through RegulatoryPathway to filter by market
        pathway_result = await db.execute(
            select(RegulatoryPathway.pathway_id).where(RegulatoryPathway.market == market)
        )
        market_pathway_ids = [row[0] for row in pathway_result.fetchall()]
        if not market_pathway_ids:
            return {"packs": []}
        query = query.where(TemplatePack.pathway_id.in_(market_pathway_ids))

    result = await db.execute(query)
    packs = result.scalars().all()

    return {
        "packs": [
            PackSummary.model_validate(p).model_dump()
            for p in packs
        ]
    }


@router.get("/{pack_id}", response_model=PackDetail)
async def get_template_pack(
    pack_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> PackDetail:
    """Get full detail of a TemplatePack including documents, sections, and source refs."""
    pack = await db.get(TemplatePack, pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="TemplatePack not found")

    # Load documents
    doc_result = await db.execute(
        select(TemplateDocument)
        .where(TemplateDocument.pack_id == pack_id)
        .order_by(TemplateDocument.sort_order)
    )
    documents = doc_result.scalars().all()
    doc_ids = [d.document_id for d in documents]

    # Load sections
    all_sections: list[TemplateSection] = []
    if doc_ids:
        sec_result = await db.execute(
            select(TemplateSection)
            .where(TemplateSection.document_id.in_(doc_ids))
            .order_by(TemplateSection.sort_order)
        )
        all_sections = sec_result.scalars().all()

    # Group sections by document_id
    sections_by_doc: dict[str, list[TemplateSection]] = {}
    for s in all_sections:
        sections_by_doc.setdefault(s.document_id, []).append(s)

    # Collect source reference IDs
    all_ref_ids: set[str] = set()
    for s in all_sections:
        if s.source_reference_ids:
            all_ref_ids.update(s.source_reference_ids)

    source_references: list[SourceReference] = []
    if all_ref_ids:
        ref_result = await db.execute(
            select(SourceReference).where(SourceReference.ref_id.in_(list(all_ref_ids)))
        )
        source_references = ref_result.scalars().all()

    return PackDetail(
        pack_id=pack.pack_id,
        pathway_id=pack.pathway_id,
        device_family=pack.device_family,
        version=pack.version,
        status=pack.status,
        documents=[
            DocumentOut(
                document_id=d.document_id,
                doc_type=d.doc_type,
                title=d.title,
                required=d.required,
                export_format=d.export_format,
                sort_order=d.sort_order,
                sections=[
                    SectionOut.model_validate(s)
                    for s in sections_by_doc.get(d.document_id, [])
                ],
            )
            for d in documents
        ],
        source_references=[SourceReferenceOut.model_validate(r) for r in source_references],
    )


@router.get("/{pack_id}/checklist", response_model=ChecklistOut)
async def get_checklist(
    pack_id: str,
    product_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> ChecklistOut:
    """Generate checklist for a pack+product pair."""
    if not product_id:
        raise HTTPException(status_code=400, detail="product_id query parameter is required")

    pack = await db.get(TemplatePack, pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="TemplatePack not found")

    result = await generate_checklist(pack_id, product_id, db)

    if "error" in result:
        if result["error"] == "product_not_found":
            raise HTTPException(status_code=404, detail="ProductProfile not found")
        raise HTTPException(status_code=500, detail="Checklist generation failed")

    return ChecklistOut(
        items=[ChecklistItemOut(**i) for i in result["items"]],
        required_count=result["required_count"],
        blocking_count=result["blocking_count"],
    )


@router.post("", response_model=TemplatePackCreateResponse, status_code=201)
async def create_template_pack(
    body: TemplatePackCreate,
    db: AsyncSession = Depends(get_async_session),
) -> TemplatePackCreateResponse:
    """Create a new TemplatePack (admin).

    Validates:
    - 409 if pack_id + version already exists
    - 400 if any non-internal section has empty source_reference_ids
    """
    # 409 check
    existing = await db.get(TemplatePack, body.pack_id)
    if existing is not None and existing.version == body.version:
        raise HTTPException(
            status_code=409, detail="TemplatePack with this pack_id and version already exists"
        )

    # [HARD] Validate source_reference_ids on non-internal sections
    for doc_data in body.documents:
        for section_data in doc_data.get("sections", []):
            is_internal = section_data.get("is_internal", False)
            source_ref_ids = section_data.get("source_reference_ids", [])
            if not is_internal and not source_ref_ids:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Section '{section_data.get('section_key', '?')}' is not internal "
                        "but has no source_reference_ids. All regulatory sections must cite sources."
                    ),
                )

    # Persist pack
    pack = TemplatePack(
        pack_id=body.pack_id,
        pathway_id=body.pathway_id,
        device_family=body.device_family,
        version=body.version,
        source_version=body.source_version,
        status=body.status,
    )
    db.add(pack)
    await db.flush()

    # Persist documents and sections
    for doc_data in body.documents:
        doc = TemplateDocument(
            document_id=doc_data["document_id"],
            pack_id=body.pack_id,
            doc_type=doc_data.get("doc_type", "general"),
            title=doc_data.get("title", ""),
            required=doc_data.get("required", True),
            export_format=doc_data.get("export_format"),
            sort_order=doc_data.get("sort_order", 0),
        )
        db.add(doc)
        await db.flush()

        for section_data in doc_data.get("sections", []):
            section = TemplateSection(
                section_id=section_data["section_id"],
                document_id=doc_data["document_id"],
                section_key=section_data.get("section_key", ""),
                title=section_data.get("title", ""),
                required=section_data.get("required", True),
                instructions=section_data.get("instructions"),
                placeholder=section_data.get("placeholder"),
                source_reference_ids=section_data.get("source_reference_ids", []),
                applicability_rule_id=section_data.get("applicability_rule_id"),
                is_internal=section_data.get("is_internal", False),
                sort_order=section_data.get("sort_order", 0),
            )
            db.add(section)

    await db.flush()
    return TemplatePackCreateResponse(pack_id=pack.pack_id, version=pack.version)
