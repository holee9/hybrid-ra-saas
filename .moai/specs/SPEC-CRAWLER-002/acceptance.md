# SPEC-CRAWLER-002 수용 기준

## 시나리오 1: authoritative crawler 단일 운영 경로 확인

**Given** hybrid-ra-saas Cloud Control Plane이 authoritative crawler로 지정되어 있을 때
**When** 운영 환경에서 크롤러를 실행하면
**Then** 하나의 경로만 실제 수집 및 push를 수행해야 한다
**And** 비 authoritative 경로는 실행되지 않거나 authoritative 경로를 위임 호출해야 한다

## 시나리오 2: idempotency — 중복 push 방지

**Given** 동일한 source URL과 document version의 문서가 이미 저장되어 있을 때
**When** 같은 문서를 다시 push하면
**Then** storage와 Regula에 중복 저장이 발생하지 않아야 한다
**And** 중복 감지 로그가 기록되어야 한다

## 시나리오 3: 동시 중복 실행 방어

**Given** crawler-job이 두 번 동시에 실행될 때
**When** 동일 문서를 각각 수집하여 push하면
**Then** 최종적으로 문서 하나만 저장되어야 한다 (idempotency 보장)

## 시나리오 4: GAP-04 완료 확인

**Given** 위 시나리오 1~3이 모두 통과된 후
**When** docs/integration-plan.md의 GAP-04 항목을 확인하면
**Then** 상태가 DONE으로 갱신되어 있어야 한다
**And** authoritative crawler 결정 근거가 기록되어 있어야 한다

## 완료 정의 (Definition of Done)

- [ ] authoritative crawler 단일 경로 운영 확인
- [ ] idempotency unit test 추가 및 통과
- [ ] smoke test에서 중복 실행 후 중복 저장 없음 확인
- [ ] docs/integration-plan.md GAP-04 DONE 갱신
- [ ] docs/deployment.md 단일 운영 경로 반영
- [ ] CI green (Refs #53)
