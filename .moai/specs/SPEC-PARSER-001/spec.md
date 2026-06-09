---
id: SPEC-PARSER-001
version: 0.1.0
status: completed
created: 2026-06-08
updated: 2026-06-09
author: drake.lee
priority: medium
issue_number: 13
---

# SPEC-PARSER-001: 동적 파서 + NLP (15개 필드 추출)

## HISTORY

- 2026-06-08 (v0.1.0): 최초 작성. SPEC-API-001 후속. PRD §11 파서 NLP 명세 기반.

---

## 0. 범위 (Scope)

### 0.1 목적

X-ray IFU(사용설명서) 문서에서 RA 규제 대응에 필요한 15개 필드를 자동 추출한다. 3단계 파이프라인(규칙 기반 → spaCy NER → 로컬 LLM 폴백)으로 신뢰도 기반 단계적 추출을 수행하며, 신뢰도 미달 시 교정 UI로 연결한다. 모든 처리는 고객 로컬 런타임 내부에서 수행되어 데이터 주권을 보장한다.

### 0.2 In-Scope (구현 대상)

- DOCX/XLSX 문서로부터 텍스트 추출 (`python-docx`, `openpyxl`)
- 15개 IFU 필드 추출 엔진 (`parser_engine` 패키지)
- 3단계 파이프라인: 규칙 기반 → spaCy NER → Ollama 로컬 LLM 폴백
- 가중치 기반 신뢰도 계산 (0.50/0.30/0.20)
- 필드별 신뢰도 점수 및 사용 단계 기록
- 교정 UI 트리거 (신뢰도 < 0.85) 및 거부 (신뢰도 < 0.50)
- `PATCH /parse/{job_id}/corrections` 교정 반영 엔드포인트
- 영어/한국어 IFU 문서 지원
- 기존 `parser.py` 스텁을 실제 구현으로 대체

### 0.3 Exclusions (What NOT to Build)

본 SPEC에서 구현하지 않는 항목:

- **spaCy 모델 학습 인프라**: 모델 학습은 수동 프로세스로 코드 외부에서 수행 (학습된 모델 파일만 로드)
- **골든 데이터셋 생성**: X-ray IFU 샘플 50개+ 데이터셋 작성은 RA 전문가의 작업
- **Ollama 모델 설치/관리**: 모델 다운로드/실행은 Docker compose 책임 (HTTP 클라이언트만 구현)
- **UI 컴포넌트**: 교정 화면 등 프론트엔드는 SPEC-UI-001 범위 (백엔드 API만 제공)
- **X-ray 외 비IFU 문서 타입**: PDF, 라벨, 패키징 등은 향후 별도 SPEC

### 0.4 Dependencies

- **선행 (Predecessor)**: SPEC-API-001 (완료, commit 0915745) — 7개 FastAPI 엔드포인트, parser 스텁 제공
- **후행 (Successor)**: SPEC-UI-001 — 교정 UI 화면 (본 SPEC의 교정 API 소비)
- **설치 완료 의존성**: `python-docx`, `openpyxl`, `transformers`, `spacy`, `sentence-transformers` (.venv)
- **외부 런타임**: Ollama 로컬 서버 (Docker compose, 모델 llama3/mistral)

---

## 1. 아키텍처 (Architecture)

### 1.1 디렉터리 구조

신규 패키지 `customer-runtime/src/app/services/parser_engine/` 를 생성하여 기존 `parser.py` 스텁을 대체한다.

```
customer-runtime/src/app/services/
├── parser.py                      # ParserService 구현체 (ParserEngine 위임)
└── parser_engine/
    ├── __init__.py                # ParserEngine export
    ├── rule_based.py              # Stage 1: 정규식 + 키워드 사전
    ├── spacy_ner.py              # Stage 2: spaCy NER 파이프라인
    ├── llm_fallback.py          # Stage 3: Ollama 로컬 HTTP 클라이언트
    ├── confidence.py            # 신뢰도 계산
    ├── docx_reader.py           # DOCX 텍스트 추출
    └── xlsx_reader.py           # XLSX 텍스트 추출
```

### 1.2 모듈 설계

| 모듈 | 책임 | 입력 | 출력 |
|------|------|------|------|
| `docx_reader` | DOCX → 평문 텍스트 | `bytes` | `str` (정규화 텍스트) |
| `xlsx_reader` | XLSX → 평문 텍스트 | `bytes` | `str` (셀 직렬화 텍스트) |
| `rule_based` | 정규식/키워드로 필드 추출 | `str` | `dict[field, FieldExtraction]` |
| `spacy_ner` | NER로 잔여 필드 추출 | `str`, 미추출 필드 목록 | `dict[field, FieldExtraction]` |
| `llm_fallback` | LLM으로 최종 폴백 | `str`, 미추출 필드 목록 | `dict[field, FieldExtraction]` |
| `confidence` | 가중치 신뢰도 계산 | 추출 메타데이터 | `float` |
| `ParserEngine` | 파이프라인 오케스트레이션 | `bytes`, `doc_type` | `ParsedFields` |

