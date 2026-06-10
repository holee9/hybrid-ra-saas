# SPEC-UI-002 구현 전략 — 검토 큐 화면 (Review Queue Screen)

작성: manager-strategy | Issue: #16 | 모드: TDD | 언어: ko

> 본 문서는 분석/계획 전용. 코드 구현 없음. manager-tdd 핸드오프용.

---

## 0. 코드베이스 검증 결과 (입력 SPEC 요약 vs 디스크 진실)

실제 파일을 읽어 입력 요약과 대조했다. 중요한 불일치 발견:

| 항목 | 입력 요약 | 디스크 진실 | 영향 |
|------|-----------|-------------|------|
| nginx SPA fallback | "없으면 404, try_files 추가 필요" | **이미 존재** (`nginx.conf:14` `try_files $uri $uri/ /index.html`) | Risk #5 거의 해소 → 검증만 |
| GET `/parse/jobs/{job_id}` 응답 | `parsed_fields` 반환 가정 | **반환 안 함** — `field_candidates/confidence/required_missing`만 (`parse.py:31-37`) | 모순 #A (아래) |
| `types/parse.ts` ParseJobResponse | — | `parsed_fields?`만 있고 `field_candidates` 없음 | 프론트/백 스키마 불일치 (기존) |
| API base path | `/parse/jobs` | nginx `/api/` proxy + `apiFetch` BASE_URL=`/api` → 실호출 `/api/parse/jobs` | useListJobs 경로는 `/parse/jobs` (apiFetch가 `/api` prepend) |
| documents.py list 패턴 | 재사용 가정 | list/pagination/count 패턴 **없음** — 신규 작성 필요 | M1 영향 |

### 모순 #A (CRITICAL — 계획에 반영)

`App.tsx:54`는 `data.parsed_fields`를 `CorrectionPanel`에 전달한다. 그러나 GET `/parse/jobs/{job_id}` 라우터는 `parsed_fields`를 **응답에 포함하지 않는다**. 즉 현재 단일 작업 화면은 정상 데이터를 못 받거나, 별도 경로로 동작 중일 가능성이 있다.

- **결정**: SPEC-UI-002 범위는 큐 화면 추가 + 라우팅. 모순 #A는 **기존 버그이며 본 SPEC 범위 밖**. App.tsx 리팩터링 시 CorrectionPanel 호출 로직을 **현재 형태 그대로 보존**(`data.parsed_fields` 전달)한다. 라우팅 컨테이너 분리만 수행, 데이터 흐름은 건드리지 않는다.
- **단, 검토 큐(`JobSummary`)는 `result_json["parsed_fields"]`에서 confidence/requires_correction을 추출**해야 하므로, 백엔드 list endpoint는 PATCH 핸들러(`parse.py:91-96`)가 쓰는 동일 경로(`result_json["parsed_fields"]`)를 신뢰 소스로 사용한다. 이게 디스크 상 검증된 유일한 정답 경로다.

---

## 1. 리스크별 아키텍처 결정

### Risk 1 — App.tsx 리팩터가 SPEC-UI-001 파괴

**결정**: 컨테이너/페이지 분리. CorrectionPanel 내부·호출 데이터 흐름 무수정.

- `main.tsx`: `<App/>` → `<BrowserRouter><App/></BrowserRouter>` (ToastProvider는 App 내부 유지)
- `App.tsx`: `<Routes>` 컨테이너로 변경
  - `/` → `<Navigate to="/jobs" replace/>`
  - `/jobs` → `<QueuePage/>`
  - `/jobs/:jobId` → 기존 AppContent 로직을 `<JobDetailRoute/>`로 추출, `jobId`를 `useParams()`에서 획득. 나머지(`useParseJob(jobId)`, loading/error/`data.parsed_fields` → CorrectionPanel)는 **현행 그대로 이식**
- `getJobId()`(`window.location.search`) 제거 → `useParams().jobId`로 대체. 이것이 유일한 데이터 획득 방식 변경.
- CorrectionPanel, useCorrections, useParseJob, FieldRow 등 **무수정**

근거: AppContent의 분기 로직(loading/error/empty/render)을 JobDetailRoute에 1:1 복사하면 SPEC-UI-001 테스트(`App.test.tsx`)는 라우팅 래핑만 조정하면 통과. 데이터 계약 불변.

### Risk 2 — overall_confidence / requires_correction 추출, N+1 회피

**결정**: 단일 `SELECT` + Python에서 `result_json` JSON 추출. N+1 없음.

