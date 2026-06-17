---
spec_id: SPEC-JOBQUEUE-001
title: "BackgroundTasks → 영속 Job Queue 전환"
status: completed
version: "1.0"
created: 2026-06-17
author: drake.lee
priority: High
issue_number: 39
dependencies: []
---

# SPEC-JOBQUEUE-001: BackgroundTasks → 영속 Job Queue 전환

## Goal

FastAPI의 인메모리(`BackgroundTasks`) 작업 실행을 Redis 기반 영속 작업 큐(arq)로 전환하여, Azure Container App의 재시작/스케일 이벤트에서도 진행 중인 작업이 유실되지 않도록 한다. 작업은 Redis에 영속되며, 워커 프로세스가 별도로 작업을 소비한다. 프로세스 재시작 시 `ParseJob.status = 'running'`에 영구히 갇히는 현상을 제거하고, 재시도/DLQ/orphan 복구를 통해 작업의 종결성(termination guarantee)을 보장한다. 기존 `GET /parse/jobs/{job_id}/status` API 계약은 변경하지 않는다.

## Background

hybrid-ra-saas는 Customer Local Runtime과 Cloud Control Plane으로 구성된 의료기기 규제 대응(RA) SaaS다. 두 런타임 모두 장시간 실행되는 비동기 작업(문서 파싱, 규제 문서 크롤링)을 FastAPI `BackgroundTasks`로 처리한다.

`BackgroundTasks`는 api 프로세스의 메모리 안에서만 동작한다. Azure Container App은 배포/스케일/헬스체크 실패 시 컨테이너를 재시작하며, 이때 실행 중이던 작업은 흔적 없이 사라진다. 결과적으로:

- `ParseJob.status`가 DB에 `'running'`으로 남은 채 영원히 갱신되지 않는다(좀비 작업).
- 사용자는 완료되지 않을 작업을 무한정 폴링한다.
- 재시도 메커니즘이 없어, 일시적 오류(예: Ollama 일시 불가)도 영구 실패로 귀결된다.

영향 범위:

1. `customer-runtime/src/app/jobs/parse_job.py` — `run_parse_job()` (문서 파싱 파이프라인). `async_session()`을 열어 `ParseJob` + `Document`를 로드하고, `pending→running→done/failed` 상태 머신을 전이하며, 성공 시 `_push_ifu_result_to_regula()`를 fire-and-forget 호출한다. 전 구간 async, SQLAlchemy 2.0.
2. `customer-runtime/src/app/routers/parse.py` — `background_tasks.add_task(run_parse_job, ...)`로 작업을 적재(enqueue)한다.
3. `cloud-control-plane/src/app/routers/crawl.py` — `_execute_crawl_job(job_id)`를 `background_tasks.add_task(...)`로 실행한다. DB 추적 상태 없이 인메모리 dict를 사용하는 one-shot 크롤이다.

기존 인프라 자산:

- `docker-compose.yml`에 5개 서비스(`api`, `postgres`, `minio`, `ollama`, `redis`)가 이미 구성되어 있다. **Redis는 이미 프로비저닝되어 있다.**
- Stack: FastAPI 0.115+, SQLAlchemy 2.0 async, Python 3.13, PostgreSQL.
- `ParseJob` 상태 머신과 `async_session()` 세션 팩토리가 이미 존재한다.

이 SPEC은 새로운 인프라를 도입하지 않고, 이미 존재하는 Redis를 작업 큐 백엔드로 활용하여 작업 영속성을 확보한다.

## Solution Overview

### 채택 기술: arq (async Redis queue)

**arq를 선택한 이유 (Celery / RabbitMQ 대비):**

- arq는 순수 async Python 라이브러리다. FastAPI의 async 런타임과 동기-비동기 브리지 없이 직결된다. Celery는 동기 코어라 async 작업 함수와의 통합에 추가 어댑터가 필요하다.
- Redis가 이미 `docker-compose.yml`에 존재한다. RabbitMQ 같은 신규 브로커 인프라가 필요 없다.
- arq의 `Worker` 클래스는 기존 `run_parse_job` 함수 시그니처에 거의 그대로 매핑된다.
- Celery + Beat 대비 운영 모델이 단순하다(워커 1개 + Redis만 필요).

