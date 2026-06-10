---
id: SPEC-UI-002
version: 0.1.0
status: draft
priority: high
issue_number: 16
---

# SPEC-UI-002 (Compact): 검토 큐 화면

## Scope

풀스택. 백엔드 `GET /parse/jobs` 신규 엔드포인트 + 프론트엔드 React Router 도입 및 검토 큐 화면(목록/상태탭/정렬/필터/페이지네이션). 단일 RA 실무자 대상.

In: GET /parse/jobs(skip/limit/status/requires_correction, 테넌트 격리), React Router 7, /jobs + /jobs/:jobId, QueuePage/JobQueueTable/JobStatusBadge/StatusTabs/SortControl/Pagination, useListJobs(폴링 5초), types/jobs.ts, Vitest + pytest, Azure Container Apps 배포(SPA 폴백/CORS).

Out: 업로드/트리거 UI, 벌크 액션, 팀/멀티유저 공유, 인증 화면, i18n, 트레이서빌리티/감사 뷰어.

선행: SPEC-UI-001(PR #15), SPEC-PARSER-001.

## Delta Markers

- [MODIFY] routers/parse.py → GET /parse/jobs
- [NEW] schemas/parse.py → JobSummary, ListJobsResponse
- [MODIFY] App.tsx → React Router 리팩터
- [MODIFY] main.tsx → BrowserRouter
- [NEW] pages/QueuePage.tsx, components/{JobQueueTable,JobStatusBadge,StatusTabs,SortControl,Pagination}.tsx
- [NEW] hooks/useListJobs.ts, types/jobs.ts
- [MODIFY] package.json → react-router-dom

## EARS Requirements

- REQ-Q-001 (Event): WHEN `/jobs` 이동 시, SHALL 상태/신뢰도/작성일 컬럼의 정렬 가능 테이블로 모든 작업 표시.
- REQ-Q-002 (Event): WHEN 상태 탭(전체/대기/처리중/완료/실패) 선택 시, SHALL 해당 상태만 필터링.
- REQ-Q-003 (Event): WHEN 행 클릭 시, SHALL `/jobs/:jobId`로 이동하여 SPEC-UI-001 CorrectionPanel 렌더링.
- REQ-Q-004 (State): WHILE requires_correction=true이면, SHALL 행을 교정 필요 인디케이터로 강조.
- REQ-Q-005 (State): WHILE status="running" 작업 존재 시, SHALL 5초마다 사용자 조작 없이 자동 갱신.
- REQ-Q-006 (Ubiquitous): backend SHALL GET /parse/jobs(skip/limit/status/requires_correction)로 테넌트 범위 JobSummary 목록 반환.
- REQ-Q-007 (Event): WHEN 신뢰도/작성일 정렬 시, SHALL 테이블 재정렬.
- REQ-Q-008 (Event): WHEN 작업 50개 초과 시, SHALL 페이지네이션(이전/다음/현재 페이지) 표시.

## Data Model

`JobSummary`: job_id, doc_id, status(pending/running/done/failed), overall_confidence(nullable), created_at, error(nullable), requires_correction.
`ListJobsResponse`: total(int), items(List[JobSummary]).
신뢰도 색상: ≥0.85 green / ≥0.75 yellow / <0.75 red (SPEC-UI-001 규칙 재사용). null → "-".

## Acceptance (요약)

- AC-001: `/jobs` 진입 → 상태/신뢰도/작성일 컬럼 행 렌더링.
- AC-002: "완료" 탭 → status=done 호출, done만 표시, 페이지 1 리셋.
- AC-003: 행 클릭 → `/jobs/:jobId` 이동, CorrectionPanel 렌더링.
- AC-004: requires_correction=true 행만 강조.
- AC-005: running 존재 시 5초 후 GET /parse/jobs 재호출.
- AC-006: 테넌트 A 인증 → total=2, A 작업만, 7개 필드 포함.
- AC-007: 신뢰도 오래된순 → 0.60/0.78/0.92 재정렬.
- AC-008: total=120 → Pagination 표시(1/3, 이전 비활성/다음 활성).
- Edge: 빈 목록(메시지+페이지네이션 숨김), 신뢰도 null("-"), 잘못된 status(422), 폴링 중단(running 0개), 로드 실패(에러 토스트), 페이지 경계(마지막 다음 비활성).
- Regression AC-R01: SPEC-UI-001 교정 화면 동작 변경 없이 유지.

## Quality Gate

테넌트 격리, status 화이트리스트 422, 프론트 테스트 Docker 비의존(fetch 모킹), 백엔드 통합 테스트 skip_no_docker, nginx SPA 폴백, 커버리지 85%+.
