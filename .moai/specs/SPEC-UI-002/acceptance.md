# SPEC-UI-002 인수 기준 (Acceptance Criteria)

프론트엔드 시나리오는 Vitest + React Testing Library(fetch는 `vi.spyOn` 모킹, 폴링은 `vi.useFakeTimers`)로, 백엔드 시나리오는 pytest + FastAPI TestClient로 검증 가능해야 한다. Given-When-Then 형식으로 작성한다.

## REQ별 시나리오

### AC-001 (REQ-Q-001): 큐 목록 로드 및 컬럼 렌더링

- **Given** `GET /parse/jobs`가 3개 작업(상태/신뢰도/작성일 포함)을 반환하는 상황에서
- **When** 사용자가 `/jobs`로 이동하면
- **Then** `JobQueueTable`이 마운트되고 3개 행이 상태(JobStatusBadge), 신뢰도(%), 작성일 컬럼과 함께 렌더링된다.

### AC-002 (REQ-Q-002): 상태 탭 필터링

- **Given** 큐 목록이 로드된 상태에서
- **When** 사용자가 "완료" 탭을 선택하면
- **Then** `GET /parse/jobs?...&status=done`이 호출되고 done 상태 작업만 목록에 표시되며, 페이지가 1로 리셋된다.

### AC-003 (REQ-Q-003): 행 클릭 시 교정 화면 이동

- **Given** 큐 목록에 `job_id="abc-123"` 작업이 표시된 상황에서
- **When** 사용자가 해당 행을 클릭하면
- **Then** 라우터가 `/jobs/abc-123`로 이동하고 SPEC-UI-001 `CorrectionPanel`이 `jobId="abc-123"`로 렌더링된다.

### AC-004 (REQ-Q-004): 교정 필요 행 강조

- **Given** 목록에 `requires_correction=true`인 작업과 `false`인 작업이 섞여 있는 상황에서
- **When** 화면이 렌더링되면
- **Then** `requires_correction=true`인 행에만 교정 필요 인디케이터(시각적 강조)가 표시된다.

### AC-005 (REQ-Q-005): 처리중 작업 자동 갱신

- **Given** 목록에 `status="running"` 작업이 하나 이상 존재하고 가짜 타이머가 활성화된 상황에서
- **When** 5초가 경과하면
- **Then** 사용자 조작 없이 `GET /parse/jobs`가 재호출되어 목록이 갱신된다.

### AC-006 (REQ-Q-006): 백엔드 목록 엔드포인트 (테넌트 범위)

- **Given** 테넌트 A에 작업 2개, 테넌트 B에 작업 1개가 존재하고 테넌트 A로 인증된 상황에서
- **When** `GET /parse/jobs`를 호출하면
- **Then** 응답은 `total=2`이고 `items`에는 테넌트 A의 작업만 포함되며, 각 항목은 `job_id`, `doc_id`, `status`, `overall_confidence`, `created_at`, `error`, `requires_correction` 필드를 가진다.

### AC-007 (REQ-Q-007): 정렬 재정렬

- **Given** 신뢰도가 0.92, 0.60, 0.78인 3개 작업이 로드된 상황에서
- **When** 사용자가 정렬을 "신뢰도 / 오래된순(낮은순)"으로 변경하면
- **Then** 테이블이 0.60, 0.78, 0.92 순으로 재정렬된다.

### AC-008 (REQ-Q-008): 페이지네이션 표시

- **Given** `GET /parse/jobs`가 `total=120`을 반환하는 상황에서
- **When** 큐 화면이 렌더링되면
- **Then** `Pagination`이 표시되고 현재 페이지(1/3) 표시와 이전(비활성)/다음(활성) 버튼이 나타난다.

## 엣지 케이스 (Edge Cases)

### AC-E01: 빈 목록

- **Given** `GET /parse/jobs`가 `total=0`, `items=[]`를 반환하는 상황에서
- **When** `/jobs`가 렌더링되면
- **Then** "표시할 작업이 없습니다" 빈 상태 메시지가 표시되고 페이지네이션은 숨겨진다.

### AC-E02: 신뢰도 null 처리

- **Given** `overall_confidence=null`인 작업(예: pending/failed)이 목록에 있는 상황에서
- **When** 행이 렌더링되면
- **Then** 신뢰도 컬럼에 "-"가 표시되고 색상 배지는 적용되지 않는다.

### AC-E03: 잘못된 status 쿼리 (백엔드)

- **Given** 인증된 상황에서
- **When** `GET /parse/jobs?status=invalid`를 호출하면
- **Then** 422 응답이 반환되고 작업 목록은 반환되지 않는다.

### AC-E04: 폴링 중단

- **Given** 폴링이 동작 중이고 목록에 running 작업이 있었던 상황에서
- **When** 재조회 결과 running 작업이 0개가 되면
- **Then** 다음 폴링 주기가 더 이상 실행되지 않는다(interval 중단).

### AC-E05: 목록 로드 실패

- **Given** `GET /parse/jobs`가 네트워크 오류를 반환하는 상황에서
- **When** `/jobs`가 렌더링되면
- **Then** 에러 상태 메시지와 에러 토스트가 표시되고, 다음 폴링 주기(running 존재 시)에 재시도된다.

### AC-E06: 페이지네이션 경계

- **Given** `total=120`(3페이지)이고 현재 마지막 페이지(3/3)인 상황에서
- **When** 페이지네이션이 렌더링되면
- **Then** 다음 버튼이 비활성화되고 이전 버튼은 활성화된다.

## 회귀 검증 (Regression)

### AC-R01: SPEC-UI-001 교정 화면 유지

- **Given** App.tsx가 React Router로 리팩터된 상황에서
- **When** `/jobs/:jobId`로 진입하면
- **Then** SPEC-UI-001 `CorrectionPanel`의 기존 동작(15개 필드 로드, confidence 배지, dirty/저장/rejected 처리)이 변경 없이 동작한다.

## 품질 게이트 (Quality Gate)

- 모든 REQ-Q-001~008에 대응하는 AC가 존재하고 통과한다.
- 프론트엔드 테스트는 Docker에 의존하지 않는다(fetch 모킹).
- 백엔드 통합 테스트는 `skip_no_docker` 마커로 로컬 Docker 부재 시 스킵된다.
- nginx SPA 폴백이 `/jobs/:jobId` 직접 접근을 200으로 서빙한다.
- 코드 커버리지 85% 이상.

## Definition of Done

- [ ] 백엔드 `GET /parse/jobs` 구현 및 pytest 통과 (REQ-Q-006)
- [ ] React Router 도입 및 `/jobs`, `/jobs/:jobId` 라우트 동작
- [ ] 큐 테이블/상태 탭/정렬/페이지네이션 구현 (REQ-Q-001/002/007/008)
- [ ] 행 클릭 교정 화면 이동 (REQ-Q-003)
- [ ] requires_correction 강조 (REQ-Q-004)
- [ ] running 폴링 5초 자동 갱신 (REQ-Q-005)
- [ ] Vitest 컴포넌트/훅 테스트 통과
- [ ] SPEC-UI-001 회귀 검증 통과 (AC-R01)
- [ ] Azure Container Apps 배포 가능성 검증 (nginx SPA 폴백, CORS_ORIGINS)
