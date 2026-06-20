---
id: SPEC-EVIDENCE-002
version: 0.1.0
status: completed
created_at: 2026-06-20
updated: 2026-06-20
author: drake.lee
priority: medium
issue_number: 56
---

# SPEC-EVIDENCE-002: Evidence Export 실제 파일 Bytes 연동 및 MinIO Delete 구현

## HISTORY

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 0.1.0 | 2026-06-20 | 최초 작성 | drake.lee |

## 개요

| 항목 | 내용 |
|------|------|
| 목적 | Evidence export에 실제 storage bytes 포함 및 MinIO delete no-op을 실제 삭제로 교체 |
| 범위 | hybrid-ra-saas 백엔드 storage/export 작업 (다운로드 UI 제외) |
| 의존 SPEC | SPEC-CRAWLER-002, SPEC-RAG-001 완료 후 진행 권장 |
| 관련 이슈 | #56 |

## 배경

현재 잔여 지점:
- `customer-runtime/src/app/services/evidence/exporter.py`: 실제 bytes 대신 sha256 placeholder content 사용
- `customer-runtime/src/app/services/storage_minio.py`: `delete_object` no-op stub

## EARS 요구사항

### Export 실제 bytes 연동

**REQ-EVIDENCE-002-001**: WHEN evidence export archive가 생성될 때, sha256 placeholder 대신 MinIO에서 가져온 실제 파일 bytes가 포함되어야 한다.

**REQ-EVIDENCE-002-002**: WHEN MinIO object가 존재하지 않을 때, 파일 누락에 대한 명시적 오류가 기록되고 export manifest에 반영되어야 한다.

**REQ-EVIDENCE-002-003**: IF tenant mismatch가 발생하면, 다른 tenant의 파일 bytes에 접근이 거부되어야 한다 (tenant isolation).

**REQ-EVIDENCE-002-004**: WHEN export 중 권한 오류가 발생하면, 전체 export가 실패하지 않고 해당 파일만 오류 처리되어야 한다.

### MinIO Delete 구현

**REQ-EVIDENCE-002-005**: WHEN delete_object가 호출될 때, MinIO에서 실제 object 삭제가 실행되어야 한다.

**REQ-EVIDENCE-002-006**: WHEN MinIO delete가 실패할 때, 오류가 관측 가능하고 호출자에게 전달되어야 한다 (silent no-op 금지).

### audit 및 정합성

**REQ-EVIDENCE-002-007**: WHEN export가 완료될 때, export manifest와 audit trail이 실제 포함된 파일 목록과 정합성을 유지해야 한다.

**REQ-EVIDENCE-002-008**: WHEN object 삭제가 실행될 때, audit 로그에 삭제 이벤트가 기록되어야 한다.

## 기술 접근 방법

1. `exporter.py`에서 MinIO object key를 이용한 실제 bytes 조회 구현
2. 누락/권한/tenant mismatch error case 처리 로직 추가
3. export manifest에 성공/실패 파일 목록 기록
4. `storage_minio.py`의 `delete_object`를 실제 MinIO client 호출로 교체
5. delete 오류 시 예외 전파 구현
6. audit logging 연동

## 영향 파일

- `customer-runtime/src/app/services/evidence/exporter.py`
- `customer-runtime/src/app/services/storage_minio.py`
- `customer-runtime/tests/` — unit/integration tests

## 제외 범위

- 다운로드 UI (ra-med-bot 담당)
- MinIO 서버 설정 변경
- Evidence Binder 로직 (SPEC-EVIDENCE-001 담당)
