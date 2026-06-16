# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/holee9/hybrid-ra-saas/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/holee9/hybrid-ra-saas/releases/tag/v0.1.0
