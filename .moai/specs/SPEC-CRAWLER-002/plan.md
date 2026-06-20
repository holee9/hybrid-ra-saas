# SPEC-CRAWLER-002 구현 계획

## 의존성

- 선행 필요: 없음 (다른 SPEC의 prereq)
- 이후 SPEC-OPS-001 E2E 검증에 반영되어야 함

## P0 — 크롤러 경로 분석 및 소유권 결정

### Task 1: 현재 크롤러 경로 매핑
- `cloud-control-plane/` 내 crawler-job 구현 확인
- ra-med-bot 측 크롤러/sync 경로 파악 (인터페이스 레벨)
- 중복 수집되는 source/document 유형 식별

### Task 2: authoritative source 결정 문서화
- 결정: hybrid-ra-saas Cloud Control Plane을 authoritative crawler로 지정 (권장)
- 결정 근거를 `docs/integration-plan.md` GAP-04 섹션에 기록
- ra-med-bot 팀에 비활성화 또는 위임 처리 요청 인터페이스 정의

## P1 — idempotency 구현 및 중복 경로 처리

### Task 3: idempotency key 설계 및 구현
- idempotency key 정의: `(source_url, document_version)` 또는 content hash
- push 전 중복 체크 로직 구현 (cloud-control-plane crawler 경로)
- 중복 감지 시 skip + 로그 기록

### Task 4: 비 authoritative 경로 비활성화
- 자체 관리 가능한 중복 cron/sync 경로 비활성화 또는 주석 처리
- ra-med-bot 측에 위임 인터페이스 정의 (직접 수정 제외)

### Task 5: 책임 경계 문서화
- `docs/integration-plan.md`에 크롤러 책임 경계 섹션 추가
- cloud-control-plane-api, crawler-job, Regula push 경로별 역할 명시

## P2 — 운영 환경 갱신 및 테스트

### Task 6: 환경변수 및 deployment 문서 갱신
- 단일 운영 경로 반영하여 `docs/deployment.md` 갱신
- 불필요해진 환경변수 제거 또는 deprecated 표시

### Task 7: idempotency 테스트 추가
- unit test: 동일 document 중복 push 시 skip 동작 확인
- smoke test: 실제 환경에서 중복 실행 후 저장/Regula 상태 확인
- 테스트 결과 docs 반영

### Task 8: GAP-04 상태 갱신
- `docs/integration-plan.md` GAP-04 → DONE 갱신
- 커밋 (Refs #53)
