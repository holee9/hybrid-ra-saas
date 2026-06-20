# SPEC-TEMPLATE-002 Compact

## 요구사항

- REQ-TEMPLATE-002-001: 운영 환경 authoring draft 생성 시 실제 TEMPLATE_API_URL 호출
- REQ-TEMPLATE-002-002: 운영 환경 checklist 생성 시 live httpx call to TEMPLATE_API_URL
- REQ-TEMPLATE-002-003: checklist generation과 authoring draft가 동일 template contract 사용
- REQ-TEMPLATE-002-004: TEMPLATE_API_URL 실패 시 deterministic 오류 또는 명시적 fallback
- REQ-TEMPLATE-002-005: timeout 발생 시 retry 후 오류 반환
- REQ-TEMPLATE-002-006: 운영 환경에서 stub/placeholder template 미사용
- REQ-TEMPLATE-002-007: stub fallback이 test-only/local-only로 명시적 제한
- REQ-TEMPLATE-002-008: README/docs에 TEMPLATE_API_URL 운영 설정 방법 명시

## 수용 기준

- 운영 설정에서 stub data 미사용 (테스트 검증)
- TEMPLATE_API_URL 실패 시 deterministic 오류/폴백
- TODO/stub 주석 운영 미완료 의미 제거
- README/docs 운영 설정 방법 반영
