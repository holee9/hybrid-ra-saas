# Global Hybrid AI RA Specialist

의료기기 제조사를 위한 하이브리드 AI 규제 운영(RA) 플랫폼 — 기획 패키지 v3.0

---

## 프로젝트 개요

공개 규제 지식(FDA · MFDS · EU MDR)을 클라우드에서 수집·관리하고,  
민감 문서(설계치·임상 원자료·소스코드)는 **고객 내부망 Docker 런타임**에서만 처리하는  
**데이터 주권 중심 셀프서비스 규제 운영 플랫폼**입니다.

> 핵심 포지셔닝: 컨설팅 대행이 아니라, **표준화된 셀프서비스 규제 운영 플랫폼**

---

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────┐
│            ☁️  Cloud Control Plane                   │
│  규제 크롤러 / 정규화 파이프라인 / PostgreSQL+pgvector │
│  S3 Archive / EventBridge / CloudWatch / Budgets    │
└──────────────────────┬──────────────────────────────┘
                       │  Outbound HTTPS only
                       │  증분 메타데이터 · 지식팩 버전관리
                       │  고객사별 테넌트 격리
┌──────────────────────▼──────────────────────────────┐
│            🛡️  Secure Sync Layer                     │
└──────────────────────┬──────────────────────────────┘
                       │  Pull 방식 (고객 → 클라우드)
┌──────────────────────▼──────────────────────────────┐
│         🖥️  Customer Local Runtime (Docker)          │
│  n8n Orchestrator / FastAPI / Dynamic Parser        │
│  Unified Schema Store / Traceability Graph          │
│  Ollama/vLLM RAG / Review UI / Audit Log            │
│                                                     │
│  ⚠️  민감 문서는 이 경계 밖으로 절대 전송하지 않음     │
└─────────────────────────────────────────────────────┘
```

**타깃 품목군:** X-ray 시스템 · 디지털 디텍터 · 촬영실 SW/PACS · 피부미용 초음파

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

---

## 구현 현황 (SPEC-API-001)

> 2026-06-08 기준 — Customer Local Runtime FastAPI + Docker Compose 전체 완료

| 항목 | 내용 |
|------|------|
| **엔드포인트** | 7개 (GET /health, POST /documents/upload, POST /parse/jobs, POST /guardrail/run, POST /rag/query, POST /audit/export, GET /sync/manifest) |
| **데이터 모델** | SQLAlchemy 9개 (Product, Document, Requirement, Risk, Control, Evidence, Finding, AuditEvent, ParseJob) + pgvector |
| **인증** | JWT HS256 + X-Tenant-ID 멀티테넌시 |
| **Docker** | 5서비스 (api, postgres, minio, ollama, redis) multi-stage 빌드 |
| **테스트** | 92 passed / 0 failed (Docker 통합 테스트 23개는 CI 전용 자동 스킵) |
| **커버리지** | 82% (목표 80% 초과) |
| **lint** | ruff 0 errors |
| **FR-210** | Air-Gap 아웃바운드 검증 구현 완료 |

SPEC 상세: [`.moai/specs/SPEC-API-001/spec.md`](.moai/specs/SPEC-API-001/spec.md)

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
| Customer Runtime API | `api-prod` | 8000 |
| 규제 문서 크롤러 API | `cloud-control-plane-api` | 8000 |
| 크롤러 스케줄 Job | `crawler-job` | — (cron 02:00 UTC) |

### 첫 배포 전 필수 수동 작업

1. Container App 환경 변수 설정 (Key Vault → `DB-CONNECTION-STRING` 등)
2. DB 마이그레이션 실행 (`alembic upgrade head` — 두 서비스 각각)

> 자세한 내용: [`docs/deployment.md`](docs/deployment.md)

---

## 비즈니스 모델

| 플랜 | 가격 | 대상 | 구성 |
|------|------|------|------|
| **Core SaaS** | $299/월 | 스타트업/초기팀 | 규제 변경 알림 + 기본 지식팩 + 표준 템플릿 |
| **Advanced Hybrid** | $12,000/년 | 중견/내부망 기업 | 로컬 Docker 에이전트 + 정합성 가드레일 + 감사로그 |
| **Setup & Enablement** | 별도 견적 | 초기 배포 고객 | 환경 점검 + 설치 + 교육 |
| **Regulatory Pack Add-on** | 제품군/국가별 과금 | 확장 고객 | 추가 품목군·국가 규제 지식팩 |

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

## 로드맵

| 단계 | 기간 | 목표 | 핵심 산출물 |
|------|------|------|-----------|
| **Phase 1 Infra** | 0~8주 | 규제 수집/저장/동기화 PoC | 크롤러, 지식팩 버전, 웹훅 알림 |
| **Phase 2 Logic** | 8~16주 | 품목군 스키마 + 파서 튜닝 | Unified Schema v0.9, DOCX/XLSX 파서 |
| **Phase 3 Product** | 16~28주 | 로컬 런타임 + 검토 워크스페이스 | Docker 패키지, Review UI, Traceability Graph |
| **Phase 4 Scale** | 28주~ | 품목/국가/파트너 확장 | Add-on 지식팩, 파트너 운영 매뉴얼 |

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

*버전: v5.2 | 최종 갱신: 2026-06-11 | 구현 완료: Customer Runtime ✅ | Terraform IaC ✅ | 규제 크롤러 ✅ | 다음: Azure 배포 검증*
