# SPEC-EVIDENCE-002 구현 계획

## 의존성

- 선행 권장: SPEC-CRAWLER-002 (#53), SPEC-RAG-001 (#54) 완료 후 진행
- SPEC-EVIDENCE-001과 독립적으로 진행 가능

## P0 — 현재 stub 분석 및 MinIO client 확인

### Task 1: 현재 코드 분석
- `exporter.py` sha256 placeholder 사용 위치 파악
- `storage_minio.py` delete_object no-op stub 위치 확인
- MinIO client 설정 및 object key 형식 파악

### Task 2: error case 설계
- 파일 누락 (object not found) → 오류 타입 정의
- 권한 오류 → 오류 타입 정의
- tenant mismatch → 차단 로직 설계
- export manifest 스키마 확장 (성공/실패 파일 목록)

## P1 — 실제 bytes 연동 구현

### Task 3: exporter.py 실제 bytes 연동
- `EvidenceFile` metadata에서 MinIO object key 추출
- MinIO client를 통해 실제 bytes 조회
- export archive에 실제 bytes 포함
- sha256 placeholder 코드 제거

### Task 4: error case 처리 구현
- 파일 누락 시 manifest에 `{file_id, status: "missing", reason: ...}` 기록
- tenant mismatch 시 접근 거부 및 audit 로그 기록
- 권한 오류 시 해당 파일만 skip (전체 export 실패 방지)

### Task 5: delete_object 실제 구현
- `storage_minio.py` delete_object no-op stub 교체
- 실제 MinIO client `.remove_object()` 또는 동등 호출
- 실패 시 예외 전파 (silent no-op 제거)

## P2 — audit logging 및 테스트

### Task 6: audit trail 연동
- export 완료 시 audit 이벤트 기록 (포함 파일 수, 실패 파일 수)
- delete 실행 시 audit 이벤트 기록 (object key, tenant)

### Task 7: unit/integration tests 추가
- export에 실제 bytes 포함 확인 테스트 (MinIO mock)
- 파일 누락 시 manifest 반영 테스트
- tenant mismatch 시 접근 거부 테스트
- delete_object 실제 호출 테스트 (MinIO mock)
- delete 실패 시 예외 전파 테스트

### Task 8: placeholder 주석 정리 및 커밋
- placeholder/stub 주석 제거 또는 test-only로 축소
- 커밋 (Refs #56)
