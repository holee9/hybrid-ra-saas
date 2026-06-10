---
id: SPEC-CRAWLER-001
version: 0.4.0
status: completed
created_at: 2026-06-10
updated: 2026-06-11
author: drake.lee
priority: medium
issue_number: 18
labels: [crawler, cloud-control-plane, regulatory-docs]
---

# SPEC-CRAWLER-001: Cloud Control Plane — Regulatory Document Crawler

## HISTORY

- **v0.4.0** (2026-06-11): 구현 완료(Sync). P0(스캐폴드 23파일+Terraform) → P1(FDA 소스+크롤러 베이스) → P2(MFDS·EU MDR+통합 테스트+CI) → fix cycle 1(RateLimiter 연결, trigger 비동기화, SSRF 검증, 예외 로깅). 최종: 단위 75 passed + 통합 2(CI 전용), 커버리지 94%, ruff 클린, drift 0. status: planned → completed.
- **v0.3.0** (2026-06-10): plan-auditor 2차 검토 결함 수정 — REQ-CRAWLER-003 EARS 분리(003/003b), REQ-CRAWLER-013/014 구현 세부사항 제거, AC-008 추가.
- **v0.2.0** (2026-06-10): plan-auditor 검토 결함 수정 — YAML frontmatter 필드 보정(created_at, labels), EARS 복합 요구사항 분리(REQ-006~013), 트레이서빌리티 정정.
- **v0.1.0** (2026-06-10): 최초 작성. Cloud Control Plane 데이터 수집 레이어로서 규제 문서 크롤러 범위 확정. 신규 `cloud-control-plane/` 디렉터리(Python FastAPI, `customer-runtime/` 구조 미러링), SPEC-INFRA-001이 생성한 `cloud-control-plane-api` Container App placeholder 이미지 교체, 신규 Azure Container App Job(`crawler-job`, cron `0 2 * * *`) Terraform 추가, 다중 소스 크롤링(FDA / MFDS / EU MDR), Azure Blob Storage 원문 저장, PostgreSQL `regulatory_documents` 신규 테이블 메타데이터 기록, SHA-256 중복 제거, robots.txt 준수 + rate limiting, Application Insights 구조화 JSON 로깅, 수동 트리거 API, CI/CD 확장, EARS 인수 기준(REQ-CRAWLER-001~015) 정의.

---

## 0. 범위 및 의존성

### 0.1 SPEC 개요

| 항목 | 내용 |
|------|------|
| SPEC-ID | SPEC-CRAWLER-001 |
| 제목 | Cloud Control Plane — Regulatory Document Crawler |
| 상태 | completed |
| 대상 디렉터리 | `cloud-control-plane/` (신규, Python FastAPI 마이크로서비스) |
| 분석 기준 | `.moai/specs/SPEC-CRAWLER-001/research.md`(코드베이스 분석), SPEC-INFRA-001 §0.2~0.4(Container App placeholder), Product 3계층 아키텍처 |
| 라이프사이클 | spec-anchored (애플리케이션 코드와 함께 유지) |
| 개발 방법론 | TDD (RED-GREEN-REFACTOR) |
| Priority | medium |

### 0.2 이 SPEC이 다루는 것 (In Scope)

- 신규 `cloud-control-plane/` 디렉터리 생성 — `customer-runtime/` 구조(`src/app/`, `docker/`, `requirements.txt`)를 미러링한 Python 3.13 FastAPI 마이크로서비스
- SPEC-INFRA-001이 생성한 `cloud-control-plane-api` Container App placeholder 이미지(`mcr.microsoft.com/k8se/quickstart:latest`, `infra/terraform/environments/prod/main.tf` 라인 94)를 실제 크롤러 이미지로 교체
- 다중 소스 크롤링: FDA(US regulatory guidance), MFDS(Korea), EU MDR(EUR-Lex 2017/745)
- Azure Container App Job(`crawler-job`) 신규 Terraform 리소스 — cron 스케줄(daily 02:00 UTC, 설정 가능)
- Azure Blob Storage 원문 저장: `regulatory-docs/{source}/{YYYY-MM-DD}/{filename}` 경로 규약
- PostgreSQL `regulatory_documents` 신규 테이블 — 메타데이터만 기록(원문 바이트 미기록)
- SHA-256 콘텐츠 해시 기반 중복 제거(변경 없으면 skip)
- robots.txt 준수 + source당 1 req/sec rate limiting + 지수 백오프(3회 재시도)
- Application Insights 구조화 JSON 로깅
- 수동 트리거 API: `POST /crawl/trigger`, `GET /crawl/status/{job_id}`, `GET /health`
- CI/CD 확장: `.github/workflows/deploy-prod.yml`에 크롤러 build+push 추가

