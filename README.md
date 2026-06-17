# hybrid-ra-saas — Regula 백엔드 인프라

**Regula**(ra-med-bot) 를 구동하는 규제 데이터 파이프라인 + 엔터프라이즈 온프레미스 패키지

> 사용자 접점 제품: **https://regula.abyz-lab.work** (ra-med-bot)  
> 이 레포: Regula에 공급되는 규제 지식 파이프라인 및 엔터프라이즈 배포 패키지

---

## 제품 구조

```
사용자 레이어
└── Regula (ra-med-bot)           https://regula.abyz-lab.work
    채팅 · 워크플로우 · 규제 레이더 · RBAC
    Vercel + Cloudflare Workers

            ↑ 규제 지식 공급            ↑ 고객 문서 컨텍스트
            │                          │
인프라 레이어 (이 레포)
├── Cloud Control Plane (Azure)        Customer Local Runtime (Docker)
│   규제 크롤러: FDA · MFDS · EU MDR   IFU 15필드 파서 (NLP 3단계)
│   매일 02:00 UTC → Azure Blob +      Guardrail 검증
│   PostgreSQL                         Audit Export (규제 제출용)
│   → [P0] Regula Vectorize 동기화     Air-gap 강제 (FR-210)
│
└── Azure Terraform IaC
    Container Apps · PostgreSQL · Key Vault · ACR
```

**타깃 품목군:** X-ray 시스템 · 디지털 디텍터 · 촬영실 SW/PACS · 피부미용 초음파

### 제품 티어

| 티어 | 제품 | 배포 | 주요 기능 |
|------|------|------|----------|
| **SaaS** | Regula (ra-med-bot) | Vercel | 규제 상담 채팅, 510k/CER 초안, 규제 레이더 |
| **Enterprise** | Regula Enterprise Edition | Docker Compose (온프레미스) | SaaS 기능 + IFU 파서, Guardrail, Audit Export, Air-gap |

---

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────┐
│            ☁️  Cloud Control Plane (Azure)           │
│  규제 크롤러: FDA · MFDS · EU MDR                    │
│  PostgreSQL + Azure Blob Storage                    │
│  Container App Job (cron 02:00 UTC)                 │
│                                                     │
│  → [P0 통합] Cloudflare Vectorize 자동 동기화         │
│    regula-fda / regula-mfds / regula-eu-mdr 인덱스  │
└──────────────────────┬──────────────────────────────┘
                       │  Outbound HTTPS only
                       │  증분 메타데이터 · 규제 문서 버전관리
┌──────────────────────▼──────────────────────────────┐
│            🛡️  Secure Sync Layer                     │
│  GET /sync/manifest — 변경 메타데이터만 외부 전달      │
└──────────────────────┬──────────────────────────────┘
                       │  Pull 방식 (고객 → 클라우드)
