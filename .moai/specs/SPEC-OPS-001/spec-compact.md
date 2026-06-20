# SPEC-OPS-001 Compact

## 요구사항

- REQ-OPS-001: api-prod / cloud-control-plane-api / crawler-job 필수 환경변수 누락 없이 설정
- REQ-OPS-002: 운영 smoke test 시 세 서비스 health endpoint 모두 200 OK
- REQ-OPS-003: IFU parse→knowledge sync→Regula 수신 E2E 오류 없이 완료
- REQ-OPS-004: audit webhook/export → Regula audit trail 반영
- REQ-OPS-005: integration-plan.md 운영 검증 필요 항목 실제 결과로 갱신
- REQ-OPS-006: README.md 테스트 수치 최신 CI 결과와 일치
- REQ-OPS-007: deployment.md runbook만으로 배포 재현 가능
- REQ-OPS-008: 미커밋 변경(uv.lock, telemetry/) 명시적 처리

## 수용 기준

- main CI green + staging/prod smoke green
- integration-plan.md pending 항목 전체 실제 상태 갱신
- GAP-04, GAP-05 DONE 처리
- README 테스트 수치 최신화
- deployment.md runbook 완성
- 미커밋 변경 커밋 또는 .gitignore 처리 완료