### 0.3 이 SPEC이 다루지 않는 것 (Exclusions — What NOT to Build)

[HARD] 아래 항목은 SPEC-CRAWLER-001 구현 범위에서 명시적으로 제외한다. spec.md는 WHAT/WHY만 다루며 구현 세부(함수명/클래스 구조/API 스키마)는 Run 단계로 위임한다.

| 제외 항목 | 사유 | 담당 |
|-----------|------|------|
| 규제 문서 15필드 파싱/추출 | 크롤러는 원문 수집·저장까지만 책임. 파싱은 별도 엔진 | SPEC-PARSER-001 (완료) |
| customer-runtime 스키마/모델 수정 | 크롤러는 Cloud Control Plane 전용. `regulatory_documents`는 신규 테이블 | 본 SPEC(신규 테이블만) |
| Customer Local Runtime 동기화 로직 | 크롤러는 수집까지만. 지식팩 동기화는 Secure Sync Layer 책임 | 미래 SPEC |
| Container App / PostgreSQL / Blob 인프라 프로비저닝 | placeholder는 SPEC-INFRA-001에서 생성 완료. 본 SPEC은 이미지 교체 + Job 추가만 | SPEC-INFRA-001 (완료) |
| OCR(스캔 PDF 텍스트화) 및 문서 포맷 변환 | 크롤러는 원문 바이트 저장만. 포맷 처리는 파서 책임 | SPEC-PARSER-001 (완료) |
| 규제 변경 알림/이메일 발송 | 알림 도메인 분리 | 미래 SPEC |
| 멀티테넌트 격리(tenant_id) | Cloud Control Plane은 중앙 공용 데이터. 테넌트 분리 불필요 | 비범위 |

### 0.4 연관 SPEC 및 의존성

- **선행 의존(완료)**: SPEC-INFRA-001 — Container App placeholder(`cloud-control-plane-api`), PostgreSQL Flexible Server, Blob Storage, ACR, Application Insights 프로비저닝
- **선행 의존(완료)**: SPEC-PARSER-001 — 15필드 추출 엔진. 크롤러가 수집한 문서는 향후 이 엔진에서 처리(본 SPEC 범위 외)
- **재사용 패턴**: `customer-runtime/src/app/services/storage.py`(StorageService), `database.py`(async engine), `config.py`(pydantic-settings), `parser_engine/llm_fallback.py`(httpx.AsyncClient 패턴)

### 0.5 아키텍처 원칙 (불변 제약)

[HARD] 크롤러는 Cloud Control Plane에서 실행되며 customer-runtime 내부에서 실행되지 않는다. 신규 `cloud-control-plane/` 디렉터리에 독립한다.
[HARD] 원문 바이트는 Blob에만 저장하고 PostgreSQL에는 메타데이터(PII 없음)만 기록한다 (FR-210 Data Sovereignty 준수).
[HARD] source당 최대 1 req/sec를 초과하지 않으며 robots.txt disallow 경로는 크롤링하지 않는다.

---

## 1. 아키텍처

※ 본 절의 디렉터리 구조, 모듈 파일명, 클래스명, 구현 세부(리소스명/cron/런타임/Dockerfile 패턴)는 비규범적 설계 제안이며, Run 단계에서 변경될 수 있습니다. (Non-normative design note)

### 1.0 구현 세부 메모 (Non-normative)

- **스케줄 잡 (REQ-CRAWLER-013 구현 제안)**: Azure Container App Job 리소스명 `crawler-job`, cron 스케줄 `0 2 * * *`(daily 02:00 UTC). Terraform `infra/terraform/environments/prod/main.tf`에 정의.
- **컨테이너 패키징 (REQ-CRAWLER-014 구현 제안)**: Python 3.13 + uv 기반 multi-stage Dockerfile(`customer-runtime/docker/Dockerfile` 빌드 패턴 일관). 빌드 산출물은 Azure Container Apps에 배포.

