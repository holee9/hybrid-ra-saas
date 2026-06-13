---
id: SPEC-PERMISSION-001
version: 0.1.0
status: planned
created_at: 2026-06-13
updated: 2026-06-13
author: moai
priority: high
issue_number: 35
labels: ["spec", "auth", "permissions", "review-workflow"]
---

# SPEC-PERMISSION-001: Role-Based Permissions and Review Workspace

## HISTORY

- **v0.1.0** (2026-06-13): 최초 작성. RA/QA 실무자(practitioner) · 품질관리자(quality_manager) · 관리자(admin) 3단계 역할 분리, 검토 큐(ReviewItem) 제출·할당·승인/반려 플로우, 이해상충 가드(본인 제출 승인 금지), 예외 승인(comment 필수), 역할 변경 감사 로그, JWT 사용자 인증(기존 API key 인증과 공존), 비활성 사용자 즉시 세션 무효화. EARS 18개 요구사항(REQ-PERM-001~018), 4개 데이터 모델, 10개 API 엔드포인트. GitHub Issue #35.

---

## 0. 범위 및 의존성

### 0.1 SPEC 개요

| 항목 | 내용 |
|------|------|
| SPEC-ID | SPEC-PERMISSION-001 |
| 제목 | Role-Based Permissions and Review Workspace |
| 상태 | planned |
| 대상 디렉터리 | `customer-runtime/` (Python FastAPI 마이크로서비스) |
| 분석 기준 | `customer-runtime/src/app/core/security.py`(기존 JWT/API key 인증), SPEC-UI-002(검토 큐 UI, RBAC 없음), PRD FR-207(Review Workspace), MRD REQ-MRD-108(Role & Permission) |
| 라이프사이클 | spec-anchored (애플리케이션 코드와 함께 유지) |
| 개발 방법론 | TDD (RED-GREEN-REFACTOR) |
| Priority | high |

### 0.2 이 SPEC이 다루는 것 (In Scope)

- 3개 빌트인 역할 정의: `practitioner`, `quality_manager`, `admin` (MVP에서 커스텀 역할 없음)
- 이메일 + 비밀번호 기반 JWT 사용자 인증 (bcrypt 해싱)
- 역할 기반 API 엔드포인트 접근 제어 미들웨어/의존성
- 검토 큐(ReviewItem) 제출·할당·승인/반려/변경요청/예외승인 플로우
- 역할별 큐 가시성: practitioner는 본인 할당 항목만, quality_manager/admin은 전체 조회
- 이해상충 가드: admin은 본인이 제출한 항목을 승인할 수 없음
- 예외 승인(checklist blocking gap 우회): quality_manager 이상, 비어있지 않은 comment 필수
- 역할 할당/회수/비활성화 감사 로그(RoleAuditLog)
- 승인 의사결정 감사 추적(ReviewDecision) — 생성 후 불변
- 비활성(deactivated) 사용자의 즉시 세션 무효화, 할당 항목 재할당 대기 처리
- 기존 API key 인증(ra-med-bot webhook용)과 신규 JWT 사용자 인증의 공존

### 0.3 이 SPEC이 다루지 않는 것 (Exclusions — What NOT to Build)

[HARD] 아래 항목은 SPEC-PERMISSION-001 구현 범위에서 명시적으로 제외한다. spec.md는 WHAT/WHY만 다루며 구현 세부(함수명/클래스 구조/API 스키마)는 Run 단계로 위임한다.