- `result_json`은 `JSON` 컬럼(`parse_job.py:27`)이라 PostgreSQL에서 행 단위로 이미 로드됨. 추가 쿼리 불필요 → 본질적으로 N+1 아님.
- 추출 경로: `result_json["parsed_fields"]["overall_confidence"]`, `["requires_correction"]` (PATCH 핸들러가 쓰는 검증된 경로).
- 안전 추출: `result_json or {}` → `.get("parsed_fields") or {}` → `.get("overall_confidence")`. pending/running(result_json=None)은 `confidence=None, requires_correction=False`.
- **`requires_correction` 필터(REQ-Q-006)**: DB 레벨 필터링은 JSON 경로 쿼리(`result_json['parsed_fields']->>'requires_correction'`)가 SQLite(테스트)/PG 호환성 문제 유발. **결정: status 필터·pagination은 DB에서, requires_correction 필터는 페이지 로드 후 적용하면 페이지 카운트가 깨진다.** → requires_correction 필터는 **DB 레벨에서 SQLAlchemy JSON 연산자**로 처리. PG는 `result_json["parsed_fields"]["requires_correction"].as_boolean()` 지원. 단 테스트 DB가 PG(testcontainers pgvector:pg16, conftest 확인됨)이므로 PG JSON 연산자 사용 가능 — 호환성 안전.
  - **단순화 우선**: REQ-Q-006의 `requires_correction` 쿼리 파라미터는 선택적. 1차 구현은 status 필터 + skip/limit만 DB 처리, requires_correction은 SQLAlchemy `.op('->')`/`cast` 사용. 복잡하면 manager-tdd가 RED 테스트로 경로 확정.

### Risk 3 — React Router 7 + React 18.3 호환

**결정**: `react-router-dom@^7` 채택. React 18.3과 호환.

- react-router v7은 React 18 지원(공식 최소 React 18). package.json `react: ^18.3.0` 충족.
- v7은 ESM, `BrowserRouter`/`Routes`/`Route`/`Navigate`/`useParams`/`useNavigate` 동일 API. 데이터 라우터(loader) 미사용 — 선언적 `<Routes>`만 사용하므로 마이그레이션 부담 최소.
- **버전 핀**: `react-router-dom: "^7"` 추가. lockfile 갱신은 manager-tdd가 `npm install` 시 수행. 설치 전 `npm view react-router-dom version`으로 peer 호환 확인 권장.
- Vitest 환경(jsdom)에서 `BrowserRouter` 동작 → 테스트는 `MemoryRouter`로 감싸 라우팅 단위 테스트.

### Risk 4 — useListJobs 폴링 생명주기 (REQ-Q-005)

**결정**: `setInterval` in `useEffect`, cleanup에서 `clearInterval`. running 작업 존재 시에만 활성.

- 폴링 조건: 현재 페이지 데이터에 `status==="running"` 행이 1개 이상일 때만 5초 간격 refetch.
- 생명주기:
  - `useEffect`가 `[skip, limit, status, hasRunning]` 의존. running 없으면 interval 미등록.
  - cleanup: 컴포넌트 unmount / 의존성 변경 / 필터 전환 시 `clearInterval`.
  - 탭 비가시(`document.hidden`) 시 폴링 일시정지는 **과설계 — 1차 제외**. 단순 5초 고정.
- `useParseJob`의 `cancelled` 플래그 패턴(`useParseJob.ts:21,52`) 차용해 in-flight 응답 무시.
- **재진입 방지**: 이전 폴 응답 도착 전 다음 폴 발생 시 race. `cancelled` + 단일 in-flight 가드로 처리.

### Risk 5 — nginx SPA fallback

**결정**: **이미 구현됨**. 검증 테스트만 추가, 수정 없음.

- `nginx.conf:13-15` `location / { try_files $uri $uri/ /index.html; }` → `/jobs/:jobId` 직접 접근 시 index.html 반환됨.
- API proxy `/api/` → `http://api:8000/` (`nginx.conf:6-11`). `apiFetch` BASE_URL=`/api`라 `/api/parse/jobs` → 백엔드 `/parse/jobs`. 정합.
- T3-5는 nginx.conf **읽기 검증**(try_files 라인 존재 확인) + CORS(`main.py:45-51` 이미 설정됨, `cors_origins_list`) 확인으로 축소. 변경 없음.

---

## 2. TASK 시퀀스 (의존성 그래프)

