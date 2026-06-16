# Integration Contract: hybrid-ra-saas ↔ ra-med-bot

Version: 1.0.0  
Effective: 2026-06-16  
Source of truth: SPEC-API-001, SPEC-APITOK-001

---

## Authentication

All protected endpoints require:

```
Authorization: Bearer <HYBRID_RA_API_TOKEN>
X-Tenant-ID: <tenant_id>
```

| Condition | HTTP Status |
|-----------|-------------|
| `HYBRID_RA_API_TOKEN` not configured on server | 503 Service Unavailable |
| Missing or invalid Bearer token | 401 Unauthorized |
| Missing `X-Tenant-ID` header | 400 Bad Request |

Environment variables required in `ra-med-bot`:

```
HYBRID_RA_API_BASE_URL=https://<customer-runtime-host>
HYBRID_RA_API_TOKEN=<shared-secret-32-bytes-minimum>
HYBRID_RA_TENANT_ID=<tenant-id>
```

---

## Endpoints

### GET /health

**Auth required:** No  
**Purpose:** Availability check

Response `200 OK`:
```json
{ "status": "ok" }
```

---

### GET /sync/manifest

**Auth required:** Yes  
**Purpose:** Fetch entity change manifest for delta sync

Query params:
- `since` (optional): ISO-8601 datetime — only return entities updated after this timestamp

Response `200 OK`:
```json
{
  "manifest_hash": "sha256hex",
  "generated_at": "2026-06-16T00:00:00Z",
  "total_count": 42,
  "entries": [
    {
      "entity_type": "product",
      "entity_id": "prod-001",
      "version_hash": "sha256hex",
      "action": "upsert",
      "updated_at": "2026-06-15T12:00:00Z"
    }
  ]
}
```

Manifest entries **never** contain `storage_key`, `content`, or raw document data (FR-210).

---

### POST /rag/query

**Auth required:** Yes  
**Purpose:** RAG-based regulatory Q&A

Request body:
```json
{
  "question": "What safety requirements apply?",
  "evidence_required": true,
  "product_id": "prod-001",
  "top_k": 5
}
```

Response `200 OK`:
```json
{
  "answer": "Based on the evidence...",
  "evidence_links": ["req-1", "req-2"],
  "confidence": 0.85,
  "submit_safe": true
}
```

- `submit_safe: false` when `evidence_required=true` and no evidence found
- `confidence: 0.0` on Ollama timeout (graceful fallback, no 5xx)

---

### POST /documents/upload

**Auth required:** Yes  
**Purpose:** Upload a DOCX source document for parsing

Request: `multipart/form-data` with `file` field (`.docx` only)

Response `200 OK`:
```json
{
  "doc_id": "uuid",
  "parse_job_id": "uuid"
}
```

Errors:
- `422` — unsupported file extension

---

### POST /guardrail/run

**Auth required:** Yes  
**Purpose:** Execute cross-document consistency rules

Request body:
```json
{
  "product_id": "prod-001",
  "doc_set_ids": ["doc-1", "doc-2"],
  "rule_set_version": "1.0"
}
```

Response `200 OK`:
```json
{
  "run_id": "uuid",
  "findings": [
    {
      "doc_id": "doc-1",
      "severity": "High",
      "message": "No risk linkage found"
    }
  ],
  "documents_flagged": ["doc-1"]
}
```

---

### POST /audit/export

**Auth required:** Yes  
**Purpose:** Export audit event log

Request body:
```json
{
  "tenant_id": "tenant-1",
  "format": "csv"
}
```

Response: Binary file download (CSV or JSON)

---

## Error Mapping

| hybrid-ra-saas response | ra-med-bot handling |
|-------------------------|---------------------|
| 503 (token not configured) | Surface as infra config error; block user flow |
| 401 (invalid token) | Log as integration-gap candidate; alert ops |
| 400 (missing X-Tenant-ID) | Client-side bug; fix adapter |
| 5xx (server error) | Retry with exponential backoff (max 3); then log |
| Timeout | Log with `confidence: 0.0` fallback if RAG; surface warning |

---

## Contract Verification

ra-med-bot MUST maintain contract tests for each endpoint using MSW or a test fixture server.

Test scenarios per endpoint:
1. Valid auth + valid body → verify response schema
2. Invalid/missing auth → verify 401
3. Malformed body → verify 4xx
4. Server-side timeout → verify graceful handling

Refs: ra-med-bot issue #156

---

## Versioning

This contract is versioned alongside `SPEC-APITOK-001`.  
Breaking changes require a new contract version and coordinated deployment.
