# SPEC-UI-001 인수 기준 (Acceptance Criteria)

모든 시나리오는 Vitest + React Testing Library로 검증 가능해야 한다. Given-When-Then 형식으로 작성한다.

## REQ별 시나리오

### AC-001 (REQ-UI-001): URL job_id 기반 초기 로드

- **Given** 유효한 `job_id`가 URL 파라미터로 제공되고 백엔드가 정상 응답하는 상황에서
- **When** `CorrectionPanel`이 마운트되면
- **Then** `GET /parse/jobs/{job_id}`가 1회 호출되고, 응답의 15개 필드가 화면에 렌더링된다.

### AC-002 (REQ-UI-002): confidence 색상 배지

- **Given** 필드별 confidence가 0.92(device_name), 0.80(warnings), 0.60(precautions)인 데이터가 로드된 상황에서
- **When** 화면이 렌더링되면
- **Then** device_name 배지는 green, warnings 배지는 yellow, precautions 배지는 red로 표시되고 각 배지에 수치가 함께 나타난다.

### AC-003 (REQ-UI-003): 필드 수정 시 dirty 표시

- **Given** 필드값이 로드된 상태에서
- **When** 사용자가 `device_name` 값을 "X-ray Model A"로 변경하면
- **Then** 해당 FieldRow에 dirty 마커가 표시되고 Save 버튼이 활성화된다.

### AC-004 (REQ-UI-004): 변경 필드만 PATCH 전송

- **Given** `device_name`만 수정되고 나머지 14개 필드는 변경되지 않은 상태에서
- **When** 사용자가 Save 버튼을 클릭하면
- **Then** `PATCH /parse/{job_id}/corrections` 본문에 `{ "corrections": { "device_name": "..." } }` 만 포함되고 다른 필드는 포함되지 않는다.

### AC-005 (REQ-UI-005): 저장 성공 처리

- **Given** PATCH 요청이 200 OK와 갱신된 `ParsedFields`를 반환하는 상황에서
- **When** Save가 완료되면
- **Then** 화면 필드값이 응답값으로 갱신되고, 성공 토스트가 표시되며, Save 버튼은 비활성화(dirty 해제)된다.

### AC-006 (REQ-UI-006): 저장 실패 롤백

- **Given** `device_name`을 수정하고 Save를 시도했으나 PATCH가 422를 반환하는 상황에서
- **When** 실패 응답을 수신하면
- **Then** `device_name` 값이 수정 직전 값으로 롤백되고, 에러 토스트가 표시된다.

### AC-007 (REQ-UI-007): rejected 문서 처리

- **Given** 로드된 데이터의 `rejected=true`인 상황에서
- **When** 화면이 렌더링되면
- **Then** `RejectedBanner`가 최상단에 표시되고, 모든 FieldRow 편집과 Save 버튼이 비활성화된다.

### AC-008 (REQ-UI-008): undo 히스토리

- **Given** 사용자가 `warnings` 값을 A에서 B로 변경한 상황에서
- **When** undo(되돌리기) 동작을 실행하면
- **Then** `warnings` 값이 A로 복원되고 dirty 상태가 해제된다.

## 엣지 케이스 (Edge Cases)

### AC-E01: 빈 ParsedFields

- **Given** 모든 필드의 `value=null`, `needs_correction=true`인 데이터가 로드된 상황에서
- **When** 화면이 렌더링되면
- **Then** 15개 필드가 모두 red 배지로 표시되고, 각 필드는 빈 값으로 편집 가능 상태가 된다(크래시 없음).

### AC-E02: 네트워크 오류 (타임아웃)

- **Given** `GET /parse/jobs/{job_id}` 요청이 네트워크 타임아웃으로 실패하는 상황에서
- **When** 로드를 시도하면
- **Then** 에러 토스트와 재시도 안내가 표시되고, 폼은 빈 상태로 유지된다.

### AC-E03: 유효하지 않은 job_id (404)

- **Given** 존재하지 않는 `job_id`가 제공된 상황에서
- **When** `GET /parse/jobs/{job_id}`가 404를 반환하면
- **Then** "작업을 찾을 수 없음" 안내가 표시되고 교정 폼은 렌더링되지 않는다.

### AC-E04: 동시 수정 방지 (Save 중 폼 비활성화)

- **Given** Save 요청이 진행 중(pending)인 상황에서
- **When** 사용자가 다른 필드를 수정하거나 Save를 재클릭하려 하면
- **Then** 폼 전체와 Save 버튼이 비활성화되어 추가 입력/중복 제출이 차단된다.

## Definition of Done

- [ ] REQ-UI-001 ~ REQ-UI-008 모두 통과하는 테스트 존재
- [ ] AC-E01 ~ AC-E04 엣지 케이스 테스트 통과
- [ ] Vitest + RTL 커버리지 85% 이상
- [ ] Docker `ui` 서비스가 port 8080에서 정상 빌드/서빙
- [ ] nginx `/api` 프록시로 same-origin API 호출 동작 확인
- [ ] PATCH 본문에 변경 필드만 포함됨을 검증(AC-004)
- [ ] JWT가 localStorage가 아닌 메모리에 보관됨을 검증(§8)
- [ ] lint(eslint) 0 경고, type-check 0 오류

## 품질 게이트 기준 (Quality Gate)

| 항목 | 기준 |
|------|------|
| 테스트 커버리지 | ≥ 85% |
| ESLint | 0 경고 |
| TypeScript | 0 오류 |
| XSS | `dangerouslySetInnerHTML` 미사용 |
| Docker 빌드 | 성공 (port 8080) |
