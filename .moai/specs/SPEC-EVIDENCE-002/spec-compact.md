# SPEC-EVIDENCE-002 Compact

## 요구사항

- REQ-EVIDENCE-002-001: export archive에 MinIO 실제 파일 bytes 포함 (sha256 placeholder 제거)
- REQ-EVIDENCE-002-002: MinIO object 누락 시 manifest에 missing 상태 기록
- REQ-EVIDENCE-002-003: tenant mismatch 시 파일 접근 거부 (tenant isolation)
- REQ-EVIDENCE-002-004: export 중 권한 오류 시 해당 파일만 오류 처리 (전체 실패 방지)
- REQ-EVIDENCE-002-005: delete_object에서 실제 MinIO object 삭제 실행
- REQ-EVIDENCE-002-006: MinIO delete 실패 시 오류 관측 가능 (silent no-op 금지)
- REQ-EVIDENCE-002-007: export manifest와 audit trail 실제 파일 목록과 정합성 유지
- REQ-EVIDENCE-002-008: object 삭제 시 audit 로그에 삭제 이벤트 기록

## 수용 기준

- export archive에 실제 evidence file content 포함
- object 삭제 MinIO 반영 및 실패 시 오류 관측 가능
- tenant isolation과 audit logging 유지
- placeholder/stub 주석 제거 또는 test-only 축소
