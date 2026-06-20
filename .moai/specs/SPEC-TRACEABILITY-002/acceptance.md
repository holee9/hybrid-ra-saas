# SPEC-TRACEABILITY-002 수용 기준

## 시나리오 1: 운영 환경에서 실제 semantic check 수행

**Given** LLM_ENDPOINT_URL이 설정된 운영 환경일 때
**When** traceability semantic mismatch detection이 실행되면
**Then** 실제 Ollama 또는 configured LLM endpoint가 호출되어야 한다
**And** 결과에 mismatch_type, confidence, rationale이 포함되어야 한다

## 시나리오 2: LLM unavailable 시 degraded result 반환

**Given** LLM endpoint가 응답하지 않을 때
**When** semantic mismatch detection이 실행되면
**Then** 실패 대신 `degraded: true`가 포함된 명시적 결과가 반환되어야 한다
**And** `confidence: 0.0`, `rationale: "LLM unavailable"` 이 포함되어야 한다

## 시나리오 3: CI 환경 deterministic 실행

**Given** CI 환경 또는 `LLM_MOCK=true` 설정일 때
**When** traceability 테스트가 실행되면
**Then** test double을 사용하여 deterministic하게 실행되어야 한다
**And** 실제 LLM endpoint 호출 없이 일관된 결과가 반환되어야 한다

## 시나리오 4: integration-contract.md 결과 스키마 확인

**Given** ra-med-bot 개발팀이 traceability 결과를 표시하려 할 때
**When** docs/integration-contract.md의 traceability 섹션을 참조하면
**Then** mismatch_type, confidence, rationale, degraded 필드가 모두 명시되어 있어야 한다

## 시나리오 5: timeout 및 retry 동작

**Given** LLM endpoint가 timeout 범위를 초과할 때
**When** semantic mismatch detection이 실행되면
**Then** 설정된 retry 횟수 이후 degraded result가 반환되어야 한다
**And** 각 retry 시도가 로그에 기록되어야 한다

## 완료 정의 (Definition of Done)

- [ ] 운영 설정에서 실제 semantic check 수행 확인
- [ ] LLM unavailable 시 degraded result 반환
- [ ] CI는 test double로 deterministic 실행
- [ ] docs/integration-contract.md에 결과 스키마 반영
- [ ] unit/integration test 추가 및 통과
- [ ] CI green (Refs #57)
