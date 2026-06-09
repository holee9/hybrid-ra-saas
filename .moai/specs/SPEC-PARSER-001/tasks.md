# Task Decomposition
SPEC: SPEC-PARSER-001

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| T-001 | FieldExtraction / ParsedFields / ExtractionStage Pydantic 모델 | REQ-001, 010 | - | src/app/schemas/parse.py | pending |
| T-002 | confidence.py 신뢰도 계산 (가중치 공식, 임계값 상수) | REQ-002 | T-001 | src/app/services/parser_engine/__init__.py, parser_engine/confidence.py | pending |
| T-003 | docx_reader.py DOCX 텍스트 추출 | REQ-001 | T-001 | parser_engine/docx_reader.py, parser_engine/errors.py, tests/fixtures/parser/ | pending |
| T-004 | xlsx_reader.py XLSX 텍스트 추출 | REQ-001 | T-001, T-003 | parser_engine/xlsx_reader.py | pending |
| T-005 | rule_based.py 정규식/키워드 추출 (영/한 사전) | REQ-006, 009 | T-001, T-002 | parser_engine/rule_based.py | pending |
| T-006 | spacy_ner.py NER 단계 (lazy import + injectable loader) | NER stage | T-001, T-002 | parser_engine/spacy_ner.py | pending |
| T-007 | llm_fallback.py Ollama HTTP 클라이언트 + 외부 호출 차단 | REQ-007 | T-001, T-002 | parser_engine/llm_fallback.py | pending |
| T-008 | ParserEngine 파이프라인 오케스트레이션 | REQ-001, 003, 004, 010 | T-002~T-007 | parser_engine/__init__.py (ParserEngine) | pending |
| T-009 | parser.py 스텁 → ParserEngine 위임 교체 + 호환성 | backward compat | T-008 | src/app/services/parser.py, src/app/deps.py | pending |
| T-010 | PATCH /parse/{job_id}/corrections 엔드포인트 | REQ-008 | T-001, T-008, T-009 | src/app/routers/parse.py, src/app/schemas/parse.py | pending |
| T-011 | 골든 데이터셋 F1 통합 테스트 (@pytest.mark.integration) | REQ-005 | T-008 | tests/test_golden_f1.py, tests/fixtures/parser/golden/ | pending |
| T-012 | 커버리지 점검(>=85%) + REFACTOR + @MX 태그 정리 | DoD | T-001~T-011 | cross-cutting, pyproject.toml | pending |
