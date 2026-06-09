# SPEC-UI-001 구현 계획 (Implementation Plan)

## 개요

`ParsedFields` 교정 UI를 React 18 + TypeScript + Vite로 구현하고 Docker `ui` 서비스로 배포한다. 구현은 **expert-frontend** 에이전트에 위임하는 것을 권장한다.

## 기술 접근 (Technical Approach)

- **Framework**: React 18 + TypeScript, Vite 빌드
- **Styling**: Tailwind CSS + shadcn/ui
- **HTTP**: `fetch` (신규 의존성 없음)
- **Testing**: Vitest + React Testing Library
- **Serving**: nginx Docker 서비스, port 8080, `/api` same-origin 프록시
- **상태관리**: 로컬 컴포넌트 상태 + dirty/undo 히스토리 (외부 상태관리 라이브러리 불필요)

## 마일스톤 (Milestones)

마일스톤은 우선순위 기반으로 정렬한다(소요 시간 추정 없음).

### M1 — 프로젝트 골격 (Priority High)

- `ui/` 디렉터리 구조 생성 (package.json, vite.config.ts, tsconfig.json, tailwind.config.ts, index.html)
- `src/types/parse.ts` — `ParsedFields` 스키마 TypeScript 미러 정의
- `src/lib/api.ts` — 인증 헤더 포함 fetch 래퍼

### M2 — 핵심 표시 컴포넌트 (Priority High)

- `ConfidenceBadge.tsx` — 색상 코딩 배지 (green/yellow/red)
- `StageIndicator.tsx` — RULE/NER/LLM/수동 chip
- `FieldRow.tsx` — 라벨, 값, 인라인 편집, 배지, chip

### M3 — 패널 + 데이터 훅 (Priority High)

- `useParseJob.ts` — `GET /parse/jobs/{id}`
- `useCorrections.ts` — `PATCH /parse/{id}/corrections` (변경 필드만)
- `CorrectionPanel.tsx` — 15개 필드 + overall_confidence 프로그레스바 + Save 버튼 + dirty/undo 상태

### M4 — Docker 통합 (Priority High)

- `docker/Dockerfile` — 멀티스테이지 빌드 (vite build → nginx serve)
- `nginx.conf` — port 8080 서빙 + `/api` 프록시
- `docker-compose.yml`에 `ui` 서비스 추가

### M5 — rejected 및 에러 처리 (Priority Medium)

- `RejectedBanner.tsx` — `rejected=true` 경고 + 재업로드 안내
- 토스트 시스템 (성공/실패)
- 401/404/422/네트워크 에러 처리 + 필드 롤백

### M6 — 테스트 및 커버리지 (Priority Medium)

- Vitest + RTL 컴포넌트/훅 테스트 (acceptance.md 시나리오 매핑)
- 85% 이상 커버리지 목표

## TDD 시퀀스 (T-001 ~ T-010)

| Task | 대상 | REQ 매핑 | 설명 |
|------|------|----------|------|
| T-001 | `parse.ts` 타입 | — | `ParsedFields`/`FieldExtraction` 타입 가드 테스트 |
| T-002 | `api.ts` | §8 | 인증 헤더(Bearer + X-Tenant-ID) 부착 검증 |
| T-003 | `ConfidenceBadge` | REQ-UI-002 | green/yellow/red 임계값 분기 테스트 |
| T-004 | `StageIndicator` | §3 | stage → 라벨 매핑 테스트 |
| T-005 | `FieldRow` | REQ-UI-003 | 클릭-to-edit dirty 상태 전환 테스트 |
| T-006 | `useParseJob` | REQ-UI-001 | job_id 기반 GET 호출 + 로드 상태 테스트 |
| T-007 | `useCorrections` | REQ-UI-004 | 변경 필드만 PATCH 본문 포함 테스트 |
| T-008 | `CorrectionPanel` 성공 | REQ-UI-005 | Save 성공 → 갱신 + 성공 토스트 테스트 |
| T-009 | `CorrectionPanel` 실패 | REQ-UI-006 | PATCH 실패 → 롤백 + 에러 토스트 테스트 |
| T-010 | `RejectedBanner` / undo | REQ-UI-007, REQ-UI-008 | rejected 폼 비활성화 + undo 히스토리 테스트 |

## 리스크 (Risks)

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 배열 필드(`string[]`) 편집 UX 모호 | 중 | 줄바꿈 구분 텍스트 입력으로 표준화, FieldRow에서 분기 처리 |
| same-origin 프록시 미설정 시 CORS 오류 | 중 | nginx.conf 프록시 우선 구현(M4), 로컬 dev는 vite proxy 사용 |
| JWT 메모리 보관 시 새로고침 토큰 소실 | 저 | 본 SPEC 범위에서 토큰 재발급은 외부 위임(로그인 SPEC) |
| PATCH partial 전송 누락 시 전체 덮어쓰기 | 고 | T-007에서 변경 필드만 포함되는지 명시적 검증 |

## 권장 에이전트

- 구현: **expert-frontend** (React 컴포넌트, 상태관리, API 통합, Vitest 테스트)
- 품질 검증: **manager-quality** (TRUST 5, 커버리지 85%+)
