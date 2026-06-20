---
id: SPEC-TRACEABILITY-002
version: 0.1.0
status: planned
created_at: 2026-06-20
updated: 2026-06-20
author: drake.lee
priority: medium
issue_number: 57
---

# SPEC-TRACEABILITY-002: Traceability Semantic Mismatch Detector 운영 구현

## HISTORY

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 0.1.0 | 2026-06-20 | 최초 작성 | drake.lee |

## 개요

| 항목 | 내용 |
|------|------|
| 목적 | Traceability semantic mismatch detector의 Ollama/test stub을 운영 가능한 detector로 전환 |
| 범위 | hybrid-ra-saas 백엔드 traceability/LLM detector 구현 (결과 표시 UI 제외) |
| 의존 SPEC | SPEC-CRAWLER-002, SPEC-RAG-001 완료 후 진행 권장 |
| 관련 이슈 | #57 |

## 배경

현재 잔여 지점:
- `customer-runtime/src/app/services/traceability/llm_detector.py`: Ollama stub
- `customer-runtime/src/app/services/traceability/graph_builder.py`: stub documents 표현

운영 환경에서 실제 semantic check가 실행되지 않아 traceability 결과를 신뢰할 수 없다.

## EARS 요구사항

### 운영 detector 구현

**REQ-TRACEABILITY-002-001**: WHEN 운영 설정에서 semantic mismatch detection이 실행될 때, 실제 Ollama 또는 configured LLM endpoint를 호출하여 semantic check를 수행해야 한다.

**REQ-TRACEABILITY-002-002**: WHEN LLM endpoint가 unavailable할 때, 실패 대신 `degraded: true`가 포함된 명시적 결과가 반환되어야 한다.

**REQ-TRACEABILITY-002-003**: WHEN semantic mismatch가 감지될 때, 결과에 confidence score와 rationale이 포함되어야 한다.

### stub 분리

**REQ-TRACEABILITY-002-004**: WHEN CI 환경에서 테스트가 실행될 때, stub/test double을 사용하여 deterministic하게 실행되어야 한다.

**REQ-TRACEABILITY-002-005**: IF production 환경에서 실행되면, stub/test double이 아닌 실제 LLM detector가 사용되어야 한다.

### 결과 스키마

**REQ-TRACEABILITY-002-006**: WHEN traceability 결과가 반환될 때, semantic mismatch schema에 `mismatch_type`, `confidence`, `rationale`, `degraded` 필드가 포함되어야 한다.

**REQ-TRACEABILITY-002-007**: WHEN docs/integration-contract.md를 참조할 때, traceability 결과 스키마가 명시되어 있어야 한다.

### timeout/retry

**REQ-TRACEABILITY-002-008**: WHEN LLM endpoint 호출 시 timeout이 발생하면, 설정된 retry 횟수 이후 degraded result가 반환되어야 한다.

## 기술 접근 방법

1. `llm_detector.py` Ollama stub을 실제 endpoint 호출로 교체
2. LLM endpoint URL 환경변수화 (`LLM_ENDPOINT_URL`, `LLM_MODEL_NAME`)
3. timeout/retry 설정
4. degraded result 반환 로직 (unavailable 시)
5. semantic mismatch 결과 스키마 정의 및 구현
6. `graph_builder.py` stub documents를 실제 document 표현으로 교체
7. CI용 test double을 pytest fixture 또는 환경변수 조건으로 명시적 분리
8. `docs/integration-contract.md`에 결과 스키마 추가

## 영향 파일

- `customer-runtime/src/app/services/traceability/llm_detector.py`
- `customer-runtime/src/app/services/traceability/graph_builder.py`
- `docs/integration-contract.md` — 결과 스키마 추가
- `customer-runtime/tests/` — tests

## 제외 범위

- 결과 표시 UI (ra-med-bot 담당)
- Ollama 서버 설치/설정
- Traceability Graph DB 구현 (SPEC-TRACEABILITY-001 담당)
