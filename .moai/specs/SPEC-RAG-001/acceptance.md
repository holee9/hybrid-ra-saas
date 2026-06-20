# SPEC-RAG-001 수용 기준

## 시나리오 1: local-only 라우팅 모드

**Given** Customer Runtime RAG 서비스가 정상 동작하고 있을 때
**When** `routing_mode: local-only`로 RAG 질의를 전송하면
**Then** Customer Runtime local RAG만 사용하여 응답을 반환해야 한다
**And** 응답의 `routing_used` 필드가 `local`이어야 한다
**And** Regula RAG 호출이 발생하지 않아야 한다

## 시나리오 2: hybrid fallback 동작

**Given** local RAG 결과의 confidence가 임계값 미만일 때
**When** `routing_mode: hybrid`로 RAG 질의를 전송하면
**Then** Regula RAG로 자동 fallback되어야 한다
**And** 응답의 `routing_used` 필드가 `regula`이어야 한다
**And** `degraded: false`이거나 Regula 결과가 정상 포함되어야 한다

## 시나리오 3: Regula RAG timeout 처리

**Given** Regula RAG 서비스가 timeout 범위를 초과할 때
**When** `routing_mode: regula-only`로 RAG 질의를 전송하면
**Then** silent failure 없이 명시적 오류 응답이 반환되어야 한다
**And** 응답에 error code와 `degraded: true`가 포함되어야 한다

## 시나리오 4: integration-contract.md 계약 명세 완비

**Given** ra-med-bot 개발팀이 RAG 연동을 구현하려 할 때
**When** docs/integration-contract.md의 RAG routing 섹션을 참조하면
**Then** request 스키마, response 스키마, error code, fallback 정책이 모두 명시되어 있어야 한다
**And** 프론트엔드 변경 없이 서버 계약만으로 구현이 가능해야 한다

## 시나리오 5: GAP-05 완료 확인

**Given** 위 시나리오 1~4가 모두 통과된 후
**When** docs/integration-plan.md의 GAP-05 항목을 확인하면
**Then** 상태가 DONE으로 갱신되어 있어야 한다

## 완료 정의 (Definition of Done)

- [ ] docs/integration-contract.md에 RAG routing contract 명시
- [ ] local-only / regula-only / hybrid fallback unit test 통과
- [ ] E2E smoke test 세 시나리오 모두 통과
- [ ] integration-plan.md GAP-05 DONE 갱신
- [ ] CI green (Refs #54)