### 1.1 디렉터리 구조

```
cloud-control-plane/                  # [NEW] customer-runtime 구조 미러링
├── src/app/
│   ├── main.py                       # [NEW] FastAPI app factory, lifespan, routers
│   ├── config.py                     # [NEW] Settings (pydantic-settings) — 크롤러 설정
│   ├── database.py                   # [NEW] SQLAlchemy async engine init
│   ├── models/
│   │   ├── base.py                   # [NEW] Base, TimestampMixin (customer-runtime 패턴 재사용)
│   │   └── regulatory_document.py    # [NEW] RegulatoryDocument ORM 모델
│   ├── schemas/
│   │   └── crawl.py                  # [NEW] Pydantic 요청/응답 모델
│   ├── routers/
│   │   ├── health.py                 # [NEW] GET /health
│   │   └── crawl.py                  # [NEW] POST /crawl/trigger, GET /crawl/status/{job_id}
│   ├── services/
│   │   ├── crawler/
│   │   │   ├── base.py               # [NEW] CrawlerSource 추상 베이스(robots.txt, rate limit, retry)
│   │   │   ├── fda.py                # [NEW] FDA source
│   │   │   ├── mfds.py               # [NEW] MFDS source
│   │   │   └── eu_mdr.py             # [NEW] EU MDR (EUR-Lex) source
│   │   ├── storage.py                # [NEW] Blob 업로드(customer-runtime StorageService 패턴)
│   │   ├── dedup.py                  # [NEW] SHA-256 해시 중복 검사
│   │   └── orchestrator.py           # [NEW] 크롤 잡 조율(소스 순회, 실패 격리)
│   └── core/
│       ├── ratelimit.py              # [NEW] source당 1 req/sec 토큰버킷
│       └── logging.py                # [NEW] 구조화 JSON 로거(Application Insights)
├── docker/Dockerfile                 # [NEW] Multi-stage (Python 3.13 + uv)
├── requirements.txt                  # [NEW] uv export 의존성
└── tests/                            # [NEW] pytest 유닛 + @pytest.mark.integration

infra/terraform/environments/prod/
└── main.tf                           # [MODIFY] 라인 94 placeholder 이미지 교체 + crawler-job 추가

.github/workflows/
└── deploy-prod.yml                   # [MODIFY] 크롤러 build+push 스텝 추가
```

### 1.2 모듈 설계 원칙

- `services/crawler/base.py`의 `CrawlerSource` 추상 베이스가 robots.txt 조회, rate limiting, 지수 백오프 재시도, User-Agent 설정을 공통 제공한다. FDA/MFDS/EU MDR는 source별 URL 발견 로직만 구현한다.
- `orchestrator.py`는 소스를 순차 순회하며 한 소스 실패가 다른 소스를 중단시키지 않는다(실패 격리).
- httpx.AsyncClient를 단일 세션으로 재사용하여 connection pooling을 적용한다(`parser_engine/llm_fallback.py` 패턴 참조).
- Blob 업로드는 `customer-runtime/src/app/services/storage.py`의 boto3 S3 호환 패턴을 재사용한다.

### 1.3 실행 모드 분리

| 모드 | 구현 | 용도 |
|------|------|------|
| Container App Job (`crawler-job`) | cron `0 2 * * *`(daily 02:00 UTC), Terraform 정의 | 스케줄 크롤링. 장기 실행 API 서버가 아닌 잡 단위 실행 |
| Container App API (`cloud-control-plane-api`) | FastAPI, `/crawl/trigger` / `/crawl/status` / `/health` | 수동 트리거 + 모니터링 |

[HARD] 스케줄 크롤링은 Container App Job으로 실행한다(장기 실행 API 서버가 크롤링을 수행하지 않는다).

### 1.4 Blob 경로 규약

```
regulatory-docs/{source}/{YYYY-MM-DD}/{filename}
```

- `{source}`: `fda` | `mfds` | `eu-mdr` (소문자 고정)
- `{YYYY-MM-DD}`: 크롤 실행일(UTC)
- `{filename}`: 원본 파일명(충돌 시 SHA-256 prefix 부가)

