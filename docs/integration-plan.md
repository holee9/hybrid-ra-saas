# 연동 교차검증 보고서: hybrid-ra-saas ↔ ra-med-bot (Regula)

**작성일:** 2026-06-12  
**작성 근거:** 양 프로젝트 소스 코드 직접 분석 (코드 레벨 교차검증)  
**범위:** 이 문서는 hybrid-ra-saas(Azure 백엔드) 측에서 수행해야 할 연동 준비 작업을 정의한다.  
ra-med-bot(Regula UI) 내부 구현은 해당 레포에서 별도 진행한다.

---

## 1. 각 프로젝트 현황 비교표

### 1.1 hybrid-ra-saas (이 레포)

| 구성요소 | 구현 상태 | 위치 |
|---------|----------|------|
| Cloud Control Plane (FastAPI) | ✅ 운영 중 | `cloud-control-plane/src/app/` |
| 규제 크롤러 (FDA / EU MDR / MFDS) | ✅ 구현 완료 | `cloud-control-plane/src/app/services/crawler/` |
| Customer Local Runtime (FastAPI) | ✅ 운영 중 | `customer-runtime/src/app/` |
| `/sync/manifest` API | ✅ 구현 완료 | `customer-runtime/src/app/routers/sync.py` |
| `/rag/query` API | ✅ 구현 완료 | `customer-runtime/src/app/routers/rag.py` |
| `/documents/upload` + `/parse/jobs/{id}` | ✅ 구현 완료 | `customer-runtime/src/app/routers/` |
| `/guardrail/run` | ✅ 구현 완료 | `customer-runtime/src/app/routers/guardrail.py` |
| `/audit/export` | ✅ 구현 완료 | `customer-runtime/src/app/routers/audit.py` |
| JWT Bearer 인증 | ✅ 구현 완료 | `customer-runtime/src/app/core/security.py` |
| **Vectorize 지식 Push 엔드포인트** | ❌ 미구현 | — |
| **ra-med-bot API Key 인증 미들웨어** | ❌ 미구현 | — |
| **CORS: regula.abyz-lab.work 허용** | ❌ 미설정 | `.env.example`, `deploy-prod.yml` |
| **Cloud Control Plane CORS 미들웨어** | ❌ 없음 | `cloud-control-plane/src/app/main.py` |

**Azure 엔드포인트:**  
`https://api-prod.victoriousforest-c9f2300f.koreacentral.azurecontainerapps.io`

### 1.2 ra-med-bot / Regula (별도 레포: `D:/workspace-github/ra-med-bot/`)

| 구성요소 | 구현 상태 | 위치 |
|---------|----------|------|
| Next.js 15 + Auth.js v5 UI | ✅ 운영 중 (Vercel) | `app/` |
| Auth: 세션 쿠키 (`authjs.session-token`) | ✅ 구현 완료 | `middleware.ts`, `middleware-edge.ts` |
| pgvector RAG (`internal` scope) | ✅ 구현 완료 | `lib/ai/retrievers/` |
| `/api/ra/consult` (SSE RAG 상담) | ✅ 구현 완료 | `app/api/ra/consult/` |
| `/api/ra/sources` (지식 베이스 통계) | ✅ 구현 완료 | `app/api/ra/sources/` |
| `/api/admin/radar/health` (크롤러 상태) | ✅ 구현 완료 | `app/api/admin/radar/health/` |
| Radar Phase 10 Cloudflare Workers 크롤러 | ✅ 정의됨 (wrangler.toml) | FDA/EU OJ/MFDS 크론 |
| **Cloudflare Vectorize 바인딩** | ❌ 미완료 | `.env.example` `CLOUDFLARE_VECTORIZE_INDEX_NAME=` (빈 값) |
| **SPEC-REGULA-VECTORIZE-001** | ❌ Pending | `lib/ai/hybrid-router.ts` |
| **hybrid-ra-saas 연동 env vars** | ❌ 없음 | `.env.example`에 `HYBRID_RA_*` 없음 |
| **지식 동기화 수신 엔드포인트** | ❌ 없음 | — |