### 아키텍처: 별도 워커 프로세스

- **customer-runtime**: 기존 `api` Container App과 분리된 `arq` 워커를 별도 프로세스로 실행한다.
  - 1차 권장: `arq <WorkerSettings 경로>` CLI로 기동하는 **별도 Container App**(예: `customer-runtime-worker`).
  - 이유: api 프로세스의 재시작/스케일 정책과 워커의 정책을 독립적으로 관리할 수 있고, 워커 OOM/크래시가 HTTP 요청 처리에 영향을 주지 않는다.
- api 프로세스는 작업을 **적재만** 한다(`ArqRedis.enqueue_job`). 실행은 워커가 담당한다.
- Redis는 작업 페이로드, 재시도 카운트, 결과의 단일 저장소다. DB의 `ParseJob`은 사용자 대면 상태의 정본(source of truth)으로 유지된다.

```
[HTTP 요청] → parse.py 라우터 → ArqRedis.enqueue_job("run_parse_job", ...)
                                          │
                                     [Redis 큐]  ← 영속 (재시작 생존)
                                          │
                              [arq 워커 프로세스] → run_parse_job() 실행
                                          │              ↓ 상태 전이
                                    [PostgreSQL ParseJob]  done/failed
```

### 디렉터리 구조 변경 (delta)

```
customer-runtime/src/app/
├── jobs/
│   ├── parse_job.py            [MODIFY] run_parse_job을 arq task 시그니처로 적응
│   └── worker.py               [NEW]    arq WorkerSettings, on_startup(orphan 복구), 함수 등록
├── queue/
│   ├── __init__.py             [NEW]
│   └── arq_pool.py             [NEW]    ArqRedis 풀 생성/주입 (enqueue 진입점)
├── routers/
│   └── parse.py                [MODIFY] background_tasks.add_task → arq enqueue
└── core/
    └── config.py               [MODIFY] REDIS_URL / arq 설정 추가 (이미 있으면 재사용)

cloud-control-plane/src/app/
├── jobs/
│   └── crawl_worker.py         [NEW]    _execute_crawl_job을 arq task로 등록
├── queue/
│   └── arq_pool.py             [NEW]    ArqRedis 풀
└── routers/
    └── crawl.py                [MODIFY] background_tasks.add_task → arq enqueue

customer-runtime/tests/
├── test_job_queue_unit.py      [NEW]    arq redis 모킹 단위 테스트
└── test_job_queue_integration.py [NEW]  실 Redis 통합 테스트 (skip_no_docker)
```

## Requirements (EARS Format)

### Functional Requirements

**REQ-JQ-001** (Ubiquitous): The system SHALL persist enqueued parse jobs in Redis such that an in-flight job survives a restart of the customer-runtime api process without data loss.

**REQ-JQ-002** (Event-Driven): WHEN a parse request is received, the system SHALL enqueue the job via an arq Redis pool (`ArqRedis.enqueue_job` / `ctx['redis']`) instead of `background_tasks.add_task`.

**REQ-JQ-003** (Event-Driven): WHEN the arq worker starts up, the system SHALL detect orphaned jobs whose `ParseJob.status = 'running'` but which are no longer present in the Redis queue, and SHALL either re-enqueue them or transition them to `'failed'` with a recorded reason (orphan recovery).

**REQ-JQ-004** (State-Driven): WHILE a job execution fails with a retryable error, the system SHALL retry the job up to a maximum of 3 attempts using exponential backoff between attempts.

**REQ-JQ-005** (Unwanted): IF a job exceeds the maximum retry count, THEN the system SHALL transition `ParseJob.status` to `'failed'`, record the terminal error, and SHALL NOT retry further (dead-letter behavior).

**REQ-JQ-006** (Event-Driven): WHEN a crawl request is received in cloud-control-plane, the system SHALL enqueue `_execute_crawl_job` via arq instead of `background_tasks.add_task`.

**REQ-JQ-007** (Ubiquitous): The system SHALL keep the response shape and semantics of `GET /parse/jobs/{job_id}/status` unchanged, so existing API consumers require no modification (no API contract break).