┌──────────────────────▼──────────────────────────────┐
│    🖥️  Customer Local Runtime (Regula Enterprise)    │
│  FastAPI · IFU 15필드 NLP 파서 · Guardrail           │
│  pgvector RAG · Audit Export · Air-gap 강제         │
│                                                     │
│  ⚠️  민감 문서는 이 경계 밖으로 절대 전송하지 않음     │
└─────────────────────────────────────────────────────┘
```

---

## 문서 완성도 현황

> 2026-06-05 SPEC-DOC-001 Run 완료 기준 (v3 교차검증 실측 → Run 반영)

| 문서 | v3 실측 | Run 후 | 85% 상태 |
|------|--------|--------|---------|
| [사업계획서](docs/bizplan.md) | 68% | **85%+** | ✅ 달성 |
| [MRD](docs/mrd.md) | 74% | **87%+** | ✅ 달성 |
| [PRD](docs/prd.md) | 81% | **85%+** | ✅ 달성 |
| 문서 간 일관성 | 68/100 | **90+** | ✅ 달성 |

### 완료 항목 (SPEC-DOC-001 Run)

| ID | 문서 | 섹션 | 상태 |
|----|------|------|------|
| T01 | BizPlan | 팀 구조 템플릿 (실명 `[기재 필요]`) | ✅ 완료 |
| T02 | BizPlan | TAM/SAM/SOM ($6.75B→$11.66B, 9.55% CAGR) | ✅ 완료 |
| T03 | BizPlan | 3년 P&L 3시나리오 + BEP 분석 | ✅ 완료 |
| T04 | BizPlan | 경쟁사 5개 비교표 (Veeva/Sparta/MasterControl/Qara) | ✅ 완료 |
| T05 | MRD | TAM/SAM/SOM (BizPlan §10 동기화) | ✅ 완료 |
| T06 | MRD | 경쟁사 명칭 포지셔닝 매트릭스 | ✅ 완료 |
| T07 | MRD | 사용자 스토리 15개 (As a/I want/So that + MoSCoW) | ✅ 완료 |
| T08 | MRD | 고객 검증 계획 구조 (실데이터 파일럿 후) | ✅ 완료 |
| T09 | PRD | UI/UX 와이어프레임 | ⏳ Phase 2 예정 |
| T10 | PRD | 파서 NLP 명세 (15필드, confidence 공식, 폴백) | ✅ 완료 |
| T11 | PRD | Docker Compose (5서비스 + .env.example) | ✅ 완료 |
| T12 | PRD | OpenAPI 3.1 완전 명세 (7엔드포인트) | ✅ 완료 |
| T13 | PRD | NFR 보안 수치 (TLS 1.3+, RPO/RTO) | ✅ 완료 |
| C03 | 신설 | `docs/shared-facts.md` 단일 출처 파일 | ✅ 완료 |

갭 상세: [`.moai/specs/SPEC-DOC-001/spec.md`](.moai/specs/SPEC-DOC-001/spec.md)

> 📖 **사용 설명서** (RA 담당자 대상): **[https://holee9.github.io/hybrid-ra-saas/user-guide.html](https://holee9.github.io/hybrid-ra-saas/user-guide.html)** — 클릭하면 바로 열림

---

## 구현 현황 (SPEC-API-001)

> 2026-06-08 기준 — Customer Local Runtime FastAPI + Docker Compose 전체 완료

| 항목 | 내용 |
|------|------|
| **엔드포인트** | 7개 (GET /health, POST /documents/upload, POST /parse/jobs, POST /guardrail/run, POST /rag/query, POST /audit/export, GET /sync/manifest) |
| **데이터 모델** | SQLAlchemy 9개 (Product, Document, Requirement, Risk, Control, Evidence, Finding, AuditEvent, ParseJob) + pgvector |
| **인증** | JWT HS256 + X-Tenant-ID (사용자 인증) / Bearer token (서비스간 인증, SPEC-APITOK-001) |
| **Docker** | 5서비스 (api, postgres, minio, ollama, redis) multi-stage 빌드 |
| **테스트** | 299 passed / 0 failed (Docker 통합 테스트는 CI 전용 자동 스킵) |
| **커버리지** | 82% (목표 80% 초과) |
| **lint** | ruff 0 errors |
| **FR-210** | Air-Gap 아웃바운드 검증 구현 완료 |

SPEC 상세: [`.moai/specs/SPEC-API-001/spec.md`](.moai/specs/SPEC-API-001/spec.md)

---

## 구현 현황 (SPEC-APITOK-001)

> 2026-06-16 기준 — Customer Local Runtime 서비스간 Bearer 토큰 인증 완료

| 항목 | 내용 |
|------|------|
| **신규 함수** | `verify_hybrid_bearer_token` (`security.py`) — 기존 `verify_api_key` / JWT 함수 FROZEN |
| **적용 라우터** | 8개 (rag, sync, audit, guardrail, documents, authoring, checklist, evidence) |
| **에러 코드** | 503 (미설정), 401 (잘못된 토큰), 400 (X-Tenant-ID 누락) |
| **환경변수** | `HYBRID_RA_API_TOKEN` (최소 32자) — ra-med-bot 측 `HYBRID_RA_API_BASE_URL`, `HYBRID_RA_TENANT_ID`와 쌍 |
| **테스트** | `test_apitok_001.py` 인증 전용, 299 unit tests pass |
| **계약 문서** | [`docs/integration-contract.md`](docs/integration-contract.md) — ra-med-bot 연동 API 계약 명세 |

SPEC 상세: [`.moai/specs/SPEC-APITOK-001/spec.md`](.moai/specs/SPEC-APITOK-001/spec.md)

---

## 구현 현황 (SPEC-UI-001)

> 2026-06-09 기준 — Customer Local Runtime UI React + TypeScript 완료

| 항목 | 내용 |
|------|------|
| **프레임워크** | React 18 + TypeScript, Vite, SPA |
| **기능** | 15개 IFU 필드 인라인 수정, confidence 시각화 |
| **API 통합** | `PATCH /parse/{job_id}/corrections` 교정 엔드포인트 |
| **테스트** | Vitest + RTL, 83/83 passed |
| **TypeScript** | 0 errors (완전 타입 안전) |
| **인증** | JWT in-memory, X-Tenant-ID 헤더 |
| **Docker** | ui 서비스 (nginx, port 8080) |
| **커버리지** | 85%+ (목표 달성) |

SPEC 상세: [`.moai/specs/SPEC-UI-001/spec.md`](.moai/specs/SPEC-UI-001/spec.md)

---

## 구현 현황 (SPEC-UI-002)

> 2026-06-09 기준 — Customer Local Runtime 검토 큐 화면 완료

| 항목 | 내용 |
|------|------|
| **큐 엔드포인트** | `GET /parse/jobs`: 테넌트 격리, 상태/교정필요 필터, skip/limit 페이지네이션 |
| **스키마** | `JobSummary`, `ListJobsResponse` Pydantic v2 |
| **큐 화면** | React Router 7, `QueuePage`, `JobQueueTable`, StatusTabs(5개), SortControl, Pagination |
| **훅** | `useListJobs`: 클라이언트 정렬 + 5초 자동갱신(running 작업 존재 시) |
| **프론트엔드 테스트** | Vitest + RTL, 113/113 passed |
| **백엔드 테스트** | pytest, 168 passed / 32 skipped(CI 전용) |
| **TypeScript** | 0 errors |
| **커버리지** | 85% (목표 달성) |
| **라우팅** | `/jobs` → QueuePage, `/jobs/:jobId` → CorrectionPanel (SPEC-UI-001 회귀 없음) |

SPEC 상세: [`.moai/specs/SPEC-UI-002/spec.md`](.moai/specs/SPEC-UI-002/spec.md)

---

## 구현 현황 (SPEC-INFRA-001)

> 2026-06-08 기준 — Cloud Control Plane Azure Terraform/IaC 완료

| 항목 | 내용 |
|------|------|
| **IaC 범위** | Azure 리소스 9종 import + 신규 3종 (tfstate, Container App 2개) |
| **Terraform** | >= 1.9.0, azurerm ~> 4.0, OIDC 전용 인증 |
| **모듈** | 5개 (container_registry, container_app_env, postgresql, key_vault, monitoring) |
| **State Backend** | Azure Blob Storage (`sthybridrasaasprod`/`tfstate`) 2단계 부트스트랩 |
| **CI/CD** | terraform.yml 신규 (PR→plan comment, main merge→apply) |
| **보안** | Key Vault 시크릿 data source 전용, OIDC 전용, *.tfvars gitignored |
| **환경** | prod / staging 분리, 공유 Container App Environment |

SPEC 상세: [`.moai/specs/SPEC-INFRA-001/spec.md`](.moai/specs/SPEC-INFRA-001/spec.md)

---

## 구현 현황 (SPEC-CRAWLER-001)

> 2026-06-11 기준 — Cloud Control Plane 규제 문서 크롤러 완료

| 항목 | 내용 |
|------|------|
| **새 서비스** | `cloud-control-plane/` Python 3.13 FastAPI 마이크로서비스 (customer-runtime 구조 미러링) |
| **크롤링 소스** | FDA(US guidance) · MFDS(한국) · EU MDR(EUR-Lex 2017/745) |
| **수집 정책** | robots.txt 준수, source당 1 req/sec rate limit, 지수 백오프 3회 재시도, SSRF netloc 검증 |
| **중복 제거** | SHA-256 콘텐츠 해시 — 변경 없는 문서 자동 skip |
| **저장** | Azure Blob `regulatory-docs/{source}/{YYYY-MM-DD}/{filename}` + PostgreSQL `regulatory_documents` 메타데이터 |
| **API** | `POST /crawl/trigger` (비동기), `GET /crawl/status/{job_id}`, `GET /health` |
| **인프라** | Terraform `crawler-job` Container App Job (cron 02:00 UTC), placeholder 이미지 교체 |
| **CI/CD** | deploy-prod.yml 크롤러 build + push + 배포 스텝 |
| **테스트** | 단위 75 passed (통합 2개는 CI 전용), 커버리지 94%, ruff 0 errors |

SPEC 상세: [`.moai/specs/SPEC-CRAWLER-001/spec.md`](.moai/specs/SPEC-CRAWLER-001/spec.md)

---

## 구현 현황 (SPEC-PARSER-001)

> 2026-06-09 기준 — Customer Local Runtime 동적 파서 NLP 엔진 완료

| 항목 | 내용 |
|------|------|
| **새 패키지** | parser_engine/ (7개 모듈: docx_reader, xlsx_reader, confidence, rule_based, spacy_ner, llm_fallback, errors) |
| **추출 필드** | 15개 IFU 필드 (device_name, intended_use, indications, contraindications, warnings, ...) |
| **파이프라인** | 3단계: 규칙 기반 → spaCy NER → Ollama 로컬 LLM 폴백 (신뢰도 기반 조기 종료) |
| **신뢰도 공식** | 0.50×완전성 + 0.30×규칙매칭 + 0.20×의미유사도 (임계값: 교정 UI 0.85, 거부 0.50) |
| **교정 API** | PATCH /parse/{job_id}/corrections — 필드 수동 교정 + 신뢰도 재계산 |
| **데이터 주권** | Stage 3 LLM은 localhost Ollama 전용 (_assert_local 코드 수준 강제) |
| **언어 지원** | 영어 + 한국어 IFU 문서 (EN/KO 사전 분리) |
| **테스트** | 70개 단위 테스트 통과, parser_engine 커버리지 92.4% (목표 85% 초과) |
| **lint** | ruff 0 errors |
| **하위 호환** | ParserService, StubParserService, ParseResult 인터페이스 유지 |

SPEC 상세: [`.moai/specs/SPEC-PARSER-001/spec.md`](.moai/specs/SPEC-PARSER-001/spec.md)

---

## 구현 현황 (SPEC-JOBQUEUE-001)

> 2026-06-17 기준 — BackgroundTasks → arq 영속 Job Queue 전환 완료

| 항목 | 내용 |
|------|------|
| **전환 대상** | `customer-runtime` + `cloud-control-plane` FastAPI `BackgroundTasks` → arq (async Redis queue) |
| **새 모듈** | `jobs/worker.py`, `jobs/worker_health.py`, `queue/arq_pool.py` (양 서비스 공히) |
| **재시도 / DLQ** | `max_tries=3` 지수 백오프 → 소진 시 `ParseJob.status='failed'` + terminal error 기록 |
| **orphan 복구** | `on_startup`: DB `status='running'` + Redis 부재 작업 → 재적재 또는 `'failed'` 처리 |
| **헬스 신호** | Redis heartbeat TTL key — Azure Container App exec liveness probe |
| **테넌트 격리** | arq 워커 경로 `explicit_tenant_context` 적용 (REQ-TI-010) |
| **API 무변경** | `GET /parse/jobs/{job_id}/status` 응답 스키마 동일 |
| **테스트** | 단위 18개 (arq Redis 모킹, Docker 불필요) + 통합 `skip_no_docker` (CI 전용 실 Redis) |
| **의존성** | `arq>=0.26` 추가 (customer-runtime, cloud-control-plane) |

SPEC 상세: [`.moai/specs/SPEC-JOBQUEUE-001/spec.md`](.moai/specs/SPEC-JOBQUEUE-001/spec.md)

---

## 레포지토리 구조

```
hybrid-ra-saas/
├── customer-runtime/             # Customer Local Runtime (SPEC-API-001 ✅ 완료)
│   ├── src/app/                  # FastAPI 애플리케이션
│   │   ├── routers/              # 7개 엔드포인트 (health, upload, parse, guardrail, rag, audit, sync)
│   │   ├── models/               # SQLAlchemy 9개 모델 (8 엔티티 + ParseJob)
│   │   ├── services/             # 비즈니스 로직 (parser_engine NLP 엔진, storage, guardrail, rag, export, airgap)
│   │   └── core/                 # JWT, rate limit, state machine
│   ├── tests/                    # pytest (162 passed, 86% coverage)
│   ├── alembic/                  # DB 마이그레이션 (pgvector)
│   ├── docker/                   # Dockerfile (multi-stage)
│   └── docker-compose.yml        # 5서비스 (api, postgres, minio, ollama, redis)
│
├── cloud-control-plane/          # Cloud Control Plane 크롤러 (SPEC-CRAWLER-001 ✅ 완료)
│   ├── src/app/                  # FastAPI 애플리케이션
│   │   ├── routers/              # crawl(trigger/status), health
│   │   ├── models/               # regulatory_documents 테이블
│   │   ├── services/             # crawler(fda/mfds/eu_mdr), orchestrator, dedup, storage
│   │   └── core/                 # rate limiter, 구조화 JSON 로깅
│   ├── tests/                    # pytest (75 passed, 94% coverage)
│   ├── alembic/                  # DB 마이그레이션
│   └── docker/                   # Dockerfile
│
├── infra/                        # Cloud Control Plane 인프라 (SPEC-INFRA-001 ✅ 완료)
│   └── terraform/                # Azure Terraform IaC
│       ├── modules/              # 5개 재사용 모듈 (ACR, CAE, PostgreSQL, KeyVault, Monitoring)
│       └── environments/         # prod / staging 환경 분리
│
├── docs/                         # 지식 베이스 (Markdown, 버전 관리) ← 기준
│   ├── user-guide.html           # 📖 RA 담당자용 사용 설명서 → https://holee9.github.io/hybrid-ra-saas/user-guide.html
│   ├── integration-contract.md   # ra-med-bot ↔ hybrid-ra-saas API 계약 명세 (SPEC-APITOK-001)
│   ├── bizplan.md                # 사업계획서 (BizPlan v3.0)
│   ├── mrd.md                    # 시장 요구사항 명세서 (MRD v3.0)
│   └── prd.md                    # 제품 요구사항 명세서 (PRD v3.0)
│
├── archive/                      # 아카이브 (변환 완료, 읽기 전용)
│   ├── 01_사업계획서_v3.0.docx
│   ├── 02_MRD_v3.0.docx
│   ├── 03_PRD_v3.0.docx
│   └── README.txt
│
├── .moai/                        # MoAI 프로젝트 메타데이터
│   ├── project/product.md        # 제품 컨텍스트 요약
│   ├── specs/SPEC-DOC-001/spec.md # 문서 완성도 계획
│   └── specs/SPEC-API-001/spec.md # Customer Local Runtime 구현 SPEC (완료)
│
├── 04_리뷰용_제안서.html           # 이해관계자 제안서 (브라우저 열람)
└── README.md                     # 이 파일
```

> **운영 원칙:** `docs/` 폴더의 Markdown이 **지식 베이스 기준**입니다.  
> `archive/`의 DOCX는 변환 완료된 원본으로, 내용 수정은 Markdown에서만 진행합니다.

---

## 도메인 설정

| 도메인 | 역할 | 대상 |
|--------|------|------|
| `regula.abyz-lab.work` | Regula 사용자 접점 | Vercel (ra-med-bot) |
| `ra.abyz-lab.work` | 엔터프라이즈 API 테스트 엔드포인트 | Azure Container App `api-prod` |

### regula.abyz-lab.work 설정

1. Cloudflare DNS에 `regula.abyz-lab.work` CNAME을 Vercel 대상으로 설정
2. ra-med-bot 레포/Vercel 프로젝트에서 도메인 바인딩과 `NEXTAUTH_URL` 설정
3. ra-med-bot Vercel 대시보드에서 도메인 검증 확인 후 Redeploy

> 현재 이 레포의 workflow는 `ci.yml`, `deploy-staging.yml`, `deploy-prod.yml`, `terraform.yml`입니다. 도메인 바인딩 workflow는 이 레포에 없습니다.

---

## 배포 가이드 (Azure)

> 상세 체크리스트 → [`docs/deployment.md`](docs/deployment.md)

### 빠른 배포 절차

```bash
# 모든 사전 조건 충족 후 (DB 마이그레이션, 환경 변수 설정 완료)
git tag v1.0.0
git push origin v1.0.0
# → deploy-prod.yml 자동 트리거 → Docker 빌드 → ACR push → 배포 → 헬스체크
```

### 배포 대상 서비스

| 서비스 | Container App 이름 | 포트 |
|--------|-------------------|------|
| Customer Runtime API (Regula Enterprise) | `api-prod` | 8000 |
| 규제 문서 크롤러 API | `cloud-control-plane-api` | 8000 |
| 크롤러 스케줄 Job | `crawler-job` | — (cron 02:00 UTC) |

### 첫 배포 전 필수 수동 작업

1. Container App 환경 변수 설정 (Key Vault → `DB-CONNECTION-STRING` 등)
2. DB 마이그레이션 실행 (`alembic upgrade head` — 두 서비스 각각)

> 자세한 내용: [`docs/deployment.md`](docs/deployment.md)

---

## 통합 로드맵 (Regula ↔ hybrid-ra-saas)

| 우선순위 | 작업 | 설명 |
|----------|------|------|
| **P0** | 크롤러 → Vectorize 자동 동기화 | 매일 수집된 FDA/MFDS/EU MDR 문서를 Regula Cloudflare Vectorize 인덱스로 자동 push. Regula 지식베이스를 항상 최신 상태 유지 |
| **P1** | IFU 파서 → Regula 프로젝트 컨텍스트 | 고객사가 IFU DOCX 업로드 → 15필드 NLP 추출 → Regula 프로젝트에 기기 컨텍스트 저장. "내 X-ray 기기가 EU MDR Class IIa 요건에 맞나요?" 쿼리 가능 |
| **P2** | Audit trail 연동 | Regula 상담/결정 이벤트 → Audit log → FDA/MDR 제출용 AI 어시스턴트 추적 패키지 export |
| **P3** | Regula Enterprise 리브랜딩 | Customer Runtime을 Regula Enterprise Edition으로 포지셔닝, Docker 이미지/README/API 헤더 정렬 |

---

## 비즈니스 모델

| 플랜 | 가격 | 제품 | 대상 |
|------|------|------|------|
| **Regula SaaS** | $299/월 | ra-med-bot (Vercel) | 스타트업 / 개인 RA 전문가 |
| **Regula Enterprise** | $12,000/년 | Customer Runtime (Docker) | 중견 의료기기 제조사 / 내부망 필요 기업 |
| **Setup & Enablement** | 별도 견적 | 설치 + 교육 패키지 | 초기 엔터프라이즈 배포 고객 |
| **Regulatory Pack Add-on** | 제품군/국가별 과금 | 추가 규제 지식팩 | 확장 고객 (NMPA, PMDA 등) |

---

## 핵심 지표 목표

| 지표 | 목표 | 측정 방법 |
|------|------|---------|
| 핵심 필드 파싱 정확도 | 85%+ | 수동 라벨링 정답 세트 비교 |
| 핵심 문서세트 검토 시간 | 10분 이내 | IFU/SRS/RMS/시험요약 샘플 기준 |
| 규제 변경 알림 반영 | 24시간 이내 | 소스 변경 → 큐 생성 시각 비교 |
| 표준 패키지 설치 | 1일 이내 | 체크리스트 완료 시간 측정 |
| 문서 준비 기간 단축 | 30~50% | 파일럿 전후 소요 시간 비교 |

---

## GitHub Actions 워크플로우

| 워크플로우 | 트리거 | 역할 |
|-----------|--------|------|
| `ci.yml` | PR → `main`, `develop` | Customer Runtime Python, Cloud Control Plane Python, Customer Runtime UI lint/test/build |
| `deploy-staging.yml` | `main` push / 수동 | staging Container App Docker 빌드 → ACR push → 배포 → 헬스체크 |
| `deploy-prod.yml` | `v*` 태그 push | Cloud Control Plane + Customer Runtime Docker 빌드 → ACR push → Container App 배포 |
| `terraform.yml` | PR / main merge | Azure 인프라 Terraform plan / apply |

> Secrets 설정 방법 → [`docs/secrets-setup.md`](docs/secrets-setup.md)

---

## 로드맵

| 단계 | 목표 | 핵심 산출물 |
|------|------|-----------|
| **완료** | Customer Runtime API + 파서 + UI + 인프라 + 크롤러 + Bearer 인증 | 7개 SPEC 완료 (API/PARSER/UI-001/UI-002/INFRA/CRAWLER/APITOK) |
| **P0 — 구현 완료 / 운영 검증 필요** | 크롤러 → Regula Vectorize 자동 동기화 | `KnowledgePushService`, `REGULA_KNOWLEDGE_PUSH_URL`, `CRAWL_PUSH_SECRET` |
| **P1 — 구현 완료 / 운영 검증 필요** | IFU 파서 → Regula 프로젝트 컨텍스트 연동 | `/rag/query` API key 인증, tenant allowlist |
| **P2 — 구현 완료 / 운영 검증 필요** | Audit trail / IFU webhook 연동 | `/audit/webhook`, `REGULA_AUDIT_WEBHOOK_URL`, `REGULA_IFU_WEBHOOK_URL` |
| **P3 — 예정** | Regula Enterprise 리브랜딩 | Docker 이미지 태그, README, API 헤더 |

품질 보강 추적: [#24](https://github.com/holee9/hybrid-ra-saas/issues/24), [#25](https://github.com/holee9/hybrid-ra-saas/issues/25), [#26](https://github.com/holee9/hybrid-ra-saas/issues/26), [#27](https://github.com/holee9/hybrid-ra-saas/issues/27). 템플릿-우선 제품 개편: [#29](https://github.com/holee9/hybrid-ra-saas/issues/29). 연동 구현 이력: [#23](https://github.com/holee9/hybrid-ra-saas/issues/23).

---

## 참고 문헌

| # | 출처 |
|---|------|
| 1 | [FDA, Overview of Device Regulation](https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/overview-device-regulation) |
| 2 | [FDA, Cybersecurity in Medical Devices (Premarket Submissions)](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cybersecurity-medical-devices-quality-management-system-considerations-and-content-premarket) |
| 3 | [EUR-Lex, Regulation (EU) 2017/745 (EU MDR)](https://eur-lex.europa.eu/eli/reg/2017/745/oj/eng) |
| 4 | [European Commission, Medical Devices / EUDAMED](https://health.ec.europa.eu/medical-devices-sector_en) |
| 5 | [MFDS, Medical Device Regulations](https://www.mfds.go.kr/eng/brd/m_40/list.do) |
| 6 | [pgvector, PostgreSQL vector similarity search](https://github.com/pgvector/pgvector) |

---

> ⚠️ 이 문서는 제품·사업 설계 문서입니다. 실제 인허가 제출 전에는 각 국가 규제기관의 최신 원문과 RA 전문가 검토가 필요합니다.

---

*버전: v6.2 | 최종 갱신: 2026-06-16 | 구현 완료: Customer Runtime ✅ | Terraform IaC ✅ | 규제 크롤러 ✅ | Bearer 인증 ✅ | API 계약 명세 ✅ | 다음: P0 크롤러→Regula Vectorize 동기화*
