---
id: SPEC-UI-002
version: 0.1.0
status: draft
created_at: 2026-06-09
updated: 2026-06-09
author: drake.lee
priority: high
issue_number: 16
labels: ["spec", "ui", "frontend", "backend"]
---

# SPEC-UI-002: 검토 큐 화면 (Review Queue Screen)

## HISTORY

- 2026-06-09 (v0.1.0): 초안 작성. SPEC-UI-001(완료, PR #15)에서 명시적으로 제외했던 "검토 큐 화면"을 정의. 여러 파싱 작업을 목록으로 표시하고 상태 탭/정렬/필터/페이지네이션을 제공하며, 행 클릭 시 SPEC-UI-001 교정 화면으로 이동한다. 풀스택 SPEC으로 백엔드 `GET /parse/jobs` 신규 엔드포인트를 포함한다. (author: drake.lee)

---

## §0 범위 (Scope)

### 0.1 목적

단일 RA 실무자가 모든 파싱 작업(parse jobs)을 한 화면에서 조망하고, 상태별로 필터링하여 교정이 필요한 작업을 신속히 찾아 SPEC-UI-001 교정 화면으로 진입할 수 있는 검토 큐 화면을 제공한다. PRD의 "10분 검토" 목표(작업 발견 → 진입 → 교정)를 달성하는 진입점(entry point)이 핵심 가치다.

본 SPEC은 풀스택 범위로, 큐 목록을 제공하는 백엔드 신규 엔드포인트 `GET /parse/jobs`와 이를 소비하는 프론트엔드 큐 화면 및 라우팅을 함께 정의한다.

### 0.2 In-Scope (포함 범위)

**백엔드**
- 신규 엔드포인트 `GET /parse/jobs`: 페이지네이션(skip/limit) + 상태 필터(status) + 교정 필요 필터(requires_correction)
- 테넌트 격리: 기존 `get_current_tenant` 의존성 적용
- 신규 스키마 `JobSummary`, `ListJobsResponse`

**프론트엔드**
- React Router 7(`react-router-dom`) 도입 및 `App.tsx` 라우터 리팩터
- 라우트: `/jobs`(큐 목록), `/jobs/:jobId`(SPEC-UI-001 교정 화면)
- 큐 페이지: `QueuePage`, `JobQueueTable`, `JobStatusBadge`, 상태 탭, 정렬 컨트롤, 페이지네이션
- 신규 훅 `useListJobs`: 목록 로드 + 처리중(running) 작업에 대한 폴링(5초)
- 신규 타입 `JobSummary`, `ListJobsResponse`

**테스트 / 배포**
- Vitest: 큐 컴포넌트 및 `useListJobs` 훅 단위/컴포넌트 테스트
- pytest: `GET /parse/jobs` 엔드포인트 테스트
- Azure Container Apps 배포: Dockerfile + nginx.conf가 배포를 지원하도록 보장(`CORS_ORIGINS` 설정 포함)

### 0.3 Exclusions (What NOT to Build)

다음 항목은 본 SPEC 범위에서 **명시적으로 제외**한다. 별도 SPEC에서 다룬다.

- **파일 업로드/파싱 트리거 UI**: 문서 업로드 및 파싱 작업 생성 화면은 별도 SPEC. 본 SPEC은 이미 생성된 작업만 조회한다.
- **벌크 액션(bulk actions)**: 다중 선택 삭제, 일괄 재처리(batch reprocess) 등은 본 SPEC 미포함.
- **팀/멀티유저 큐 공유**: 단일 RA 실무자 가정. 사용자 ID 기반 필터/할당/공유는 제외. 테넌트 격리만 적용.
- **인증 화면(로그인/토큰 발급)**: JWT는 외부에서 주입받는다고 가정. 로그인 UI는 본 SPEC 미포함.
- **다국어(i18n) UI**: 한국어 단일 로케일만 지원. 다국어는 후행 SPEC.
- **트레이서빌리티 그래프 / 감사 로그 뷰어**: 작업 이력 시각화 화면은 본 SPEC 범위 밖.

### 0.4 Dependencies (의존성)

- **선행**: SPEC-UI-001 (완료, PR #15 merged) — `CorrectionPanel` 및 교정 화면 컴포넌트/훅 제공. 본 SPEC의 `/jobs/:jobId` 라우트가 이를 렌더링한다.
- **선행**: SPEC-PARSER-001 (완료) — `ParseJob` 모델, `ParseJobStatus`(pending/running/done/failed), 기존 `GET /parse/jobs/{job_id}`, `PATCH /parse/{job_id}/corrections` 제공.
- **신규**: 백엔드 `GET /parse/jobs` 엔드포인트는 본 SPEC에서 구현한다(기존에 존재하지 않음).
- **신규**: `customer-runtime/ui`에 `react-router-dom`(React Router 7) 의존성 추가.

---

## §1 아키텍처 (Architecture)

### 3-레이어 컨텍스트

- **Cloud Control Plane (Azure)**: 규제 데이터/스토리지 — 본 SPEC 직접 변경 없음.
- **Secure Sync Layer**: outbound HTTPS only — 본 SPEC 직접 변경 없음.
- **Customer Local Runtime (Docker compose)**: api + ui + postgres + minio + ollama + redis — 본 SPEC의 변경 대상은 `api`(엔드포인트 추가)와 `ui`(큐 화면/라우팅)다.

### 디렉터리 구조 (delta 표기)

```
customer-runtime/
├── docker-compose.yml            # 변경 없음 (ui 서비스 기존 존재)
├── src/app/
│   ├── routers/
│   │   └── parse.py              # [MODIFY] GET /parse/jobs 엔드포인트 추가
│   ├── schemas/
│   │   └── parse.py              # [NEW] JobSummary, ListJobsResponse 스키마 추가
│   └── models/
│       └── parse_job.py          # 변경 없음 (ParseJob, ParseJobStatus 재사용)
└── ui/src/
    ├── App.tsx                   # [MODIFY] React Router 도입, 라우터로 리팩터
    ├── main.tsx                  # [MODIFY] BrowserRouter 래핑
    ├── pages/
    │   └── QueuePage.tsx         # [NEW] 큐 페이지 (탭/정렬/페이지네이션 컨테이너)
    ├── components/
    │   ├── JobQueueTable.tsx     # [NEW] 작업 목록 테이블
    │   ├── JobStatusBadge.tsx    # [NEW] 상태 배지 (대기/처리중/완료/실패)
    │   ├── StatusTabs.tsx        # [NEW] 상태 탭 (전체/대기/처리중/완료/실패)
    │   ├── SortControl.tsx       # [NEW] 정렬 컨트롤 (작성일/신뢰도, 최신순/오래된순)
    │   ├── Pagination.tsx        # [NEW] 페이지네이션 (이전/다음/현재 페이지)
    │   ├── CorrectionPanel.tsx   # 기존 (SPEC-UI-001) — /jobs/:jobId에서 재사용
    │   ├── FieldRow.tsx          # 기존
    │   ├── ConfidenceBadge.tsx   # 기존 — 신뢰도 색상 규칙 재사용
    │   ├── StageIndicator.tsx    # 기존
    │   └── RejectedBanner.tsx    # 기존
    ├── hooks/
    │   ├── useListJobs.ts        # [NEW] GET /parse/jobs + running 폴링(5초)
    │   ├── useParseJob.ts        # 기존
    │   └── useCorrections.ts     # 기존
    ├── types/
    │   ├── jobs.ts               # [NEW] JobSummary, ListJobsResponse 타입
    │   └── parse.ts              # 기존
    └── lib/
        ├── api.ts                # 기존 apiFetch() 재사용
        └── toast.tsx            # 기존 토스트 Context 재사용
```

### 라우팅 구조

```
BrowserRouter
└── Routes
    ├── /              → Navigate to /jobs (redirect)
    ├── /jobs          → QueuePage
    │                     ├── StatusTabs
    │                     ├── SortControl
    │                     ├── JobQueueTable
    │                     │   └── (row) → JobStatusBadge, ConfidenceBadge
    │                     └── Pagination
    └── /jobs/:jobId   → CorrectionPanel (SPEC-UI-001, jobId from useParams)
```

기존 SPEC-UI-001은 `?job_id=<uuid>` 쿼리 파라미터로 교정 화면을 단일 페이지로 렌더링했다. 본 SPEC에서 라우팅을 도입하며 교정 화면 진입을 `/jobs/:jobId` 경로 파라미터 기반으로 통합한다. `CorrectionPanel`은 `useParams().jobId`로 작업 ID를 받도록 진입부만 조정한다(컴포넌트 내부 로직 변경 없음).

---

## §2 데이터 모델

### 2.1 백엔드 스키마 ([NEW] `customer-runtime/src/app/schemas/parse.py`)

기존 `ParseJob` 모델(`models/parse_job.py`)을 목록 요약 형태로 노출하는 신규 스키마를 추가한다.

```python
# schemas/parse.py (추가)
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class JobSummary(BaseModel):
    job_id: str
    doc_id: str
    status: str                      # ParseJobStatus: pending/running/done/failed
    overall_confidence: Optional[float] = None
    created_at: datetime
    error: Optional[str] = None
    requires_correction: bool


class ListJobsResponse(BaseModel):
    total: int
    items: List[JobSummary]
```

### 2.2 프론트엔드 타입 ([NEW] `customer-runtime/ui/src/types/jobs.ts`)

백엔드 스키마를 TypeScript로 미러링한다.

```typescript
export type JobStatus = "pending" | "running" | "done" | "failed";

export interface JobSummary {
  job_id: string;
  doc_id: string;
  status: JobStatus;
  overall_confidence: number | null;
  created_at: string; // ISO 8601
  error: string | null;
  requires_correction: boolean;
}

export interface ListJobsResponse {
  total: number;
  items: JobSummary[];
}

// 상태 탭 정의 (전체 + 4개 상태)
export const STATUS_TABS = [
  { key: "all", label: "전체", status: null },
  { key: "pending", label: "대기", status: "pending" },
  { key: "running", label: "처리중", status: "running" },
  { key: "done", label: "완료", status: "done" },
  { key: "failed", label: "실패", status: "failed" },
] as const;

export type SortField = "created_at" | "confidence";
export type SortOrder = "newest" | "oldest";

export const PAGE_SIZE = 50;
```

---

## §3 컴포넌트 및 엔드포인트 설계

### 3.1 백엔드: `GET /parse/jobs` ([MODIFY] `routers/parse.py`)

| 항목 | 사양 |
|------|------|
| 경로 | `GET /parse/jobs` |
| 쿼리 파라미터 | `skip: int = 0`, `limit: int = 50`, `status: Optional[str] = None`, `requires_correction: Optional[bool] = None` |
| 응답 | `ListJobsResponse` → `{ total: int, items: List[JobSummary] }` |
| 정렬 | `created_at` 기준 내림차순(최신순) 기본 |
| 테넌트 격리 | `get_current_tenant` 의존성으로 현재 테넌트의 작업만 조회 |

동작:
- `status`가 주어지면 해당 상태의 작업만 필터링한다(유효 값: pending/running/done/failed).
- `requires_correction`이 주어지면 해당 boolean과 일치하는 작업만 필터링한다.
- `total`은 필터 적용 후 전체 개수(페이지네이션 이전), `items`는 `skip`/`limit` 적용 후 페이지다.
- 잘못된 `status` 값은 422를 반환한다.

### 3.2 QueuePage ([NEW])

- `useListJobs` 훅으로 현재 탭/정렬/페이지에 해당하는 목록을 로드한다.
- 상단에 `StatusTabs`(전체/대기/처리중/완료/실패)와 `SortControl`을 배치한다.
- 본문에 `JobQueueTable`을 렌더링한다.
- 하단에 `Pagination`(total > 50일 때)을 표시한다.
- 로딩/빈 상태/에러 상태를 구분 표시한다(빈 상태: "표시할 작업이 없습니다").

### 3.3 JobQueueTable ([NEW])

- 컬럼: 상태(JobStatusBadge), 신뢰도(overall_confidence를 %로, ConfidenceBadge 색상 규칙 적용), 작성일(created_at 포맷).
- 각 행은 클릭 가능하며 클릭 시 `/jobs/:jobId`로 이동한다(React Router `navigate`).
- `requires_correction=true`인 행은 교정 필요 인디케이터(시각적 강조)를 표시한다.
- 신뢰도 색상은 SPEC-UI-001 규칙 재사용: ≥0.85 green-100/green-800, ≥0.75 yellow-100/yellow-800, <0.75 red-100/red-800. `overall_confidence=null`이면 "-" 표시.

### 3.4 JobStatusBadge ([NEW])

| status | 라벨 | 색상 (Tailwind) |
|--------|------|----------------|
| `pending` | 대기 | gray-100 / gray-800 |
| `running` | 처리중 | blue-100 / blue-800 |
| `done` | 완료 | green-100 / green-800 |
| `failed` | 실패 | red-100 / red-800 |

### 3.5 StatusTabs ([NEW])

- `STATUS_TABS` 5개 탭을 렌더링한다.
- 선택된 탭은 강조(active) 스타일(예: border-b-2 border-blue-600, text-blue-600)을 적용한다.
- 탭 선택 시 `status` 필터를 변경하고 페이지를 1로 리셋한다.

### 3.6 SortControl ([NEW])

- 정렬 필드(작성일/신뢰도)와 순서(최신순/오래된순) 선택.
- 정렬 변경 시 목록을 재정렬하고 페이지를 1로 리셋한다.

### 3.7 Pagination ([NEW])

- 이전/다음 버튼 + 현재 페이지/전체 페이지 표시.
- `total <= 50`이면 페이지네이션을 숨긴다.
- 첫 페이지에서 이전 버튼, 마지막 페이지에서 다음 버튼을 비활성화한다.

### 3.8 useListJobs ([NEW])

- 입력: `{ status, sortField, sortOrder, page }`.
- `GET /parse/jobs?skip={page*50}&limit=50&status={status}`를 호출한다.
- 응답을 `{ items, total, loading, error }`로 노출한다.
- **폴링**: 현재 목록에 `status="running"` 작업이 하나 이상 있으면 5초 간격으로 자동 재조회한다. running 작업이 없으면 폴링을 중단한다.
- 정렬은 클라이언트 측에서 적용한다(백엔드 기본 정렬은 created_at 내림차순). 신뢰도 정렬은 `overall_confidence` 기준, null은 후순위.

---

## §4 API 통합

### 엔드포인트

| 동작 | 메서드 | 경로 | 용도 |
|------|--------|------|------|
| 목록 조회 | GET | `/parse/jobs` | `ListJobsResponse` 로드 (본 SPEC 신규) |
| 단건 조회 | GET | `/parse/jobs/{job_id}` | 교정 화면 진입 시 (SPEC-UI-001 재사용) |
| 교정 저장 | PATCH | `/parse/{job_id}/corrections` | 교정 화면 저장 (SPEC-UI-001 재사용) |

### 인증 헤더 (`src/lib/api.ts` 재사용)

```
Authorization: Bearer {jwt}
X-Tenant-ID: {tenant_id}
Content-Type: application/json
```

### 에러 처리

| 상태 코드 | 처리 |
|-----------|------|
| 401 | 인증 실패 토스트. 목록 비활성화 |
| 422 | 잘못된 쿼리 파라미터 토스트(예: 잘못된 status) |
| 네트워크/타임아웃 | 에러 토스트 + 재시도 안내. 폴링은 다음 주기에 재시도 |

---

## §5 Azure Container Apps 배포

- 기존 인프라: Container Apps Environment `cae-hybrid-ra-saas-staging`, Container Registry `acrhybridrasaasprod.azurecr.io`.
- UI Docker 서비스: nginx:alpine(port 8080) — `docker-compose.yml`에 기존 존재.
- 기존 GitHub Actions: `.github/workflows/deploy-staging.yml`(push → develop).
- 본 SPEC은 라우팅 도입으로 SPA 폴백이 필수다. nginx.conf는 `try_files $uri $uri/ /index.html`로 클라이언트 라우팅(`/jobs`, `/jobs/:jobId`)을 지원해야 한다.
- `CORS_ORIGINS` 설정이 staging 도메인을 포함하도록 보장한다.
- Dockerfile은 Vite 빌드 산출물(`dist/`)을 nginx로 서빙하며 ACR 푸시/Container Apps 배포가 가능하도록 구성한다.

---

## §6 EARS 요구사항

### REQ-Q-001 (Event-Driven)

**When** 사용자가 `/jobs`로 이동하면, the system **shall** 모든 파싱 작업을 상태(status), 신뢰도(confidence %), 작성일(created_at) 컬럼을 가진 정렬 가능한 테이블로 표시한다.

### REQ-Q-002 (Event-Driven)

**When** 사용자가 상태 탭(전체/대기/처리중/완료/실패) 중 하나를 선택하면, the system **shall** 해당 상태의 작업만 보이도록 목록을 필터링한다.

### REQ-Q-003 (Event-Driven)

**When** 사용자가 작업 행을 클릭하면, the system **shall** `/jobs/:jobId`로 이동하여 SPEC-UI-001 `CorrectionPanel`을 렌더링한다.

### REQ-Q-004 (State-Driven)

**While** `requires_correction`이 true이면, the system **shall** 해당 작업 행을 교정 필요 인디케이터로 시각적으로 강조한다.

### REQ-Q-005 (State-Driven)

**While** 목록에 status가 "처리중(running)"인 작업이 존재하면, the system **shall** 사용자 조작 없이 5초마다 목록을 자동 갱신한다.

### REQ-Q-006 (Ubiquitous)

The backend **shall** `GET /parse/jobs`를 skip/limit/status/requires_correction 쿼리 파라미터와 함께 제공하며, 현재 테넌트로 범위가 제한된 작업 요약(JobSummary) 목록을 반환한다.

### REQ-Q-007 (Event-Driven)

**When** 사용자가 신뢰도(confidence) 또는 작성일(created_at) 기준으로 정렬하면, the system **shall** 테이블을 해당 기준으로 재정렬한다.

### REQ-Q-008 (State-Driven)

**While** 작업 수가 50개를 초과하면, the system **shall** 페이지네이션 컨트롤(이전/다음, 현재 페이지 표시)을 표시한다.

---

## §7 인수 기준 (Acceptance Criteria)

EARS 형식 인수 기준. 상세 Given-When-Then 시나리오는 `acceptance.md`에 정의한다.

### AC-001 (Event-Driven)
**When** 사용자가 `/jobs`에 진입하면, the system **shall** `GET /parse/jobs`를 호출하여 작업 목록을 상태·신뢰도·작성일 컬럼을 포함한 테이블로 렌더링한다.

### AC-002 (Event-Driven)
**When** 사용자가 상태 탭(전체/대기/처리중/완료/실패)을 선택하면, the system **shall** 선택된 상태 파라미터로 `GET /parse/jobs?status=<value>`를 재호출하여 필터된 목록만 표시한다.

### AC-003 (Event-Driven)
**When** 사용자가 작업 행을 클릭하면, the system **shall** `/jobs/:jobId`로 이동하여 SPEC-UI-001 `CorrectionPanel`을 렌더링한다.

### AC-004 (State-Driven)
**While** running 상태 작업이 목록에 존재하면, the system **shall** 5초 간격으로 `GET /parse/jobs`를 자동 재호출하여 목록을 갱신한다.

### AC-005 (Event-Driven)
**When** `GET /parse/jobs`가 호출되면, the system **shall** 현재 테넌트의 작업만 반환하며 다른 테넌트의 작업을 포함하지 않는다.

---

## §8 보안 (Security)

- **테넌트 격리**: `GET /parse/jobs`는 `get_current_tenant` 의존성으로 현재 테넌트의 작업만 반환한다. 다른 테넌트 작업이 목록에 노출되지 않는다.
- **JWT 보관**: SPEC-UI-001과 동일하게 메모리 스토어 사용(localStorage 금지).
- **입력 검증**: `status` 쿼리 파라미터는 서버에서 화이트리스트(pending/running/done/failed) 검증한다. 잘못된 값은 422.
- **XSS 방지**: 목록 셀 값은 React 기본 escaping에 의존. `dangerouslySetInnerHTML` 금지.

---

## §9 의존성

- **선행**: SPEC-UI-001 (완료, PR #15), SPEC-PARSER-001 (완료)
- **후행**: 파일 업로드/트리거 UI (예정, 별도 SPEC)

---

## 전문가 자문 권장

본 SPEC은 풀스택(백엔드 엔드포인트 + 프론트엔드 라우팅/큐 화면) 범위다. 구현 단계에서 **expert-backend**(엔드포인트/테넌트 격리/페이지네이션)와 **expert-frontend**(React Router 도입/큐 컴포넌트/폴링 훅) 자문을 권장한다. Azure Container Apps 배포 검증은 **expert-devops** 자문을 권장한다.
