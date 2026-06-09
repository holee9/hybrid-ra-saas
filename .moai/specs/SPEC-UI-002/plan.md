# SPEC-UI-002 구현 계획 (Implementation Plan)

검토 큐 화면을 풀스택으로 구현한다. 백엔드 목록 엔드포인트를 먼저 확보(P0)한 뒤, 프론트엔드 라우팅과 큐 UI(P1), 마지막으로 폴링/페이지네이션 polish와 테스트(P2) 순으로 진행한다.

## 기술 접근 (Technical Approach)

- **백엔드**: 기존 `routers/parse.py`에 `GET /parse/jobs`를 추가하고, `schemas/parse.py`에 `JobSummary`/`ListJobsResponse`를 정의한다. `ParseJob` 모델과 `get_current_tenant` 의존성을 재사용한다. 정렬은 created_at 내림차순 기본, 필터는 status/requires_correction.
- **프론트엔드**: `react-router-dom`(React Router 7)을 도입하고 `App.tsx`를 라우터 컨테이너로 리팩터한다. 기존 단일 페이지 교정 화면은 `/jobs/:jobId` 경로로 통합한다. 큐 화면은 컨테이너(`QueuePage`)와 프레젠테이션 컴포넌트(`JobQueueTable`, `JobStatusBadge`, `StatusTabs`, `SortControl`, `Pagination`)로 분리한다.
- **상태/데이터**: `useListJobs` 훅이 목록 로드 + running 폴링(5초)을 캡슐화한다. 정렬은 클라이언트 측, 필터/페이지네이션은 쿼리 파라미터 기반.
- **스타일**: Tailwind CSS만 사용(UI 라이브러리 없음). 한국어 텍스트. SPEC-UI-001 색상 규칙 재사용.
- **배포**: nginx SPA 폴백(`try_files ... /index.html`)으로 클라이언트 라우팅을 지원하도록 보장하고, Azure Container Apps 배포 가능성을 검증한다.

## 마일스톤 (Milestones)

### M1 — 백엔드 목록 엔드포인트 (Priority: High / P0)

선행 조건이며 프론트엔드가 의존한다. 가장 먼저 완료한다.

작업:
- T1-1 [NEW] `schemas/parse.py`에 `JobSummary`, `ListJobsResponse` 추가.
- T1-2 [MODIFY] `routers/parse.py`에 `GET /parse/jobs` 추가:
  - 쿼리 파라미터 `skip=0`, `limit=50`, `status: Optional[str]`, `requires_correction: Optional[bool]`.
  - `get_current_tenant`로 테넌트 범위 제한.
  - status 화이트리스트(pending/running/done/failed) 검증, 잘못된 값은 422.
  - created_at 내림차순 정렬, `total`(필터 후 전체) + `items`(페이지) 반환.
- T1-3 pytest: 목록 반환, status 필터, requires_correction 필터, 페이지네이션(total/items), 테넌트 격리, 잘못된 status 422 검증.

완료 기준:
- REQ-Q-006 충족.
- `GET /parse/jobs` pytest 통과(통합 테스트는 CI 전용, `skip_no_docker` 마커 적용).

### M2 — 라우팅 + 큐 UI (Priority: High / P1)

M1 완료 후 진행. 화면의 핵심 가치를 구현한다.

작업:
- T2-1 [NEW] `ui`에 `react-router-dom` 의존성 추가(`package.json`).
- T2-2 [MODIFY] `main.tsx`를 `BrowserRouter`로 래핑.
- T2-3 [MODIFY] `App.tsx`를 라우터로 리팩터:
  - `/` → `/jobs` 리다이렉트.
  - `/jobs` → `QueuePage`.
  - `/jobs/:jobId` → `CorrectionPanel`(`useParams().jobId` 사용).
