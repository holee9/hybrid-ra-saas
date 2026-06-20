# SPEC-RAG-001 구현 계획

## 의존성

- 선행 필요: 없음 (다른 SPEC의 prereq)
- SPEC-OPS-001 E2E 검증에 RAG smoke test 시나리오 포함

## P0 — 라우팅 정책 설계 및 계약 문서화

### Task 1: 라우팅 정책 정의
- routing_mode 파라미터 스키마 설계
  - `local-only`: Customer Runtime RAG만 사용
  - `regula-only`: Regula RAG만 사용
  - `hybrid`: local 우선, 임계값 미만 시 Regula fallback
- 임계값 기준 정의 (confidence score 또는 result count)
- timeout 값 정의 (Regula RAG 호출 timeout: 기본값 설정)

### Task 2: docs/integration-contract.md RAG routing 섹션 작성
- Request 스키마: `routing_mode`, context 필드 명세
- Response 스키마: `routing_used`, `sources`, `confidence`, `degraded` 필드
- Error code 목록: timeout, unavailable, invalid_mode 등
- Fallback 정책 명세

## P1 — 백엔드 라우팅 hook 구현

### Task 3: Customer Runtime RAG router 구현
- `customer-runtime/src/app/routers/` 내 RAG endpoint에 routing_mode 파라미터 추가
- routing_mode 기반 분기 로직 구현

### Task 4: 서비스 계층 라우팅 로직 구현
- `customer-runtime/src/app/services/` 내 RAG 서비스에 routing 분기 구현
- local RAG 호출 → confidence 평가 → fallback 결정
- Regula RAG 호출 (httpx async, timeout 설정)
- timeout/retry 로직 구현
- degraded result 반환 로직 (Regula unavailable 시)

### Task 5: 응답 스키마 확장
- `routing_used` 필드: 실제 사용된 경로
- `sources` 필드: 출처 문서 정보
- `confidence` 필드: 신뢰도 점수
- `degraded` 필드: fallback 또는 partial 결과 여부

## P2 — 테스트 및 문서 완성

### Task 6: unit tests 작성
- routing_mode별 분기 로직 테스트
- timeout 및 fallback 동작 테스트
- 응답 스키마 검증 테스트

### Task 7: E2E smoke test 시나리오 작성
- local-only 모드 정상 동작 확인
- regula-only 모드 정상 동작 확인
- hybrid 모드 fallback 동작 확인 (local 결과 임계값 미만 시뮬레이션)

### Task 8: GAP-05 상태 갱신 및 커밋
- `docs/integration-plan.md` GAP-05 → DONE 갱신
- 커밋 (Refs #54)
