# SPEC-PERMISSION-001 — Task Breakdown

연관: spec.md / Issue #35
방법론: TDD (RED-GREEN-REFACTOR). 각 태스크는 테스트 우선.

---

## P0 — 인증 기반 + 역할 미들웨어

선행 의존: 없음. `customer-runtime/src/app/core/security.py` 확장.

| ID | 태스크 | 대응 REQ | 산출물(제안) |
|----|--------|----------|--------------|
| P0-1 | `users` 테이블 ORM 모델 + role enum(practitioner/quality_manager/admin) + is_active | 데이터 모델 §3.1 | `models/user.py`, Alembic migration |
| P0-2 | bcrypt `hash_password`/`verify_password`를 security.py에 추가 | REQ-PERM-001, 보안 | `core/security.py` 확장 |
| P0-3 | `POST /auth/login` — email+password 검증, JWT access(1h)+refresh(7d) 발급 | REQ-PERM-001, 002, 003 | `routers/auth.py` |
| P0-4 | `POST /auth/refresh` — refresh token 검증 후 access 재발급 | REQ-PERM-004 | `routers/auth.py` |
| P0-5 | `get_current_user` 의존성 — Bearer JWT 디코드 + DB is_active 확인 | REQ-PERM-005, 018 | `core/deps.py` |
| P0-6 | `require_role(*roles)` 의존성 — 역할 불일치 시 403 | REQ-PERM-006 | `core/deps.py` |
| P0-7 | `GET /users/me` — 현재 사용자 프로필 + 역할 반환 | REQ-PERM-005 | `routers/users.py` |
| P0-8 | `POST /users`(admin) — 사용자 생성 | REQ-PERM-010 | `routers/users.py` |
| P0-9 | `PATCH /users/{id}/role`(admin) — 역할 할당 + RoleAuditLog 기록 | REQ-PERM-010, 017 | `routers/users.py`, `models/role_audit_log.py` |
| P0-10 | 로그인 자격증명 미노출 검증(401, 이메일/비번 구분 안 함) | REQ-PERM-002 | 테스트 |
| P0-11 | 기존 `verify_api_key` 회귀 테스트(공존 보장) | §1.1 | 테스트 |

P0 완료 기준: login/refresh/me 동작, admin이 사용자 생성·역할 할당, 비활성 사용자 401, API key 경로 무회귀, 커버리지 ≥ 85%.

---

## P1 — 검토 큐 워크플로 + 이해상충 가드

선행 의존: P0(users, 역할 미들웨어).

| ID | 태스크 | 대응 REQ | 산출물(제안) |
|----|--------|----------|--------------|
| P1-1 | `review_items` 테이블 ORM(item_type/priority/status enum) | §3.2 | `models/review_item.py`, migration |
| P1-2 | `review_decisions` 테이블 ORM(불변, UPDATE/DELETE 비노출) | §3.3 | `models/review_decision.py`, migration |
| P1-3 | `POST /review-items` — 제출, status=pending, submitter 기록 | REQ-PERM-011 | `routers/review.py` |
| P1-4 | `GET /review-items` 역할 필터 — practitioner 본인만 / manager·admin 전체 | REQ-PERM-008, 009 | `routers/review.py` |
| P1-5 | `PATCH /review-items/{id}/assign`(manager+) — assigned_to 설정, in_review 전이 | REQ-PERM-012 | `routers/review.py` |
| P1-6 | `POST /review-items/{id}/decide`(manager+) — ReviewDecision 생성 + status 갱신 | REQ-PERM-013 | `routers/review.py` |
| P1-7 | practitioner decide 호출 403 차단 | REQ-PERM-007 | 테스트 |
| P1-8 | reject 시 comment 누락 422 | REQ-PERM-014 | `routers/review.py` |
| P1-9 | 이해상충 가드 — admin 본인 제출 항목 승인 403 | REQ-PERM-015 | `routers/review.py` |

P1 완료 기준: 제출→할당→승인/반려 상태 전이, 역할별 큐 가시성, practitioner 승인 차단, 본인 승인 차단, 커버리지 ≥ 85%.

---

## P2 — 예외 승인 + 감사 + 생명주기

선행 의존: P1.

| ID | 태스크 | 대응 REQ | 산출물(제안) |
|----|--------|----------|--------------|
| P2-1 | `exception_approve` 액션 — quality_manager+ 권한, comment 필수 | REQ-PERM-014, 016 | `routers/review.py` |
| P2-2 | `GET /audit/decisions`(manager+) — ReviewDecision 이력 조회 | REQ-PERM-NFR-001 | `routers/audit.py` |
| P2-3 | ReviewDecision 불변성 검증(수정/삭제 엔드포인트 부재 테스트) | REQ-PERM-NFR-001 | 테스트 |
| P2-4 | 비활성화 시 assigned_to null 재할당 처리 | REQ-PERM-NFR-003 | `routers/users.py` |
| P2-5 | 역할 미들웨어 오버헤드 ≤ 5ms 벤치 | REQ-PERM-NFR-002 | 테스트/벤치 |
| P2-6 | (선택) 이메일 알림 — 로컬 SMTP 연동(할당/결정 시) | §0.2 P2 | `services/notify.py` |

P2 완료 기준: 예외 승인 + comment 강제, 감사 export, 불변성 보장, 비활성화 재할당, 미들웨어 오버헤드 충족.

---

## 전문가 자문 트리거

- expert-backend: P0-2(bcrypt), P0-3~6(JWT+미들웨어), P1 SQLAlchemy async.
- expert-security: P0-10(열거 방지), P0-9/P2-2(감사), P1-9(이해상충), P2-3(불변성).

## 검증 게이트(전 단계 공통)

- ruff clean, mypy/pyright 통과
- pytest 커버리지 ≥ 85%
- 기존 `verify_api_key` 회귀 없음
- 모든 코드 주석 영어
