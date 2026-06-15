---
id: SPEC-AUTHORING-001
version: 0.1.0
status: planned
created_at: 2026-06-13
updated: 2026-06-13
author: moai
priority: high
issue_number: 31
labels: ["spec", "authoring", "guided-writing", "ai-draft"]
---

# SPEC-AUTHORING-001: Guided Authoring Workspace

## HISTORY

- **v0.1.0** (2026-06-13): 최초 작성. SPEC-TEMPLATE-001(Template Pack Registry)의 데이터 모델(TemplatePack → TemplateDocument → TemplateSection)을 콘텐츠 트리로 소비하는 **섹션별 가이드 작성 워크스페이스** 범위 확정. ProductProfile + TemplatePack로부터 AuthoringSession 생성, 섹션 상태 머신(empty → ai_draft → human_edited → complete), 로컬 Ollama + pgvector RAG 기반 AI 초안 생성, 진행률 추적, 저장·재개, TemplateDocument 순서를 보존한 DOCX 내보내기를 정의. AuthoringSession/AuthoringSectionEntry/AuthoringProgress 3개 엔티티, 6개 API 엔드포인트, EARS REQ-AUTHOR-001~018, 인수 기준 AC-001~016, P0/P1/P2 산출물 정의. status: draft → planned.

---

## 0. 범위 및 의존성

### 0.1 SPEC 개요

| 항목 | 내용 |
|------|------|
| SPEC-ID | SPEC-AUTHORING-001 |
| 제목 | Guided Authoring Workspace |
| 상태 | planned |
| 대상 디렉터리 | `customer-runtime/` (Customer Local Runtime — FastAPI + PostgreSQL + Ollama + MinIO) |
| 분석 기준 | PRD FR-214(Guided Authoring Workspace), MRD REQ-MRD-113(Template-Driven Document Authoring), SPEC-TEMPLATE-001 데이터 모델, 4x4 페르소나 분석 |
| 라이프사이클 | spec-anchored (애플리케이션 코드와 함께 유지) |
| 개발 방법론 | TDD (RED-GREEN-REFACTOR) |
| Priority | high |
| 위상 | **P1(스타트업 CTO) 핵심 해금 SPEC** — 빈 페이지 대신 템플릿 섹션 트리 기반 가이드 작성 + AI 초안 제공 |

### 0.2 전략적 위상 (왜 high인가)

SPEC-TEMPLATE-001이 "무엇을, 어떤 구조로 작성할지"를 정의(데이터 모델·레지스트리)했다면, SPEC-AUTHORING-001은 그 구조를 **실제 작성 행위로 연결**한다. 템플릿 팩은 정의되었으나 작성 워크스페이스가 없으면 P1은 여전히 빈 페이지 앞에 선다.

| 페르소나 | 핵심 질문 | 본 SPEC 이전 | 본 SPEC 이후 |
|----------|-----------|--------------|--------------|
| **P1 — Startup CTO** (최우선) | "무엇을, 어떤 구조로 작성하나?" (기존 문서 **없음**) | 템플릿 구조는 보이나 작성 불가 | **핵심 해금** — 섹션별 가이드 + AI 초안 생성으로 첫 문서 작성 가능 |
| **P4 — Consulting Partner** | "클라이언트별 작성 오버헤드 절감" | 클라이언트마다 처음부터 | 디바이스별 AuthoringSession 재사용, 1인당 오버헤드 약 70% 절감 |
| **P2 — RA/QA 실무자** | "파서 정정 후 섹션 갱신" | 수동 정합 | 작성 워크스페이스에서 템플릿 구조 기준 기존 콘텐츠 정합 |

[HARD] P1(기존 문서 없는 스타트업)은 SPEC-AUTHORING-001 없이는 제품을 **전혀** 사용할 수 없다. 본 SPEC이 그 진입 경로다.

### 0.3 이 SPEC이 다루는 것 (In Scope)

