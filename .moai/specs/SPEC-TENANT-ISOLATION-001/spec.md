---
spec_id: SPEC-TENANT-ISOLATION-001
title: ORM Level Automatic Tenant Filtering
status: completed
version: "1.0"
created: 2026-06-17
github_issue: 38
dependencies:
  - SPEC-PERMISSION-001
  - SPEC-APITOK-001
---

# SPEC-TENANT-ISOLATION-001: ORM Level Automatic Tenant Filtering

## Goal

Customer Runtime의 ORM 계층에서 `tenant_id` 필터링을 자동화하여, 개발자가 쿼리마다 수동으로 테넌트 필터를 추가하는 데 의존하지 않고도 교차 테넌트(cross-tenant) 데이터 유출을 구조적으로 차단한다. `TenantMixin`을 상속한 모든 모델의 SELECT 쿼리에 현재 요청의 `tenant_id` 조건이 자동으로 주입되며, 필터 누락은 더 이상 데이터 유출이 아니라 명시적 오류로 전환된다.

## Background

Customer Runtime는 27개 ORM 모델(`src/app/models/`)과 16개 API 라우터로 구성된 의료기기 규제 대응(Regulatory Affairs) SaaS의 핵심 런타임이다. 각 테넌트는 의료기기 제조사이며, 규제 제출 문서, 위험 분석, 추적성 그래프, 증거 바인더 등 규제 감사 대상 데이터를 저장한다.