**REQ-JQ-008** (Ubiquitous): The system SHALL expose a worker health signal (a health endpoint or a process-level healthcheck) suitable for an Azure Container App liveness/readiness probe.

**REQ-JQ-009** (Event-Driven): WHEN `run_parse_job` succeeds under arq, the system SHALL preserve the existing success side effect of pushing the IFU result to Regula (`_push_ifu_result_to_regula`).

**REQ-JQ-010** (State-Driven): WHILE a job transitions through `pending → running → done/failed`, the system SHALL update `ParseJob.status` in PostgreSQL as the user-facing source of truth, consistent with the pre-migration state machine.

### Non-Functional Requirements

**REQ-NF-JQ-001** (Testability): Integration tests that require a real Redis SHALL be marked with the project `skip_no_docker` marker so they run CI-only and do not block local unit-test runs.

**REQ-NF-JQ-002** (Testability): Unit tests SHALL mock the arq Redis interface so that no real Redis instance is required for unit test execution.

**REQ-NF-JQ-003** (Compatibility): The migration SHALL be incremental — enqueue-side and worker-side changes MUST coexist with the existing `ParseJob` schema and state machine without a breaking database migration.

**REQ-NF-JQ-004** (Observability): The system SHALL log retry attempts (REQ-JQ-004), dead-letter transitions (REQ-JQ-005), and orphan recoveries (REQ-JQ-003) as structured events for audit and operational visibility.

## Acceptance Criteria

1. **재시작 생존 (REQ-JQ-001)**: 파싱 작업을 적재한 직후 api 프로세스를 강제 종료/재시작해도, 워커가 동일 작업을 Redis에서 소비하여 정상 완료시키고 `ParseJob.status`가 `'done'`이 된다. 작업은 유실되지 않는다.

2. **enqueue 경로 전환 (REQ-JQ-002)**: `parse.py`에 `background_tasks.add_task(run_parse_job, ...)` 호출이 더 이상 존재하지 않으며, arq enqueue 호출로 대체되었다. (코드 검사 + 동작 테스트)

3. **orphan 복구 (REQ-JQ-003)**: DB에 `status='running'`이지만 Redis 큐에 없는 작업을 시드한 뒤 워커를 기동하면, 해당 작업이 재적재되거나 `'failed'`(사유 기록)로 전이된다. `'running'`에 영구히 남는 작업이 0건이다.

4. **재시도 + 백오프 (REQ-JQ-004)**: 일시적 오류를 발생시키는 작업이 최대 3회까지 지수 백오프 간격으로 재시도된다. 재시도 횟수와 간격이 로그로 확인된다.

5. **DLQ 종결 (REQ-JQ-005)**: 3회 재시도를 모두 소진한 작업은 `status='failed'`로 전이되고 terminal error가 기록되며, 이후 재시도가 발생하지 않는다.

6. **크롤 전환 (REQ-JQ-006)**: `cloud-control-plane/.../crawl.py`의 `background_tasks.add_task(...)`가 arq enqueue로 대체되었고, 크롤 작업이 워커에서 실행된다.

7. **API 무변경 (REQ-JQ-007)**: `GET /parse/jobs/{job_id}/status`의 응답 스키마/필드/상태값이 마이그레이션 전후 동일하다. 기존 API 계약 테스트가 수정 없이 통과한다.

8. **워커 헬스 (REQ-JQ-008)**: 워커 헬스 신호(엔드포인트 또는 healthcheck)가 정상 시 성공, 워커 다운 시 실패를 반환하여 Azure Container App probe로 사용 가능하다.

9. **성공 부수효과 보존 (REQ-JQ-009)**: arq 경로에서 파싱 성공 시 `_push_ifu_result_to_regula`가 마이그레이션 전과 동일하게 호출된다.

10. **단위/통합 테스트 분리 (REQ-NF-JQ-001, REQ-NF-JQ-002)**: 단위 테스트는 arq Redis를 모킹하여 Redis 없이 통과한다. 통합 테스트는 `skip_no_docker`로 마크되어 CI Docker 환경에서만 실 Redis로 실행된다.

