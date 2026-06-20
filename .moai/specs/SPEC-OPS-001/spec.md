---
id: SPEC-OPS-001
version: 0.1.0
status: planned
created_at: 2026-06-20
updated: 2026-06-20
author: drake.lee
priority: high
issue_number: 58
---

# SPEC-OPS-001: 운영 배포 E2E 검증 및 문서 최신화 마감

## HISTORY

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 0.1.0 | 2026-06-20 | 최초 작성 | drake.lee |

## 개요

| 항목 | 내용 |
|------|------|
| 목적 | 운영 배포 검증, integration-plan 미결 항목 처리, README 테스트 수치 최신화 |
| 범위 | hybrid-ra-saas 배포/백엔드 E2E/docs (프론트엔드 화면 QA 제외) |
| 의존 SPEC | SPEC-CRAWLER-002 (#53), SPEC-RAG-001 (#54) |
| 관련 이슈 | #58 |

## 배경

- `docs/deployment.md`: Container App 환경 변수 수동 작업 미완
- `docs/integration-plan.md`: 운영 검증 필요 항목, GAP-03 수신부 pending, GAP-04/05 P1
- `README.md`: 오래된 테스트 수치 존재
- 미커밋 변경: `cloud-control-plane/uv.lock`, `.moai/evolution/telemetry/`

## EARS 요구사항

### 배포 검증

**REQ-OPS-001**: WHEN Azure Container App 환경변수 점검이 실행될 때, api-prod / cloud-control-plane-api / crawler-job 세 서비스 모두 필수 환경변수가 누락 없이 설정되어야 한다.

**REQ-OPS-002**: WHEN 운영 smoke test가 실행될 때, api-prod / cloud-control-plane-api / crawler-job 각 서비스의 health endpoint가 200 OK를 반환해야 한다.

**REQ-OPS-003**: WHEN IFU parse result push → knowledge sync trigger → Regula 수신 E2E가 실행될 때, 전체 파이프라인이 오류 없이 완료되어야 한다.

**REQ-OPS-004**: WHEN audit webhook/export가 실행될 때, Regula audit trail에 해당 이벤트가 반영되어야 한다.

### 문서 최신화

**REQ-OPS-005**: IF integration-plan.md에 "운영 검증 필요" 항목이 존재하면, 실제 검증 결과(DONE/BLOCKED/N-A)로 갱신되어야 한다.

**REQ-OPS-006**: WHEN README.md의 테스트 수치를 확인할 때, 최신 CI 결과와 일치해야 한다.

**REQ-OPS-007**: WHEN deployment.md를 참조할 때, runbook만으로 재현 가능한 배포 절차가 기술되어야 한다.

### 미커밋 변경 처리

**REQ-OPS-008**: WHEN 현재 미커밋 변경(`cloud-control-plane/uv.lock`, `.moai/evolution/telemetry/`)을 처리할 때, 각 파일에 대한 커밋 또는 .gitignore 추가 결정이 명시적으로 이루어져야 한다.

## 기술 접근 방법

1. Azure CLI 또는 포털을 통해 Container App 환경변수 설정 확인
2. curl/httpx를 이용한 health check smoke test 실행
3. E2E 시나리오 수동 실행 및 결과 기록
4. integration-plan.md 상태 필드 갱신
5. README.md 테스트 수치 업데이트
6. deployment.md runbook 완성

## 영향 파일

- `docs/deployment.md`
- `docs/integration-plan.md`
- `README.md`
- `CHANGELOG.md` (선택)
- `cloud-control-plane/uv.lock`
- `.moai/evolution/telemetry/` (gitignore 또는 커밋)

## 제외 범위

- 프론트엔드 화면 QA (ra-med-bot 담당)
- 신규 기능 개발
- 인프라 구성 변경