현재 격리 모델은 개발자가 모든 데이터베이스 쿼리에 `WHERE tenant_id = :current_tenant` 조건을 직접 작성하는 데 의존한다. codemaps 분석(`dependencies.md` issue #6)은 다음과 같은 위험 패턴을 식별했다.

```python
# DANGEROUS: 테넌트 필터 누락 — 전체 테넌트 데이터 노출
documents = await session.query(Document).all()

# SAFE: 테넌트 필터 적용
documents = await session.query(Document).filter(
    Document.tenant_id == current_tenant_id
).all()
```

`tenant_id`를 단 한 곳에서라도 누락하면 다른 제조사의 규제 데이터가 노출된다. 의료기기 규제 데이터는 영업비밀과 환자 안전 정보를 포함하므로, 단일 누락도 규제 위반(예: ISO 13485, FDA 21 CFR Part 11의 데이터 무결성/접근 통제)과 계약 위반으로 직결된다. 27개 모델 × 16개 라우터의 모든 쿼리를 사람이 검수하는 방식은 확장 불가능하며, 신규 라우터/쿼리가 추가될 때마다 유출 표면이 늘어난다.

기존 자산:
- `app.models.base.TenantMixin` — `tenant_id` 컬럼(인덱스 포함)을 제공하는 믹스인이 이미 존재한다.
- `app.deps.get_current_tenant` / `get_current_user` — JWT의 `tenant_id` 클레임과 `X-Tenant-ID` 헤더를 대조하여 테넌트를 확정한다.
- `app.database.async_sessionmaker` — `AsyncSession`을 생성하는 단일 세션 팩토리.
- `app.core.security` — JWT/API key 인증 경계(SPEC-PERMISSION-001, SPEC-APITOK-001).

이 SPEC는 이미 확정된 `tenant_id`를 ORM 계층까지 전파하여, 인증 경계에서 데이터 접근 경계까지 일관된 격리를 보장한다.

## Scope

### In Scope

- `TenantMixin`을 상속한 모델(현재 대부분의 비즈니스 모델)에 대한 세션 레벨 자동 SELECT 필터링
- 요청 컨텍스트에서 ORM 계층으로의 `tenant_id` 전파 메커니즘
- INSERT 시 `tenant_id` 자동 설정/검증
- admin/superuser 역할에 대한 명시적 우회(bypass) 경로
- 자동 필터링을 적용할 수 없는 컨텍스트(백그라운드 작업, 마이그레이션) 처리 규칙
- 격리 위반을 검증하는 보안 테스트 스위트
- 기존 라우터/쿼리에 대한 점진적 마이그레이션 전략

### Out of Scope

- `TenantMixin`을 상속하지 않는 글로벌 테이블(예: 시스템 설정, 규제 템플릿 카탈로그)에 대한 필터링 — 이들은 의도적으로 테넌트 공유 자원이다
- 행 수준 보안(PostgreSQL Row-Level Security, RLS) 데이터베이스 네이티브 구현 — 본 SPEC은 애플리케이션 ORM 계층 범위로 한정 (RLS는 후속 SPEC에서 별도 평가)
- 컬럼 수준 암호화 또는 필드 마스킹
- 테넌트 간 데이터 마이그레이션/병합 도구
- 기존 인증 메커니즘(JWT, API token)의 변경 — 본 SPEC은 인증 결과인 `tenant_id`를 소비할 뿐 인증을 재정의하지 않는다
- 라우터의 권한(RBAC) 로직 변경 — SPEC-PERMISSION-001 소관

## Requirements (EARS Format)

### Functional Requirements

**REQ-TI-001** (Ubiquitous): The system SHALL provide a tenant context propagation mechanism (a `ContextVar`) that carries the active `tenant_id` from the request boundary into the ORM layer for the lifetime of a single request.

**REQ-TI-002** (Event-Driven): WHEN an `AsyncSession` executes a SELECT against a model that inherits `TenantMixin`, the system SHALL automatically append a `tenant_id == <current tenant>` predicate to the query.

**REQ-TI-003** (Unwanted): IF a query against a `TenantMixin` model is executed AND no tenant context is set AND the request is not an admin/system context, THEN the system SHALL raise an explicit error rather than returning unfiltered rows.

**REQ-TI-004** (Event-Driven): WHEN a new instance of a `TenantMixin` model is added to a session for INSERT AND its `tenant_id` is unset, the system SHALL populate `tenant_id` from the current tenant context.

**REQ-TI-005** (Unwanted): IF a new or updated `TenantMixin` instance carries a `tenant_id` that differs from the current tenant context, THEN the system SHALL reject the write with an explicit error (prevent tenant spoofing on write).

**REQ-TI-006** (State-Driven): WHILE the current request context is marked as an admin/superuser bypass, the system SHALL execute queries without injecting the automatic tenant predicate.

**REQ-TI-007** (Event-Driven): WHEN `tenant_id` is resolved by an authentication dependency (`get_current_tenant`, `get_current_user`, `verify_hybrid_bearer_token`, `verify_api_key`), the system SHALL set the tenant context before any ORM access occurs in the request.

**REQ-TI-008** (Event-Driven): WHEN a request completes (success or failure), the system SHALL clear the tenant context so it cannot leak into a subsequent request served by the same worker.

**REQ-TI-009** (Optional): WHERE a query intentionally targets a tenant-shared global table (a model that does NOT inherit `TenantMixin`), the system SHALL execute the query without any tenant predicate.

**REQ-TI-010** (State-Driven): WHILE executing a background task or data migration outside an HTTP request, the system SHALL require the caller to explicitly establish a tenant context (or an explicit system/bypass context) before any `TenantMixin` query.

**REQ-TI-011** (Ubiquitous): The system SHALL expose a verifiable, machine-checkable inventory of which models are tenant-scoped versus tenant-shared, so coverage can be audited in CI.

**REQ-TI-012** (Event-Driven): WHEN the automatic filter is applied to a relationship load (eager or lazy) of a `TenantMixin` model, the system SHALL ensure the related rows are also constrained to the current tenant.

### Non-Functional Requirements

**REQ-TI-NF-001** (Performance): The automatic filtering SHALL NOT add more than 5ms of latency per query relative to the equivalent hand-written `tenant_id` filter, measured at P95 over a representative query workload.

**REQ-TI-NF-002** (Security): The tenant isolation guarantee SHALL be verifiable via an automated penetration/negative test that attempts cross-tenant reads and writes and confirms all are denied.

**REQ-TI-NF-003** (Compatibility): The mechanism SHALL NOT require changes to existing router function signatures or query call sites to be secure-by-default; routers that already pass `tenant_id` explicitly MUST continue to work unchanged.

**REQ-TI-NF-004** (Observability): The system SHALL log (without leaking other tenants' data) any occurrence of REQ-TI-003 and REQ-TI-005 violations as security events for audit.

## Acceptance Criteria

1. **자동 필터 적용**: 테넌트 컨텍스트가 `tenant-A`로 설정된 상태에서 `select(Document)`를 `WHERE` 절 없이 실행하면, 반환된 모든 행의 `tenant_id == "tenant-A"`이며 `tenant-B`의 행은 0건이다. (REQ-TI-002)

2. **컨텍스트 미설정 차단**: 테넌트 컨텍스트가 설정되지 않은 상태에서 `TenantMixin` 모델 쿼리를 실행하면, 빈/전체 결과가 아니라 명시적 예외가 발생한다. (REQ-TI-003)

3. **쓰기 시 테넌트 자동 설정 및 스푸핑 차단**: `tenant-A` 컨텍스트에서 `tenant_id`를 지정하지 않고 `Document`를 생성하면 `tenant_id`가 `tenant-A`로 채워진다. `tenant-B`로 명시 지정하면 쓰기가 거부된다. (REQ-TI-004, REQ-TI-005)

4. **admin 우회**: admin 우회 컨텍스트에서 동일한 `select(Document)`를 실행하면 모든 테넌트의 행이 반환된다. (REQ-TI-006)

5. **글로벌 테이블 무필터**: `TenantMixin`을 상속하지 않는 모델 쿼리는 테넌트 컨텍스트와 무관하게 전체 행을 반환한다. (REQ-TI-009)

6. **라우터 무변경 회귀**: 기존 16개 라우터의 통합 테스트가 코드 수정 없이 모두 통과하며, 각 라우터는 자신의 테넌트 데이터만 반환한다. (REQ-TI-NF-003)

7. **요청 간 컨텍스트 격리**: 동일 워커가 `tenant-A` 요청을 처리한 직후 `tenant-B` 요청을 처리할 때, `tenant-A`의 컨텍스트가 누출되지 않는다. (REQ-TI-008)

8. **교차 테넌트 침투 테스트**: 자동화된 보안 테스트가 교차 테넌트 읽기/쓰기를 시도하고 전건 차단을 확인한다. (REQ-TI-NF-002)

9. **성능 회귀 게이트**: 자동 필터 경로의 P95 쿼리 지연이 수동 필터 대비 +5ms 이내임을 벤치마크로 확인한다. (REQ-TI-NF-001)

10. **모델 커버리지 감사**: CI에서 테넌트 스코프/공유 모델 인벤토리를 검증하여, 새 모델이 분류 누락 시 빌드가 실패한다. (REQ-TI-011)

## Technical Approach (High Level)

코드가 아닌 아키텍처 결정 수준의 스케치다. 구현 세부는 Run 단계에서 확정한다.

### 결정 1 — tenant_id를 ORM 계층으로 전달하는 방법: ContextVar

- 후보: (a) `contextvars.ContextVar`로 요청 범위 테넌트 보관, (b) 세션 `info` 딕셔너리에 테넌트 주입, (c) 매 쿼리에 `tenant_id` 인자 강제.
- 선택: **ContextVar 기반**. FastAPI 의존성(`get_current_tenant` 등)이 인증 직후 `ContextVar`에 `tenant_id`를 설정하고, ORM 이벤트 리스너가 이를 읽는다. (c)는 REQ-TI-NF-003(라우터 무변경)을 위반하므로 제외. (b)는 세션 핸들이 호출부까지 전파되어야 하는 결합을 만든다.
- 정리는 의존성의 finally 또는 미들웨어에서 `ContextVar.reset()`으로 수행하여 REQ-TI-008을 보장한다.

### 결정 2 — 자동 필터 주입 지점: SQLAlchemy ORM 이벤트 vs 커스텀 Session vs `__init_subclass__`

- 후보:
  - (a) SQLAlchemy `do_orm_execute` 이벤트 + `with_loader_criteria` — 모델별 필터 조건을 SELECT 실행 시점에 주입.
  - (b) 커스텀 `Session`/`Query` 서브클래스 — 쿼리 빌드 단계에서 필터 추가.
  - (c) `Base.__init_subclass__` — 클래스 정의 시점에 기본 조건 부착.
- 선택: **(a) `do_orm_execute` + `with_loader_criteria`**. 이 조합은 SQLAlchemy 2.0이 공식 지원하는 "전역 행 필터" 패턴으로, 직접 쿼리뿐 아니라 관계 로딩(eager/lazy)에도 적용되어 REQ-TI-012를 자연스럽게 충족한다. (b)는 비동기 세션에서 깨지기 쉽고 유지보수 부담이 크다. (c)는 SELECT 시점의 동적 `tenant_id`를 표현하기 어렵다.
- 쓰기 측(REQ-TI-004/005)은 `before_flush`(또는 `before_insert`/`before_update`) 이벤트에서 `tenant_id` 자동 설정과 불일치 거부를 수행한다.

### 결정 3 — admin/superuser 우회

- `ContextVar`에 테넌트 값과 별도로 "bypass" 플래그(또는 sentinel 테넌트 값)를 둔다.
- `do_orm_execute` 리스너는 bypass가 활성일 때 `with_loader_criteria`를 주입하지 않는다 (REQ-TI-006).
- bypass 설정 권한은 SPEC-PERMISSION-001의 admin 역할 검사를 통과한 의존성에서만 부여한다 — 우회는 인증/인가 경계에서만 활성화 가능하며, 임의 코드가 스스로 우회를 켤 수 없도록 한다.

### 결정 4 — 컨텍스트 미설정 처리 (fail-closed)

- 리스너는 대상 모델이 `TenantMixin`을 상속하는지 검사한다 (REQ-TI-011의 인벤토리와 일치).
- 테넌트 컨텍스트가 없고 bypass도 아니면 예외를 발생시킨다 (REQ-TI-003) — 기본 동작은 fail-closed.
- 백그라운드 작업/마이그레이션은 명시적 컨텍스트 진입(컨텍스트 매니저)을 요구한다 (REQ-TI-010).

### 결정 5 — 기존 쿼리 마이그레이션 경로

- 자동 필터는 기존의 수동 `tenant_id` 필터와 충돌하지 않는다 (동일 조건 중복은 결과를 바꾸지 않음). 따라서 라우터를 한꺼번에 수정할 필요 없이 **secure-by-default로 즉시 동작**한다 (REQ-TI-NF-003).
- 후속 정리 단계에서 중복된 수동 필터를 점진 제거할 수 있으나, 이는 선택적 리팩터링이며 격리 보장의 전제 조건은 아니다.
- 모델 분류(tenant-scoped vs shared)는 CI 감사 테스트로 강제한다 (결정 4의 인벤토리 = REQ-TI-011).

## Affected Files

구현 시 변경/추가가 예상되는 파일 목록이다.

- `customer-runtime/src/app/db/tenant_context.py` (신규) — `ContextVar` 정의, set/reset/bypass 헬퍼, 명시적 컨텍스트 매니저(REQ-TI-001, REQ-TI-010).
- `customer-runtime/src/app/db/tenant_filter.py` (신규) — `do_orm_execute` 리스너(`with_loader_criteria` 주입)와 `before_flush` 리스너(쓰기 검증) 등록(REQ-TI-002, REQ-TI-004, REQ-TI-005, REQ-TI-012).
- `customer-runtime/src/app/database.py` — 세션 팩토리 생성 시 이벤트 리스너 연결(엔진/세션 이벤트 바인딩).
- `customer-runtime/src/app/deps.py` — `get_current_tenant`/`get_current_user`가 `tenant_id` 확정 후 테넌트 컨텍스트를 설정하고 요청 종료 시 reset(REQ-TI-007, REQ-TI-008).
- `customer-runtime/src/app/core/security.py` — `verify_hybrid_bearer_token`/`verify_api_key`가 반환하는 `tenant_id`를 컨텍스트에 연결(서비스 간 호출 경로, REQ-TI-007).
- `customer-runtime/src/app/main.py` — (선택) 미들웨어로 요청 경계 컨텍스트 정리 보강.
- `customer-runtime/src/app/models/base.py` — `TenantMixin` 인벤토리/판별 헬퍼 보강(필요 시), 모델 분류 마커.
- `customer-runtime/tests/test_tenant_isolation.py` (신규) — 단위/통합/보안 테스트.
- `customer-runtime/tests/test_tenant_isolation_perf.py` (신규) — 성능 회귀 벤치마크(REQ-TI-NF-001).
- `customer-runtime/tests/test_model_tenant_coverage.py` (신규) — 모델 분류 CI 감사(REQ-TI-011).

## Test Plan

**단위 테스트 (Unit)**
- ContextVar set/reset/bypass 동작 및 요청 간 누출 부재(REQ-TI-001, REQ-TI-008).
- `before_flush` 리스너의 `tenant_id` 자동 설정 및 불일치 거부(REQ-TI-004, REQ-TI-005).
- 컨텍스트 미설정 시 fail-closed 예외(REQ-TI-003).

**통합 테스트 (Integration, 실 DB 대상)**
- `tenant-A`/`tenant-B` 두 테넌트의 데이터를 시드 후, A 컨텍스트에서 각 `TenantMixin` 모델을 조회하여 A 데이터만 반환됨을 확인(REQ-TI-002).
- 관계 로딩(eager/lazy)에서도 교차 테넌트 행이 섞이지 않음(REQ-TI-012).
- admin bypass에서 전체 테넌트 반환(REQ-TI-006).
- 글로벌(비 TenantMixin) 모델 무필터(REQ-TI-009).
- 기존 16개 라우터 통합 테스트 무변경 회귀(REQ-TI-NF-003).
- (lessons.md 반영) 통합 테스트는 CI 전용 실 DB 픽스처에서 동작하도록 설계하며 mock으로 대체하지 않는다.

**보안 테스트 (Security / Negative)**
- 교차 테넌트 읽기 시도 전건 차단(REQ-TI-NF-002).
- 쓰기 시 `tenant_id` 스푸핑 시도 거부(REQ-TI-005).
- 위반 발생 시 보안 이벤트 로깅 확인(REQ-TI-NF-004).

**성능 테스트 (Performance)**
- 자동 필터 vs 수동 필터 P95 지연 비교가 +5ms 이내(REQ-TI-NF-001).

**커버리지 게이트**
- 신규 모듈 ≥85% 커버리지(TRUST 5 Tested).
- 모델 분류 감사 테스트가 신규 모델 누락 시 실패(REQ-TI-011).

## Risk Assessment

**Risk 1 — `with_loader_criteria`가 일부 쿼리 형태(원시 SQL, Core `text()`, 일부 서브쿼리)에 적용되지 않아 사각지대 발생**
- 영향: 우회 경로로 교차 테넌트 유출 잔존 — 치명적.
- 완화: 인벤토리 기반 CI 감사로 ORM 비경유 데이터 접근을 탐지하고 금지(grep/AST 검사). 원시 SQL이 불가피한 경로는 명시적 tenant 바인딩을 코드 리뷰 필수 항목으로 지정. 보안 테스트가 각 모델 경로를 전수 검증.

**Risk 2 — 비동기(ContextVar) 컨텍스트가 백그라운드 태스크/`asyncio.gather`/스레드 풀 경계에서 전파되지 않거나 누출**
- 영향: 요청 간 컨텍스트 혼선 또는 fail-closed 예외 과다 발생(가용성 저하).
- 완화: 요청 경계(미들웨어/의존성 finally)에서 reset 보장. 백그라운드 경로는 REQ-TI-010의 명시적 컨텍스트 매니저를 강제. `gather` 사용 구간은 컨텍스트 복사 패턴 적용 및 전용 테스트로 검증.

**Risk 3 — 자동 필터가 기존 수동 필터와 중복되어 성능 저하 또는 미묘한 쿼리 플랜 변화**
- 영향: P95 지연 증가로 REQ-TI-NF-001 미충족 가능.
- 완화: `tenant_id`는 이미 인덱스 컬럼(`TenantMixin`). 중복 조건은 동일 술어이므로 옵티마이저가 정규화. 성능 벤치마크 게이트로 회귀 차단하고, 필요 시 후속 단계에서 수동 중복 필터 정리.

## Implementation Notes

**완료일**: 2026-06-17  
**커밋**: `7a79675` (구현), `9f7d049` (테스트 수정)  
**참조 이슈**: #38 (closed)

### 구현 결과

| 구성요소 | 파일 | 상태 |
|----------|------|------|
| ContextVar 모듈 | `db/tenant_context.py` | ✅ 완료 |
| ORM 리스너 | `db/tenant_filter.py` | ✅ 완료 |
| 세션 팩토리 연결 | `database.py` | ✅ 완료 |
| 의존성 generator 전환 | `deps.py` | ✅ 완료 |
| 보안 함수 generator 전환 | `core/security.py` | ✅ 완료 |
| 모델 helper | `models/base.py` | ✅ 완료 |
| 단위 테스트 | `tests/test_tenant_isolation.py` | ✅ 22개 pass |
| 모델 분류 감사 | `tests/test_model_tenant_coverage.py` | ✅ 4개 pass |

### 미완료 항목 (후속 SPEC 대상)

- `MIGRATION_PENDING_MODELS` 15개 기존 모델에 `TenantMixin` 추가 (Alembic 마이그레이션 필요)
- 통합 테스트 (AC-010 포함) — CI Docker 환경에서 실행
- 기존 라우터의 중복 수동 `tenant_id` 필터 정리 (선택적 최적화)
