# SPEC-RAG-001 Compact

## 요구사항

- REQ-RAG-001: local-only / regula-only / hybrid 세 가지 라우팅 모드 지원
- REQ-RAG-002: hybrid 모드에서 local 결과 임계값 미만 시 Regula 자동 fallback
- REQ-RAG-003: Regula RAG timeout 시 명시적 degraded 응답 반환 (silent failure 금지)
- REQ-RAG-004: request에 routing_mode 또는 context 필드 포함 가능
- REQ-RAG-005: 응답에 routing_used, sources, confidence 필드 포함
- REQ-RAG-006: 표준 error code/message/retry 가능 여부 명시 오류 응답
- REQ-RAG-007: 프론트엔드 변경 없이 서버 계약만으로 ra-med-bot 구현 가능
- REQ-RAG-008: local-only / regula-only / hybrid E2E smoke test 모두 검증

## 수용 기준

- docs/integration-contract.md에 RAG routing contract 명시
- Customer Runtime 백엔드 라우팅/timeout/fallback 테스트 통과
- integration-plan.md GAP-05 DONE 갱신
- 프론트엔드 변경 없이 ra-med-bot 구현 가능한 서버 계약 완비