| 제외 항목 | 사유 | 담당 |
|-----------|------|------|
| 커스텀 역할 정의/RBAC 권한 매트릭스 편집 UI | MVP는 3개 빌트인 역할로 고정. 동적 권한은 과설계 | 미래 SPEC |
| 제3자 OAuth/SSO/SAML 로그인 | MVP는 email+password만. OAuth는 엔터프라이즈 단계 | 미래 SPEC |
| API key 인증 메커니즘 재설계 | 기존 `verify_api_key`(GAP-02)는 그대로 유지. JWT는 별도 경로로 추가 | 본 SPEC(공존만) |
| ra-med-bot / Vercel(Regula SaaS) 측 변경 | 클라우드 컨트롤 플레인은 본 SPEC 범위 외 | 비범위 |
| 검토 큐 화면 UI 컴포넌트 구현 | 화면은 SPEC-UI-002 책임. 본 SPEC은 RBAC 백엔드 + API만 | SPEC-UI-002 |
| 이메일 알림 인프라(SMTP 서버 구축) | P2 선택사항(로컬 SMTP 연동만). 알림 도메인은 분리 | 미래 SPEC |
| 비밀번호 재설정/이메일 인증/2FA | MVP는 admin이 사용자 생성·비활성화. 셀프서비스 비번 흐름은 후속 | 미래 SPEC |
| 검토 대상 엔티티(document_set/authoring_session 등) 자체의 생성/편집 로직 | 본 SPEC은 검토 워크플로 메타데이터(ReviewItem)만 다룸. 대상 엔티티는 각 도메인 SPEC | 각 도메인 SPEC |
| 멀티테넌트 사용자 격리 | Customer Local Runtime은 단일 테넌트 온프레미스 배포. tenant_id는 기존 JWT claim 유지하되 역할 격리만 추가 | 비범위 |

### 0.4 연관 SPEC 및 의존성

- **기존 코드 의존**: `customer-runtime/src/app/core/security.py` — `create_token`/`decode_token`(JWT HS256), `verify_api_key`(API key, ra-med-bot용). 본 SPEC은 이 모듈을 **확장**하며 기존 함수를 깨지 않는다.
- **소비처(미구현)**: SPEC-UI-002 검토 큐 화면 — 본 SPEC이 제공하는 RBAC API를 호출하여 역할별 가시성을 적용한다.
- **PRD**: FR-207 Review Workspace — 검토 큐, 상태, 담당자, 우선순위, 승인/반려 플로우, RA/QA/관리자 역할별 권한 및 상태 전이.
- **MRD**: REQ-MRD-108(Role & Permission, must-have), REQ-MRD-105(Self-Service UX — 비전문 개발자도 기본 업로드/검토 가능).

### 0.5 아키텍처 원칙 (불변 제약)

[HARD] 두 인증 메커니즘은 공존한다 — API key 인증(기존, 서버-서버 webhook)과 JWT 사용자 인증(신규, UI 사용자). 신규 인증이 기존 API key 경로를 변경하지 않는다.
[HARD] 비밀번호는 bcrypt로 해싱하여 저장하며 평문/가역 암호화로 저장하지 않는다.
[HARD] 비활성(`is_active = false`) 사용자는 매 요청 시 차단된다(JWT가 유효해도 거부).
[HARD] ReviewDecision은 생성 후 수정·삭제되지 않는다(감사 불변성).
[HARD] admin은 본인이 제출한 ReviewItem을 승인/예외승인할 수 없다(이해상충 가드).

### 0.6 사용자 페르소나 (배경)

| 페르소나 | 역할 | 핵심 니즈 |
|----------|------|-----------|
| P3 — 품질관리자(주 사용자) | quality_manager | "누가 무엇을 검토했고 누가 승인했는지 알아야 하며, 최종 승인은 나만 할 수 있어야 한다." 현재 역할 분리 없음 — 어떤 API key든 무엇이든 가능. |
| P2 — RA/QA 실무자 | practitioner | "전체 시스템이 아니라 내게 할당된 검토 항목만 보고 싶다." |
| P1 — 스타트업 CTO(관리자) | admin | "혼자일 때는 모든 역할을 겸하지만, 성장하면 팀원에게 역할을 부여해야 한다." |

---

## 1. 아키텍처

※ 본 절의 모듈 파일명, 클래스명, 의존성 주입 패턴 등 구현 세부는 비규범적 설계 제안이며, Run 단계에서 변경될 수 있습니다. (Non-normative design note)

### 1.0 구현 세부 메모 (Non-normative)

- **역할 미들웨어 제안**: FastAPI `Depends`로 현재 사용자 + 역할을 해석하는 의존성(`get_current_user`, `require_role(*roles)`). `decode_token`으로 JWT 검증 후 DB에서 `is_active` 확인.
- **비밀번호 해싱 제안**: `passlib[bcrypt]` 또는 `bcrypt` 직접 사용. `security.py`에 `hash_password`/`verify_password` 추가.
- **두 인증 경로 분리 제안**: API key는 기존 `X-Regula-API-Key` 헤더(webhook), JWT 사용자는 `Authorization: Bearer` 헤더(UI). 엔드포인트별로 어느 의존성을 쓸지 명시.

