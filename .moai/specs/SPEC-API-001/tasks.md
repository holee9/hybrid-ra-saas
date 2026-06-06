## Task Decomposition
SPEC: SPEC-API-001

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| T-001 | 프로젝트 스캐폴드 + config.py (Pydantic Settings) | infra | - | pyproject.toml, requirements.txt, .env.example, src/app/__init__.py, src/app/config.py | pending |
| T-002 | Async DB 엔진 + 세션 팩토리 + Base/Mixin | infra | T-001 | src/app/database.py, src/app/models/base.py, src/app/models/__init__.py | pending |
| T-003 | conftest: testcontainers Postgres + async client | infra/test | T-002 | tests/conftest.py, tests/__init__.py | pending |
| T-004 | SQLAlchemy 9개 모델 (8 엔티티 + ParseJob) | schema | T-002 | src/app/models/product.py, document.py, requirement.py, risk.py, control.py, evidence.py, finding.py, audit.py, parse_job.py | pending |
| T-005 | Alembic 초기 마이그레이션 (pgvector + 9 테이블) | schema | T-004 | alembic.ini, alembic/env.py, alembic/script.py.mako, alembic/versions/0001_initial_schema.py | pending |
| T-006 | JWT create/decode (HS256) | REQ-API-001 | T-001 | src/app/core/security.py, src/app/core/__init__.py | pending |
| T-007 | Auth deps (get_current_tenant / get_current_user) | REQ-API-001 | T-006 | src/app/deps.py | pending |
| T-008 | App factory + GET /health | REQ-API-002 | T-003 | src/app/main.py, src/app/routers/health.py, src/app/routers/__init__.py, src/app/schemas/errors.py, src/app/schemas/__init__.py, src/app/services/__init__.py | pending |
| T-009 | Storage 서비스 (MinIO/boto3) + Audit 서비스 | REQ-API-003,011 | T-004 | src/app/services/storage.py, src/app/services/audit.py | pending |
| T-010 | POST /documents/upload | REQ-API-003 | T-007,T-008,T-009 | src/app/routers/documents.py, src/app/schemas/document.py | pending |
| T-011 | Parser 서비스 + BackgroundTasks + GET /parse/jobs/{id} + 상태 머신 | REQ-API-004 | T-010 | src/app/services/parser.py, src/app/jobs/parse_job.py, src/app/jobs/__init__.py, src/app/routers/parse.py, src/app/schemas/parse.py, src/app/core/state_machine.py | pending |
| T-012 | Guardrail 규칙 엔진 + POST /guardrail/run | REQ-API-007 | T-011 | src/app/services/guardrail.py, src/app/routers/guardrail.py, src/app/schemas/guardrail.py | pending |
| T-013 | RAG 서비스 + POST /rag/query | REQ-API-008,009 | T-011 | src/app/services/rag.py, src/app/routers/rag.py, src/app/schemas/rag.py | pending |
| T-014 | Export 서비스 + POST /audit/export | REQ-API-010 | T-012,T-013 | src/app/services/export.py, src/app/schemas/audit.py | pending |
| T-015 | 필드 보정 핸들러 + before/after AuditEvent | REQ-API-006,011 | T-011 | src/app/routers/documents.py (확장) | pending |
| T-016 | GET /sync/manifest (delta + hash, 민감 데이터 배제) | REQ-API-012 | T-008 | src/app/routers/sync.py, src/app/schemas/sync.py | pending |
| T-017 | Air-gap 아웃바운드 검증 (FR-210) | REQ-API-013 | T-016 | src/app/services/airgap.py | pending |
| T-018 | Rate limiting 미들웨어 (slowapi, 100/min/tenant → 429) | REQ-API-014 | T-007 | src/app/core/ratelimit.py | pending |
| T-019 | Docker multi-stage + compose 5서비스 + entrypoint | REQ-API-015 | T-005,T-008 | docker/Dockerfile, docker/entrypoint.sh, docker-compose.yml, README.md | pending |
| T-020 | 커버리지 80% 달성 + 성능 검증 | all | all | tests/ (gap-fill) | pending |