- T2-4 [NEW] `types/jobs.ts`: `JobSummary`, `ListJobsResponse`, `STATUS_TABS`, 정렬/페이지 상수.
- T2-5 [NEW] `useListJobs` 훅(폴링 제외, 기본 로드/필터/페이지네이션 우선).
- T2-6 [NEW] `JobStatusBadge`(대기/처리중/완료/실패 색상).
- T2-7 [NEW] `JobQueueTable`(상태/신뢰도/작성일 컬럼, 행 클릭 → navigate, requires_correction 강조).
- T2-8 [NEW] `StatusTabs`(전체/대기/처리중/완료/실패, 탭 선택 시 필터 변경 + 페이지 리셋).
- T2-9 [NEW] `QueuePage`(탭/테이블 컨테이너, 로딩/빈/에러 상태).

완료 기준:
- REQ-Q-001, REQ-Q-002, REQ-Q-003, REQ-Q-004 충족.
- `/jobs` 진입 시 목록 렌더링, 상태 탭 필터, 행 클릭 시 교정 화면 진입 동작.

### M3 — Polish + 정렬/페이지네이션/폴링 + 테스트 (Priority: Medium / P2)

M2 완료 후 진행. 사용성 완성과 검증.

작업:
- T3-1 [NEW] `SortControl`(작성일/신뢰도, 최신순/오래된순) + `useListJobs` 클라이언트 정렬.
- T3-2 [NEW] `Pagination`(이전/다음/현재 페이지, total<=50 시 숨김, 경계 비활성화).
- T3-3 [MODIFY] `useListJobs`에 running 폴링(5초) 추가: running 작업 존재 시에만 폴링, 없으면 중단.
- T3-4 Vitest: `useListJobs`(로드/필터/페이지/폴링 타이머), `JobQueueTable`(컬럼/행 클릭/강조), `StatusTabs`(필터 변경), `JobStatusBadge`(색상), `Pagination`(경계). fetch는 `vi.spyOn`으로 모킹.
- T3-5 [MODIFY] nginx.conf SPA 폴백 검증(`try_files`), `CORS_ORIGINS` staging 도메인 포함 확인, Dockerfile 빌드 검증.

완료 기준:
- REQ-Q-005, REQ-Q-007, REQ-Q-008 충족.
- 전체 EARS 요구사항 충족, acceptance.md 시나리오 통과.
- Azure Container Apps 배포 가능성 검증.

## 파일 변경 요약 (Delta Markers)

| 마커 | 파일 | 변경 내용 |
|------|------|-----------|
| [MODIFY] | `customer-runtime/src/app/routers/parse.py` | `GET /parse/jobs` 엔드포인트 추가 |
| [NEW] | `customer-runtime/src/app/schemas/parse.py` | `JobSummary`, `ListJobsResponse` 스키마 추가 |
| [MODIFY] | `customer-runtime/ui/src/App.tsx` | React Router 도입, 라우터 리팩터 |
| [MODIFY] | `customer-runtime/ui/src/main.tsx` | `BrowserRouter` 래핑 |
| [NEW] | `customer-runtime/ui/src/pages/QueuePage.tsx` | 큐 페이지 컨테이너 |
| [NEW] | `customer-runtime/ui/src/components/JobQueueTable.tsx` | 작업 목록 테이블 |
| [NEW] | `customer-runtime/ui/src/components/JobStatusBadge.tsx` | 상태 배지 |
| [NEW] | `customer-runtime/ui/src/components/StatusTabs.tsx` | 상태 탭 |
| [NEW] | `customer-runtime/ui/src/components/SortControl.tsx` | 정렬 컨트롤 |
| [NEW] | `customer-runtime/ui/src/components/Pagination.tsx` | 페이지네이션 |
| [NEW] | `customer-runtime/ui/src/hooks/useListJobs.ts` | 목록 로드 + 폴링 훅 |
| [NEW] | `customer-runtime/ui/src/types/jobs.ts` | `JobSummary`, `ListJobsResponse` 타입 |
| [MODIFY] | `customer-runtime/ui/package.json` | `react-router-dom` 의존성 추가 |
| [MODIFY] | `customer-runtime/ui/nginx.conf` | SPA 폴백 검증(이미 존재 시 확인) |

