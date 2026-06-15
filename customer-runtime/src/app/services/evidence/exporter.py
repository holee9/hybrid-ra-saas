"""ZIP export service — SPEC-EVIDENCE-001."""
from __future__ import annotations

import io
import json
import zipfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.evidence_binder import EvidenceBinder
    from app.models.evidence_file import EvidenceFile
    from app.models.evidence_link import EvidenceLink


async def export_zip(
    binder: "EvidenceBinder",
    links: list["EvidenceLink"],
    files: list["EvidenceFile"],
) -> bytes:
    """Build an in-memory ZIP containing manifest.json + file stubs.

    ZIP structure:
        manifest.json  — binder metadata + link list + file sha256 hashes
        files/{original_filename}  — one stub entry per EvidenceFile
    """
    manifest = {
        "binder_id": binder.binder_id,
        "product_profile_id": binder.product_profile_id,
        "pack_id": binder.pack_id,
        "name": binder.name,
        "status": binder.status,
        "created_by": binder.created_by,
        "sealed_at": binder.sealed_at.isoformat() if binder.sealed_at else None,
        "links": [
            {
                "link_id": lnk.link_id,
                "source_entity_type": lnk.source_entity_type,
                "source_entity_id": lnk.source_entity_id,
                "target_entity_type": lnk.target_entity_type,
                "target_ref": lnk.target_ref,
                "link_type": lnk.link_type,
            }
            for lnk in links
        ],
        "files": [
            {
                "file_id": f.file_id,
                "original_filename": f.original_filename,
                "content_type": f.content_type,
                "size_bytes": f.size_bytes,
                "sha256": f.sha256,
            }
            for f in files
        ],
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        for evidence_file in files:
            # Stub: real bytes not stored locally; use sha256 as placeholder content
            stub_content = f"sha256:{evidence_file.sha256}\n".encode()
            zf.writestr(f"files/{evidence_file.original_filename}", stub_content)

    return buf.getvalue()