### 1.3 데이터 흐름

```
file_bytes
  → docx_reader / xlsx_reader (doc_type 분기)
  → text
  → ParserEngine.run_pipeline(text)
      → for each field:
          stage1 rule_based  → conf>=0.85? done
          stage2 spacy_ner   → conf>=0.85? done
          stage3 llm_fallback → conf>=0.85? done
          else: mark needs_correction
  → ParsedFields (15 fields + per-field confidence + stage)
```

`parser.py`의 `ParserService.parse()`는 `ParserEngine`을 호출하고 결과를 기존 `ParseResult`(혹은 확장)로 반환한다. `StubParserService`는 테스트용으로 유지한다.

---

## 2. 데이터 모델 (Data Models)

`customer-runtime/src/app/schemas/parse.py`에 추가한다.

### 2.1 FieldExtraction

```python
from enum import Enum
from pydantic import BaseModel, Field

class ExtractionStage(str, Enum):
    RULE = "rule_based"
    NER = "spacy_ner"
    LLM = "llm_fallback"
    NONE = "none"

class FieldExtraction(BaseModel):
    value: str | list[str] | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    stage: ExtractionStage
    needs_correction: bool = False
```

### 2.2 ParsedFields (15개 필드)

```python
class ParsedFields(BaseModel):
    # required
    device_name: FieldExtraction
    intended_use: FieldExtraction
    indications: FieldExtraction
    contraindications: FieldExtraction
    warnings: FieldExtraction               # array value
    device_classification: FieldExtraction
    region_targets: FieldExtraction
    cybersecurity_requirements: FieldExtraction  # digital devices
    # important
    precautions: FieldExtraction
    product_code: FieldExtraction
    maintenance_interval: FieldExtraction
    cleaning_disinfection: FieldExtraction
    software_version: FieldExtraction        # software-inclusive devices
    # optional
    accessories: FieldExtraction             # array value
    disposal_instructions: FieldExtraction

    overall_confidence: float = Field(ge=0.0, le=1.0)
    requires_correction: bool = False
    rejected: bool = False
```

필드 분류 (PRD §11):

| 필드 | 분류 | 비고 |
|------|------|------|
| device_name | required | |
| intended_use | required | |
| indications | required | |
| contraindications | required | |
| warnings | required | array |
| device_classification | required | |
| region_targets | required | |
| cybersecurity_requirements | required | 디지털 기기 |
| precautions | important | |
| product_code | important | |
| maintenance_interval | important | |
| cleaning_disinfection | important | |
| software_version | important | 소프트웨어 포함 기기 |
| accessories | optional | array |
| disposal_instructions | optional | |

---

## 3. 3단계 파이프라인 (PRD §11.3)

### 3.1 Stage 1 — 규칙 기반 추출 (rule_based.py)

- **입력**: 정규화된 평문 텍스트
- **방법**: 필드별 정규식 패턴 + 키워드 사전 매칭 (영/한 사전 분리)
- **출력**: `dict[field, FieldExtraction]` (stage=RULE)
- **제약**: 네트워크 호출 없음, GPU 없음 (REQ-PARSER-006)
- **폴백 트리거**: 필드 신뢰도 < 0.85 → Stage 2로 전달

### 3.2 Stage 2 — spaCy NER (spacy_ner.py)

- **입력**: 평문 텍스트 + Stage 1 미충족 필드 목록
- **방법**: 커스텀 학습된 spaCy NER 모델 로드 후 엔티티 추출 (모델 파일은 외부 제공)
- **출력**: `dict[field, FieldExtraction]` (stage=NER)
- **폴백 트리거**: 필드 신뢰도 < 0.85 → Stage 3로 전달

### 3.3 Stage 3 — LLM 폴백 (llm_fallback.py)

- **입력**: 평문 텍스트 + Stage 2 미충족 필드 목록
- **방법**: Ollama 로컬 HTTP API 호출 (llama3/mistral), 필드별 추출 프롬프트
- **출력**: `dict[field, FieldExtraction]` (stage=LLM)
- **제약**: 로컬 Ollama 전용 — 외부 API 호출 절대 금지 (REQ-PARSER-007, 데이터 주권)
- **폴백 트리거**: 필드 신뢰도 < 0.85 → `needs_correction=True`

### 3.4 단계 종료 조건

- 임의 단계에서 필드 신뢰도 >= 0.85 → 해당 필드 확정, 다음 단계 건너뜀
- 모든 단계 후 신뢰도 < 0.85 → 교정 UI 마크
- overall_confidence < 0.50 → 문서 거부, 재업로드 요청