---

## 2. 연동 인터페이스 갭 목록

### GAP-01 [P0 BLOCKER] CORS: regula.abyz-lab.work 미허용

**현황:**
- Customer Runtime 프로덕션: `CORS_ORIGINS=*` (`.github/workflows/deploy-prod.yml` line 142)
- Cloud Control Plane: CORS 미들웨어 자체 없음 (`main.py` 에 `CORSMiddleware` 없음)
- ra-med-bot이 Azure API를 직접 호출 시 CORS 차단 위험 (향후 `*` 제거 시)

**필요 조치 (이 레포):**
1. `deploy-prod.yml`: `CORS_ORIGINS=*` → `CORS_ORIGINS=https://regula.abyz-lab.work,https://api-prod.victoriousforest-c9f2300f.koreacentral.azurecontainerapps.io`
2. Cloud Control Plane `main.py`에 `CORSMiddleware` 추가 (regula.abyz-lab.work 허용)
3. `.env.example` 기본값 업데이트

---

### GAP-02 [P0 BLOCKER] 인증 브릿지: JWT Bearer ↔ Auth.js 세션 쿠키

**현황:**
- hybrid-ra-saas: `Authorization: Bearer <jwt_token>` (JWT, HS256)
- ra-med-bot: Auth.js v5 세션 쿠키 (`authjs.session-token`)
- 서버 간(ra-med-bot backend → hybrid-ra-saas) 호출 시 사용할 인증 수단 미정의

**설계 결정:**  
ra-med-bot → hybrid-ra-saas 호출은 **서버 사이드 API Key 패턴**으로 처리한다.  
(사용자 세션 쿠키를 백엔드 간 전달하는 방식은 보안상 부적절)

**필요 조치 (이 레포):**
1. Customer Runtime에 API Key 인증 미들웨어 추가 (`X-Regula-API-Key` 헤더)
2. `config.py`에 `regula_api_key: str` 설정 추가
3. `deps.py`에 `get_regula_client()` 의존성 추가 (API Key 검증)
4. `.env.example`에 `REGULA_API_KEY=` 항목 추가
5. GitHub Secrets에 `REGULA_API_KEY` 등록 필요

**ra-med-bot 측 (별도 레포 작업):**
- `.env.example`에 `HYBRID_RA_API_KEY=`, `HYBRID_RA_API_URL=` 추가
- 서버 사이드 fetch 헤더: `X-Regula-API-Key: ${process.env.HYBRID_RA_API_KEY}`

---

### GAP-03 [P0 BLOCKER] Vectorize 지식 동기화 파이프라인 없음

**현황:**
- hybrid-ra-saas Cloud Control Plane: FDA/EU MDR/MFDS 문서를 크롤링 → Azure Blob/PostgreSQL 저장
- ra-med-bot: `CLOUDFLARE_VECTORIZE_INDEX_NAME=` (빈 값) — Vectorize 미연결, pgvector fallback 사용 중
- `SPEC-REGULA-VECTORIZE-001` (ra-med-bot 내 `lib/ai/hybrid-router.ts`) pending 상태
- **두 레포 사이에 문서 동기화 메커니즘이 전혀 없음**

**아키텍처 결정:**  
Cloud Control Plane 크롤 완료 후 → Cloudflare Workers를 통해 Vectorize에 upsert하는  
**Push 방식(Webhook trigger)**이 Pull 폴링보다 적합하다. (실시간성, Azure Egress 절감)

**필요 조치 (이 레포):**

```
Cloud Control Plane (Azure)
  POST /crawl/trigger → run_crawl_job() 완료 후
  → POST https://regula.abyz-lab.work/api/admin/radar/sync  (신규 엔드포인트, ra-med-bot 측)
     Body: { job_id, source, documents: [{id, url, hash, content}] }
     Auth: X-Crawl-Push-Secret: ${CRAWL_PUSH_SECRET}
```

1. `cloud-control-plane/src/app/services/orchestrator.py`:  
   크롤 완료 후 `knowledge_push_service.push(documents)` 호출 추가