## Technical Approach (High Level)

코드가 아닌 아키텍처 결정 수준의 스케치다. 구현 세부는 Run 단계에서 확정한다.

### 결정 1 — enqueue 진입점: ArqRedis 풀

- api 프로세스는 `arq.create_pool(RedisSettings)`로 생성한 `ArqRedis` 인스턴스를 FastAPI 앱 상태(또는 의존성)로 보유한다.
- `parse.py` 라우터는 `await arq_pool.enqueue_job("run_parse_job", job_id, doc_id, tenant, parser, file_bytes)`로 적재한다.
- 풀은 앱 lifespan에서 1회 생성/종료한다(요청마다 연결 생성 금지).

### 결정 2 — 워커 함수 시그니처 적응

- arq 작업 함수는 첫 인자로 `ctx`(arq 컨텍스트)를 받는다. 기존 `run_parse_job(job_id, doc_id, tenant, parser, file_bytes)`를 arq용으로 래핑한다.
- 권장: `async def run_parse_job(ctx, job_id, doc_id, tenant, parser, file_bytes)` 형태로 `ctx`를 추가하고, 내부 로직은 기존 `async_session()` 기반을 재사용한다.
- `WorkerSettings.functions`에 작업 함수를 등록하고, `on_startup`에서 orphan 복구를 실행한다.
- `file_bytes`가 큰 페이로드인 경우 Redis 직접 전달 대신 MinIO 객체 키를 전달하고 워커가 재로드하는 방식을 Run 단계에서 평가한다(Redis 메모리 보호). 본 SPEC은 경로만 명시하고 임계값 결정은 구현에 위임한다.

### 결정 3 — 재시도/백오프/DLQ

- 재시도는 arq의 `max_tries` (= 3)와 작업 내 backoff 또는 arq의 재시도 스케줄로 구현한다.
- 재시도 가능 오류(일시적 I/O, Ollama 일시 불가)와 비재시도 오류(입력 검증 실패)를 구분한다. 비재시도 오류는 즉시 `failed`로 종결한다.
- `max_tries` 소진 시 작업 함수의 마지막 핸들러(또는 `on_job_end`/예외 경로)에서 `ParseJob.status='failed'` + terminal error 기록을 보장한다(REQ-JQ-005).

### 결정 4 — orphan 복구 (워커 startup)

- 워커 `on_startup`에서 `SELECT * FROM parse_jobs WHERE status='running'`을 조회한다.
- 각 작업에 대해: Redis 큐/진행 집합에 존재하면 그대로 두고, 존재하지 않으면 재적재 또는 `failed`(사유: "orphaned by restart") 전이.
- 정책(재적재 vs 실패)은 작업 멱등성에 따라 결정한다. `run_parse_job`이 멱등(같은 입력 재실행 안전)이면 재적재를 기본값으로 한다. Run 단계에서 멱등성 검증 후 확정.

### 결정 5 — 워커 헬스 (REQ-JQ-008)

- 옵션 A: 워커가 주기적으로 Redis에 heartbeat 키(`worker:heartbeat`, TTL 포함)를 갱신하고, 별도 경량 헬스 엔드포인트(또는 api 측 `/health/worker`)가 키 신선도를 검사.
- 옵션 B: arq 워커 컨테이너에 `arq --check` 기반 컨테이너 healthcheck 사용.
- Azure Container App probe와의 호환을 위해 옵션 A(HTTP 헬스)를 1차 권장하되, Run 단계에서 운영 단순성을 보고 확정.

### 결정 6 — 점진적 마이그레이션 (BackgroundTasks → arq, API 무중단)

- `ParseJob` 스키마/상태 머신은 변경하지 않는다(REQ-NF-JQ-003). enqueue 측만 교체하므로 DB 마이그레이션이 없다.
- `GET /parse/jobs/{job_id}/status`는 여전히 DB의 `ParseJob`을 읽으므로 응답이 동일하다(REQ-JQ-007).
- 전환 순서: (1) arq 풀/워커 추가 → (2) `parse.py` enqueue 교체 → (3) 워커 배포 → (4) `crawl.py` 교체. 각 단계는 독립 배포 가능하며, api와 워커가 동일 Redis를 공유하면 즉시 동작한다.