### 1.1 두 인증 메커니즘 공존

| 경로 | 헤더 | 용도 | 의존성 |
|------|------|------|--------|
| API key (기존) | `X-Regula-API-Key` | ra-med-bot → Customer Runtime webhook (서버-서버) | `verify_api_key` (변경 없음) |
| JWT 사용자 (신규) | `Authorization: Bearer <token>` | UI 사용자 로그인 세션 | `get_current_user` (신규) |

[HARD] 신규 JWT 사용자 인증 추가가 기존 `verify_api_key` 동작을 변경해서는 안 된다.

### 1.2 역할 권한 매트릭스

| 작업 | practitioner | quality_manager | admin |
|------|:---:|:---:|:---:|
| 문서 업로드 / 작성 세션 생성·편집 | O | O | O |
| 검토 제출 / 증빙 첨부 | O | O | O |
| 본인 할당 검토 항목 조회 | O | O | O |
| 전체 검토 항목 조회(모든 사용자) | X | O | O |
| 승인 / 반려 (comment) | X | O | O |
| 예외 승인(blocking gap 우회, comment 필수) | X | O | O |
| 감사 로그 export | X | O | O |
| 사용자 생성 / 역할 할당 / 비활성화 | X | X | O |
| 라이선스 상태 조회 / 시스템 설정 | X | X | O |
| **본인 제출 항목 승인** | — | — | **X (이해상충 가드)** |

### 1.3 검토 항목 상태 전이

```
pending ──(assign)──> in_review ──(approve)─────────> approved
   │                      │
   │                      ├──(reject)─────────────> rejected
   │                      ├──(request_changes)────> pending (재제출 대기)
   │                      └──(exception_approve)──> exception_approved
   │
   └──(submitter 직접)──> in_review (할당 없이 검토 시작 가능)
```

- `approve` / `reject` / `exception_approve`는 quality_manager 이상만 수행한다.
- `exception_approve`는 checklist blocking gap이 있는 항목을 우회 승인하며 comment가 필수다.

### 1.4 통합 흐름

```
사용자 로그인 (POST /auth/login)
  → email+password 검증 (bcrypt)
  → JWT 발급 (access 1h + refresh 7d)
검토 제출 (POST /review-items)
  → ReviewItem(status=pending) 생성
관리자 할당 (PATCH /review-items/{id}/assign)
  → assigned_to 설정, status=in_review
의사결정 (POST /review-items/{id}/decide)
  → 역할 검증(quality_manager+) → 이해상충 가드 → ReviewDecision INSERT(불변) → ReviewItem.status 갱신
감사 조회 (GET /audit/decisions)
  → ReviewDecision 이력 반환
```

---

## 2. EARS 요구사항

요구사항은 5개 모듈로 그룹화한다: M1(인증), M2(역할 접근 제어), M3(검토 워크플로), M4(이해상충·예외승인), M5(감사·생명주기).

### M1 — 인증 (Authentication)

**REQ-PERM-001 (Event-Driven, Login)**
When a user submits valid email and password to `POST /auth/login`, the system shall verify the password against the bcrypt hash and return a JWT access token and a refresh token.

**REQ-PERM-002 (Unwanted Behavior, Invalid credentials)**
If the email does not exist or the password does not match the stored bcrypt hash, then the system shall reject the login with HTTP 401 and shall NOT reveal whether the email or the password was incorrect.

**REQ-PERM-003 (Ubiquitous, Token TTL)**
The system shall issue access tokens with a 1-hour expiry and refresh tokens with a 7-day expiry.

**REQ-PERM-004 (Event-Driven, Token refresh)**
When a client submits a valid, non-expired refresh token to `POST /auth/refresh`, the system shall issue a new access token.

**REQ-PERM-005 (Event-Driven, Current user profile)**
When an authenticated user requests `GET /users/me`, the system shall return the user's profile including their assigned role.

### M2 — 역할 접근 제어 (Role-Based Access Control)

