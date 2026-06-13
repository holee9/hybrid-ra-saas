"""TDD tests for SPEC-TEMPLATE-001 — Regulatory Template Pack Registry.

AC-001 through AC-012 coverage.
Uses SQLite in-memory — no Docker required.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def template_client():
    """Create test client with SQLite in-memory DB and all SPEC-TEMPLATE-001 models."""
    from unittest.mock import MagicMock, patch

    fake_settings = MagicMock()
    fake_settings.database_url = TEST_DB_URL
    fake_settings.cors_origins_list = []
    fake_settings.crawler_fda_enabled = False
    fake_settings.crawler_mfds_enabled = False
    fake_settings.crawler_eu_mdr_enabled = False

    with patch("app.config.Settings", return_value=fake_settings):
        with patch("app.main.Settings", return_value=fake_settings):
            with patch("app.database.init_engine"):
                from app.main import create_app
                from app.database import get_async_session
                from app.models.base import Base

                # Register all models with Base
                from app.models import (  # noqa: F401
                    ProductProfile,
                    RegulatoryPathway,
                    TemplatePack,
                    TemplateDocument,
                    ApplicabilityRule,
                    TemplateSection,
                    SourceReference,
                    ChecklistItem,
                )

                engine = create_async_engine(
                    TEST_DB_URL, connect_args={"check_same_thread": False}
                )
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

                session_factory = async_sessionmaker(engine, expire_on_commit=False)

                async def override_get_db():
                    async with session_factory() as session:
                        try:
                            yield session
                            await session.commit()
                        except Exception:
                            await session.rollback()
                            raise

                fastapi_app = create_app()
                fastapi_app.dependency_overrides[get_async_session] = override_get_db

                async with AsyncClient(
                    transport=ASGITransport(app=fastapi_app), base_url="http://test"
                ) as ac:
                    yield ac, session_factory

                fastapi_app.dependency_overrides.clear()
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
                await engine.dispose()


# ---------------------------------------------------------------------------
# Helpers to pre-seed test data
# ---------------------------------------------------------------------------

async def _seed_pathway(session_factory, pathway_id="US-FDA-510K", market="US"):
    from app.models.regulatory_pathway import RegulatoryPathway

    async with session_factory() as session:
        session.add(
            RegulatoryPathway(
                pathway_id=pathway_id,
                market=market,
                authority="FDA",
                submission_type="510k",
                device_class="Class II",
                applicable_standards=["ISO 13485"],
            )
        )
        await session.commit()


async def _seed_pack(session_factory, pack_id="PACK-001", pathway_id="US-FDA-510K",
                     device_family="X-ray System", status="active"):
    from app.models.template_pack import TemplatePack

    async with session_factory() as session:
        session.add(
            TemplatePack(
                pack_id=pack_id,
                pathway_id=pathway_id,
                device_family=device_family,
                version="1.0",
                status=status,
            )
        )
        await session.commit()


async def _seed_source_ref(session_factory, ref_id="SRC-001"):
    from app.models.source_reference import SourceReference

    async with session_factory() as session:
        session.add(
            SourceReference(
                ref_id=ref_id,
                regulation_name="Test Regulation",
                article="Art 1",
                url="https://example.com/reg",
            )
        )
        await session.commit()


async def _seed_full_pack_with_sections(
    session_factory,
    pack_id="PACK-FULL",
    pathway_id="US-FDA-510K",
    software_in_device_rule=False,
):
    """Seed a full pack with documents, sections, and optionally a SW applicability rule."""
    from app.models.applicability_rule import ApplicabilityRule
    from app.models.source_reference import SourceReference
    from app.models.template_document import TemplateDocument
    from app.models.template_pack import TemplatePack
    from app.models.template_section import TemplateSection

    async with session_factory() as session:
        session.add(
            SourceReference(
                ref_id="SRC-TEST-001",
                regulation_name="Test Reg",
                url="https://example.com",
            )
        )
        session.add(
            TemplatePack(
                pack_id=pack_id,
                pathway_id=pathway_id,
                device_family="X-ray System",
                version="1.0",
                status="active",
            )
        )
        await session.flush()

        session.add(
            TemplateDocument(
                document_id=f"{pack_id}-DOC-001",
                pack_id=pack_id,
                doc_type="design_history_file",
                title="Design History File",
                required=True,
                sort_order=1,
            )
        )
        await session.flush()

        # Non-SW section — always applicable
        session.add(
            TemplateSection(
                section_id=f"{pack_id}-SEC-001",
                document_id=f"{pack_id}-DOC-001",
                section_key="device_description",
                title="Device Description",
                required=True,
                source_reference_ids=["SRC-TEST-001"],
                is_internal=False,
                sort_order=1,
            )
        )

        if software_in_device_rule:
            # Add applicability rule: only when software_in_device == true
            session.add(
                ApplicabilityRule(
                    rule_id=f"{pack_id}-RULE-SW",
                    condition_field="software_in_device",
                    condition_value="true",
                    template_pack_id=pack_id,
                )
            )
            await session.flush()

            session.add(
                TemplateSection(
                    section_id=f"{pack_id}-SEC-SW",
                    document_id=f"{pack_id}-DOC-001",
                    section_key="software_documentation",
                    title="Software Documentation",
                    required=True,
                    source_reference_ids=["SRC-TEST-001"],
                    applicability_rule_id=f"{pack_id}-RULE-SW",
                    is_internal=False,
                    sort_order=2,
                )
            )

        await session.commit()


# ---------------------------------------------------------------------------
# AC-001: POST /product-profiles
# ---------------------------------------------------------------------------

async def test_ac001_create_product_profile_returns_201(template_client):
    """AC-001: POST /product-profiles with valid body → 201 with product_id."""
    client, _ = template_client
    resp = await client.post(
        "/product-profiles",
        json={
            "device_name": "My X-ray Device",
            "classification": "Class II",
            "target_market": ["US"],
            "software_in_device": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "product_id" in data
    assert "created_at" in data
    assert len(data["product_id"]) == 36  # uuid4


async def test_ac001b_create_product_profile_missing_device_name_422(template_client):
    """AC-001b: POST /product-profiles missing device_name → 422."""
    client, _ = template_client
    resp = await client.post(
        "/product-profiles",
        json={"classification": "Class II"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AC-002: POST /template-packs/resolve
# ---------------------------------------------------------------------------

async def test_ac002_resolve_returns_pack_candidate(template_client):
    """AC-002: resolve with US FDA 510K X-ray profile → returns pack candidate."""
    client, session_factory = template_client
    await _seed_pathway(session_factory)
    await _seed_pack(session_factory)

    resp = await client.post(
        "/template-packs/resolve",
        json={
            "product_profile": {
                "device_name": "X-ray Device",
                "target_market": ["US"],
                "device_family": "X-ray System",
                "software_in_device": False,
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "pack_candidates" in data
    assert len(data["pack_candidates"]) >= 1
    assert data["pack_candidates"][0]["pack_id"] == "PACK-001"


# ---------------------------------------------------------------------------
# AC-003: resolve response structure
# ---------------------------------------------------------------------------

async def test_ac003_resolve_response_includes_all_fields(template_client):
    """AC-003: resolve response includes applicable_documents, applicable_sections,
    excluded_sections, source_references."""
    client, session_factory = template_client
    await _seed_pathway(session_factory)
    await _seed_source_ref(session_factory)
    await _seed_full_pack_with_sections(session_factory, "PACK-AC003")

    resp = await client.post(
        "/template-packs/resolve",
        json={
            "product_profile": {
                "device_name": "X-ray Device",
                "target_market": ["US"],
                "device_family": "X-ray System",
                "software_in_device": False,
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "matched_pathways" in data
    assert "pack_candidates" in data
    assert "applicable_documents" in data
    assert "applicable_sections" in data
    assert "excluded_sections" in data
    assert "source_references" in data


# ---------------------------------------------------------------------------
# AC-004: POST /template-packs — regulatory section missing source_refs → 400
# ---------------------------------------------------------------------------

async def test_ac004_create_pack_missing_source_refs_returns_400(template_client):
    """AC-004: POST /template-packs with non-internal section with empty source_reference_ids → 400."""
    client, session_factory = template_client
    await _seed_pathway(session_factory)

    resp = await client.post(
        "/template-packs",
        json={
            "pack_id": "PACK-BAD-001",
            "pathway_id": "US-FDA-510K",
            "device_family": "X-ray System",
            "version": "1.0",
            "documents": [
                {
                    "document_id": "DOC-BAD-001",
                    "doc_type": "dhf",
                    "title": "Bad Doc",
                    "required": True,
                    "sections": [
                        {
                            "section_id": "SEC-BAD-001",
                            "section_key": "missing_refs",
                            "title": "No Source Refs",
                            "required": True,
                            "source_reference_ids": [],  # empty — should fail
                            "is_internal": False,
                        }
                    ],
                }
            ],
        },
    )
    assert resp.status_code == 400
    assert "source_reference_ids" in resp.json()["detail"].lower() or "source" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# AC-005: is_internal sections not labeled as authority-mandated
# ---------------------------------------------------------------------------

async def test_ac005_internal_section_allowed_without_source_refs(template_client):
    """AC-005: is_internal=True sections pass creation even without source_reference_ids."""
    client, session_factory = template_client
    await _seed_pathway(session_factory)

    resp = await client.post(
        "/template-packs",
        json={
            "pack_id": "PACK-INTERNAL-001",
            "pathway_id": "US-FDA-510K",
            "device_family": "X-ray System",
            "version": "1.0",
            "documents": [
                {
                    "document_id": "DOC-INT-001",
                    "doc_type": "internal",
                    "title": "Internal Doc",
                    "required": False,
                    "sections": [
                        {
                            "section_id": "SEC-INT-001",
                            "section_key": "internal_notes",
                            "title": "Internal Notes",
                            "required": False,
                            "source_reference_ids": [],
                            "is_internal": True,  # OK — internal
                        }
                    ],
                }
            ],
        },
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# AC-006: GET /template-packs?market=KR
# ---------------------------------------------------------------------------

async def test_ac006_list_packs_filter_by_market(template_client):
    """AC-006: GET /template-packs?market=KR&device_family=X-ray+System → only KR packs."""
    client, session_factory = template_client

    # Seed KR pathway and pack
    from app.models.regulatory_pathway import RegulatoryPathway
    from app.models.template_pack import TemplatePack

    async with session_factory() as session:
        session.add(
            RegulatoryPathway(
                pathway_id="KR-MFDS-MD",
                market="KR",
                authority="MFDS",
                submission_type="medical_device",
                device_class="Class II",
                applicable_standards=[],
            )
        )
        session.add(
            RegulatoryPathway(
                pathway_id="US-FDA-510K",
                market="US",
                authority="FDA",
                submission_type="510k",
                device_class="Class II",
                applicable_standards=[],
            )
        )
        await session.flush()
        session.add(
            TemplatePack(
                pack_id="KR-XRAY-V1",
                pathway_id="KR-MFDS-MD",
                device_family="X-ray System",
                version="1.0",
                status="active",
            )
        )
        session.add(
            TemplatePack(
                pack_id="US-XRAY-V1",
                pathway_id="US-FDA-510K",
                device_family="X-ray System",
                version="1.0",
                status="active",
            )
        )
        await session.commit()

    resp = await client.get("/template-packs?market=KR&device_family=X-ray+System")
    assert resp.status_code == 200
    packs = resp.json()["packs"]
    pack_ids = [p["pack_id"] for p in packs]
    assert "KR-XRAY-V1" in pack_ids
    assert "US-XRAY-V1" not in pack_ids


# ---------------------------------------------------------------------------
# AC-007: GET /template-packs/{pack_id}
# ---------------------------------------------------------------------------

async def test_ac007_get_pack_returns_document_tree(template_client):
    """AC-007: GET /template-packs/{pack_id} returns document tree + sections + source_refs."""
    client, session_factory = template_client
    await _seed_pathway(session_factory)
    await _seed_full_pack_with_sections(session_factory, "PACK-DETAIL")

    resp = await client.get("/template-packs/PACK-DETAIL")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pack_id"] == "PACK-DETAIL"
    assert "documents" in data
    assert len(data["documents"]) >= 1
    assert "sections" in data["documents"][0]
    assert len(data["documents"][0]["sections"]) >= 1


async def test_ac007b_get_pack_not_found_returns_404(template_client):
    """GET /template-packs/{pack_id} → 404 if not found."""
    client, _ = template_client
    resp = await client.get("/template-packs/NONEXISTENT")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# AC-008 / AC-009: software_in_device applicability
# ---------------------------------------------------------------------------

async def test_ac008_software_in_device_true_includes_sw_sections(template_client):
    """AC-008: software_in_device=True checklist includes SW sections."""
    client, session_factory = template_client
    await _seed_pathway(session_factory)
    await _seed_full_pack_with_sections(
        session_factory, "PACK-SW-TRUE", software_in_device_rule=True
    )

    # Create product with software_in_device=True
    resp = await client.post(
        "/product-profiles",
        json={
            "device_name": "SW Device",
            "target_market": ["US"],
            "device_family": "X-ray System",
            "software_in_device": True,
        },
    )
    assert resp.status_code == 201
    product_id = resp.json()["product_id"]

    resp = await client.get(
        f"/template-packs/PACK-SW-TRUE/checklist?product_id={product_id}"
    )
    assert resp.status_code == 200
    data = resp.json()
    section_ids = [i["section_id"] for i in data["items"]]
    assert "PACK-SW-TRUE-SEC-SW" in section_ids


async def test_ac009_software_in_device_false_excludes_sw_sections(template_client):
    """AC-009: software_in_device=False checklist excludes SW-only sections."""
    client, session_factory = template_client
    await _seed_pathway(session_factory)
    await _seed_full_pack_with_sections(
        session_factory, "PACK-SW-FALSE", software_in_device_rule=True
    )

    resp = await client.post(
        "/product-profiles",
        json={
            "device_name": "Non-SW Device",
            "target_market": ["US"],
            "device_family": "X-ray System",
            "software_in_device": False,
        },
    )
    assert resp.status_code == 201
    product_id = resp.json()["product_id"]

    resp = await client.get(
        f"/template-packs/PACK-SW-FALSE/checklist?product_id={product_id}"
    )
    assert resp.status_code == 200
    data = resp.json()
    section_ids = [i["section_id"] for i in data["items"]]
    # SW section excluded
    assert "PACK-SW-FALSE-SEC-SW" not in section_ids
    # Non-SW section present
    assert "PACK-SW-FALSE-SEC-001" in section_ids


# ---------------------------------------------------------------------------
# AC-011: unsupported jurisdiction
# ---------------------------------------------------------------------------

async def test_ac011_resolve_unsupported_jurisdiction(template_client):
    """AC-011: resolve for unsupported jurisdiction → {status: "unsupported"}."""
    client, session_factory = template_client
    # No pathways seeded for JP market

    resp = await client.post(
        "/template-packs/resolve",
        json={
            "product_profile": {
                "device_name": "Japan Device",
                "target_market": ["JP"],
                "device_family": "X-ray System",
                "software_in_device": False,
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unsupported"
    assert "reason" in data


async def test_ac011b_resolve_no_active_pack_returns_unsupported(template_client):
    """AC-011b: pathway exists but no active pack → unsupported."""
    client, session_factory = template_client
    await _seed_pathway(session_factory)
    await _seed_pack(session_factory, status="draft")  # draft — not active

    resp = await client.post(
        "/template-packs/resolve",
        json={
            "product_profile": {
                "device_name": "Draft Device",
                "target_market": ["US"],
                "device_family": "X-ray System",
                "software_in_device": False,
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unsupported"


# ---------------------------------------------------------------------------
# AC-012: POST /template-packs admin
# ---------------------------------------------------------------------------

async def test_ac012_create_template_pack_persists_and_returns_pack_id(template_client):
    """AC-012: POST /template-packs admin → persists pack, returns pack_id+version."""
    client, session_factory = template_client
    await _seed_pathway(session_factory)
    await _seed_source_ref(session_factory, "SRC-ADMIN-001")

    resp = await client.post(
        "/template-packs",
        json={
            "pack_id": "PACK-ADMIN-001",
            "pathway_id": "US-FDA-510K",
            "device_family": "X-ray System",
            "version": "2.0",
            "documents": [
                {
                    "document_id": "DOC-ADMIN-001",
                    "doc_type": "dhf",
                    "title": "Admin Test Doc",
                    "required": True,
                    "sections": [
                        {
                            "section_id": "SEC-ADMIN-001",
                            "section_key": "test_section",
                            "title": "Test Section",
                            "required": True,
                            "source_reference_ids": ["SRC-ADMIN-001"],
                            "is_internal": False,
                        }
                    ],
                }
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["pack_id"] == "PACK-ADMIN-001"
    assert data["version"] == "2.0"

    # Verify persisted
    resp2 = await client.get("/template-packs/PACK-ADMIN-001")
    assert resp2.status_code == 200
    assert resp2.json()["pack_id"] == "PACK-ADMIN-001"


async def test_ac012b_duplicate_pack_returns_409(template_client):
    """AC-012b: POST /template-packs same pack_id+version → 409."""
    client, session_factory = template_client
    await _seed_pathway(session_factory)
    await _seed_pack(session_factory, pack_id="PACK-DUP", pathway_id="US-FDA-510K")

    resp = await client.post(
        "/template-packs",
        json={
            "pack_id": "PACK-DUP",
            "pathway_id": "US-FDA-510K",
            "device_family": "X-ray System",
            "version": "1.0",
            "documents": [],
        },
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------

async def test_checklist_missing_product_id_returns_400(template_client):
    """GET /template-packs/{pack_id}/checklist without product_id → 400."""
    client, session_factory = template_client
    await _seed_pathway(session_factory)
    await _seed_pack(session_factory)

    resp = await client.get("/template-packs/PACK-001/checklist")
    assert resp.status_code == 400


async def test_checklist_nonexistent_pack_returns_404(template_client):
    """GET /template-packs/{pack_id}/checklist with bad pack_id → 404."""
    client, _ = template_client

    resp = await client.post(
        "/product-profiles",
        json={"device_name": "Test Device"},
    )
    product_id = resp.json()["product_id"]

    resp = await client.get(f"/template-packs/BAD-PACK/checklist?product_id={product_id}")
    assert resp.status_code == 404


async def test_resolve_without_product_or_profile_returns_400(template_client):
    """POST /template-packs/resolve with no product_id or product_profile → 400."""
    client, _ = template_client
    resp = await client.post("/template-packs/resolve", json={})
    assert resp.status_code == 400


async def test_list_packs_returns_packs_field(template_client):
    """GET /template-packs returns {packs: [...]}."""
    client, session_factory = template_client
    await _seed_pathway(session_factory)
    await _seed_pack(session_factory)

    resp = await client.get("/template-packs")
    assert resp.status_code == 200
    assert "packs" in resp.json()


async def test_applicability_evaluator_equality(template_client):
    """ApplicabilityRule evaluator correctly handles string equality."""
    from app.models.applicability_rule import ApplicabilityRule
    from app.models.product_profile import ProductProfile
    from app.services.applicability import evaluate_rule

    rule = ApplicabilityRule(
        rule_id="TEST-RULE",
        condition_field="classification",
        condition_value="Class II",
        template_pack_id="DUMMY",
    )
    profile = ProductProfile(product_id="P1", device_name="D", classification="Class II")
    assert evaluate_rule(rule, profile) is True

    profile_no_match = ProductProfile(product_id="P2", device_name="D", classification="Class III")
    assert evaluate_rule(rule, profile_no_match) is False


async def test_applicability_evaluator_none_rule(template_client):
    """evaluate_rule with None rule returns True (always applicable)."""
    from app.models.product_profile import ProductProfile
    from app.services.applicability import evaluate_rule

    profile = ProductProfile(product_id="P1", device_name="D")
    assert evaluate_rule(None, profile) is True
