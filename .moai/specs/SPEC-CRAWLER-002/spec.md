---
id: SPEC-CRAWLER-002
version: 0.1.0
status: planned
created_at: 2026-06-20
updated: 2026-06-20
author: drake.lee
priority: high
issue_number: 53
---

# SPEC-CRAWLER-002: GAP-04 크롤러 운영 소유권 정리 및 중복 실행 제거

## HISTORY

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 0.1.0 | 2026-06-20 | 최초 작성 | drake.lee |

## 개요

| 항목 | 내용 |
|------|------|
| 목적 | hybrid-ra-saas와 ra-med-bot 간 크롤러 중복 운영 정리 및 authoritative owner 확정 |
| 범위 | hybrid-ra-saas 백엔드/인프라 작업 (ra-med-bot UI 제외) |
| 의존 SPEC | SPEC-CRAWLER-001 (완료) |
| 관련 이슈 | #53 |
| prereq | SPEC-OPS-001의 선행 조건 |

## 배경

`docs/integration-plan.md`의 GAP-04가 P1로 미해결 상태이다. hybrid-ra-saas와 ra-med-bot 양측이 규제/지식 수집 경로를 보유하여 중복 수집, 중복 push, 상충된 최신성 판단 위험이 존재한다.

## EARS 요구사항

### 소유권 결정

**REQ-CRAWLER-002-001**: WHEN 크롤러 소유권 결정이 이루어질 때, hybrid-ra-saas Cloud Control Plane 또는 ra-med-bot 중 하나가 authoritative source로 공식 지정되어야 한다.

**REQ-CRAWLER-002-002**: IF authoritative crawler가 결정된 후, 다른 쪽의 크롤러/cron/sync 경로는 비활성화되거나 authoritative source를 호출하는 형태로 전환되어야 한다.

### 중복 제거

**REQ-CRAWLER-002-003**: WHEN 동일 source/version/document가 두 번 이상 수집/push될 때, idempotency 보장으로 중복 저장 및 중복 동기화가 방지되어야 한다.

**REQ-CRAWLER-002-004**: WHEN cloud-control-plane-api, crawler-job, Regula knowledge push 경로를 확인할 때, 각 경로의 책임 경계가 문서화되어 있어야 한다.

### 운영 환경

**REQ-CRAWLER-002-005**: WHEN 운영 환경 배포 시, 환경변수와 deployment 문서가 단일 운영 경로를 반영하도록 갱신되어야 한다.

**REQ-CRAWLER-002-006**: WHEN idempotency 검증을 위한 테스트가 실행될 때, 같은 문서의 중복 push가 storage/Regula에 중복 반영되지 않음이 확인되어야 한다.

## 기술 접근 방법

1. 현재 크롤러 경로 매핑: cloud-control-plane crawler-job vs ra-med-bot 측 경로
2. authoritative source 결정 (기본 권장: hybrid-ra-saas Cloud Control Plane)
3. 비 authoritative 경로 비활성화 또는 위임 처리
4. idempotency key 정의: (source_url, document_version) 또는 content hash 기반
5. push 전 중복 체크 로직 구현
6. 책임 경계 문서화 및 환경변수 갱신

## 영향 파일

- `cloud-control-plane/` — crawler job 설정 및 구현
- `docs/integration-plan.md` — GAP-04 상태 갱신
- `docs/deployment.md` — 운영 경로 반영
- `.github/workflows/` — crawler-job 배포 파이프라인 (해당 시)

## 제외 범위

- ra-med-bot UI 변경
- ra-med-bot 측 크롤러 코드 직접 수정 (비활성화 요청만)