2. `cloud-control-plane/src/app/services/` 에 `knowledge_push.py` 신규 작성:  
   HTTP POST to `REGULA_KNOWLEDGE_PUSH_URL`, signed with `CRAWL_PUSH_SECRET`
3. `cloud-control-plane/src/app/config.py`에 추가:
   - `regula_knowledge_push_url: str = ""`  
   - `crawl_push_secret: str = ""`
4. `.env.example`에 해당 항목 추가
5. GitHub Secrets: `REGULA_KNOWLEDGE_PUSH_URL`, `CRAWL_PUSH_SECRET`

---

### GAP-04 [P1] 크롤러 중복 운영

**현황:**
- hybrid-ra-saas `cloud-control-plane`: FastAPI 크롤러 (FDA, EU MDR, MFDS)
- ra-med-bot `wrangler.toml` Phase 10: Cloudflare Workers 크롤러  
  (FDA Federal Register 18:15 UTC, EU OJ 18:45 UTC, MFDS 19:15 UTC)
- **동일 규제 출처를 양측에서 독립적으로 크롤링** — 정보 불일치 위험

**결정 필요:**

| 역할 분리 방안 | 설명 |
|-------------|------|
| **Option A (권장):** hybrid-ra-saas = 단일 크롤러, ra-med-bot = 소비자 | Azure 크롤러 완료 → Push → Vectorize. ra-med-bot Phase 10 크롤러는 **비활성화** |
| Option B: 독립 운영, 주기 조율 | ra-med-bot Phase 10 크롤러가 다른 데이터 소스 커버 시 유지 (EU OJ = 다른 출처) |

**현재 권장:** Option A. EU OJ와 FDA Federal Register가 실제로 base crawlers와 중복이면 ra-med-bot Phase 10 cron 비활성화.  
이 결정은 ra-med-bot 레포 작업에서 확인 후 반영.

**이 레포 조치:**
- `docs/integration-plan.md`에 결정 사항 기록 (이 문서)
- Cloud Control Plane 크롤러가 단일 소스 오브 트루스로 지정될 경우: 크롤러 범위를 EU OJ 포함으로 확장 검토 필요

---

### GAP-05 [P1] Customer Runtime RAG ↔ ra-med-bot RAG 라우팅 미정의

**현황:**
- hybrid-ra-saas: `/rag/query` → 고객사 로컬 문서 RAG (온프레미스)
- ra-med-bot `/api/ra/consult`: public_corpus(Vectorize) + internal(pgvector) RAG
- **Enterprise 고객사가 ra-med-bot에서 자사 IFU/SOP 기반 RAG를 원할 때** 어떤 경로?

**설계 결정:**  
ra-med-bot `hybridRetrieve(scope='internal')` → pgvector(Neon) = ra-med-bot 자체 DB  
고객사 로컬 문서 RAG = Customer Runtime 직접 접근 (별도 URL, VPN/Zero Trust)  
ra-med-bot에서 Customer Runtime `/rag/query`를 프록시하는 API 추가는 **P2 이후** 검토.

**이 레포 필요 조치 (P1):**
- Customer Runtime `config.py`에 `regula_allowed_tenants: str = ""` 추가  
  (ra-med-bot → Customer Runtime 호출을 허용할 tenant 목록, 쉼표 구분)
- `/rag/query` 엔드포인트에 API Key 인증 경로 추가 (GAP-02 API Key 패턴 재사용)

---

### GAP-06 [P2] 감사 로그(Audit Trail) 연계 없음

**현황:**
- hybrid-ra-saas: `/audit/export` — 규제 감사 로그 CSV/JSON 내보내기
- ra-med-bot: 감사 로그 수신 기능 없음

**필요 조치 (P2, 이 레포):**
- `POST /audit/webhook` 신규 엔드포인트 추가: 규제 이벤트 발생 시 Regula로 push
- `config.py`에 `regula_audit_webhook_url: str = ""`

---

### GAP-07 [P2] IFU 파서 결과를 Regula context에 연결 없음

