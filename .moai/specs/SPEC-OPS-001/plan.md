# SPEC-OPS-001 구현 계획

## 의존성

- 선행: SPEC-CRAWLER-002 (GAP-04), SPEC-RAG-001 (GAP-05) 완료 후 진행 권장
- 병렬 가능: 문서 최신화 작업은 선행 SPEC 완료 전 착수 가능

## P0 — 미커밋 변경 처리 및 환경변수 점검

### Task 1: 미커밋 변경 정리
- `cloud-control-plane/uv.lock`: 의존성 변경이면 커밋, 불필요하면 revert
- `.moai/evolution/telemetry/`: 운영 데이터면 .gitignore 추가, 아니면 커밋
- 결정 후 git commit (Refs #58)

### Task 2: Azure Container App 환경변수 점검
- 대상 서비스: api-prod, cloud-control-plane-api, crawler-job
- 점검 항목: `docs/deployment.md`의 필수 환경변수 목록 대조
- 누락 항목 발견 시 Azure 포털 또는 az CLI로 설정
- 점검 결과를 `docs/deployment.md`에 기록

## P1 — 운영 smoke test 및 E2E 검증

### Task 3: Health check smoke test
- 각 서비스 health endpoint 호출 및 응답 코드 확인
- 실패 시 로그 확인 및 원인 파악

### Task 4: E2E 파이프라인 검증
- IFU parse result push → knowledge sync trigger → Regula 수신 흐름 실행
- audit webhook/export → Regula audit trail 반영 확인
- 성공/실패 결과를 `docs/integration-plan.md`에 기록

## P2 — 문서 최신화

### Task 5: integration-plan.md 갱신
- GAP-03 수신부 상태 갱신 (DONE / BLOCKED / N-A)
- GAP-04, GAP-05가 SPEC 완료 후 DONE으로 갱신
- "운영 검증 필요" 항목 전체 실제 결과로 대체

### Task 6: README.md 테스트 수치 갱신
- 최신 CI 결과에서 커버리지/테스트 수치 확인
- README.md 내 수치 업데이트

### Task 7: deployment.md runbook 완성
- Container App 환경변수 설정 절차 명시
- smoke test 실행 방법 기술
- 배포 재현 절차 검증

### Task 8: 최종 커밋 및 CI 확인
- 변경 사항 커밋 (Refs #58)
- CI green 확인
- main 기준 staging/prod smoke 최종 확인