```
M1 (P0, 백엔드)  ──────────────►  M2 (P1, 라우팅+큐 UI)  ──────────►  M3 (P2, 정렬/페이지/폴링/테스트)
  T1-1 schemas                      T2-1 react-router-dom 설치           T3-1 SortControl + 클라 정렬
  T1-2 GET /parse/jobs   ┐          T2-2 main.tsx BrowserRouter          T3-2 Pagination
  T1-3 pytest (unit+int) ┘─dep─┐    T2-3 App.tsx 라우터 컨테이너         T3-3 running 폴링(5s)
                               │    T2-4 types/jobs.ts                    T3-4 Vitest 전체
                               └──► T2-5 useListJobs (load/filter/page)   T3-5 nginx 검증+CORS
                                    T2-6 JobStatusBadge
                                    T2-7 JobQueueTable
                                    T2-8 StatusTabs
                                    T2-9 QueuePage
```

의존성 규칙:
- M1 완료(엔드포인트 + 통과 테스트) 후 M2 착수. M2의 useListJobs는 M1 응답 스키마에 의존.
- M2 내부: T2-4(types) → T2-5(hook) → T2-6/7/8(컴포넌트) → T2-9(QueuePage 조립). T2-1/2/3(라우팅 인프라)은 T2-4와 병렬 가능.
- M3는 M2 큐 화면 동작 후. T3-1~3 기능 추가, T3-4 테스트는 마지막, T3-5 검증.
- 순환 참조 없음.

---

## 3. 파일별 구현 노트

### 백엔드 (M1)

**`schemas/parse.py` [MODIFY] — T1-1**
- 추가: `JobSummary`, `ListJobsResponse` (기존 모델 무수정, append만).
- `JobSummary`: `job_id: str`, `doc_id: str`, `status: str`, `overall_confidence: float | None`, `requires_correction: bool`, `created_at: datetime`.
- `ListJobsResponse`: `items: list[JobSummary]`, `total: int`, `skip: int`, `limit: int`.
- Pydantic v2: `model_validate` 사용. `datetime`은 자동 ISO 직렬화.
- 주의: `requires_correction` 기본 False (pending/running 작업).

**`routers/parse.py` [MODIFY] — T1-2**
- 추가: `@router.get("/jobs", response_model=ListJobsResponse)`. **주의: `/jobs/{job_id}`(line 19)보다 먼저 또는 FastAPI 라우트 매칭 순서 확인.** `/jobs`(고정)와 `/jobs/{job_id}`(동적)는 충돌 안 함(FastAPI가 정적 우선) — 단 안전하게 `/jobs` 핸들러를 `/jobs/{job_id}` **위에** 정의.
- 쿼리 파라미터: `skip: int = 0`, `limit: int = 50`, `status: str | None = None`, `requires_correction: bool | None = None`. `limit` 상한 가드(e.g. `min(limit, 200)`).
- 쿼리: `select(ParseJob).where(ParseJob.tenant_id == tenant)` + status 필터 + `order_by(ParseJob.created_at.desc())` + `.offset(skip).limit(limit)`. `total`은 별도 `select(func.count())` (count 쿼리 1회 — N+1 아님, 총 2쿼리).
- 테넌트 범위(REQ-Q-006): `tenant_id == tenant` 필수. `get_current_tenant` 의존성(`deps.py:13`) 사용.
- `JobSummary` 생성 시 `result_json` 안전 추출 헬퍼 함수 분리(`_extract_summary_fields(job) -> tuple[float|None, bool]`) — 테스트 용이.
- requires_correction DB 필터: SQLAlchemy JSON 연산. PG 테스트 환경이라 `ParseJob.result_json["parsed_fields"]["requires_correction"]` 경로 표현식 사용. RED 테스트로 경로 확정 권장.

**`jobs.py` 테스트 [NEW] — T1-3**
- 단위: `_extract_summary_fields` 헬퍼 — result_json None / parsed_fields 없음 / 정상 케이스. **Docker 불필요** (순수 함수).
- 통합: `@skip_no_docker` 마커(`conftest.py:84`). `client` fixture 사용. 테넌트 격리(다른 tenant 작업 안 보임), status 필터, pagination(skip/limit), 50개 초과 → total 정확성.
- conftest의 `client` fixture는 JWT/X-Tenant-ID 헤더 필요 — 기존 통합 테스트(parse/documents) 헤더 생성 패턴 재사용.

### 프론트엔드 (M2/M3)

**`package.json` [MODIFY] — T2-1**: `dependencies`에 `"react-router-dom": "^7"` 추가.