**현황:**
- hybrid-ra-saas: `/documents/upload` → `/parse/jobs/{id}` → IFU 파싱 결과 (requirements, risks, controls)
- ra-med-bot: 자체 document upload API 있음 (`/api/ra/admin/documents/upload`) — 별개로 운영 중

**필요 조치 (P2, 이 레포):**
- 파싱 완료 후 Regula에 구조화된 IFU 데이터 push webhook 추가
- 또는 ra-med-bot이 `/parse/jobs/{id}` 결과를 직접 폴링하는 방식

---

## 3. hybrid-ra-saas에서 해야 할 작업 (이 레포 전용)

### P0 — 연동 차단 해제 (구현 전 필수)

| 작업 | 파일 | 유형 |
|-----|------|------|
| Cloud Control Plane CORS 미들웨어 추가 | `cloud-control-plane/src/app/main.py` | 코드 수정 |
| Customer Runtime CORS 운영 환경 명시적 허용 | `deploy-prod.yml` line 142 | 설정 수정 |
| Customer Runtime API Key 인증 미들웨어 | `customer-runtime/src/app/core/security.py` | 코드 추가 |
| `config.py` — regula_api_key 항목 추가 | `customer-runtime/src/app/config.py` | 코드 수정 |
| knowledge_push.py 서비스 신규 작성 | `cloud-control-plane/src/app/services/knowledge_push.py` | 신규 파일 |
| orchestrator.py — 크롤 완료 후 push 호출 | `cloud-control-plane/src/app/services/orchestrator.py` | 코드 수정 |
| `.env.example` 연동 항목 추가 | `.env.example` | 설정 수정 |
| GitHub Secrets 등록 | Repository Settings | 운영 작업 |

### P1 — 연동 안정화

| 작업 | 파일 | 유형 |
|-----|------|------|
| Customer Runtime tenant allowlist 설정 | `customer-runtime/src/app/config.py` | 코드 수정 |
| `/rag/query` API Key 인증 경로 추가 | `customer-runtime/src/app/routers/rag.py` | 코드 수정 |
| 크롤러 범위 결정 후 EU OJ 추가 여부 확인 | `cloud-control-plane/src/app/services/crawler/` | 코드 추가 (검토 후) |

### P2 — 기능 확장

| 작업 | 파일 | 유형 |
|-----|------|------|
| `/audit/webhook` 엔드포인트 추가 | `customer-runtime/src/app/routers/audit.py` | 코드 추가 |
| IFU 파싱 완료 후 Regula webhook push | `customer-runtime/src/app/jobs/parse_job.py` | 코드 수정 |

---

## 4. 단계별 연동 계획 (P0 → P3)

### Phase 0: 연동 차단 해제 (이 레포 P0 완료 + ra-med-bot P0 완료 후)

**성공 기준:**  
ra-med-bot 백엔드에서 `HYBRID_RA_API_URL` + `HYBRID_RA_API_KEY`로  
`GET /health` 호출 → `200 OK` 반환 확인

```
hybrid-ra-saas                         ra-med-bot (Regula)
──────────────────────────────────     ────────────────────────────────
[P0-1] CORS: regula.abyz-lab.work  →   브라우저 fetch 허용
[P0-2] API Key 미들웨어 추가       →   X-Regula-API-Key 헤더 인증
[P0-3] knowledge_push.py 작성      →   [별도 레포] /api/admin/radar/sync 수신
```

### Phase 1: 지식 동기화 (Vectorize 연결)

**성공 기준:**  
Azure 크롤러 트리거 → 24시간 내 ra-med-bot Vectorize에 문서 반영  
`GET /api/ra/sources` 응답에서 `sectionCount > 0` 확인

```
cloud-control-plane crrawl 완료
  → knowledge_push.push(documents)
  → POST /api/admin/radar/sync  (ra-med-bot, 별도 구현)
  → Cloudflare Workers: Vectorize.upsert(embeddings)
  → hybridRetrieve(scope='public_corpus') → Vectorize 검색 성공
```

