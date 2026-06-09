# SPEC-PARSER-001 인수 기준 (Acceptance Criteria)

Given-When-Then 형식. 모든 시나리오는 pytest로 검증 가능해야 한다. 목표 커버리지 85%+.

## 시나리오 1 — 15개 필드 추출 (REQ-001, 010)

- **Given** 15개 필드를 포함한 유효한 DOCX X-ray IFU 문서
- **When** `ParserEngine.parse(bytes, "docx")` 호출
- **Then** `ParsedFields`가 15개 필드를 모두 포함하고, 각 필드는 `confidence`와 `stage`를 가진다

## 시나리오 2 — XLSX 입력 (REQ-001)

- **Given** 유효한 XLSX IFU 문서
- **When** `parse(bytes, "xlsx")` 호출
- **Then** `xlsx_reader`가 텍스트를 추출하고 파이프라인이 정상 동작한다

## 시나리오 3 — 신뢰도 공식 (REQ-002)

- **Given** completeness=0.8, rule_match=0.9, semantic=0.7인 필드
- **When** `confidence.calculate()` 호출
- **Then** 결과는 0.50*0.8 + 0.30*0.9 + 0.20*0.7 = 0.81 (부동소수점 허용오차 내)

## 시나리오 4 — 교정 UI 트리거 (REQ-003)

- **Given** 3단계 모두 수행 후 신뢰도가 0.85 미만인 필드
- **When** 파이프라인 완료
- **Then** 해당 필드 `needs_correction=True`, `ParsedFields.requires_correction=True`

## 시나리오 5 — 문서 거부 (REQ-004)

- **Given** overall_confidence가 0.50 미만으로 산출되는 문서
- **When** 파이프라인 완료
- **Then** `ParsedFields.rejected=True`, 재업로드 요청 신호 반환

## 시나리오 6 — Stage 1 격리 (REQ-006)

- **Given** 임의 IFU 텍스트
- **When** `rule_based.extract()` 호출
- **Then** 네트워크 소켓/GPU 호출이 발생하지 않는다 (호출 차단 검증)

## 시나리오 7 — 데이터 주권 (REQ-007)

- **Given** Stage 3 LLM 폴백 실행
- **When** `llm_fallback.extract()` 호출
- **Then** localhost/Ollama 외부의 어떤 HTTP 엔드포인트도 호출되지 않는다 (외부 URL 모킹 시 호출 0회)

## 시나리오 8 — 단계 조기 종료

- **Given** Stage 1에서 신뢰도 0.90을 얻은 필드
- **When** 파이프라인 실행
- **Then** Stage 2/3은 해당 필드에 대해 호출되지 않고, `stage=RULE`로 확정

## 시나리오 9 — 교정 API (REQ-008)

- **Given** 기존 job_id와 교정 값 `{"device_name": "X-ray Model A"}`
- **When** `PATCH /parse/{job_id}/corrections` 호출
- **Then** device_name 값 갱신, `confidence=1.0`, `stage=NONE`, overall_confidence 재계산

## 시나리오 10 — 교정 API 필드 검증

- **Given** 화이트리스트 외 필드명 `{"unknown_field": "x"}`
- **When** 교정 API 호출
- **Then** 422 검증 오류 반환, 데이터 변경 없음

## 시나리오 11 — 한국어 문서 (REQ-009)

- **Given** 한국어 IFU 문서
- **When** 파이프라인 실행
- **Then** 한국어 사전으로 필드 추출 성공 (required 필드 추출률 검증)

## 시나리오 12 — 골든 데이터셋 F1 (REQ-005)

- **Given** X-ray IFU 골든 데이터셋 50개+ (`@pytest.mark.integration`)
- **When** 전체 데이터셋 파이프라인 실행
- **Then** 매크로 F1 점수 >= 0.85

## Edge Cases

- 빈 문서 → 모든 필드 `value=None`, `stage=NONE`, rejected 처리
- 손상된 DOCX/XLSX → reader가 명시적 예외 발생 (bare except 금지)
- 일부 필드만 존재 → 누락 required 필드는 needs_correction
- 매우 큰 문서 → 텍스트 추출 메모리 한계 처리 (입력 크기 검증)

## Quality Gate / Definition of Done

- [ ] REQ-PARSER-001 ~ 010 전부 테스트로 검증
- [ ] 테스트 커버리지 >= 85%
- [ ] ruff check 통과, 타입 힌트 전체 적용
- [ ] 외부 API 호출 부재 검증 통과 (REQ-007)
- [ ] 골든 F1 통합 테스트 작성 (데이터셋 제공 시 >=0.85)
- [ ] `parser.py` 스텁 → `ParserEngine` 위임 교체 완료, 기존 API 호환
- [ ] @MX 태그 정리 (high fan_in 함수 ANCHOR)