## MX 태그 계획 (mx_plan)

| 우선순위 | 파일 | 대상 | 태그 | 사유 |
|---------|------|------|------|------|
| P1 | `routers/parse.py` | `list_parse_jobs()` | `@MX:ANCHOR` | 공개 API 경계, fan_in >= 3 (QueuePage, useListJobs, 미래 테스트 코드) |
| P1 | `hooks/useListJobs.ts` | polling interval 로직 | `@MX:WARN` | setInterval 사용 — cleanup 누락 시 메모리 누수 위험. @MX:REASON: cleanup 반드시 useEffect return에서 clearInterval 호출 |
| P2 | `schemas/parse.py` | `JobSummary`, `ListJobsResponse` | `@MX:NOTE` | 백엔드-프론트엔드 데이터 계약. 필드 변경 시 types/jobs.ts 동기 수정 필요 |
| P2 | `types/jobs.ts` | `STATUS_TABS`, `PAGE_SIZE` | `@MX:NOTE` | 비즈니스 규칙 상수 — 5개 상태 탭, 50개/페이지 하드코딩. 변경 시 백엔드 limit 기본값과 동기화 필요 |
| P3 | `App.tsx` | Routes 라우팅 테이블 | `@MX:ANCHOR` | 모든 페이지 진입점. fan_in >= 2 (QueuePage, CorrectionPanel). 라우트 추가 시 반드시 여기 등록 |

---

## 리스크 및 완화 (Risks & Mitigation)

| 리스크 | 영향 | 완화 |
|--------|------|------|
| App.tsx 라우터 리팩터가 SPEC-UI-001 교정 화면 진입을 깨뜨림 | High | `CorrectionPanel` 내부 로직은 변경하지 않고 진입부(jobId 소스)만 `useParams`로 조정. SPEC-UI-001 기존 테스트를 회귀 검증. |
| 폴링이 화면 이탈 후에도 계속 실행되어 누수 발생 | Medium | `useEffect` cleanup에서 interval clear. running 작업 없으면 폴링 중단. |
| nginx SPA 폴백 누락으로 `/jobs/:jobId` 직접 접근 시 404 | High | nginx.conf `try_files ... /index.html` 명시 검증을 M3 작업에 포함. |
| 백엔드 정렬/필터와 클라이언트 정렬 불일치 | Medium | 백엔드는 created_at 기본 정렬만, 신뢰도 정렬은 클라이언트에서 일관 처리. 정렬 규칙을 spec §3.8에 고정. |
| 통합 테스트가 로컬 Docker 부재 시 실패 | Medium | LESSON 적용: 백엔드 통합 테스트에 `skip_no_docker` 마커, 프론트엔드는 fetch 모킹으로 Docker 비의존. |
| Azure 배포 시 CORS_ORIGINS staging 도메인 누락 | Medium | M3에서 staging 도메인 포함 여부를 명시 확인. |

## 테스트 전략 (Testing Strategy)

- **프론트엔드(Vitest + RTL)**: `vi.spyOn(global, "fetch")`로 API 모킹, `waitFor`/`screen` 쿼리. 폴링은 `vi.useFakeTimers`로 타이머 제어. Docker 비의존.
- **백엔드(pytest + FastAPI TestClient)**: `GET /parse/jobs`의 필터/페이지네이션/테넌트 격리/422 검증.
- **통합 테스트(CI 전용)**: 로컬 Docker 부재 시 `skip_no_docker` 마커로 스킵(이전 SPEC LESSON 적용).

## 의존성 순서 (Dependency Order)

M1(백엔드) → M2(라우팅+큐 UI, M1의 엔드포인트 필요) → M3(polish+테스트). M1과 M2의 타입 정의(JobSummary)는 백엔드 스키마를 단일 출처로 하여 일관성을 유지한다.