## @MX Tag Targets

Run 단계에서 다음 함수에 @MX 태그를 부여한다. fan_in이 높거나 위험 구간인 함수가 대상이다.

- `run_parse_job` (`jobs/parse_job.py`) — **@MX:ANCHOR**. enqueue(라우터), 워커, orphan 복구, 테스트에서 호출되는 핵심 작업 함수(fan_in ≥ 3). 시그니처가 큐 계약(불변)이다.
- `enqueue_parse_job` / `ArqRedis` 풀 접근 헬퍼 (`queue/arq_pool.py`) — **@MX:ANCHOR**. 모든 enqueue 경로의 단일 진입점(fan_in ≥ 3).
- 워커 `on_startup` orphan 복구 (`jobs/worker.py`) — **@MX:WARN** (+ @MX:REASON). 재시작마다 실행되며 DB 상태를 일괄 전이하는 위험 구간. 잘못된 정책은 정상 작업을 `failed` 처리할 수 있음.
- 재시도/DLQ 종결 경로 — **@MX:NOTE**. terminal 상태 전이 비즈니스 규칙.

## Out of Scope (What NOT to Build)

- **Celery / RabbitMQ 도입** — 본 SPEC은 arq + 기존 Redis로 한정한다.
- **신규 인프라 프로비저닝** — Redis는 이미 존재. 추가 브로커/스토리지 없음.
- **`ParseJob` 스키마 변경 또는 신규 DB 마이그레이션** — 상태 머신과 테이블은 그대로 유지(REQ-NF-JQ-003).
- **`GET /parse/jobs/{job_id}/status` 응답 스키마 변경** — API 계약 불변(REQ-JQ-007).
- **JWT/API token 인증 메커니즘 변경** — 인증은 SPEC-PERMISSION-001 / SPEC-APITOK-001 소관.
- **tenant 격리 로직 변경** — SPEC-TENANT-ISOLATION-001 소관. 워커 경로에서 tenant 컨텍스트를 어떻게 확립할지는 해당 SPEC의 REQ-TI-010(백그라운드 작업 명시적 컨텍스트)을 따른다.
- **작업 우선순위 큐 / 멀티 큐 라우팅** — 단일 기본 큐로 한정. 우선순위 분리는 후속 SPEC.
- **분산 cron/스케줄링(arq cron jobs)** — 주기 작업은 본 SPEC 범위 밖. 현 범위는 요청-구동 작업의 영속화.
- **크롤 작업의 DB 상태 추적 신규 도입** — `crawl.py`는 enqueue 경로만 arq로 전환한다. 인메모리 dict를 DB 추적으로 승격하는 작업은 별도 SPEC에서 평가.

## Implementation Notes

**구현 완료**: 2026-06-17 (커밋 3de9c78)

### 구현 파일 목록

| 파일 | 유형 | 내용 |
|------|------|------|
| `customer-runtime/src/app/jobs/parse_job.py` | MODIFY | arq task 시그니처 (`ctx` 첫 인자), `ParserService` 제거(Redis 직렬화 불가), `explicit_tenant_context` 적용 (REQ-TI-010) |
| `customer-runtime/src/app/jobs/worker.py` | NEW | arq `WorkerSettings`: `max_tries=3`, `on_startup` orphan 복구, `on_job_abort` DLQ 전이 |
| `customer-runtime/src/app/jobs/worker_health.py` | NEW | Redis heartbeat TTL key — Azure Container App liveness probe |
| `customer-runtime/src/app/queue/arq_pool.py` | NEW | `ArqRedis` 풀 생성/주입, fan_in ≥ 3 단일 enqueue 진입점 (@MX:ANCHOR) |
| `customer-runtime/src/app/routers/documents.py` | MODIFY | `background_tasks.add_task(run_parse_job, ...)` → arq enqueue |
| `customer-runtime/src/app/main.py` | MODIFY | arq pool lifespan 통합 |
| `customer-runtime/pyproject.toml` | MODIFY | `arq>=0.26` 추가 |
| `cloud-control-plane/src/app/jobs/crawl_worker.py` | NEW | `_execute_crawl_job` arq task 등록 |
| `cloud-control-plane/src/app/queue/arq_pool.py` | NEW | `ArqRedis` 풀 (cloud-control-plane) |
| `cloud-control-plane/src/app/routers/crawl.py` | MODIFY | `background_tasks.add_task(...)` → arq enqueue |
| `cloud-control-plane/pyproject.toml` | MODIFY | `arq>=0.26` 추가 |
| `customer-runtime/tests/test_job_queue_unit.py` | NEW | 18개 단위 테스트 (arq Redis 모킹, Docker 불필요) |
| `customer-runtime/tests/test_job_queue_integration.py` | NEW | 통합 테스트 (`skip_no_docker`, CI 전용 실 Redis) |