**이 레포 작업:**
- `orchestrator.py` 크롤 완료 후 push 호출
- `knowledge_push.py` HTTP client 구현

**ra-med-bot 레포 작업 (별도):**
- `SPEC-REGULA-VECTORIZE-001` 구현 완료
- `/api/admin/radar/sync` 수신 엔드포인트 구현
- `CLOUDFLARE_VECTORIZE_INDEX_NAME` 설정

### Phase 2: 기업용 RAG 브릿지 (Enterprise 고객)

**성공 기준:**  
ra-med-bot `/api/ra/consult`에서 고객사 IFU 기반 검색 결과 포함 확인

```
ra-med-bot UI 상담 요청
  → hybridRetrieve(scope='public_corpus')  → Vectorize
  → [NEW] hybridRetrieve(scope='enterprise') → Customer Runtime /rag/query
     X-Regula-API-Key: ${HYBRID_RA_API_KEY}
     X-Tenant-ID: ${tenant_id}
  → 결과 병합 → 응답
```

**이 레포 작업:**
- `/rag/query` API Key 인증 경로 추가
- tenant allowlist 검증 미들웨어

### Phase 3: 감사/파서 완전 연계

**성공 기준:**  
규제 문서 업로드 → IFU 파싱 → Regula 상담 context에 자동 반영

```
Customer Runtime
  POST /documents/upload → 파싱 완료 → AuditEvent 생성
  → POST /audit/webhook (Regula)
  → Regula UI: 최신 IFU 요건 기반 상담 가능
```

---

## 5. API 컨트랙트 명세

### 5.1 Knowledge Push (Cloud Control Plane → ra-med-bot)

**신규 — 이 레포에서 발신, ra-med-bot에서 수신**

```
POST https://regula.abyz-lab.work/api/admin/radar/sync
Headers:
  Content-Type: application/json
  X-Crawl-Push-Secret: <CRAWL_PUSH_SECRET>

Body:
{
  "job_id": "uuid",
  "source": "eu_mdr" | "fda" | "mfds",
  "crawled_at": "2026-06-12T18:00:00Z",
  "documents": [
    {
      "id": "uuid",
      "url": "https://eur-lex.europa.eu/...",
      "title": "EU MDR Annex XIV",
      "content": "...",        // 원문 텍스트 (max 100KB per doc)
      "hash": "sha256:...",    // 중복 방지
      "language": "en",
      "regulation_type": "EU_MDR" | "FDA_510K" | "MFDS_고시"
    }
  ]
}

Response:
  202 Accepted — { "received": N, "queued_for_embedding": M }
  401 Unauthorized — Invalid secret
  422 Unprocessable Entity — Schema validation error
```

### 5.2 Customer Runtime RAG (ra-med-bot → Customer Runtime)

**기존 엔드포인트에 API Key 인증 경로 추가**

```
POST https://api-prod.victoriousforest-c9f2300f.koreacentral.azurecontainerapps.io/rag/query
Headers:
  Content-Type: application/json
  X-Regula-API-Key: <HYBRID_RA_API_KEY>   // NEW: API Key 인증
  X-Tenant-ID: <tenant_id>

Body:
{
  "query": "IFU 요구사항 조회...",
  "top_k": 5,
  "filters": { "document_type": "IFU" }
}

Response:
  200 OK — { "results": [...], "sources": [...] }
  401 Unauthorized — Invalid API Key
  403 Forbidden — Tenant not in allowlist
```

### 5.3 Health Check (ra-med-bot → Customer Runtime, 연동 검증용)

```
GET https://api-prod.victoriousforest-c9f2300f.koreacentral.azurecontainerapps.io/health
Headers:
  X-Regula-API-Key: <HYBRID_RA_API_KEY>

Response:
  200 OK — { "status": "ok", "version": "1.0.0" }
```

---

## 6. 환경변수 체크리스트

### 6.1 hybrid-ra-saas (이 레포) — 추가 필요

