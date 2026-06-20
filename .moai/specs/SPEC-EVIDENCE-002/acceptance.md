# SPEC-EVIDENCE-002 수용 기준

## 시나리오 1: export archive에 실제 파일 content 포함

**Given** MinIO에 evidence 파일이 저장되어 있을 때
**When** evidence export를 실행하면
**Then** export archive에 sha256 placeholder가 아닌 실제 파일 bytes가 포함되어야 한다
**And** export manifest에 성공적으로 포함된 파일 목록이 기록되어야 한다

## 시나리오 2: 파일 누락 시 manifest 반영

**Given** 일부 evidence 파일의 MinIO object가 존재하지 않을 때
**When** evidence export를 실행하면
**Then** 전체 export가 실패하지 않아야 한다
**And** export manifest에 해당 파일이 `missing` 상태로 기록되어야 한다

## 시나리오 3: tenant isolation 보장

**Given** tenant A의 evidence export 요청이 있을 때
**When** tenant B의 object key에 접근을 시도하면
**Then** 접근이 거부되어야 한다
**And** audit 로그에 tenant mismatch 이벤트가 기록되어야 한다

## 시나리오 4: delete_object 실제 MinIO 삭제

**Given** MinIO에 evidence 파일이 저장되어 있을 때
**When** delete_object를 호출하면
**Then** MinIO에서 실제 object가 삭제되어야 한다
**And** 삭제 후 동일 object key 조회 시 not found가 반환되어야 한다

## 시나리오 5: delete 실패 시 오류 관측 가능

**Given** MinIO delete 중 오류가 발생할 때
**When** delete_object를 호출하면
**Then** no-op이 아닌 명시적 예외가 전파되어야 한다
**And** 오류가 로그에 기록되어야 한다

## 완료 정의 (Definition of Done)

- [ ] export archive에 실제 evidence file content 포함
- [ ] object 삭제가 MinIO에 반영되고 실패 시 오류 관측 가능
- [ ] tenant isolation과 audit logging 유지
- [ ] placeholder/stub 주석 제거 또는 test-only 축소
- [ ] unit/integration test 추가 및 통과
- [ ] CI green (Refs #56)