---

## 4. 신뢰도 계산 (PRD §11.2)

```
confidence = 0.50 * field_completeness_score
           + 0.30 * rule_match_score
           + 0.20 * semantic_similarity_score

CORRECTION_UI_THRESHOLD = 0.85
REJECT_THRESHOLD = 0.50
```

- **field_completeness_score**: 필드 값 존재/형식 충족 정도 (0.0~1.0)
- **rule_match_score**: 정규식/키워드 매칭 강도 (0.0~1.0)
- **semantic_similarity_score**: `sentence-transformers` 임베딩으로 기대 의미와의 코사인 유사도 (0.0~1.0)
- **overall_confidence**: required 필드 가중 평균 (필드 가중치는 confidence.py에 정의)

임계값은 상수로 정의하며 환경변수 오버라이드 가능하게 설계한다.

---

## 5. API 변경 (API Changes)

### 5.1 PATCH /parse/{job_id}/corrections

`customer-runtime/src/app/routers/parse.py`에 추가.

- **요청 본문**: `{field_name: corrected_value, ...}` (부분 갱신)
- **동작**: 지정 필드 값 갱신 → 해당 필드 `stage=NONE`(수동), `confidence=1.0`, `needs_correction=False` 처리 → overall_confidence 재계산
- **응답**: 갱신된 `ParsedFields`
- **검증**: job_id 존재 확인, 필드명 화이트리스트 검증 (15개 필드만 허용)

### 5.2 기존 엔드포인트 영향

- `POST /parse`: 스텁 → 실제 `ParserEngine` 호출로 동작 변경. 응답 스키마는 `ParsedFields`를 포함하도록 확장 (`ParseJobResponse` 호환 유지).

---

## 6. CI/CD 노트

- **변경 불필요**: 기존 pytest 기반 CI 파이프라인 그대로 사용.
- 골든 데이터셋 F1 테스트는 fixture로 제공되는 샘플에 의존하며, 통합 테스트는 CI 전용으로 설계 (로컬 Ollama 미존재 시 skip 마커 처리).
- spaCy 모델/Ollama는 CI에서 mock 또는 skip — 실제 모델 의존 테스트는 `@pytest.mark.integration` 분리.

---

## 7. EARS 요구사항 (Requirements)

- **REQ-PARSER-001** (Event-Driven): **WHEN** DOCX 또는 XLSX 파일이 제출되면, the system **SHALL** 3단계 파이프라인을 사용하여 15개 IFU 필드를 모두 추출한다.
- **REQ-PARSER-002** (Ubiquitous): The system **SHALL** 가중치 공식(0.50/0.30/0.20)을 사용하여 신뢰도 점수를 계산한다.
- **REQ-PARSER-003** (Unwanted/Conditional): **IF** 3단계 모두 수행 후 신뢰도가 0.85 미만이면, **then** the system **SHALL** 해당 필드를 교정 UI 대상으로 표시한다.
- **REQ-PARSER-004** (Unwanted/Conditional): **IF** 신뢰도가 0.50 미만이면, **then** the system **SHALL** 문서를 거부하고 재업로드를 요청한다.
- **REQ-PARSER-005** (Ubiquitous): The system **SHALL** 골든 데이터셋(X-ray IFU 샘플 50개 이상)에서 85% 이상의 F1 점수를 달성한다.
- **REQ-PARSER-006** (Ubiquitous): The system **SHALL** Stage 1(규칙 기반)을 네트워크 호출 및 GPU 없이 처리한다.
- **REQ-PARSER-007** (Unwanted): The system **SHALL** Stage 3(LLM)을 로컬 Ollama로만 처리하며 외부 API를 호출하지 **않는다** (데이터 주권).
- **REQ-PARSER-008** (Event-Driven): **WHEN** `PATCH /parse/{job_id}/corrections`가 호출되면, the system **SHALL** 필드 값을 갱신하고 신뢰도를 재계산한다.
- **REQ-PARSER-009** (Ubiquitous): The system **SHALL** 영어 및 한국어 IFU 문서를 지원한다.
- **REQ-PARSER-010** (Ubiquitous): 추출된 모든 필드는 필드별 신뢰도 점수와 사용된 추출 단계를 **SHALL** 포함한다.

---

## 8. 인수 기준 (Acceptance Criteria)

상세 Given-When-Then 시나리오는 `acceptance.md` 참조. 핵심 기준:

- DOCX/XLSX 입력 시 15개 필드 모두 포함된 `ParsedFields` 반환 (REQ-001)
- 신뢰도 계산이 가중치 공식과 일치 (REQ-002)
- 신뢰도 < 0.85 필드는 `needs_correction=True` (REQ-003)
- overall_confidence < 0.50 시 `rejected=True` (REQ-004)
- 골든 데이터셋 F1 >= 0.85 (REQ-005)
- Stage 1이 네트워크/GPU 없이 동작 (REQ-006)
- Stage 3가 localhost Ollama 외 호출 없음 (REQ-007, 네트워크 모킹으로 검증)
- 교정 API 호출 후 값 갱신 + 신뢰도 재계산 (REQ-008)
- 한/영 문서 모두 추출 성공 (REQ-009)
- 모든 필드에 confidence + stage 존재 (REQ-010)
- 테스트 커버리지 >= 85%

---

## 9. 보안 (Security)

- **데이터 주권 (Data Sovereignty)**: 모든 파싱은 고객 로컬 런타임 내에서 수행. Stage 3 LLM은 로컬 Ollama(`http://localhost` 또는 Docker 내부 호스트)만 호출 — 외부 클라우드 API 호출 금지 (REQ-PARSER-007).
- **네트워크 격리 검증**: 단위 테스트에서 외부 HTTP 호출 시도를 모킹/차단하여 데이터 유출 경로 부재를 확인.
- **입력 검증**: 업로드 파일 타입/크기 검증, 교정 API 필드명 화이트리스트 검증으로 임의 필드 주입 차단.
- **민감정보 로깅 금지**: 추출된 문서 본문/필드 값을 로그에 평문 기록하지 않음.

---

## 10. 의존성 (Dependencies)

| 관계 | SPEC | 상태 | 비고 |
|------|------|------|------|
| 선행 | SPEC-API-001 | 완료 (commit 0915745) | parser 스텁 + 7 엔드포인트 |
| 후행 | SPEC-UI-001 | 예정 | 교정 UI (본 SPEC 교정 API 소비) |

라이브러리 의존성: `python-docx`, `openpyxl`, `transformers`, `spacy`, `sentence-transformers` (설치 완료). 외부 런타임: Ollama (Docker compose 책임).

---

## 부록 A. 구현 순서 (TDD Sequence)

RED → GREEN → REFACTOR. 각 태스크는 실패 테스트 작성 후 구현.

- **T-001**: `FieldExtraction` / `ParsedFields` / `ExtractionStage` Pydantic 모델 작성 + 검증 테스트
- **T-002**: `confidence.py` 신뢰도 계산 (가중치 공식, 임계값 상수) + 단위 테스트 (REQ-002)
- **T-003**: `docx_reader.py` DOCX 텍스트 추출 + fixture 테스트
- **T-004**: `xlsx_reader.py` XLSX 텍스트 추출 + fixture 테스트
- **T-005**: `rule_based.py` 정규식/키워드 추출 (영/한 사전) + 필드별 테스트 (REQ-006, 009)
- **T-006**: `spacy_ner.py` NER 단계 (모델 로드 모킹) + 단위 테스트
- **T-007**: `llm_fallback.py` Ollama HTTP 클라이언트 (외부 호출 차단 검증) + 테스트 (REQ-007)
- **T-008**: `ParserEngine` 파이프라인 오케스트레이션 (단계 종료/폴백 로직) + 통합 테스트 (REQ-001, 003, 004, 010)
- **T-009**: `parser.py` 스텁 → `ParserEngine` 위임으로 교체 + 호환성 테스트
- **T-010**: `PATCH /parse/{job_id}/corrections` 엔드포인트 + API 테스트 (REQ-008)
- **T-011**: 골든 데이터셋 F1 통합 테스트 (`@pytest.mark.integration`) (REQ-005)
- **T-012**: 커버리지 점검(>=85%) + REFACTOR + @MX 태그 정리

---

## 구현 노트 (Implementation Notes)

**완료일:** 2026-06-09  
**커밋:** b7fdc0e (메인 구현), ed9229d (XLSX 크기 제한 + 아티팩트), 1f554e3 (진행)  
**GitHub Issue:** #13 (자동 종료: Refs #13)

### 실제 구현 vs 계획 차이

| 항목 | 계획 | 실제 |
|------|------|------|
| `errors.py` | 계획에 없음 | 신규 추가 (DocxReadError, XlsxReadError, InputTooLargeError 분리) |
| XLSX 크기 제한 | DOCX만 명시 | XLSX에도 동일하게 50MB 제한 적용 (evaluator-active 발견) |
| CorrectionsRequest | 직접 dict 전달 | `{"corrections": {...}}` Pydantic wrapper 사용 (422 검증 명확화) |
| spaCy 설치 상태 | 설치됨으로 기술 | 미설치 — lazy import + graceful degrade로 처리 (B1) |

### 검증 결과

- 단위 테스트: 70 passed, 25 skipped (통합 테스트 CI 전용)
- parser_engine 커버리지: 92.4% (목표 85% 초과)
- evaluator-active: PASS (Functionality 92, Security 88, Craft 90, Consistency 95)
- ruff lint: clean
