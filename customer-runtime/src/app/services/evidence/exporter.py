"""ZIP export service — SPEC-EVIDENCE-001, SPEC-EVIDENCE-002."""
from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.storage import StoragePort
    from app.models.evidence_binder import EvidenceBinder
    from app.models.evidence_file import EvidenceFile
    from app.models.evidence_link import EvidenceLink

logger = logging.getLogger(__name__)


# @MX:ANCHOR: [AUTO] ZIP export entry point — called by evidence router (SPEC-EVIDENCE-002).
# @MX:REASON: Router and integration tests depend on this signature; storage param required for real bytes.
async def export_zip(
    binder: "EvidenceBinder",
    links: list["EvidenceLink"],
    files: list["EvidenceFile"],
    storage: "StoragePort | None" = None,
) -> bytes:
    """Build an in-memory ZIP containing manifest.json + real file bytes from MinIO.

    ZIP structure:
        manifest.json     — binder metadata + link list + file info + export_summary
        files/{filename}  — real bytes fetched from MinIO per EvidenceFile.storage_ref

    REQ-EVIDENCE-002-001: real bytes included when storage is provided.
    REQ-EVIDENCE-002-002: missing object -> manifest failed entry.
    REQ-EVIDENCE-002-003: binder_id mismatch in storage_ref -> access denied.
    REQ-EVIDENCE-002-004: per-file failure continues export for remaining files.
    REQ-EVIDENCE-002-007: manifest reflects actual included/failed files.
    """
    included: list[dict] = []
    failed: list[dict] = []

    manifest_files: list[dict] = [
        {
            "file_id": f.file_id,
            "original_filename": f.original_filename,
            "content_type": f.content_type,
            "size_bytes": f.size_bytes,
            "sha256": f.sha256,
        }
        for f in files
    ]

    manifest: dict = {
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
        "files": manifest_files,
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for evidence_file in files:
            file_content: bytes | None = None

            if storage is None:
                # Fallback: no storage injected — use sha256 stub (backwards-compatible)
                logger.warning(
                    "export_zip_no_storage",
                    extra={
                        "file_id": evidence_file.file_id,
                        "storage_ref": evidence_file.storage_ref,
                    },
                )
                file_content = f"sha256:{evidence_file.sha256}\n".encode()
                included.append(
                    {"file_id": evidence_file.file_id, "key": evidence_file.storage_ref}
                )
            else:
                # REQ-EVIDENCE-002-003: tenant isolation — check binder_id in storage_ref
                ref = evidence_file.storage_ref
                ref_binder_id = _extract_binder_id_from_ref(ref)
                if ref_binder_id is not None and ref_binder_id != binder.binder_id:
                    logger.warning(
                        "export_tenant_isolation_violation",
                        extra={
                            "file_id": evidence_file.file_id,
                            "storage_ref": ref,
                            "expected_binder_id": binder.binder_id,
                            "found_binder_id": ref_binder_id,
                        },
                    )
                    failed.append(
                        {
                            "file_id": evidence_file.file_id,
                            "key": ref,
                            "error": "tenant_isolation_violation",
                        }
                    )
                    continue

                # REQ-EVIDENCE-002-001: fetch real bytes
                # REQ-EVIDENCE-002-002: missing object -> log + failed entry
                # REQ-EVIDENCE-002-004: continue on per-file error
                try:
                    file_content = await storage.download(ref)
                    included.append({"file_id": evidence_file.file_id, "key": ref})
                    logger.info(
                        "export_file_fetched",
                        extra={
                            "file_id": evidence_file.file_id,
                            "key": ref,
                            "size_bytes": len(file_content),
                        },
                    )
                except Exception as exc:
                    logger.error(
                        "export_file_failed",
                        extra={
                            "file_id": evidence_file.file_id,
                            "key": ref,
                            "error": str(exc),
                        },
                    )
                    failed.append(
                        {
                            "file_id": evidence_file.file_id,
                            "key": ref,
                            "error": str(exc),
                        }
                    )
                    continue

            zf.writestr(f"files/{evidence_file.original_filename}", file_content)

        # REQ-EVIDENCE-002-007: manifest reflects actual included/failed state
        manifest["export_summary"] = {
            "included_count": len(included),
            "failed_count": len(failed),
            "included": included,
            "failed": failed,
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    return buf.getvalue()


def _extract_binder_id_from_ref(storage_ref: str) -> str | None:
    """Extract binder_id from storage_ref path.

    Expected format: "{prefix}/evidence/{binder_id}/{uuid}/{filename}"
    Returns None if format is unexpected (isolation check is skipped).
    """
    parts = storage_ref.split("/")
    try:
        evidence_idx = parts.index("evidence")
        if evidence_idx + 1 < len(parts):
            return parts[evidence_idx + 1]
    except ValueError:
        pass
    return None
