# SPEC-CRAWLER-002 Compact

## 요구사항

- REQ-CRAWLER-002-001: hybrid-ra-saas 또는 ra-med-bot 중 authoritative crawler 공식 지정
- REQ-CRAWLER-002-002: 비 authoritative 경로 비활성화 또는 위임 전환
- REQ-CRAWLER-002-003: 동일 source/version 중복 push idempotency 보장
- REQ-CRAWLER-002-004: cloud-control-plane-api, crawler-job, Regula push 경로 책임 경계 문서화
- REQ-CRAWLER-002-005: 운영 환경변수 및 deployment 문서 단일 경로 반영 갱신
- REQ-CRAWLER-002-006: 중복 push 방지 unit/smoke test 추가

## 수용 기준

- 하나의 authoritative crawler path만 운영 경로로 존재
- 중복 실행 시 storage/Regula에 중복 반영 없음
- integration-plan.md GAP-04 DONE 갱신
- unit/integration test 또는 smoke test 통과
