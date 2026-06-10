# Task Decomposition

SPEC: SPEC-CRAWLER-001 (Issue #18)

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| T-001 | FastAPI app factory (lifespan, router 등록) | REQ-011/012 | - | cloud-control-plane/src/app/main.py | completed |
| T-002 | pydantic-settings Settings | REQ-009 | - | cloud-control-plane/src/app/config.py | completed |
| T-003 | SQLAlchemy async engine init | REQ-004 | T-002 | cloud-control-plane/src/app/database.py | completed |
| T-004 | RegulatoryDocument ORM 모델 | REQ-004 | T-003 | cloud-control-plane/src/app/models/base.py, models/regulatory_document.py | completed |
| T-005 | regulatory_documents 마이그레이션 + content_hash UNIQUE | REQ-003b/004 | T-004 | cloud-control-plane/alembic/versions/ | completed |
| T-006 | GET /health 라우터 | REQ-015 | T-001 | cloud-control-plane/src/app/routers/health.py | completed |
| T-007 | Multi-stage Dockerfile + pyproject.toml | REQ-014 | - | cloud-control-plane/docker/Dockerfile, pyproject.toml | completed |
| T-008 | Terraform placeholder 교체 + crawler-job | REQ-013/015 | - | infra/terraform/environments/prod/main.tf, variables.tf | completed |
| T-009 | 구조화 JSON 로거 (App Insights) | REQ-010 | T-002 | cloud-control-plane/src/app/core/logging.py | completed |
| T-010 | CrawlerSource 추상 베이스 (robots.txt) | REQ-007/008 | T-001~009 | cloud-control-plane/src/app/services/crawler/base.py | completed |
| T-011 | min-interval rate limiter (1 req/s/source) | REQ-009 | T-010 | cloud-control-plane/src/app/core/ratelimit.py | completed |
| T-012 | 지수 백오프 재시도 3회 + 실패 격리 | REQ-005/006 | T-010 | services/crawler/base.py (MODIFY) | completed |
| T-013 | SHA-256 dedup 서비스 | REQ-003/003b | T-005 | cloud-control-plane/src/app/services/dedup.py | completed |
| T-014 | Blob 업로드 서비스 + 경로 규약 | REQ-001/002 | T-002 | cloud-control-plane/src/app/services/storage.py | completed |
| T-015 | FDA source 구현 | REQ-001 | T-010~014 | cloud-control-plane/src/app/services/crawler/fda.py | completed |
| T-016 | orchestrator (소스 순회, 실패 격리, INSERT) | REQ-001/004/006 | T-015 | cloud-control-plane/src/app/services/orchestrator.py | completed |
| T-017 | 수동 트리거 API | REQ-011/012 | T-016 | cloud-control-plane/src/app/routers/crawl.py, schemas/crawl.py | completed |
| T-018 | MFDS source 구현 | REQ-001 | T-016 | cloud-control-plane/src/app/services/crawler/mfds.py | completed |
| T-019 | EU MDR source 구현 | REQ-001 | T-016 | cloud-control-plane/src/app/services/crawler/eu_mdr.py | completed |
| T-020 | 유닛 테스트 (Docker 비의존) | AC-002/003/004/006 | T-010~017 | cloud-control-plane/tests/ | completed |
| T-021 | 통합 테스트 (skip_no_docker, CI 전용) | AC-001 | T-020 | cloud-control-plane/tests/integration/ | completed |
| T-022 | deploy-prod.yml 크롤러 build+push | REQ-015 | T-007 | .github/workflows/deploy-prod.yml (MODIFY) | completed |
