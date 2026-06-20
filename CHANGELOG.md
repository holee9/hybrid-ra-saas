# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-06-20 — 1차 완료 마일스톤

### 완료 (Regula 연동)

- ra-med-bot ↔ hybrid-ra-saas 1차 연동 완료
  - ra-med-bot #188: inbound webhook 엔드포인트 (audit / ifu / knowledge-sync) 구현 완료
  - ra-med-bot #189: GitHub Secrets 3개 등록 완료 (HYBRID_RA_API_TOKEN, REGULA_API_KEY, CRAWL_PUSH_SECRET)
  - ra-med-bot #168: Evidence API UI 연동 완료
  - ra-med-bot #169: Traceability API UI 연동 완료
  - ra-med-bot #171: Authoring API UI 연동 완료
  - ra-med-bot #191: Vercel 환경변수 설정 완료 (HYBRID_RA_API_BASE_URL, HYBRID_RA_TENANT_ID)
- `api-prod` 환경변수 `REGULA_KNOWLEDGE_PUSH_URL` 추가 배포 완료 (Refs #51)
- `customer-runtime/.env.example` 누락 항목 추가 — GAP-08 (Refs #50)

### 누적 완료 SPEC (v1.0.0 기준)

| SPEC | 내용 |
|------|------|
| SPEC-API-001 | Customer Local Runtime FastAPI + Docker Compose |
| SPEC-PARSER-001 | IFU 15필드 NLP 파서 엔진 (3단계 파이프라인) |
| SPEC-UI-001 | IFU 파싱 결과 교정 UI (React + TypeScript) |
| SPEC-UI-002 | 검토 큐 화면 (React Router, 5-tab 상태 필터) |
| SPEC-INFRA-001 | Azure Terraform IaC (Container Apps / PostgreSQL / Key Vault) |
| SPEC-CRAWLER-001 | 규제 문서 크롤러 (FDA / MFDS / EU MDR) |
| SPEC-APITOK-001 | 서비스간 Bearer 토큰 인증 |
| SPEC-TENANT-ISOLATION-001 | ORM 수준 자동 테넌트 필터링 |
| SPEC-JOBQUEUE-001 | BackgroundTasks → arq 영속 Job Queue 전환 |

## [0.9.1] - 2026-06-17

### Fixed

- `OLLAMA_TIMEOUT` 25s → 8s 조정 — REQ-API-009 준수 (3회 retry 시 최악 27s ≤ 30s SLA)
  (`customer-runtime/src/app/services/rag.py`, Refs #46)

## [0.9.0] - 2026-06-17

### Added (SPEC-JOBQUEUE-001)

- `customer-runtime/src/app/jobs/worker.py` 신규: arq `WorkerSettings` 정의
  - `max_tries=3` 지수 백오프 재시도 (REQ-JQ-004)
  - `on_startup` orphan 복구: DB `status='running'` + Redis 부재 작업 → 재적재 또는 `'failed'` 전이 (REQ-JQ-003)
  - `on_job_abort` DLQ 전이: 최대 재시도 소진 시 `ParseJob.status='failed'` + terminal error 기록 (REQ-JQ-005)
- `customer-runtime/src/app/jobs/worker_health.py` 신규: Redis heartbeat TTL key — Azure Container App liveness probe (REQ-JQ-008)
- `customer-runtime/src/app/queue/arq_pool.py` 신규: `ArqRedis` 풀 생성/주입, 단일 enqueue 진입점 (fan_in ≥ 3)
- `cloud-control-plane/src/app/jobs/crawl_worker.py` 신규: `_execute_crawl_job` arq task 등록 (REQ-JQ-006)
- `cloud-control-plane/src/app/queue/arq_pool.py` 신규: cloud-control-plane `ArqRedis` 풀
- `customer-runtime/tests/test_job_queue_unit.py` 신규: 18개 단위 테스트 (arq Redis 인터페이스 모킹, Docker 불필요)
- `customer-runtime/tests/test_job_queue_integration.py` 신규: 통합 테스트 (`skip_no_docker`, CI 전용 실 Redis)

### Changed

- `customer-runtime/src/app/jobs/parse_job.py`: arq task 시그니처 (`ctx` 첫 인자), `explicit_tenant_context` 적용 (REQ-TI-010)
- `customer-runtime/src/app/routers/documents.py`: `background_tasks.add_task(run_parse_job, ...)` → arq enqueue (REQ-JQ-002)
- `customer-runtime/src/app/main.py`: arq pool lifespan 통합
- `cloud-control-plane/src/app/routers/crawl.py`: `background_tasks.add_task(...)` → arq enqueue (REQ-JQ-006)
- `customer-runtime/pyproject.toml`, `cloud-control-plane/pyproject.toml`: `arq>=0.26` 의존성 추가

### Security / Resilience

- FastAPI `BackgroundTasks` 인메모리 실행 제거 → Redis 영속 큐로 전환: Azure Container App 재시작/스케일 이벤트에서 작업 유실 차단
- `ParseJob.status='running'` 좀비 작업 구조적 제거 (orphan 복구)
- API 계약 무변경: `GET /parse/jobs/{job_id}/status` 응답 스키마 동일 (REQ-JQ-007)

## [0.8.0] - 2026-06-17

### Added (SPEC-TENANT-ISOLATION-001)

- `customer-runtime/src/app/db/` 신규 서브패키지: ORM 수준 자동 테넌트 필터링 인프라
  - `db/tenant_context.py`: `ContextVar` 기반 요청 범위 테넌트 컨텍스트 관리
    - `set_tenant_context()` / `get_tenant_context()` / `clear_tenant_context()`
    - `bypass_tenant_context()`: 관리자 우회 async context manager
    - `explicit_tenant_context()`: 백그라운드 태스크용 명시적 컨텍스트 (REQ-TI-010)
    - `TenantContextError`: 컨텍스트 미설정 시 fail-closed 예외
  - `db/tenant_filter.py`: SQLAlchemy 2.0 ORM 이벤트 리스너 (REQ-TI-002, REQ-TI-004, REQ-TI-005)
    - `do_orm_execute` 리스너: `with_loader_criteria(TenantMixin, ..., include_aliases=True)` 자동 주입
      - 관계(relationship) eager/lazy 로드 포함 모든 SELECT에 적용
      - 컨텍스트 미설정 시 `TenantContextError` (fail-closed, 빈 결과 반환 없음)
    - `before_flush` 리스너: INSERT 시 `tenant_id` 자동 설정, 교차 테넌트 쓰기 시 `TenantWriteViolation` 발생
    - `register_tenant_filter(session_factory)`: 세션 팩토리에 두 리스너 등록
- `database.py`: `init_engine()` 내부에 `register_tenant_filter()` 연결 (투명한 적용)
- `deps.py`: `get_current_tenant`, `get_current_user` async generator 전환 — ContextVar 설정/해제 보장
- `core/security.py`: `verify_hybrid_bearer_token`, `verify_api_key` async generator 전환
  - `verify_api_key` 함수 시그니처 FROZEN 유지 (REQ-TI-NF-003)
- `models/base.py`: `is_tenant_scoped()` helper 추가 (REQ-TI-011 모델 인벤토리)
- `tests/test_tenant_isolation.py` 신규: 단위 테스트 22개 (DB 불필요, ContextVar + ORM 리스너)
- `tests/test_model_tenant_coverage.py` 신규: CI 감사 테스트
  - `KNOWN_GLOBAL_MODELS`: 의도적 글로벌 모델 명시적 분류
  - `MIGRATION_PENDING_MODELS`: SPEC 이전 15개 기존 모델 명시적 분류 (향후 마이그레이션 대상)

### Security

- 교차 테넌트 데이터 유출 구조적 차단: 개발자가 쿼리마다 `WHERE tenant_id=:x` 수동 작성에 의존하지 않음
- 테넌트 스푸핑 방어: `before_flush`에서 `tenant_id` 위조 시도 즉시 탐지·거부 및 보안 로그 기록

## [0.7.0] - 2026-06-16

### Added (SPEC-APITOK-001)

- `verify_hybrid_bearer_token` FastAPI 의존성 추가 (`security.py`): 서비스간 Bearer 토큰 인증
  - `HYBRID_RA_API_TOKEN` 미설정 시 503 (인프라 설정 오류), 잘못된 토큰 시 401, `X-Tenant-ID` 누락 시 400
  - 기존 `verify_api_key`·JWT 인증 함수 FROZEN (미변경)
- 8개 라우터에 Bearer 인증 적용: `rag`, `sync`, `audit`, `guardrail`, `documents`, `authoring`, `checklist`, `evidence`
- `test_apitok_001.py` 신규: 인증 전용 테스트 파일 (503/401/400/200 시나리오)
- `docs/integration-contract.md` 신규: ra-med-bot ↔ hybrid-ra-saas API 계약 명세

### Changed

- `.env.example`: `HYBRID_RA_API_TOKEN` 필수 환경변수 추가 (최소 32자)
- 전체 테스트: 299 passed / 0 failed (단위 테스트 기준)

## [0.6.0] - 2026-06-11

### Added (SPEC-CRAWLER-001)

- `cloud-control-plane/` 신규 Python 3.13 FastAPI 마이크로서비스: 규제 문서 자동 수집 파이프라인 (Issue #18)
  - 다중 소스 크롤러: FDA(US guidance) / MFDS(한국) / EU MDR(EUR-Lex 2017/745)
  - `CrawlerSource` 공통 베이스: robots.txt 준수, source당 1 req/sec rate limiting, 지수 백오프 3회 재시도, SSRF netloc 검증
  - SHA-256 콘텐츠 해시 중복 제거 (`dedup.py`) — 변경 없는 문서 skip
  - Azure Blob Storage 원문 저장: `regulatory-docs/{source}/{YYYY-MM-DD}/{filename}` 경로 규약
  - PostgreSQL `regulatory_documents` 신규 테이블 (Alembic 마이그레이션 0001) — 메타데이터만 기록
  - 수동 트리거 API: `POST /crawl/trigger`(BackgroundTasks 비동기), `GET /crawl/status/{job_id}`, `GET /health`
  - Application Insights 구조화 JSON 로깅 (`core/logging.py`)
- Terraform: `crawler-job` Azure Container App Job 신규 (cron `0 2 * * *`, 설정 가능), `cloud-control-plane-api` placeholder 이미지를 실제 크롤러 이미지로 교체
- CI/CD: `.github/workflows/deploy-prod.yml`에 크롤러 build + push + 배포 스텝 추가
- 테스트: 단위 75 passed + 통합 2(`@skip_no_docker`, CI 전용), 커버리지 94%, ruff 0 errors

## [0.5.0] - 2026-06-09

### Added (SPEC-UI-002)

- `GET /parse/jobs` 백엔드 엔드포인트: 테넌트 격리, 상태/교정필요 필터, skip/limit 페이지네이션
  - `JobSummary`, `ListJobsResponse` Pydantic v2 스키마 추가
  - `_extract_summary_fields()` 헬퍼: `result_json["parsed_fields"]`에서 안전 추출
  - pytest: 6개 단위 테스트(Docker 불필요) + 7개 통합 테스트(`@skip_no_docker`, CI 전용)
- 검토 큐 화면 React 18 SPA:
  - React Router 7 도입: `BrowserRouter`, `/jobs` → QueuePage, `/jobs/:jobId` → CorrectionPanel
  - `QueuePage`: StatusTabs(5개), SortControl(작성일/신뢰도), JobQueueTable, Pagination 조합
  - `useListJobs` 훅: 5초 자동갱신(running 작업 존재 시), 클라이언트 정렬, cancelled 가드
  - Pagination: total≤50 시 자동 숨김, 경계 비활성화
  - Vitest 테스트: 113/113 통과

## [0.4.0] - 2026-06-09

### Added (SPEC-UI-001)

- `customer-runtime/ui` React 18 + TypeScript 단일 SPA: Vite 번들러, 15개 IFU 필드 인라인 수정
  - confidence 시각화 (green/yellow/red 배지), `PATCH /parse/{job_id}/corrections` API 소비
  - Vitest + RTL 테스트: 83/83 passed, 0 TypeScript errors
  - Docker ui 서비스: nginx, port 8080, docker-compose.yml 통합
  - JWT in-memory 인증, X-Tenant-ID 환경 변수 로드
  - ESLint (flat config), prettier 포맷팅 설정

## [0.3.0] - 2026-06-09

### Added (SPEC-PARSER-001)

- `parser_engine` 패키지: X-ray IFU 문서에서 15개 규제 필드 자동 추출 엔진
  - `docx_reader`, `xlsx_reader`: DOCX/XLSX → 텍스트 추출 (50MB 크기 제한)
  - `confidence.py`: 가중치 신뢰도 공식 (0.50×완전성 + 0.30×규칙 + 0.20×의미)
  - `rule_based.py`: Stage 1 정규식/키워드 사전 추출 (영어/한국어, 네트워크/GPU 없음)
  - `spacy_ner.py`: Stage 2 NER 추출 (lazy import, spaCy 미설치 시 자동 우회)
  - `llm_fallback.py`: Stage 3 Ollama 로컬 LLM 폴백 (localhost 전용, 데이터 주권 보장)
  - `errors.py`: 커스텀 예외 (DocxReadError, XlsxReadError, InputTooLargeError)
- `ExtractionStage`, `FieldExtraction`, `ParsedFields` Pydantic 모델 추가
- `PATCH /parse/{job_id}/corrections` 교정 API: 수동 교정 + 신뢰도 재계산
- `EngineParserService`: 실제 파이프라인 구현체 (StubParserService 하위호환 유지)
- CI 테스트 분리: `@pytest.mark.integration` (Ollama/spaCy/골든 데이터셋 의존 테스트 CI 전용)

### Changed

- `parser.py`: 스텁 → EngineParserService 위임 구조로 확장 (기존 인터페이스 유지)
- `deps.py`: `get_parser()` 의존성 제공자 추가
- `tests/conftest.py`: `skip_no_ollama`, `skip_no_spacy`, `skip_no_golden` 마커 추가

### Security

- REQ-PARSER-007: `_assert_local()` 코드 수준 호스트 가드 — localhost/ollama 외 LLM 호출 차단

## [0.2.0] - 2026-06-08

### Added (SPEC-INFRA-001)

- Azure Terraform IaC: Container Registry, Container App Environment, PostgreSQL, Key Vault, Monitoring 모듈
- OIDC 전용 인증, Key Vault 시크릿 data source, `*.tfvars` gitignored
- `terraform.yml` CI/CD: PR → plan comment, main merge → apply

## [0.1.0] - 2026-06-08

### Added (SPEC-API-001)

- Customer Local Runtime: FastAPI 7개 엔드포인트 (health, upload, parse, guardrail, rag, audit, sync)
- SQLAlchemy 9개 데이터 모델 + pgvector 임베딩
- JWT HS256 + X-Tenant-ID 멀티테넌시
- Docker Compose 5서비스 (api, postgres, minio, ollama, redis)
- Air-Gap 아웃바운드 검증 (FR-210)

[Unreleased]: https://github.com/holee9/hybrid-ra-saas/compare/v0.9.1...HEAD
[0.9.1]: https://github.com/holee9/hybrid-ra-saas/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/holee9/hybrid-ra-saas/releases/tag/v0.1.0
