# SPEC-TEMPLATE-002 구현 계획

## 의존성

- 선행 권장: SPEC-CRAWLER-002 (#53), SPEC-RAG-001 (#54) 완료 후 진행
- prereq 완료 전에도 독립적으로 착수 가능

## P0 — 현재 stub 분석 및 template client 설계

### Task 1: 현재 stub 위치 및 사용 패턴 파악
- `customer-runtime/src/app/routers/authoring.py` stub/cloud resolver 분석
- `customer-runtime/src/app/services/checklist/generator.py` TODO 분석
- TEMPLATE_API_URL 스키마 파악 (API 명세 확인)

### Task 2: template client 모듈 설계
- 공통 template client 인터페이스 설계
- httpx async client 설정 (timeout, retry, base_url)
- error mapping 정의 (HTTP 4xx/5xx → 애플리케이션 오류)

## P1 — live httpx 구현

### Task 3: authoring.py cloud resolver 구현
- `customer-runtime/src/app/routers/authoring.py` stub 교체
- TEMPLATE_API_URL live httpx call 구현
- timeout/retry 설정 (환경변수 `TEMPLATE_API_TIMEOUT`, `TEMPLATE_API_RETRY_COUNT`)

### Task 4: checklist generator.py TODO 구현
- `customer-runtime/src/app/services/checklist/generator.py` `@MX:TODO` 해소
- live httpx call to TEMPLATE_API_URL 구현
- authoring과 동일한 template client 공유

### Task 5: stub 분리
- 기존 stub/placeholder를 pytest fixture 또는 `TEMPLATE_MOCK=true` 환경변수 조건으로 명시적 분리
- 운영 경로에서 stub 코드 도달 불가능하게 처리
- `@MX:TODO` 주석 제거 또는 `@MX:NOTE`로 교체

## P2 — 테스트 및 문서

### Task 6: contract/unit tests 추가
- TEMPLATE_API_URL 정상 호출 단위 테스트 (mock)
- timeout 발생 시 오류 반환 테스트
- retry 동작 테스트
- stub이 운영 경로에서 사용되지 않음을 검증하는 테스트

### Task 7: 문서 갱신
- README.md 또는 `docs/configuration.md`에 TEMPLATE_API_URL 설정 방법 추가
- 환경변수 목록 갱신
- 커밋 (Refs #55)