### 핵심 결정사항 (Run 단계 확정)

- **`file_bytes` 직접 전달 채택**: Redis 직접 전달(MinIO 키 경유 불채택) — 현실적 파일 크기 범위에서 Redis 메모리 부담 수용 가능 판단
- **`ParserService` 인스턴스 제거**: Redis 직렬화 불가 → 워커 내부에서 재생성 (SPEC Technical Approach 결정 2 확정)
- **orphan 복구 정책**: 재적재 우선(멱등성 확인 후 확정). `run_parse_job`은 동일 입력 재실행 시 DB 상태를 재초기화 후 실행하므로 멱등 처리 가능
- **헬스 신호**: 옵션 A(Redis heartbeat TTL key) 채택 — `worker_health.py`가 TTL key를 갱신, Azure Container App exec probe로 key 존재 확인

### 수용 기준 검증 결과

| AC | 요건 | 검증 방법 | 결과 |
|----|------|----------|------|
| AC-001 | 재시작 생존 | 통합 테스트 (`skip_no_docker`) | ✅ |
| AC-002 | enqueue 경로 전환 | 코드 검사 (`background_tasks.add_task` 제거 확인) | ✅ |
| AC-003 | orphan 복구 | 단위 테스트 (DB 시드 + 워커 기동 모킹) | ✅ |
| AC-004 | 재시도 + 백오프 | 단위 테스트 (retry count 검증) | ✅ |
| AC-005 | DLQ 종결 | 단위 테스트 (`status='failed'` + terminal error 기록) | ✅ |
| AC-006 | 크롤 전환 | 코드 검사 | ✅ |
| AC-007 | API 무변경 | 기존 API 계약 테스트 수정 없이 통과 | ✅ |
| AC-008 | 워커 헬스 | `worker_health.py` TTL key 구현 | ✅ |
| AC-009 | 성공 부수효과 보존 | 단위 테스트 (`_push_ifu_result_to_regula` 호출 검증) | ✅ |
| AC-010 | 단위/통합 테스트 분리 | `skip_no_docker` marker 적용 확인 | ✅ |

## Dependencies

- **기존 인프라**: `docker-compose.yml`의 `redis` 서비스(이미 존재).
- **신규 패키지**: `arq` (Python). `customer-runtime`과 `cloud-control-plane`의 의존성에 추가.
- **연관 SPEC**:
  - SPEC-TENANT-ISOLATION-001 — 워커 실행 경로에서 tenant 컨텍스트를 REQ-TI-010(명시적 컨텍스트 매니저)에 따라 확립해야 함. 본 SPEC 구현 시 워커가 작업의 `tenant`를 받아 컨텍스트를 설정한다.
  - SPEC-APITOK-001 / SPEC-PERMISSION-001 — 인증 경계. 본 SPEC은 인증 결과를 소비할 뿐 변경하지 않음.

## Expert Consultation (권장)

- **expert-backend**: arq WorkerSettings 구성, `run_parse_job`의 arq 시그니처 적응, 재시도/백오프 정책, orphan 복구 멱등성 검증.
- **expert-devops**: customer-runtime worker Container App 분리 배포, Azure Container App liveness/readiness probe와 워커 헬스(REQ-JQ-008) 연동, Redis 연결/스케일 구성.