**`main.tsx` [MODIFY] — T2-2**: `import { BrowserRouter }`, `<App/>` → `<BrowserRouter><App/></BrowserRouter>`. StrictMode 유지.

**`App.tsx` [MODIFY] — T2-3**: `<Routes>` 컨테이너. `/`→Navigate, `/jobs`→QueuePage, `/jobs/:jobId`→JobDetailRoute(기존 AppContent 이식, jobId는 useParams). ToastProvider 위치 유지. Risk 1 결정 준수.

**`types/jobs.ts` [NEW] — T2-4**:
- `JobSummary`(백엔드 스키마 미러: job_id/doc_id/status/overall_confidence: number|null/requires_correction/created_at: string).
- `ListJobsResponse`(items/total/skip/limit).
- `STATUS_TABS` 상수: `[{key:'all',label:'전체'},{key:'pending',label:'대기'},{key:'running',label:'처리중'},{key:'done',label:'완료'},{key:'failed',label:'실패'}]`. **status 값은 백엔드 enum(`pending/running/done/failed`, `parse_job.py:10-14`)과 정확히 일치.**
- `PAGE_SIZE = 50` (REQ-Q-008과 정합).

**`hooks/useListJobs.ts` [NEW] — T2-5 (기본), T3-1/T3-3 (확장)**:
- `useParseJob` 패턴 차용: `apiFetch('/parse/jobs?'+params).then(r=>r.json())`, `cancelled` 가드.
- 상태: data(ListJobsResponse)/loading/error/현재 status·skip. 쿼리스트링 빌드(skip/limit/status).
- T3-1: 클라이언트 정렬(신뢰도/작성일) — 페이지 내 정렬. **주의: DB는 created_at desc 고정 정렬. 클라 정렬은 현재 페이지 한정**(REQ-Q-007 "재정렬"은 표시 정렬로 해석). 전역 정렬 필요 시 백엔드 order_by 파라미터 추가 — 1차는 클라 정렬.
- T3-3: running 폴링 — Risk 4 결정.

**`components/JobStatusBadge.tsx` [NEW] — T2-6**: status→색상. `ConfidenceBadge.tsx` 색상 컨벤션 참고(green/yellow/red). pending=회색, running=파랑, done=초록, failed=빨강.

**`components/JobQueueTable.tsx` [NEW] — T2-7**:
- 컬럼: 상태(JobStatusBadge)/신뢰도(ConfidenceBadge 재사용 가능)/작성일/(requires_correction 강조).
- 행 클릭 → `useNavigate()('/jobs/'+jobId)` (REQ-Q-003).
- requires_correction=true 행 강조(REQ-Q-004): 배경/테두리 클래스. ARIA 고려.

**`components/StatusTabs.tsx` [NEW] — T2-8**: STATUS_TABS 렌더, 선택 시 useListJobs status 변경(REQ-Q-002). 탭 전환 시 skip=0 리셋.

**`components/SortControl.tsx` [NEW] — T3-1**: 신뢰도/작성일 정렬 토글. useListJobs 클라 정렬 트리거.

**`components/Pagination.tsx` [NEW] — T3-2**: 이전/다음/현재 페이지(REQ-Q-008). total/skip/limit로 페이지 계산. skip 갱신.

**`pages/QueuePage.tsx` [NEW] — T2-9**: StatusTabs + SortControl + JobQueueTable + Pagination 조립. useListJobs 단일 소스. ToastProvider 컨텍스트 사용 가능.

---

## 4. 마일스톤별 테스트 전략

| 마일스톤 | 테스트 | Docker/모킹 |
|----------|--------|-------------|
| M1 단위 | `_extract_summary_fields` 순수함수 (None/누락/정상) | 불필요 |
| M1 통합 | GET /parse/jobs: 테넌트 격리, status 필터, skip/limit, total 정확성, requires_correction 필터 | `@skip_no_docker`, conftest `client` |
| M2 | App 라우팅(MemoryRouter), JobQueueTable 행클릭→navigate, StatusTabs 필터, JobStatusBadge 색상, useListJobs 로드/필터 | `vi.spyOn(global,'fetch')` |
| M3 | SortControl 정렬, Pagination 이전/다음, 폴링(vi.useFakeTimers + interval), 강조 표시 | fake timers + fetch mock |
| M3 검증 | nginx.conf try_files 라인 존재, CORS 설정 확인 | 읽기 검증만 |