**REQ-PERM-006 (State-Driven, Role enforcement)**
While a JWT-authenticated request targets a role-restricted endpoint, the system shall permit the request only if the user's role is included in that endpoint's allowed roles, and shall otherwise reject it with HTTP 403.

**REQ-PERM-007 (Unwanted Behavior, Practitioner approval block)**
If a user with role `practitioner` calls the decision endpoint (`POST /review-items/{id}/decide`), then the system shall reject the request with HTTP 403.

**REQ-PERM-008 (State-Driven, Queue visibility — practitioner)**
While a `practitioner` requests `GET /review-items`, the system shall return only the review items assigned to that practitioner.

**REQ-PERM-009 (State-Driven, Queue visibility — manager/admin)**
While a `quality_manager` or `admin` requests `GET /review-items`, the system shall return all review items across all users.

**REQ-PERM-010 (Unwanted Behavior, User management restriction)**
If a non-`admin` user calls a user-management endpoint (`POST /users` or `PATCH /users/{id}/role`), then the system shall reject the request with HTTP 403.

### M3 — 검토 워크플로 (Review Workflow)

**REQ-PERM-011 (Event-Driven, Submit for review)**
When an authenticated user submits a review item via `POST /review-items`, the system shall create a ReviewItem with status `pending` and record the submitter.

**REQ-PERM-012 (Event-Driven, Assign reviewer)**
When a `quality_manager` or `admin` assigns a review item via `PATCH /review-items/{id}/assign`, the system shall set the item's `assigned_to` field and transition its status to `in_review`.

**REQ-PERM-013 (Event-Driven, Approve/reject decision)**
When a `quality_manager` or `admin` submits a decision via `POST /review-items/{id}/decide`, the system shall create an immutable ReviewDecision record and update the ReviewItem status to match the decision action.

**REQ-PERM-014 (Unwanted Behavior, Reject requires comment)**
If a decision action is `reject` or `exception_approve` and the comment is empty or missing, then the system shall reject the request with HTTP 422.

### M4 — 이해상충 및 예외 승인 (Conflict of Interest & Exception Approval)

**REQ-PERM-015 (Unwanted Behavior, Self-approval guard)**
If an `admin` attempts to approve, reject, or exception-approve a review item that they themselves submitted, then the system shall reject the request with HTTP 403.

**REQ-PERM-016 (State-Driven, Exception approval authority)**
While a decision action is `exception_approve`, the system shall permit it only if the actor's role is `quality_manager` or `admin`.

### M5 — 감사 및 생명주기 (Audit & Lifecycle)

**REQ-PERM-017 (Event-Driven, Role change audit)**
When an `admin` assigns or revokes a user's role via `PATCH /users/{id}/role`, the system shall write a RoleAuditLog entry recording the actor, target user, previous role, new role, and timestamp.

**REQ-PERM-018 (Unwanted Behavior, Deactivated user block)**
If a request carries a valid JWT but the associated user's `is_active` flag is `false`, then the system shall reject the request with HTTP 401 regardless of token validity.

### 비기능 요구사항 (Non-Functional)

**REQ-PERM-NFR-001 (Ubiquitous, Audit immutability)**
The system shall NOT provide any endpoint or operation that modifies or deletes a ReviewDecision record after its creation.

**REQ-PERM-NFR-002 (State-Driven, Role check overhead)**
While performing the role-check middleware on a request, the added latency shall not exceed 5ms (excluding database round-trip for the user lookup, which may be cached).

**REQ-PERM-NFR-003 (Event-Driven, Deactivation reassignment)**
When an `admin` deactivates a user, the system shall clear the `assigned_to` field (set to null) on all review items currently assigned to that user, returning them to a pending-reassignment state.

---

## 3. 데이터 모델

※ 컬럼명/타입은 비규범적 설계 제안이며 Run 단계에서 조정될 수 있다.

### 3.1 `users` 테이블 (신규)

```sql
CREATE TABLE users (
    user_id         VARCHAR(36)  PRIMARY KEY,            -- uuid4
    email           VARCHAR(320) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,               -- bcrypt
    role            VARCHAR(20)  NOT NULL DEFAULT 'practitioner',  -- practitioner|quality_manager|admin
    is_active       BOOLEAN      NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_login      TIMESTAMPTZ  NULL
);
CREATE UNIQUE INDEX ux_users_email ON users (email);
```