```dotenv
# Customer Runtime (.env.example 추가)
REGULA_API_KEY=                    # ra-med-bot → Customer Runtime 인증 키 (32자 이상)
REGULA_ALLOWED_TENANTS=            # 쉼표 구분 tenant ID 목록 (빈 값 = 전체 허용)
CORS_ORIGINS=https://regula.abyz-lab.work,http://localhost:3000   # 현재: localhost:8080

# Cloud Control Plane (.env.example 추가)
REGULA_KNOWLEDGE_PUSH_URL=https://regula.abyz-lab.work/api/admin/radar/sync
CRAWL_PUSH_SECRET=                 # 32자 이상 랜덤 시크릿 (openssl rand -hex 32)
```

### 6.2 ra-med-bot (별도 레포) — 추가 필요

```dotenv
# 이 레포에서 정의한 계약에 맞게 ra-med-bot 측 추가 필요
HYBRID_RA_API_URL=https://api-prod.victoriousforest-c9f2300f.koreacentral.azurecontainerapps.io
HYBRID_RA_API_KEY=                 # REGULA_API_KEY와 동일 값
CLOUDFLARE_VECTORIZE_INDEX_NAME=regula-public-corpus   # SPEC-REGULA-VECTORIZE-001
CRAWL_PUSH_SECRET=                 # 이 레포 CRAWL_PUSH_SECRET과 동일 값
```

### 6.3 GitHub Secrets 등록 목록 (이 레포)

| Secret 이름 | 용도 |
|------------|------|
| `REGULA_API_KEY` | Customer Runtime API Key 인증 |
| `CRAWL_PUSH_SECRET` | Cloud Control Plane → ra-med-bot Push 서명 |
| `REGULA_KNOWLEDGE_PUSH_URL` | Push 대상 URL |

---

## 7. 문서 개정 필요 항목

이 계획 수립에 따라 아래 문서를 별도 개정한다:

| 문서 | 개정 항목 | 우선순위 |
|------|----------|---------|
| `docs/bizplan.md` | §1 4레이어 아키텍처, §4 Regula SaaS 수익 모델, §6 파트너십 전략 | P0 |
| `docs/mrd.md` | §3 Regula SaaS vs Enterprise MVP 분리, §6 Vectorize 연동 요구사항 | P1 |
| `docs/prd.md` | §2 아키텍처 4번째 레이어(Regula SaaS), §10.2 GAP-T09 UI 화면 명세 | P1 |
| `README.md` | P0~P3 연동 로드맵 업데이트 (이 문서 기반) | P0 |

---

## 8. 연동 검증 시나리오

연동 완료 후 아래 시나리오로 E2E 검증한다:

### 시나리오 1: 지식 동기화 (Phase 1 완료 기준)
1. `POST /crawl/trigger` 호출 (또는 cron 트리거)
2. 크롤 완료 후 `GET /crawl/status/{job_id}` → `completed` 확인
3. ra-med-bot `GET /api/admin/radar/health` → `updates_last_24h > 0` 확인
4. ra-med-bot `GET /api/ra/sources` → `sectionCount > 0` (Vectorize 반영) 확인

### 시나리오 2: Regula → Customer Runtime RAG (Phase 2 완료 기준)
1. ra-med-bot에서 유효한 `X-Regula-API-Key` 헤더로 `/rag/query` 호출
2. `200 OK` + 관련 문서 청크 반환 확인
3. 잘못된 API Key → `401 Unauthorized` 확인

### 시나리오 3: 감사 로그 연계 (Phase 3 완료 기준)
1. Customer Runtime에서 규제 검토 이벤트 발생
2. `POST /audit/webhook` 자동 호출 확인
3. ra-med-bot 감사 화면에서 이벤트 수신 확인

---

**관련 GitHub Issues:** 연동 작업 트래킹을 위한 이슈 생성 필요 (아래 §9 참조)

**관련 SPEC:** SPEC-INTEGRATION-001 (별도 SPEC 문서로 승격 검토)

---

*이 문서는 코드 레벨 교차분석 결과를 기반으로 작성되었다.*  
*양 프로젝트의 실제 구현이 진행됨에 따라 주기적으로 업데이트한다.*
