# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/holee9/hybrid-ra-saas/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/holee9/hybrid-ra-saas/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/holee9/hybrid-ra-saas/releases/tag/v0.1.0
