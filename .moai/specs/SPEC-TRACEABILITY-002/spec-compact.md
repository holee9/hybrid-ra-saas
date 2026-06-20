# SPEC-TRACEABILITY-002 Compact

## 요구사항

- REQ-TRACEABILITY-002-001: 운영 설정에서 실제 Ollama/configured LLM endpoint 호출로 semantic check 수행
- REQ-TRACEABILITY-002-002: LLM unavailable 시 `degraded: true` 포함 명시적 결과 반환
- REQ-TRACEABILITY-002-003: semantic mismatch 결과에 confidence score와 rationale 포함
- REQ-TRACEABILITY-002-004: CI 환경에서 stub/test double로 deterministic 실행
- REQ-TRACEABILITY-002-005: production 환경에서 실제 LLM detector 사용 (stub 제외)
- REQ-TRACEABILITY-002-006: 결과 스키마에 mismatch_type, confidence, rationale, degraded 포함
- REQ-TRACEABILITY-002-007: docs/integration-contract.md에 traceability 결과 스키마 명시
- REQ-TRACEABILITY-002-008: timeout 시 retry 후 degraded result 반환

## 수용 기준

- 운영 설정에서 detector가 실제 semantic check 수행
- LLM unavailable 시 명시적 degraded result 반환
- CI는 stub/test double로 deterministic 유지
- docs와 integration-contract에 결과 스키마 반영