### 1.5 통합 흐름

```
crawler-job (cron)  →  orchestrator
  → CrawlerSource.discover()  (robots.txt 확인, rate-limited fetch)
  → dedup.check(sha256)       (해시 일치 시 skip)
  → storage.upload(blob_path) (원문 바이트 → Blob)
  → regulatory_documents INSERT (메타데이터만)
  → JSON 로그 → Application Insights
```

---

## 2. EARS 요구사항

요구사항은 5개 모듈로 그룹화한다: M1(수집·저장), M2(데이터 무결성), M3(안정성·준수), M4(관측성·API), M5(배포·CI).

### M1 — 수집 및 저장

**REQ-CRAWLER-001 (Event-Driven, Scheduled crawling)**
When the `crawler-job` cron schedule fires at 02:00 UTC daily, the crawler shall fetch new regulatory documents from each enabled source (FDA, MFDS, EU MDR) and store raw bytes to Azure Blob Storage.

**REQ-CRAWLER-002 (Ubiquitous, Blob path convention)**
The crawler shall store every fetched document in Azure Blob Storage under the path `regulatory-docs/{source}/{YYYY-MM-DD}/{filename}`, where `{source}` is one of `fda`, `mfds`, `eu-mdr`.

### M2 — 데이터 무결성

**REQ-CRAWLER-003 (Event-Driven, Hash computation)**
When the crawler fetches a document, it shall compute the SHA-256 hash of the document's raw byte content.

**REQ-CRAWLER-003b (Unwanted Behavior, Deduplication skip)**
If the computed SHA-256 hash matches an existing `regulatory_documents.content_hash` record in the database, then the crawler shall skip Blob Storage upload and database row insertion for that document.

**REQ-CRAWLER-004 (Event-Driven, Metadata write)**
When a new (non-duplicate) document is successfully stored to Blob, the crawler shall insert a metadata row into the PostgreSQL `regulatory_documents` table containing source, blob_path, content_hash, fetched_at, and source_url — and shall NOT write raw document content to PostgreSQL.

### M3 — 안정성 및 준수

**REQ-CRAWLER-005 (Unwanted Behavior, Retry)**
If a network error or non-2xx HTTP response occurs while fetching a document, then the crawler shall retry the fetch up to 3 times with exponential backoff (initial delay 2s, multiplier 2).

**REQ-CRAWLER-006 (Unwanted Behavior, Failure continuation)**
If all retry attempts for a document fetch are exhausted, then the crawler shall log the failure and continue processing the next document without aborting the job.

**REQ-CRAWLER-007 (Ubiquitous, robots.txt read)**
The crawler shall read each source's robots.txt before crawling any URL from that source.

**REQ-CRAWLER-008 (Ubiquitous, robots.txt disallow)**
The crawler shall NOT fetch any URL that is disallowed by that source's robots.txt.

**REQ-CRAWLER-009 (State-Driven, Rate limiting)**
While crawling a source, the crawler shall not exceed 1 request per second.

### M4 — 관측성 및 API

**REQ-CRAWLER-010 (Ubiquitous, Structured logging)**
The crawler shall emit structured JSON log entries (with fields: timestamp, level, source, event, document_count, job_id) to Application Insights for every crawl job lifecycle event.

**REQ-CRAWLER-011 (Event-Driven, Manual trigger API)**
When a client sends `POST /crawl/trigger`, the API shall start an asynchronous crawl job and return a `job_id`.

**REQ-CRAWLER-012 (Event-Driven, Job status API)**
When a client sends `GET /crawl/status/{job_id}`, the API shall return the current status of that job.

### M5 — 배포 및 CI

**REQ-CRAWLER-013 (Ubiquitous, Scheduled execution)**
The system shall support scheduled daily execution of the crawler via a dedicated infrastructure job resource.

**REQ-CRAWLER-014 (Ubiquitous, Container packaging)**
The crawler shall be packaged as a container image deployable to Azure Container Apps.

**REQ-CRAWLER-015 (Event-Driven, CI/CD)**
When a release tag matching `v*` is pushed, the `deploy-prod.yml` workflow shall build the crawler image, push it to ACR, and deploy it to the `cloud-control-plane-api` Container App and `crawler-job`.

