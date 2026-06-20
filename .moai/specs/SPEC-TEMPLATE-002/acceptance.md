# SPEC-TEMPLATE-002 수용 기준

## 시나리오 1: 운영 환경에서 실제 template 사용

**Given** TEMPLATE_API_URL이 설정된 운영 환경일 때
**When** authoring draft 생성 요청을 전송하면
**Then** stub 데이터가 아닌 TEMPLATE_API_URL에서 가져온 실제 template이 사용되어야 한다
**And** 응답에 실제 template 내용이 포함되어야 한다

## 시나리오 2: checklist 생성 실제 연동

**Given** TEMPLATE_API_URL이 설정된 운영 환경일 때
**When** checklist 생성 요청을 전송하면
**Then** live httpx call이 TEMPLATE_API_URL에 전송되어야 한다
**And** 반환된 template을 기반으로 checklist가 생성되어야 한다

## 시나리오 3: TEMPLATE_API_URL 실패 시 deterministic 오류

**Given** TEMPLATE_API_URL 서비스가 응답하지 않을 때
**When** authoring 또는 checklist 요청을 전송하면
**Then** undefined 동작 또는 stub fallback 없이 명시적 오류 응답이 반환되어야 한다
**And** 오류 코드와 메시지가 포함되어야 한다

## 시나리오 4: test 환경에서 stub 허용

**Given** `TEMPLATE_MOCK=true` 또는 pytest 환경일 때
**When** authoring 또는 checklist 요청을 전송하면
**Then** 명시적 test-only stub이 사용되어야 한다
**And** 운영 환경에서는 동일 코드 경로가 실행되지 않아야 한다

## 시나리오 5: TODO 주석 미존재 확인

**Given** 구현 완료 후
**When** authoring.py와 generator.py를 검색하면
**Then** `@MX:TODO: implement live httpx call` 패턴의 주석이 존재하지 않아야 한다

## 완료 정의 (Definition of Done)

- [ ] 운영 설정에서 stub data 사용 없음 (테스트로 검증)
- [ ] TEMPLATE_API_URL 실패 시 deterministic 오류/폴백 정책 적용
- [ ] 관련 TODO/stub 주석이 운영 미완료 의미로 남지 않음
- [ ] README/docs에 운영 설정 방법 반영
- [ ] CI green (Refs #55)