- ProductProfile + TemplatePack로부터 **AuthoringSession 생성**
- 템플릿 섹션 트리 렌더링(필수/선택 구분, 작성 지침·플레이스홀더 포함)
- 섹션 **상태 머신**(empty → ai_draft → human_edited → complete, 선택 섹션은 skipped)
- 로컬 **Ollama LLM + pgvector RAG** 기반 섹션 AI 초안 생성
- AI 초안 **신뢰도 및 출처 참조** 표시
- **진행률 추적**(completion_pct, blocking gaps 목록)
- 세션 **저장·재개**(부분 완료 상태 영속화)
- TemplateDocument 순서를 보존한 **DOCX/JSON 내보내기**
- 선택 섹션 **건너뛰기(skip)** + 사유 기록

### 0.4 이 SPEC이 다루지 않는 것 (Exclusions — What NOT to Build)

[HARD] 아래 항목은 SPEC-AUTHORING-001 구현 범위에서 명시적으로 제외한다. spec.md는 WHAT/WHY만 다루며 구현 세부(함수명/클래스 구조/내부 API 스키마)는 Run 단계로 위임한다.

| 제외 항목 | 사유 | 담당 |
|-----------|------|------|
| TemplatePack/TemplateDocument/TemplateSection 정의·등록 | 본 SPEC은 콘텐츠 트리를 **소비**만 한다. 정의는 선행 SPEC | SPEC-TEMPLATE-001 (의존) |
| 증거 바인더 첨부·관리 로직 | 섹션 콘텐츠 작성까지만. 증거 첨부는 별도 도메인 | SPEC-EVIDENCE-001 (예정) |
| 갭 분석/리포트 산출 알고리즘 | blocking_gaps 목록(미완성 필수 섹션)은 노출하되 갭 분석 엔진은 별도 | 미래 SPEC |
| 파서 정합(reconciliation) 엔진 | 작성 워크스페이스에서 기존 콘텐츠 입력은 가능하나 자동 정합 엔진은 별도 | SPEC-PARSER 계열 |
| 클라우드로의 고객 콘텐츠 전송 | [HARD] 모든 LLM 호출은 로컬 Ollama. 고객 콘텐츠는 클라우드로 나가지 않음 | 비범위 (FR-210 Data Sovereignty) |
| 검토 큐/워크플로 승인 라우팅 | reviewer_comment 필드만 정의, 검토 큐 화면은 별도 | SPEC-UI-002 (예정) |
| 실시간 동시 편집(협업 커서/CRDT) | 단일 세션 작성·저장·재개까지만 | 비범위 |
| 최종 규제 결정·법적 사인오프 | 시스템은 작성 보조까지만 | 비범위 |
| ra-med-bot / Vercel UI(Regula SaaS UI) | 본 리포 범위 외 | 비범위 (Lesson #4) |

### 0.5 연관 SPEC 및 의존성

- **선행 의존(필수)**: SPEC-TEMPLATE-001 — TemplatePack/TemplateDocument/TemplateSection 데이터 모델. 본 SPEC의 섹션 트리·작성 지침·출처 참조의 출처
- **선행 의존(완료)**: SPEC-PARSER-001 — 필드 추출 엔진. P2 콘텐츠 입력 시 향후 정합 대상(본 SPEC은 정합 엔진 미포함)
- **후속 의존(예정)**: SPEC-EVIDENCE-001 — AuthoringSectionEntry에 증거 첨부 추가, SPEC-UI-002 — 검토 큐 연동
- **재사용 패턴**: `customer-runtime/src/app/`의 SQLAlchemy async 모델, pydantic-settings config, FastAPI router 패턴, `parser_engine/llm_fallback.py`의 Ollama httpx.AsyncClient 패턴, pgvector 임베딩 검색 패턴

### 0.6 아키텍처 원칙 (불변 제약)

[HARD] 본 SPEC의 데이터 모델·API·LLM 호출은 모두 **Customer Local Runtime**에서 실행한다. Cloud Control Plane으로 고객 콘텐츠를 전송하지 않는다.
[HARD] AI 초안은 인간이 편집하기 전까지 **"AI 생성, 미검증(AI generated, not verified)"** 으로 명확히 표기한다.
[HARD] 매칭되는 TemplatePack/섹션 트리가 없으면 빈 세션을 생성하지 않고 의존 SPEC의 `unsupported` 응답을 그대로 전파한다(speculative 작성 금지).
[HARD] AI 초안 생성은 섹션당 30초 이내에 완료하거나 timeout 상태를 반환한다.

---

## 1. 아키텍처

※ 본 절의 디렉터리 구조, 모듈 파일명, 클래스명, 내부 구현 세부는 비규범적 설계 제안이며, Run 단계에서 변경될 수 있습니다. (Non-normative design note)

### 1.1 도메인 구조 (Non-normative)

```
customer-runtime/src/app/
├── models/
│   ├── authoring_session.py        # [NEW] AuthoringSession ORM
│   ├── authoring_section_entry.py  # [NEW] AuthoringSectionEntry ORM
│   └── authoring_progress.py       # [NEW] AuthoringProgress (뷰/집계 또는 ORM)
├── schemas/
│   ├── authoring_session.py        # [NEW] 세션 생성/조회 Pydantic
│   ├── authoring_section.py        # [NEW] 섹션 콘텐츠/AI 초안 Pydantic
│   └── authoring_export.py         # [NEW] export 요청/응답
├── routers/
│   └── authoring.py                # [NEW] sessions / sections / ai-draft / export
├── services/
│   ├── authoring_session.py        # [NEW] 세션 생성·진행률 집계
│   ├── section_state.py            # [NEW] 섹션 상태 머신 전이 검증
│   ├── ai_draft.py                 # [NEW] Ollama + pgvector RAG 초안 생성
│   └── docx_exporter.py            # [NEW] TemplateDocument 순서 보존 DOCX/JSON 내보내기
└── migrations/                     # [MODIFY] 3개 테이블 신규 마이그레이션
```

### 1.2 설계 원칙

- **섹션 트리**는 SPEC-TEMPLATE-001 데이터(또는 Cloud Control Plane에서 동기화된 지식팩)를 읽기 전용으로 소비한다. 작성 워크스페이스는 템플릿을 수정하지 않는다.
- **AI 초안 생성**은 로컬 Ollama + pgvector RAG로만 수행한다. RAG 컨텍스트는 로컬 지식 베이스(규제 문서 임베딩)에서 검색한다.
- **상태 머신**은 서비스 레이어에서 허용 전이만 허용한다(예: complete → empty 직접 전이 금지, human_edited를 거쳐야 함).
- **진행률**은 필수 섹션 기준으로 계산한다. 선택 섹션의 skip은 미완성으로 계산하지 않는다.
- **export**는 TemplateDocument의 `sort_order`와 TemplateSection의 `sort_order`를 보존하여 문서 순서를 재현한다.

### 1.3 통합 흐름

```
ProductProfile + pack_id
  → POST /authoring/sessions                  (세션 생성 → session_id, 섹션별 empty entry 생성)
  → GET  /authoring/sessions/{id}/sections    (섹션 트리 + entry 상태)
  → POST /authoring/sections/{entry_id}/ai-draft  (Ollama + RAG 초안 생성 → ai_draft 상태)
  → PATCH /authoring/sections/{entry_id}      (인간 편집 저장 → human_edited/complete)
  → GET  /authoring/sessions/{id}             (진행률 요약 + blocking gaps)
  → POST /authoring/sessions/{id}/export      (TemplateDocument 순서 보존 DOCX/JSON)
```

---

## 2. 데이터 모델

3개 엔티티. 모든 `created_at`/`updated_at`은 TIMESTAMPTZ, 기본 키는 UUID.

### 2.1 AuthoringSession

작성 세션 — ProductProfile + TemplatePack의 작성 인스턴스.

| 필드 | 타입 | 설명 |
|------|------|------|
| `session_id` | VARCHAR(36) PK | uuid4 |
| `product_profile_id` | VARCHAR(36) NOT NULL | 대상 ProductProfile (SPEC-TEMPLATE-001) |
| `pack_id` | VARCHAR(64) NOT NULL | 작성 기준 TemplatePack (SPEC-TEMPLATE-001) |
| `status` | VARCHAR(16) NOT NULL | `draft` / `in_progress` / `complete` / `submitted` |
| `created_by` | VARCHAR(128) | 생성 사용자 식별자 |
| `created_at` | TIMESTAMPTZ NOT NULL | 생성 시각 |
| `updated_at` | TIMESTAMPTZ NOT NULL | 갱신 시각 |

### 2.2 AuthoringSectionEntry

세션 내 섹션별 작성 항목 — TemplateSection 1개당 1개.

| 필드 | 타입 | 설명 |
|------|------|------|
| `entry_id` | VARCHAR(36) PK | uuid4 |
| `session_id` | VARCHAR(36) FK → AuthoringSession | 소속 세션 |
| `section_id` | VARCHAR(48) NOT NULL | 원본 TemplateSection (SPEC-TEMPLATE-001) |
| `content` | TEXT | 작성 콘텐츠(인간 편집 결과) |
| `ai_draft` | TEXT NULL | AI 생성 초안(편집 전 원본 보존) |
| `ai_draft_confidence` | FLOAT NULL | AI 초안 신뢰도(0.0~1.0) |
| `ai_draft_sources` | VARCHAR[] NULL | AI 초안 RAG 출처 참조 ID 목록 |
| `status` | VARCHAR(16) NOT NULL | `empty` / `ai_draft` / `human_edited` / `complete` / `skipped` |
| `skip_reason` | TEXT NULL | skip 사유(선택 섹션 한정) |
| `reviewer_comment` | TEXT NULL | 검토자 코멘트(SPEC-UI-002 연동 예약) |
| `updated_at` | TIMESTAMPTZ NOT NULL | 갱신 시각 |

허용 상태(`status`): `empty`, `ai_draft`, `human_edited`, `complete`, `skipped`.

### 2.3 AuthoringProgress

세션 진행률 집계 — 뷰 또는 파생 집계.

| 필드 | 타입 | 설명 |
|------|------|------|
| `session_id` | VARCHAR(36) PK/FK → AuthoringSession | 소속 세션 |
| `total_required_sections` | INT NOT NULL | 필수 섹션 총수 |
| `completed_sections` | INT NOT NULL | complete 상태 필수 섹션 수 |
| `blocking_gaps` | VARCHAR[] | 미완성 필수 섹션 section_id 목록 |
| `completion_pct` | FLOAT NOT NULL | 완료율(completed / total_required × 100) |

---

## 3. 섹션 상태 머신

AuthoringSectionEntry.status 전이 규칙.

```
empty ──ai-draft 생성──▶ ai_draft ──인간 편집──▶ human_edited ──완료 표시──▶ complete
  │                          │                                                  │
  │──인간 직접 편집─────────────────────────────▶ human_edited                  │
  │                                                                            │
  │──(선택 섹션) skip──▶ skipped                          complete ──재편집──▶ human_edited
```

허용 전이:
- `empty` → `ai_draft` (AI 초안 생성)
- `empty` → `human_edited` (AI 없이 직접 작성)
- `empty` → `skipped` (선택 섹션만)
- `ai_draft` → `human_edited` (초안 편집)
- `ai_draft` → `complete` (초안 그대로 승인은 불가 — 반드시 human_edited 경유, REQ-AUTHOR-007 참조)
- `human_edited` → `complete` (완료 표시)
- `complete` → `human_edited` (재편집)
- `skipped` → `empty` (skip 취소, 선택 섹션만)

금지 전이:
- 임의 상태 → `ai_draft` (오직 `empty`에서만 AI 초안 생성 — 기존 콘텐츠 덮어쓰기 방지)
- `complete`/`human_edited` → `skipped` (작성된 내용 skip 금지)
- 필수 섹션 → `skipped` (REQ-AUTHOR-014)

---

## 4. API 계약

모든 응답은 JSON. 인증은 customer-runtime의 기존 API Key 패턴을 따른다. 모든 LLM·데이터 처리는 로컬에서 수행.

### 4.1 `POST /authoring/sessions`

ProductProfile + pack_id로 세션 생성.

- **Request body**: `product_profile_id`(필수), `pack_id`(필수), `created_by`
- **동작**: pack의 섹션 트리를 읽어 섹션마다 `empty` 상태 AuthoringSectionEntry를 생성
- **Response 201**: `{ session_id, status, total_sections, created_at }`
- **Error**: `400` 필수 필드 누락, `404` pack 없음/섹션 트리 없음, `409` 동일 profile+pack 활성 세션 중복(정책에 따라), `401` 인증 실패

### 4.2 `GET /authoring/sessions/{id}`

세션 + 진행률 요약 조회.

- **Response 200**: `{ session, progress: { total_required_sections, completed_sections, blocking_gaps[], completion_pct } }`
- **Error**: `404` 세션 없음, `401` 인증 실패

### 4.3 `GET /authoring/sessions/{id}/sections`

섹션 트리 + entry 상태 조회.

- **Response 200**: `{ sections[] }` — 각 항목: section_id, section_key, title, required, instructions, placeholder, sort_order, entry: { entry_id, status, content, ai_draft, ai_draft_confidence, ai_draft_sources[] }
- **Error**: `404` 세션 없음, `401` 인증 실패

### 4.4 `PATCH /authoring/sections/{entry_id}`

섹션 콘텐츠 저장(인간 편집) 또는 상태 전이.

- **Request body**: `content`(선택), `status`(선택: human_edited/complete/skipped/empty), `skip_reason`(skip 시)
- **동작**: 상태 머신 검증 후 전이. content 저장 시 status는 최소 human_edited로 전이
- **Response 200**: `{ entry_id, status, updated_at }`
- **Error**: `400` 금지 전이/필수 섹션 skip 시도, `404` entry 없음, `401` 인증 실패

### 4.5 `POST /authoring/sections/{entry_id}/ai-draft`

해당 섹션 AI 초안 생성(로컬 Ollama + pgvector RAG).

- **동작**: 섹션 instructions + ProductProfile 컨텍스트로 로컬 지식 베이스 RAG 검색 → Ollama 초안 생성 → `ai_draft`/`ai_draft_confidence`/`ai_draft_sources` 저장 → status `ai_draft`로 전이
- **전제**: entry.status == `empty` (기존 콘텐츠 덮어쓰기 방지)
- **Response 200**: `{ entry_id, ai_draft, ai_draft_confidence, ai_draft_sources[], status: "ai_draft", verified: false }`
- **Response 200 (timeout)**: `{ status: "timeout", reason }` — 30초 초과 시
- **Error**: `409` entry가 empty 상태 아님, `404` entry 없음, `401` 인증 실패

### 4.6 `POST /authoring/sessions/{id}/export`

TemplateDocument 순서 보존 내보내기.

- **Request body**: `format` (`docx` | `json`)
- **동작**: TemplateDocument.sort_order + TemplateSection.sort_order 순으로 섹션 콘텐츠 직렬화
- **Response 200**: DOCX 바이너리(스트림) 또는 JSON 구조
- **Error**: `400` 미지원 format, `404` 세션 없음, `401` 인증 실패

---

## 5. EARS 요구사항

요구사항은 5개 모듈로 그룹화한다: M1(세션·섹션 트리), M2(상태 머신), M3(AI 초안), M4(진행률·저장), M5(내보내기·skip).

### M1 — 세션 및 섹션 트리

**REQ-AUTHOR-001 (Event-Driven, 세션 생성)**
When a `POST /authoring/sessions` request is received with a valid `product_profile_id` and `pack_id`, the system SHALL create an AuthoringSession and one `empty` AuthoringSectionEntry per template section in the pack, then return the assigned `session_id`.

**REQ-AUTHOR-002 (Unwanted Behavior, 미지원 팩)**
If the requested `pack_id` has no resolvable section tree, then the system SHALL reject session creation with a `404` error and SHALL NOT create an empty or speculative session.

**REQ-AUTHOR-003 (Event-Driven, 섹션 트리 조회)**
When a `GET /authoring/sessions/{id}/sections` request is received, the system SHALL return each template section with its title, instructions, placeholder, required flag, and the current entry status.

**REQ-AUTHOR-004 (Ubiquitous, 필수/선택 구분)**
The system SHALL distinguish required sections from optional sections in every section tree response so that the client can render the required-versus-optional distinction.

### M2 — 섹션 상태 머신

**REQ-AUTHOR-005 (State-Driven, 전이 검증)**
While processing a `PATCH /authoring/sections/{entry_id}` status change, the system SHALL permit only the allowed state transitions and SHALL reject disallowed transitions with a `400` error.

**REQ-AUTHOR-006 (Event-Driven, 콘텐츠 저장 전이)**
When a `PATCH /authoring/sections/{entry_id}` request saves non-empty `content`, the system SHALL set the entry status to at least `human_edited`.

**REQ-AUTHOR-007 (Unwanted Behavior, AI 초안 직접 완료 금지)**
If an entry in `ai_draft` status is set to `complete` without passing through `human_edited`, then the system SHALL reject the transition with a `400` error, requiring human review before completion.

### M3 — AI 초안 생성

**REQ-AUTHOR-008 (Event-Driven, AI 초안 생성)**
When a `POST /authoring/sections/{entry_id}/ai-draft` request is received for an entry in `empty` status, the system SHALL generate a draft using the local Ollama model with pgvector RAG over the local knowledge base, and SHALL store the draft, its confidence score, and its source references.

**REQ-AUTHOR-009 (Unwanted Behavior, 클라우드 전송 금지)**
The system SHALL NOT transmit customer authoring content or product profile data to any cloud service during AI draft generation; all model inference SHALL execute on the local runtime.

**REQ-AUTHOR-010 (Ubiquitous, AI 초안 표기)**
The system SHALL mark every AI-generated draft as "AI generated, not verified" until the entry transitions to `human_edited`.

**REQ-AUTHOR-011 (Ubiquitous, 출처 표시)**
The system SHALL include the RAG source references used for an AI draft in the draft response so that the user can see which knowledge sources informed the draft.

**REQ-AUTHOR-012 (Unwanted Behavior, 덮어쓰기 방지)**
If a `POST /authoring/sections/{entry_id}/ai-draft` request targets an entry not in `empty` status, then the system SHALL reject it with a `409` error and SHALL NOT overwrite existing content.

**REQ-AUTHOR-013 (Event-Driven, 성능 한도)**
When AI draft generation for a section exceeds 30 seconds, the system SHALL return a `timeout` status instead of blocking indefinitely.

### M4 — 진행률 및 저장·재개

**REQ-AUTHOR-014 (Unwanted Behavior, 필수 섹션 skip 금지)**
If a `PATCH /authoring/sections/{entry_id}` request attempts to set a required section's status to `skipped`, then the system SHALL reject the request with a `400` error.

**REQ-AUTHOR-015 (Ubiquitous, 진행률 계산)**
The system SHALL compute `completion_pct` as the ratio of completed required sections to total required sections, and SHALL exclude optional and skipped sections from the required-section denominator.

**REQ-AUTHOR-016 (Event-Driven, blocking gaps)**
When a `GET /authoring/sessions/{id}` request is received, the system SHALL return the list of required sections that are not yet `complete` as blocking gaps.

**REQ-AUTHOR-017 (State-Driven, 저장·재개)**
While a session is in `draft` or `in_progress` status, the system SHALL persist every section entry change so that the session can be resumed later with all partial content and statuses intact.

### M5 — 내보내기 및 skip

**REQ-AUTHOR-018 (Event-Driven, 순서 보존 내보내기)**
When a `POST /authoring/sessions/{id}/export` request is received, the system SHALL produce the document with sections ordered by the TemplateDocument and TemplateSection sort order defined in the source template pack.

---

## 6. 인수 기준 (Acceptance Criteria)

각 REQ는 하나 이상의 AC에 대응한다. 상세 Given/When/Then 시나리오는 `acceptance.md` 참조.

- **AC-001**: Given a valid product_profile_id and pack_id, when `POST /authoring/sessions` is called, the system returns `201` with a session_id and one empty entry per section.
- **AC-002**: Given a pack_id with no resolvable section tree, when session creation is called, the system returns `404` and no session is persisted.
- **AC-003**: Given a session, when `GET /authoring/sessions/{id}/sections` is called, each section returns title, instructions, placeholder, required flag, and entry status.
- **AC-004**: Given a mixed required/optional pack, when the section tree is read, required and optional sections are distinguishable.
- **AC-005**: Given an entry in `complete` status, when a `PATCH` attempts `complete → skipped`, the system returns `400`.
- **AC-006**: Given an empty entry, when content is saved via `PATCH`, the entry status becomes `human_edited`.
- **AC-007**: Given an entry in `ai_draft` status, when a `PATCH` sets it directly to `complete`, the system returns `400`.
- **AC-008**: Given an empty entry, when `POST .../ai-draft` is called, an ai_draft with confidence and source references is stored and status becomes `ai_draft`.
- **AC-009**: During AI draft generation, no outbound request carries customer content to a cloud endpoint (verified via mocked/inspected network layer).
- **AC-010**: Given a freshly generated AI draft (status `ai_draft`), when it is rendered, it is marked "AI generated, not verified".
- **AC-011**: Given an AI draft response, when inspected, it contains the RAG source references used.
- **AC-012**: Given an entry already in `human_edited`, when `POST .../ai-draft` is called, the system returns `409` and content is unchanged.
- **AC-013**: Given an AI draft that exceeds 30 seconds, when generation runs, the system returns a `timeout` status.
- **AC-014**: Given a required section, when a `PATCH` attempts to set it `skipped`, the system returns `400`.
- **AC-015**: Given a session with 3 of 5 required sections complete, when `GET /authoring/sessions/{id}` is called, completion_pct is 60 and blocking_gaps lists the 2 incomplete required sections.
- **AC-016**: Given a session with content, when `POST .../export?format=docx` is called, the DOCX sections follow the template document/section sort order.

---

## 7. 구현 단계 (Implementation Phases)

### P0 — Critical (Foundation)

- 데이터 모델 마이그레이션: AuthoringSession + AuthoringSectionEntry 테이블
- 세션 CRUD (`POST /authoring/sessions`, `GET /authoring/sessions/{id}`)
- 섹션 트리 API (`GET /authoring/sessions/{id}/sections`) — 템플릿 섹션을 entry와 함께 반환
- 콘텐츠 저장 (`PATCH /authoring/sections/{entry_id}`) 기본 경로
- 대응: REQ-AUTHOR-001, 002, 003, 004, 006 / AC-001, 002, 003, 004, 006

### P1 — High

- AI 초안 생성 (`POST /authoring/sections/{entry_id}/ai-draft`) — Ollama + pgvector RAG
- AI 초안 신뢰도·출처·미검증 표기
- 섹션 상태 머신 전이 검증(human_edited 경유 완료)
- 진행률 추적(completion_pct, blocking_gaps) + AuthoringProgress 집계
- 저장·재개 영속화
- 성능 한도(30초 timeout)
- 대응: REQ-AUTHOR-005, 007, 008, 009, 010, 011, 012, 013, 015, 016, 017 / AC-005, 007, 008, 009, 010, 011, 012, 013, 015

### P2 — Medium

- DOCX 내보내기(TemplateDocument 순서 보존) + JSON 내보내기
- 일괄 AI 초안(세션 내 모든 empty 섹션 1회 호출)
- 선택 섹션 skip + 사유 + 필수 섹션 skip 금지
- 세션 공유 URL
- 대응: REQ-AUTHOR-014, 018 / AC-014, 016

---

## 8. 보안 및 컴플라이언스

- [HARD] 모든 LLM 추론은 로컬 Ollama에서 수행한다. 고객 콘텐츠·프로파일은 클라우드로 전송하지 않는다(FR-210 Data Sovereignty).
- [HARD] AI 초안은 human_edited 전까지 "AI generated, not verified"로 표기한다(환각·미검증 방지).
- [HARD] 미지원 팩에 대해 빈/추측성 세션을 생성하지 않는다.
- AI 초안 생성은 섹션당 30초 timeout으로 무한 차단을 방지한다.
- API Key 인증은 기존 customer-runtime 패턴을 재사용한다.

---

## 9. 전문가 자문 권장

- **expert-backend**: SQLAlchemy async 3엔티티 모델, 섹션 상태 머신 서비스 설계, Ollama httpx 비동기 호출 + pgvector RAG 검색, 진행률 집계 쿼리, 30초 timeout 처리
- **expert-frontend**: 섹션 트리 작성 워크스페이스 UI(필수/선택 구분, AI 초안 미검증 배지, 진행률 표시) — 후속 UI SPEC에서 상세화

---

## 10. 트레이서빌리티 매트릭스

| REQ | FR / MRD | AC | Phase |
|-----|----------|-----|-------|
| REQ-AUTHOR-001 | FR-214 | AC-001 | P0 |
| REQ-AUTHOR-002 | FR-214 / SPEC-TEMPLATE-001 | AC-002 | P0 |
| REQ-AUTHOR-003 | FR-214 | AC-003 | P0 |
| REQ-AUTHOR-004 | FR-214 | AC-004 | P0 |
| REQ-AUTHOR-005 | FR-214 | AC-005 | P1 |
| REQ-AUTHOR-006 | FR-214 | AC-006 | P0 |
| REQ-AUTHOR-007 | FR-214 | AC-007 | P1 |
| REQ-AUTHOR-008 | FR-214 / MRD REQ-MRD-113 | AC-008 | P1 |
| REQ-AUTHOR-009 | FR-210 / FR-214 | AC-009 | P1 |
| REQ-AUTHOR-010 | FR-214 | AC-010 | P1 |
| REQ-AUTHOR-011 | FR-214 | AC-011 | P1 |
| REQ-AUTHOR-012 | FR-214 | AC-012 | P1 |
| REQ-AUTHOR-013 | FR-214 | AC-013 | P1 |
| REQ-AUTHOR-014 | FR-214 | AC-014 | P2 |
| REQ-AUTHOR-015 | FR-214 | AC-015 | P1 |
| REQ-AUTHOR-016 | FR-214 | AC-015 | P1 |
| REQ-AUTHOR-017 | FR-214 | (저장·재개 검증) | P1 |
| REQ-AUTHOR-018 | FR-214 / MRD REQ-MRD-113 | AC-016 | P2 |

---

## 11. Open Decisions

- 섹션 트리를 Customer Runtime 로컬 캐시에 둘지, Cloud Control Plane에서 매 세션 동기화할지(지식팩 동기화 SPEC과 조율 필요).
- 동일 product_profile + pack에 대한 다중 활성 세션 허용 여부(현재 409 정책은 미확정).
- pgvector RAG 검색 대상 지식 베이스의 인덱싱 시점(크롤러 수집 → 임베딩 파이프라인 연결).
- 일괄 AI 초안(P2)의 동시성 한도(섹션 N개 병렬 생성 시 로컬 GPU/CPU 부하).
- AuthoringProgress를 DB 뷰로 둘지, 매 조회 시 집계 쿼리로 계산할지.
