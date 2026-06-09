# SPEC-PARSER-001 구현 계획 (Plan)

선행: SPEC-API-001 (완료). 방법론: TDD (RED-GREEN-REFACTOR). 언어: Python 3.12, FastAPI, async/await.

## 기술 접근 (Technical Approach)

- 신규 패키지 `customer-runtime/src/app/services/parser_engine/`로 기존 `parser.py` 스텁 대체
- 3단계 파이프라인을 필드 단위로 순차 적용, 신뢰도 0.85 도달 시 조기 종료
- 신뢰도 = 0.50*completeness + 0.30*rule_match + 0.20*semantic_similarity
- Stage 3는 Ollama 로컬 HTTP 전용 (외부 호출 차단)
- 모든 I/O 경로는 async/await, Pydantic v2 모델

## 마일스톤 (우선순위 기반, 시간 추정 없음)

### M1 — 데이터 모델 + 신뢰도 (Priority High)
- `ParsedFields`, `FieldExtraction`, `ExtractionStage` (schemas/parse.py)
- `confidence.py` 가중치 계산 + 임계값 상수
- 대응: T-001, T-002 / REQ-002

### M2 — 문서 리더 (Priority High)
- `docx_reader.py`, `xlsx_reader.py`
- 대응: T-003, T-004

### M3 — 추출 단계 (Priority High)
- `rule_based.py` (영/한 사전, 네트워크/GPU 없음)
- `spacy_ner.py` (모델 로드 모킹)
- `llm_fallback.py` (Ollama, 외부 호출 차단)
- 대응: T-005~T-007 / REQ-006, 007, 009

### M4 — 오케스트레이션 + 통합 (Priority High)
- `ParserEngine` 파이프라인 (단계 종료/폴백)
- `parser.py` 위임 교체
- 대응: T-008, T-009 / REQ-001, 003, 004, 010

### M5 — 교정 API (Priority Medium)
- `PATCH /parse/{job_id}/corrections`
- 대응: T-010 / REQ-008

### M6 — 품질 게이트 (Priority Medium)
- 골든 데이터셋 F1 통합 테스트
- 커버리지 >=85%, REFACTOR, @MX 정리
- 대응: T-011, T-012 / REQ-005

## 위험 (Risks)

| 위험 | 영향 | 완화 |
|------|------|------|
| spaCy 커스텀 모델 미제공 | Stage 2 실증 불가 | 모델 인터페이스 모킹, 실제 모델은 외부 제공 가정 (Exclusion) |
| Ollama 미설치 환경 | Stage 3 테스트 불가 | `@pytest.mark.integration` 분리, CI 전용 + skip 마커 |
| 골든 데이터셋 부재 | REQ-005 검증 불가 | fixture placeholder, 데이터셋은 RA 전문가 작업 (Exclusion) |
| 한/영 사전 불균형 | 한국어 추출 정확도 저하 | 언어별 사전 분리, 언어 감지 후 분기 |
| 외부 API 누출 가능성 | 데이터 주권 위반 | 단위 테스트에서 외부 HTTP 호출 모킹/차단 검증 (REQ-007) |

## 전문가 협의 권장

- 백엔드 키워드 (API, 파이프라인, async): expert-backend 협의 권장
- 본 SPEC은 NLP/파싱 엔진 중심 — 구현 단계에서 expert-backend 활용