테스트 원칙(Lessons 적용):
- 백엔드 통합 → `skip_no_docker` (CI 전용).
- 프론트 → `vi.spyOn(global,"fetch")` Docker-free 모킹.
- 폴링 테스트: `vi.useFakeTimers()` + `vi.advanceTimersByTime(5000)`, cleanup으로 clearInterval 검증(leak 방지).
- SPEC-UI-001 회귀: 기존 `App.test.tsx`가 라우터 래핑으로 깨지면 MemoryRouter로 감싸 수정(테스트 의도 보존).

---

## 5. 품질 체크

**TypeScript**:
- `JobSummary.overall_confidence: number | null` (백엔드 None 대응). strict null 처리.
- STATUS_TABS `as const`, status 리터럴 유니온 타입.
- `created_at: string` (JSON 직렬화된 ISO). Date 변환은 표시 시점.
- tsconfig strict — `noUncheckedIndexedAccess` 등 기존 설정 준수.

**Pydantic v2**:
- `model_validate` (parse_obj 금지). `JobSummary`/`ListJobsResponse` BaseModel.
- `datetime` 필드 자동 직렬화. `overall_confidence: float | None` Optional 명시.
- 기존 `ParsedFields`/`ParseJobResponse` 무수정.

**SQLAlchemy 2.0 async**:
- `select(ParseJob).where(...).order_by(...).offset().limit()` + `await db.execute()` + `.scalars().all()`.
- count: `select(func.count()).select_from(ParseJob).where(tenant 필터+status)`.
- `expire_on_commit=False` (기존 설정). 읽기 전용이라 commit 불필요.
- JSON 경로 필터는 PG 연산자 — 테스트 DB(pgvector:pg16) 호환 확인됨.

**@MX 태그**:
- `GET /parse/jobs` 핸들러: 신규 public 엔드포인트 → `@MX:NOTE` (한국어, `code_comments: ko`이나 기존 코드가 영문 혼용 — 기존 파일 컨벤션 따름, 현재 parse.py는 영문 @MX).
- `_extract_summary_fields`: fan_in(핸들러+테스트) 고려, 정착 시 ANCHOR 평가.
- `useListJobs`/`apiFetch` 호출: 기존 apiFetch가 이미 ANCHOR.

---

## 6. 커밋 전략

규칙: Conventional Commits, **모든 footer에 `Refs #16`**, 커밋 메시지 한국어(`git_commit_messages: ko`).

마일스톤별 커밋(TDD RED→GREEN→REFACTOR 사이클 단위):

```
M1:
  feat(parse): JobSummary/ListJobsResponse 스키마 추가
  feat(parse): GET /parse/jobs 목록 엔드포인트 구현
  test(parse): 목록 엔드포인트 단위·통합 테스트

M2:
  build(ui): react-router-dom 의존성 추가
  refactor(ui): BrowserRouter 도입 및 App 라우터 컨테이너화
  feat(ui): 검토 큐 화면(QueuePage) 및 컴포넌트 추가

M3:
  feat(ui): 정렬·페이지네이션·자동갱신 추가
  test(ui): 큐 화면 컴포넌트·훅 테스트
  chore(ui): nginx SPA fallback 및 CORS 검증
```

각 커밋 footer:
```

Refs #16
```

진행 코멘트(Lessons): P0(M1)/P1(M2)/P2(M3) 완료 시점에 Issue #16에 진행 코멘트.

---

## 7. 핸드오프 요약 (→ manager-tdd)

- **모드**: TDD (RED→GREEN→REFACTOR).
- **순서**: M1 전량 → M2 → M3. M1 통과 전 M2 착수 금지.
- **불변 보존**: CorrectionPanel/useCorrections/useParseJob/FieldRow 무수정. App.tsx는 라우팅 분리만, `data.parsed_fields`→CorrectionPanel 흐름 보존(모순 #A는 본 SPEC 범위 밖).
- **신뢰 소스**: confidence/requires_correction은 `result_json["parsed_fields"]`에서 추출(PATCH 핸들러 검증 경로).
- **버전**: `react-router-dom@^7` (React 18.3 호환), 설치 전 peer 확인.
- **테스트**: 백엔드 통합 `@skip_no_docker`, 프론트 `vi.spyOn(global,"fetch")`, 폴링 `vi.useFakeTimers`.
- **커밋**: 전 커밋 `Refs #16`, 한국어 메시지.
- **확정 필요(manager-tdd가 RED로)**: requires_correction DB 필터의 정확한 SQLAlchemy JSON 표현식.
- **검증 완료**: nginx SPA fallback 이미 존재(수정 불필요), CORS 이미 설정됨.
