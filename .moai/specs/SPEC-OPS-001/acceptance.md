# SPEC-OPS-001 수용 기준

## 시나리오 1: 운영 서비스 health smoke test

**Given** Azure Container App에 api-prod, cloud-control-plane-api, crawler-job이 배포되어 있고
**And** 필수 환경변수가 모두 설정되어 있을 때
**When** 각 서비스의 health endpoint에 GET 요청을 전송하면
**Then** 세 서비스 모두 HTTP 200 OK를 반환해야 한다
**And** 응답 body에 `{"status": "ok"}` 또는 동등한 healthy 상태가 포함되어야 한다

## 시나리오 2: IFU E2E 파이프라인 검증

**Given** 운영 환경이 정상 동작하고 있을 때
**When** IFU parse result를 push하면
**Then** knowledge sync trigger가 자동으로 실행되어야 한다
**And** Regula knowledge base에 해당 문서가 수신 반영되어야 한다
**And** 전체 흐름이 오류 없이 완료되어야 한다

## 시나리오 3: audit trail E2E 검증

**Given** 운영 환경에서 Evidence export가 실행될 때
**When** audit webhook이 발송되면
**Then** Regula audit trail에 해당 이벤트가 기록되어야 한다
**And** audit 로그에서 tenant, timestamp, event type이 확인 가능해야 한다

## 시나리오 4: integration-plan.md 상태 최신화

**Given** E2E 검증이 완료된 후
**When** docs/integration-plan.md를 열면
**Then** "운영 검증 필요" 항목이 모두 실제 상태(DONE/BLOCKED/N-A)로 갱신되어 있어야 한다
**And** GAP-04, GAP-05 항목이 DONE으로 표시되어 있어야 한다

## 시나리오 5: README 테스트 수치 일치

**Given** 최신 CI 실행 결과가 있을 때
**When** README.md의 테스트 수치를 확인하면
**Then** CI 결과의 커버리지/테스트 통과 수치와 일치해야 한다

## 완료 정의 (Definition of Done)

- [ ] main 기준 CI green
- [ ] staging/prod smoke test 모두 green
- [ ] integration-plan.md의 pending 항목 전체 상태 갱신
- [ ] README.md 테스트 수치 최신화
- [ ] deployment.md runbook만으로 배포 재현 가능
- [ ] 미커밋 변경 처리 완료 (커밋 또는 .gitignore)
