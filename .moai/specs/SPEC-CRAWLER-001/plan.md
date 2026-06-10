# SPEC-CRAWLER-001 — 구현 계획 (plan.md)

규제 문서 크롤러 구현 계획. 우선순위 기반 단계(시간 추정 없음). 각 태스크는 ID, 설명, 생성/수정 파일, 인수 기준 연결로 구성한다.

## 단계 개요

| 단계 | 이름 | 초점 |
|------|------|------|
| P0 | MVP 스캐폴드 | FastAPI 골격 + Docker + Terraform Job + DB 마이그레이션 |
| P1 | FDA 소스 | 가장 구조화된 소스 우선 구현 + 공통 베이스 검증 |
| P2 | MFDS + EU MDR + 통합 테스트 | 나머지 소스 + end-to-end 통합 검증 |

---

## P0 — MVP 스캐폴드

| 태스크 | 설명 | 파일 (NEW/MODIFY) | 인수 기준 |
|--------|------|-------------------|-----------|
| T-001 | `cloud-control-plane/` 디렉터리 + FastAPI app factory(lifespan, router 등록) | [NEW] `cloud-control-plane/src/app/main.py` | AC-005 |
| T-002 | pydantic-settings 기반 Settings(크롤러 소스 enable 플래그, timeout, retry, rate limit) | [NEW] `cloud-control-plane/src/app/config.py` | AC-003 |
| T-003 | SQLAlchemy async engine init(customer-runtime database.py 패턴) | [NEW] `cloud-control-plane/src/app/database.py` | AC-001 |
| T-004 | `RegulatoryDocument` ORM 모델 + Base/TimestampMixin | [NEW] `cloud-control-plane/src/app/models/base.py`, `models/regulatory_document.py` | AC-001 |
| T-005 | DB 마이그레이션 — `regulatory_documents` 테이블 + content_hash UNIQUE 인덱스 | [NEW] `cloud-control-plane/migrations/` (또는 SQL) | AC-001, AC-002 |
| T-006 | `GET /health` 라우터 | [NEW] `cloud-control-plane/src/app/routers/health.py` | AC-005 |
| T-007 | Multi-stage Dockerfile(Python 3.13 + uv) + requirements.txt | [NEW] `cloud-control-plane/docker/Dockerfile`, `requirements.txt` | AC-007 |
| T-008 | Terraform — placeholder 이미지 교체 + `crawler-job`(cron `0 2 * * *`) | [MODIFY] `infra/terraform/environments/prod/main.tf` | AC-007 |
| T-009 | 공통 인프라 — 구조화 JSON 로거(Application Insights) | [NEW] `cloud-control-plane/src/app/core/logging.py` | AC-005 |

---

## P1 — FDA 소스 (가장 구조화된 소스부터)

| 태스크 | 설명 | 파일 (NEW/MODIFY) | 인수 기준 |
|--------|------|-------------------|-----------|
| T-010 | `CrawlerSource` 추상 베이스 — robots.txt 조회/파싱, User-Agent | [NEW] `cloud-control-plane/src/app/services/crawler/base.py` | AC-006 |
| T-011 | source당 1 req/sec 토큰버킷 rate limiter | [NEW] `cloud-control-plane/src/app/core/ratelimit.py` | AC-003 |
| T-012 | 지수 백오프 재시도(3회) + 실패 격리 | [MODIFY] `services/crawler/base.py` | AC-004 |
| T-013 | SHA-256 중복 검사 서비스 | [NEW] `cloud-control-plane/src/app/services/dedup.py` | AC-002 |
| T-014 | Blob 업로드 서비스(customer-runtime StorageService 패턴) + 경로 규약 | [NEW] `cloud-control-plane/src/app/services/storage.py` | AC-001 |
| T-015 | FDA source 구현(URL 발견 + fetch) | [NEW] `cloud-control-plane/src/app/services/crawler/fda.py` | AC-001 |
| T-016 | orchestrator — 소스 순회, 실패 격리, 메타데이터 INSERT | [NEW] `cloud-control-plane/src/app/services/orchestrator.py` | AC-001, AC-004 |
| T-017 | 수동 트리거 API(`POST /crawl/trigger`, `GET /crawl/status/{job_id}`) | [NEW] `cloud-control-plane/src/app/routers/crawl.py`, `schemas/crawl.py` | AC-005 |

---

## P2 — MFDS + EU MDR + 통합 테스트

| 태스크 | 설명 | 파일 (NEW/MODIFY) | 인수 기준 |
|--------|------|-------------------|-----------|
| T-018 | MFDS source 구현 | [NEW] `cloud-control-plane/src/app/services/crawler/mfds.py` | AC-001, AC-003 |
| T-019 | EU MDR(EUR-Lex 2017/745) source 구현 | [NEW] `cloud-control-plane/src/app/services/crawler/eu_mdr.py` | AC-001, AC-003 |
| T-020 | 유닛 테스트 — dedup, rate limit, retry, robots.txt(Docker 비의존) | [NEW] `cloud-control-plane/tests/` | AC-002, AC-003, AC-004, AC-006 |
| T-021 | 통합 테스트(`@pytest.mark.integration`, skip_no_docker) — 스케줄 잡 end-to-end | [NEW] `cloud-control-plane/tests/integration/` | AC-001 |
| T-022 | CI/CD — deploy-prod.yml에 크롤러 build+push 스텝 추가 | [MODIFY] `.github/workflows/deploy-prod.yml` | AC-007 |

---

## 기술 접근

- httpx.AsyncClient 단일 세션 재사용(connection pooling), `parser_engine/llm_fallback.py` 패턴 참조.
- Blob 업로드는 boto3 S3 호환 클라이언트(customer-runtime `storage.py` 재사용).
- `crawler-job`은 장기 실행 서버가 아닌 Container App Job — 잡 종료 시 컨테이너 종료.
- DB 레벨 `content_hash` UNIQUE 인덱스로 중복 INSERT를 이중 방지.

## 리스크

- **소스 HTML 구조 변경**: FDA/MFDS/EU MDR 페이지 구조 변화 시 URL 발견 로직 깨짐 → source별 셀렉터를 설정으로 분리, 실패 시 로그+continue.
- **rate limit/robots.txt 변경**: 소스 정책 변화 → robots.txt 매 잡 실행 시 재조회.
- **통합 테스트 외부 의존**: 실제 소스 호출은 CI 불안정 유발 → 통합 테스트는 `@pytest.mark.integration`으로 CI 제외, 유닛은 모킹.

## 의존성 순서

T-001~T-009(P0) → T-010~T-017(P1, FDA로 베이스 검증) → T-018~T-022(P2). P0 완료 전 P1 착수 불가(스캐폴드 의존).