---

## 3. 데이터 모델

### 3.1 `regulatory_documents` 테이블 (신규)

```sql
CREATE TABLE regulatory_documents (
    doc_id          VARCHAR(36)  PRIMARY KEY,            -- uuid4
    source          VARCHAR(16)  NOT NULL,               -- 'fda' | 'mfds' | 'eu-mdr'
    source_url      VARCHAR(1024) NOT NULL,              -- 원문 URL
    blob_path       VARCHAR(512) NOT NULL,               -- regulatory-docs/{source}/{date}/{filename}
    filename        VARCHAR(255) NOT NULL,
    content_hash    VARCHAR(64)  NOT NULL,               -- SHA-256 hex
    content_type    VARCHAR(128) NULL,                   -- MIME type
    byte_size       BIGINT       NULL,
    fetched_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ux_regdoc_content_hash ON regulatory_documents (content_hash);
CREATE INDEX ix_regdoc_source_fetched ON regulatory_documents (source, fetched_at);
```

- `content_hash` UNIQUE 인덱스가 DB 레벨 중복 방지를 보장한다(REQ-CRAWLER-003b 보강).
- 원문 바이트 컬럼은 존재하지 않는다(FR-210 준수). PII 컬럼 없음.
- `customer-runtime` 스키마(`documents`, `parse_jobs`)는 수정하지 않는다.

---

## 4. What NOT to Build (Exclusions 요약)

§0.3 참조. 최소 3개 핵심 제외:

1. **15필드 파싱/추출** — SPEC-PARSER-001 책임. 크롤러는 원문 수집·저장까지만.
2. **customer-runtime 스키마 수정** — `regulatory_documents`는 Cloud Control Plane 전용 신규 테이블. 기존 `documents`/`parse_jobs` 미수정.
3. **인프라 프로비저닝** — Container App/PostgreSQL/Blob은 SPEC-INFRA-001에서 생성 완료. 본 SPEC은 placeholder 이미지 교체 + `crawler-job` 추가만.
4. **OCR / 포맷 변환** — 원문 바이트 저장만. 텍스트화는 파서 책임.

---

## 5. 보안 및 컴플라이언스

- [HARD] PostgreSQL에는 원문/PII를 기록하지 않는다(FR-210). 원문은 암호화된 Blob에만 저장.
- [HARD] robots.txt disallow 준수, source당 1 req/sec 상한.
- 외부 요청에 식별 가능한 User-Agent를 설정한다.
- Blob/PostgreSQL 자격 증명은 환경 변수(Key Vault data source)로만 주입한다.

---

## 6. 전문가 자문 권장

- **expert-backend**: FastAPI 비동기 잡 오케스트레이션, httpx connection pooling, SQLAlchemy async 패턴
- **expert-devops**: Azure Container App Job cron 구성, ACR 이미지 태깅, deploy-prod.yml OIDC 확장

---

## 7. 인수 기준 연결

각 REQ는 하나 이상의 AC에 대응한다. 상세 Given/When/Then 시나리오는 `acceptance.md` 참조.

| REQ | AC |
|-----|-----|
| REQ-CRAWLER-001 | AC-001 |
| REQ-CRAWLER-002 | AC-001 (blob path 검증) |
| REQ-CRAWLER-003 | AC-002 (해시 계산) |
| REQ-CRAWLER-003b | AC-002 (중복 skip) |
| REQ-CRAWLER-004 | AC-001 (metadata 검증) |
| REQ-CRAWLER-005 | AC-004 (재시도) |
| REQ-CRAWLER-006 | AC-004 (실패 시 로그+continue) |
| REQ-CRAWLER-007 | AC-006 (robots.txt 재조회) |
| REQ-CRAWLER-008 | AC-006 (disallow skip) |
| REQ-CRAWLER-009 | AC-003 (rate limit) |
| REQ-CRAWLER-010 | AC-005 (로그 검증) |
| REQ-CRAWLER-011 | AC-005 (trigger) |
| REQ-CRAWLER-012 | AC-005 (status) |
| REQ-CRAWLER-013 | AC-008 (Terraform Job 정의 검증) |
| REQ-CRAWLER-014 | AC-007 |
| REQ-CRAWLER-015 | AC-007 |
