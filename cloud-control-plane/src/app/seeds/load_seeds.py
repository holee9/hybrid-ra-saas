"""Seed loader — populates regulatory reference data into the database.

Usage:
    uv run python -m app.seeds.load_seeds
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

SEEDS_DIR = Path(__file__).parent


async def load_seeds(database_url: str) -> None:
    """Load all seed data into the database."""
    engine = create_async_engine(database_url, echo=False)

    # Import all models to register with Base
    from app.models import (  # noqa: F401
        ApplicabilityRule,
        Base,
        RegulatoryPathway,
        SourceReference,
        TemplatePack,
        TemplateDocument,
        TemplateSection,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # 1. RegulatoryPathways
        pathways_data = json.loads((SEEDS_DIR / "regulatory_pathways.json").read_text())
        for d in pathways_data:
            existing = await session.get(RegulatoryPathway, d["pathway_id"])
            if existing is None:
                session.add(RegulatoryPathway(**d))

        await session.flush()

        # 2. SourceReferences
        refs_data = json.loads((SEEDS_DIR / "source_references.json").read_text())
        for d in refs_data:
            existing = await session.get(SourceReference, d["ref_id"])
            if existing is None:
                session.add(SourceReference(**d))

        await session.flush()

        # 3. ApplicabilityRules (before sections that reference them)
        rules_data = json.loads((SEEDS_DIR / "applicability_rules.json").read_text())
        for d in rules_data:
            existing = await session.get(ApplicabilityRule, d["rule_id"])
            if existing is None:
                session.add(ApplicabilityRule(**d))

        await session.flush()

        # 4. TemplatePacks + documents + sections
        packs_data = json.loads((SEEDS_DIR / "template_packs.json").read_text())
        for pack_data in packs_data:
            documents = pack_data.pop("documents", [])
            existing = await session.get(TemplatePack, pack_data["pack_id"])
            if existing is None:
                session.add(TemplatePack(**pack_data))
                await session.flush()

                for doc_data in documents:
                    sections = doc_data.pop("sections", [])
                    existing_doc = await session.get(TemplateDocument, doc_data["document_id"])
                    if existing_doc is None:
                        session.add(TemplateDocument(pack_id=pack_data["pack_id"], **doc_data))
                        await session.flush()

                        for sec_data in sections:
                            existing_sec = await session.get(TemplateSection, sec_data["section_id"])
                            if existing_sec is None:
                                session.add(
                                    TemplateSection(
                                        document_id=doc_data["document_id"], **sec_data
                                    )
                                )

        await session.commit()

    await engine.dispose()
    print("Seed data loaded successfully.")


if __name__ == "__main__":
    db_url = os.environ.get(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./cloud_control_plane.db",
    )
    asyncio.run(load_seeds(db_url))