### 3.2 `review_items` 테이블 (신규)

```sql
CREATE TABLE review_items (
    item_id      VARCHAR(36)  PRIMARY KEY,
    item_type    VARCHAR(32)  NOT NULL,   -- document_set|authoring_session|checklist_snapshot|evidence_binder
    item_ref_id  VARCHAR(36)  NOT NULL,   -- 대상 엔티티 FK (느슨한 참조)
    submitted_by VARCHAR(36)  NOT NULL REFERENCES users(user_id),
    assigned_to  VARCHAR(36)  NULL REFERENCES users(user_id),
    priority     VARCHAR(10)  NOT NULL DEFAULT 'normal',  -- low|normal|high|urgent
    status       VARCHAR(24)  NOT NULL DEFAULT 'pending', -- pending|in_review|approved|rejected|exception_approved
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    reviewed_at  TIMESTAMPTZ  NULL
);
CREATE INDEX ix_reviewitem_assigned ON review_items (assigned_to, status);
CREATE INDEX ix_reviewitem_status ON review_items (status, priority);
```

### 3.3 `review_decisions` 테이블 (신규, 불변)

```sql
CREATE TABLE review_decisions (
    decision_id VARCHAR(36)  PRIMARY KEY,
    item_id     VARCHAR(36)  NOT NULL REFERENCES review_items(item_id),
    reviewer_id VARCHAR(36)  NOT NULL REFERENCES users(user_id),
    action      VARCHAR(20)  NOT NULL,   -- approve|reject|request_changes|exception_approve
    comment     TEXT         NULL,       -- reject/exception_approve 시 NOT NULL 강제(앱 레벨)
    decided_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_decision_item ON review_decisions (item_id, decided_at);
```

- [HARD] UPDATE/DELETE를 노출하지 않는다(REQ-PERM-NFR-001).
- `action IN ('reject','exception_approve')`인 경우 `comment`는 비어있지 않아야 한다(REQ-PERM-014, 앱 레벨 검증).

### 3.4 `role_audit_log` 테이블 (신규)

```sql
CREATE TABLE role_audit_log (
    log_id         VARCHAR(36)  PRIMARY KEY,
    actor_id       VARCHAR(36)  NOT NULL REFERENCES users(user_id),
    target_user_id VARCHAR(36)  NOT NULL REFERENCES users(user_id),
    action         VARCHAR(20)  NOT NULL,   -- role_assigned|role_revoked|user_deactivated
    previous_role  VARCHAR(20)  NULL,
    new_role       VARCHAR(20)  NULL,
    reason         TEXT         NULL,
    timestamp      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_roleaudit_target ON role_audit_log (target_user_id, timestamp);
```

---

## 4. API 엔드포인트

※ 경로/메서드는 규범적이나 요청/응답 스키마 세부는 Run 단계 위임.

| 메서드 | 경로 | 권한 | REQ |
|--------|------|------|-----|
| POST | `/auth/login` | 비인증 | REQ-PERM-001, 002 |
| POST | `/auth/refresh` | refresh token | REQ-PERM-004 |
| GET | `/users/me` | 인증 | REQ-PERM-005 |
| POST | `/users` | admin | REQ-PERM-010 |
| PATCH | `/users/{id}/role` | admin | REQ-PERM-010, 017 |
| GET | `/review-items` | 인증(역할 필터) | REQ-PERM-008, 009 |
| POST | `/review-items` | 인증 | REQ-PERM-011 |
| PATCH | `/review-items/{id}/assign` | quality_manager+ | REQ-PERM-012 |
| POST | `/review-items/{id}/decide` | quality_manager+ | REQ-PERM-007, 013, 014, 015, 016 |
| GET | `/audit/decisions` | quality_manager+ | REQ-PERM-NFR-001 |

---

## 5. What NOT to Build (Exclusions 요약)

§0.3 참조. 최소 핵심 제외:

1. **커스텀 역할 / 동적 RBAC 권한 편집** — MVP는 3개 빌트인 역할 고정.
2. **제3자 OAuth / SSO / 2FA / 비밀번호 재설정 흐름** — email+password만, admin이 사용자 생성·비활성화.
3. **검토 큐 화면 UI** — SPEC-UI-002 책임. 본 SPEC은 RBAC 백엔드 + API만.
4. **API key 인증 재설계** — 기존 `verify_api_key`(GAP-02)는 그대로 유지, JWT는 별도 경로 추가.
5. **이메일 알림 인프라** — P2 선택(로컬 SMTP 연동만), 알림 도메인 분리.

---

## 6. 보안 및 컴플라이언스

- [HARD] 비밀번호는 bcrypt로 해싱하여 저장한다(평문/가역 암호화 금지).
- [HARD] 로그인 실패 시 이메일/비밀번호 중 무엇이 틀렸는지 노출하지 않는다(REQ-PERM-002, 사용자 열거 방지).
- [HARD] 비활성 사용자는 유효한 JWT가 있어도 매 요청 차단한다(REQ-PERM-018).
- [HARD] ReviewDecision은 불변이다 — 수정/삭제 엔드포인트를 제공하지 않는다(감사 무결성).
- [HARD] 이해상충 가드 — admin은 본인 제출 항목을 승인할 수 없다(REQ-PERM-015).
- JWT secret은 환경 변수(`jwt_secret`, 기존 `Settings` 재사용)로만 주입한다.
- 두 인증 메커니즘 공존 시 엔드포인트별로 어느 인증을 요구하는지 명시한다(혼선 방지).

---

## 7. 전문가 자문 권장

- **expert-backend**: FastAPI 의존성 기반 역할 미들웨어, JWT access/refresh 흐름, SQLAlchemy async 사용자 조회 캐싱, bcrypt 통합. (키워드: API, auth, database)
- **expert-security**: 이해상충 가드 우회 경로 점검, 사용자 열거 방지, 비활성 사용자 세션 무효화, 감사 불변성 검증. (키워드: auth, audit, OWASP)

---

## 8. 구현 단계

| 단계 | 범위 |
|------|------|
| **P0** | `users` 테이블 + role enum, JWT 인증 엔드포인트(login/refresh/me), 역할 기반 미들웨어/의존성, admin 사용자 생성 + 역할 할당. (REQ-PERM-001~006, 010, 017, 018) |
| **P1** | `review_items` + `review_decisions` 테이블, 제출 플로우, 승인/반려 엔드포인트, 역할 필터 큐 API, 이해상충 가드. (REQ-PERM-007~009, 011~015) |
| **P2** | 예외 승인 + 감사 추적, 감사 로그 export, 비활성화 시 재할당, 이메일 알림(선택, 로컬 SMTP). (REQ-PERM-016, NFR-001~003) |

---

## 9. 인수 기준 연결

각 REQ는 하나 이상의 AC에 대응한다. 상세 Given/When/Then 시나리오는 `acceptance.md` 참조(미작성 시 Run 단계에서 생성).

| REQ | 검증 포인트 |
|-----|-------------|
| REQ-PERM-001/002 | 로그인 성공/실패, 자격증명 미노출 |
| REQ-PERM-003/004 | access 1h / refresh 7d 만료, refresh 재발급 |
| REQ-PERM-005 | /users/me 역할 포함 응답 |
| REQ-PERM-006/007/010 | 역할별 403 차단 |
| REQ-PERM-008/009 | practitioner 본인 항목만 / manager 전체 |
| REQ-PERM-011/012/013 | 제출→할당→의사결정 상태 전이 |
| REQ-PERM-014 | reject/exception comment 누락 시 422 |
| REQ-PERM-015 | admin 본인 제출 승인 403 |
| REQ-PERM-016 | exception_approve 권한 검증 |
| REQ-PERM-017 | 역할 변경 시 RoleAuditLog 기록 |
| REQ-PERM-018 | 비활성 사용자 401 |
| REQ-PERM-NFR-001 | ReviewDecision 수정 엔드포인트 부재 |
| REQ-PERM-NFR-002 | 미들웨어 오버헤드 ≤ 5ms |
| REQ-PERM-NFR-003 | 비활성화 시 assigned_to null 처리 |
