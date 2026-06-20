# SPEC-TRACEABILITY-002 구현 계획

## 의존성

- 선행 권장: SPEC-CRAWLER-002 (#53), SPEC-RAG-001 (#54) 완료 후 진행
- SPEC-TRACEABILITY-001과 독립적으로 진행 가능

## P0 — 현재 stub 분석 및 결과 스키마 설계

### Task 1: 현재 stub 분석
- `llm_detector.py` Ollama stub 구현 파악
- `graph_builder.py` stub documents 표현 파악
- 실제 Ollama 또는 LLM endpoint API 스키마 확인

### Task 2: semantic mismatch 결과 스키마 정의
- `mismatch_type`: 불일치 유형 enum 정의
- `confidence`: 0.0~1.0 신뢰도 점수
- `rationale`: 불일치 근거 텍스트
- `degraded`: LLM unavailable 시 true
- docs/integration-contract.md에 스키마 섹션 추가

## P1 — 실제 LLM detector 구현

### Task 3: llm_detector.py 실제 구현
- Ollama stub을 실제 Ollama 또는 configured LLM endpoint 호출로 교체
- 환경변수: `LLM_ENDPOINT_URL`, `LLM_MODEL_NAME`
- httpx async call 구현
- timeout 설정 (`LLM_TIMEOUT`, 기본값 정의)
- retry 로직 구현

### Task 4: degraded result 반환 로직
- LLM unavailable 시: `degraded: true`, `confidence: 0.0`, `rationale: "LLM unavailable"`
- timeout 초과 후 retry 소진 시 동일 처리

### Task 5: graph_builder.py stub 교체
- stub documents 표현을 실제 document 모델로 교체
- SPEC-TRACEABILITY-001의 document 스키마 참조

### Task 6: CI test double 분리
- Ollama stub을 pytest fixture 또는 `LLM_MOCK=true` 환경변수 조건으로 명시적 분리
- CI에서는 test double 사용, 운영에서는 실제 endpoint 사용 보장

## P2 — 테스트 및 계약 문서

### Task 7: traceability tests 추가
- 정상 LLM 응답 시 mismatch 감지 테스트 (test double)
- LLM unavailable 시 degraded result 반환 테스트
- timeout 및 retry 동작 테스트
- CI deterministic 실행 확인 테스트

### Task 8: 계약 문서 및 커밋
- `docs/integration-contract.md` traceability 결과 스키마 섹션 완성
- 커밋 (Refs #57)
