---
id: SPEC-CHECKLIST-001
version: 0.1.0
status: planned
created_at: 2026-06-13
updated: 2026-06-13
author: moai
priority: high
issue_number: 32
labels: ["spec", "checklist", "gap-analysis", "compliance"]
---

# SPEC-CHECKLIST-001: Checklist & Gap Engine

## HISTORY

- **v0.1.0** (2026-06-13): 최초 작성. Template-first 전환의 검증 레이어로서 Checklist & Gap Engine 범위 확정. TemplatePack 섹션 → 라이브 체크리스트 변환, 누락/미검토/증거없음 항목을 GapFinding으로 식별, blocking/warning/info 심각도 구분, ChecklistItem 런타임 상태 머신(pending → in_progress → complete | waived | blocked), 선택 항목 waiver(정당화 필수), ChecklistSnapshot 불변성(final 잠금), XLSX/PDF export, AuthoringSession 완성 상태 통합, summary API 성능(≤200ms). 데이터 모델 4엔티티(ChecklistSnapshot/GapFinding/ChecklistExport + SPEC-TEMPLATE-001 ChecklistItem 런타임 확장). API 7개. EARS REQ-CHECK-001~018, P0/P1/P2 단계. GitHub Issue #32 연결.

---

## 0. 범위 및 의존성

### 0.1 SPEC 개요

| 항목 | 내용 |
|------|------|
| SPEC-ID | SPEC-CHECKLIST-001 |
| 제목 | Checklist & Gap Engine |
| 상태 | planned |
| 대상 디렉터리 | `customer-runtime/` (로컬 런타임 — FastAPI + PostgreSQL + Ollama + MinIO) |
| 분석 기준 | SPEC-TEMPLATE-001(ChecklistItem 엔티티 정의), SPEC-AUTHORING-001(AuthoringSession 완성 상태), PRD FR-213, MRD REQ-MRD-114 |
| 라이프사이클 | spec-anchored (애플리케이션 코드와 함께 유지) |
| 개발 방법론 | TDD (RED-GREEN-REFACTOR) |
| Priority | high |

### 0.2 목적 (Why)

규제 제출 전, RA/QA 실무자(P2)는 "무엇이 빠졌는가"를 수동으로 찾을 방법이 없다. 현재 제품에는 체크리스트 기능이 전혀 없다. 본 SPEC은 TemplatePack 섹션을 라이브 체크리스트로 변환하고, 누락·미검토·증거없음 항목을 자동으로 GapFinding으로 도출하여 제출 가능 여부를 결정 가능하게 만든다.

페르소나별 가치:
- **P2 — RA/QA 실무자(주 사용자)**: 제출 전 자동 갭 탐지. "무엇이 빠졌는지 자동으로 알려달라."
- **P4 — 컨설팅 파트너**: device family + pathway별 재사용 가능한 체크리스트 구조. "한 고객사의 X-ray 체크리스트를 만들면 다음 고객사에서도 구조를 재사용하고 싶다."
- **P3 — 품질 책임자**: 승인 전 갭 리포트. "승인하기 전에 필수 항목이 모두 완료됐는지 알아야 한다."

### 0.3 이 SPEC이 다루는 것 (In Scope)

- TemplatePack 섹션 → 라이브 ChecklistSnapshot 생성 (pack_id + 선택적 session_id 기반)
- 필수(required) vs 선택(optional) 섹션 구분에 따른 blocking vs non-blocking 갭 도출
- ChecklistItem 런타임 상태 머신: `pending → in_progress → complete | waived | blocked`
- 증거 첨부 추적(`evidence_required` 플래그 항목의 증거 충족 여부 — Evidence Binder 연동 예약)
- Waiver 워크플로: 선택 항목만 waive 가능, 정당화 텍스트 필수
- GapFinding 심각도: `blocking`(제출 차단) / `warning`(검토 필요) / `info`(정보성)
- 갭 리포트 export: XLSX(TemplateDocument당 시트 1개), PDF(규제 포맷)
- ChecklistSnapshot 불변성: `final` 상태 스냅샷은 수정 불가
- summary API 성능: 진행률 + blocking 갭 수, ≤200ms 응답
- AuthoringSession 완성 상태(AuthoringSectionEntry status) 통합 → 체크리스트 항목 상태 반영

### 0.4 이 SPEC이 다루지 않는 것 (Exclusions — What NOT to Build)

[HARD] 아래 항목은 SPEC-CHECKLIST-001 구현 범위에서 명시적으로 제외한다. spec.md는 WHAT/WHY만 다루며 구현 세부(함수명/클래스 구조/API 스키마)는 Run 단계로 위임한다.

| 제외 항목 | 사유 | 담당 |
|-----------|------|------|
| TemplatePack/TemplateSection 데이터 모델 정의 | ChecklistItem 엔티티는 이미 정의됨. 본 SPEC은 런타임 동작만 확장 | SPEC-TEMPLATE-001 (planned) |
| 가이드 작성 에디터(섹션 작성 UI/AI 초안) | 작성 워크플로는 별도. 본 SPEC은 완성 상태를 소비만 | SPEC-AUTHORING-001 (planned) |
| 증거 파일 첨부·업로드·관리 로직 | 본 SPEC은 `evidence_required` 충족 여부 추적만. 첨부 처리는 별도 | SPEC-EVIDENCE-001 (미래) |
| 문서 세트 승인 워크플로(Review Workspace) | blocking 갭이 승인을 차단한다는 제약만 정의. 승인 UI/플로는 별도 | FR-207 Review Workspace (미래 SPEC) |
| 규제 변경 알림/이메일 발송 | 알림 도메인 분리 | 미래 SPEC |
| ra-med-bot / Vercel | 본 제품 범위 외 | 비범위 |
| 필수 항목 waive | [HARD] 필수 섹션 항목은 절대 waive 불가. 선택 항목만 가능 | 본 SPEC(제약으로 정의) |

### 0.5 연관 SPEC 및 의존성

- **선행 의존(planned)**: SPEC-TEMPLATE-001 — `ChecklistItem` 엔티티(checklist_item_id, section_id, status, blocking, evidence_required, reviewer_status) 정의. 본 SPEC은 이 엔티티를 런타임 테이블로 구체화하고 상태 머신·갭 도출 동작을 추가한다. TemplateDocument/TemplateSection 트리를 읽기 전용으로 소비.
- **선행 의존(planned)**: SPEC-AUTHORING-001 — `AuthoringSession`, `AuthoringSectionEntry`(status: empty/ai_draft/human_edited/complete/skipped) 완성 상태가 체크리스트 항목 상태로 매핑된다.
- **연동 예약(미래)**: SPEC-EVIDENCE-001 — `evidence_required` 항목의 증거 충족 신호 제공.
- **연동 예약(미래)**: FR-207 Review Workspace — blocking 갭이 문서 세트 승인을 차단.
- **재사용 패턴**: `customer-runtime/src/app/services/storage.py`(MinIO 업로드, export 파일 저장), `database.py`(async engine), `config.py`(pydantic-settings), `models/base.py`(TimestampMixin).

### 0.6 아키텍처 원칙 (불변 제약)

[HARD] Checklist & Gap Engine은 Customer Local Runtime(`customer-runtime/`)에서 실행된다. 고객 콘텐츠는 클라우드로 전송하지 않는다 (FR-210 Data Sovereignty).
[HARD] 필수 섹션에서 생성된 ChecklistItem은 waive할 수 없다. waiver는 선택 섹션 항목에만 허용하며 정당화 텍스트가 반드시 있어야 한다.
[HARD] `final` 상태로 확정된 ChecklistSnapshot은 항목 상태·갭을 포함하여 일체 수정할 수 없다(불변).
[HARD] blocking 갭이 존재하면 문서 세트 제출/승인을 차단한다(승인 게이트는 FR-207 연동 시 적용).

---

## 1. 아키텍처

※ 본 절의 디렉터리 구조, 모듈 파일명, 클래스명, 구현 세부는 비규범적 설계 제안이며, Run 단계에서 변경될 수 있습니다. (Non-normative design note)

### 1.1 디렉터리 구조 (제안)

```
customer-runtime/src/app/
├── models/
│   ├── checklist_item.py        # [NEW] ChecklistItem 런타임 ORM (SPEC-TEMPLATE-001 엔티티 구체화)
│   ├── checklist_snapshot.py    # [NEW] ChecklistSnapshot ORM
│   ├── gap_finding.py           # [NEW] GapFinding ORM
│   └── checklist_export.py      # [NEW] ChecklistExport ORM
├── schemas/
│   └── checklist.py             # [NEW] Pydantic 요청/응답 모델
├── routers/
│   └── checklist.py             # [NEW] /checklists/* 엔드포인트
├── services/
│   ├── checklist/
│   │   ├── generator.py         # [NEW] TemplatePack 섹션 → ChecklistSnapshot 생성
│   │   ├── gap_engine.py        # [NEW] GapFinding 도출(누락/미검토/증거없음)
│   │   ├── state_machine.py     # [NEW] 항목 상태 전이 검증
│   │   ├── waiver.py            # [NEW] waiver 워크플로(선택 항목만, 정당화 필수)
│   │   └── authoring_sync.py    # [NEW] AuthoringSession 완성 상태 매핑
│   └── export/
│       ├── xlsx.py              # [NEW] XLSX export (TemplateDocument당 시트)
│       └── pdf.py               # [NEW] PDF export (규제 포맷)
└── tests/                       # [NEW] pytest 유닛 + @pytest.mark.skip_no_docker 통합
```

### 1.2 상태 머신 (런타임)

ChecklistItem 런타임 상태(`status`)는 다음 전이만 허용한다.

```
pending ──→ in_progress ──→ complete
   │             │
   │             └──────────→ blocked
   └──→ waived (선택 항목 한정, 정당화 필수)
blocked ──→ in_progress (해소 시 복귀)
```

[HARD] 허용 상태: `pending`, `in_progress`, `complete`, `waived`, `blocked`.
[HARD] `waived`는 `blocking=false`(선택 항목)인 ChecklistItem에서만 진입 가능하며 정당화 텍스트가 있어야 한다.

업스트림(SPEC-TEMPLATE-001 ChecklistItem `status`: `not_started/drafted/evidence_attached/needs_review/approved/not_applicable/blocked`)과의 매핑은 §3.5 참조. 본 SPEC의 런타임 상태가 체크리스트 진행 추적의 권위 소스다.

### 1.3 갭 도출 흐름

```
POST /checklists/generate (pack_id, session_id?)
  → generator: 적용 섹션 순회 → ChecklistItem 생성(blocking/evidence_required 상속)
  → authoring_sync: session_id 있으면 AuthoringSectionEntry 상태 매핑
  → gap_engine: 각 항목 평가 → GapFinding 생성
       · 필수 항목 미완료      → severity=blocking (gap_type=missing_content)
       · evidence_required 미충족 → severity=blocking|warning (gap_type=no_evidence)
       · 리뷰 미수행            → severity=warning (gap_type=unreviewed)
       · 참조 불완전            → severity=info (gap_type=incomplete_reference)
  → ChecklistSnapshot INSERT (draft) + 집계(total/complete/blocking_gaps_count)
```

---

## 2. API 계약 (제안)

상세 스키마는 Run 단계 위임. 엔드포인트·책임만 정의.

| 메서드 | 경로 | 책임 | 대응 REQ |
|--------|------|------|----------|
| POST | `/checklists/generate` | pack_id + 선택적 session_id로 체크리스트 생성, snapshot_id 반환 | REQ-CHECK-001, 002, 010 |
| GET | `/checklists/{snapshot_id}` | 항목 + 갭 포함 전체 체크리스트 조회 | REQ-CHECK-005 |
| GET | `/checklists/{snapshot_id}/gaps` | 갭 목록(severity 필터 가능) | REQ-CHECK-006, 008 |
| PATCH | `/checklists/{snapshot_id}/items/{item_id}` | 항목 상태 갱신(상태 머신 검증) | REQ-CHECK-003, 011 |
| POST | `/checklists/{snapshot_id}/items/{item_id}/waive` | 선택 항목 waive(정당화 필수) | REQ-CHECK-004, 012 |
| POST | `/checklists/{snapshot_id}/export` | XLSX/PDF export | REQ-CHECK-013, 014 |
| GET | `/checklists/{snapshot_id}/summary` | 진행률 % + blocking 갭 수(≤200ms) | REQ-CHECK-007, 015 |

---

## 3. 데이터 모델

### 3.1 ChecklistItem (런타임 테이블 — SPEC-TEMPLATE-001 엔티티 구체화)

| 필드 | 타입 | 설명 |
|------|------|------|
| `checklist_item_id` | VARCHAR(48) PK | 항목 식별자 |
| `snapshot_id` | VARCHAR(36) FK → ChecklistSnapshot | 소속 스냅샷 |
| `section_id` | VARCHAR(48) | 원본 TemplateSection 참조(읽기 전용) |
| `status` | VARCHAR(24) NOT NULL | `pending`/`in_progress`/`complete`/`waived`/`blocked` |
| `blocking` | BOOLEAN NOT NULL | 차단 여부(필수 섹션 = true) |
| `evidence_required` | BOOLEAN NOT NULL | 증거 첨부 필요 여부 |
| `evidence_satisfied` | BOOLEAN NOT NULL DEFAULT false | 증거 충족 여부(Evidence Binder 연동 예약) |
| `reviewer_status` | VARCHAR(24) NULL | 리뷰어 상태 |
| `waiver_justification` | TEXT NULL | waiver 정당화(waived일 때만 NOT NULL) |
| `created_at` / `updated_at` | TIMESTAMPTZ | 타임스탬프 |

### 3.2 ChecklistSnapshot

| 필드 | 타입 | 설명 |
|------|------|------|
| `snapshot_id` | VARCHAR(36) PK | uuid4 |
| `session_id` | VARCHAR(36) NULL | AuthoringSession 또는 standalone(null) |
| `pack_id` | VARCHAR(48) NOT NULL | 원본 TemplatePack |
| `generated_at` | TIMESTAMPTZ NOT NULL | 생성 시각 |
| `total_items` | INT NOT NULL | 전체 항목 수 |
| `complete_items` | INT NOT NULL | 완료 항목 수 |
| `blocking_gaps_count` | INT NOT NULL | blocking 갭 수 |
| `status` | VARCHAR(16) NOT NULL | `draft` / `final` |

### 3.3 GapFinding

| 필드 | 타입 | 설명 |
|------|------|------|
| `gap_id` | VARCHAR(36) PK | uuid4 |
| `snapshot_id` | VARCHAR(36) FK → ChecklistSnapshot | 소속 스냅샷 |
| `section_id` | VARCHAR(48) NOT NULL | 대상 섹션 |
| `gap_type` | VARCHAR(32) NOT NULL | `missing_content`/`no_evidence`/`unreviewed`/`incomplete_reference` |
| `severity` | VARCHAR(16) NOT NULL | `blocking`/`warning`/`info` |
| `description` | TEXT NOT NULL | 갭 설명 |
| `suggested_action` | TEXT NULL | 권장 조치 |
| `resolved_at` | TIMESTAMPTZ NULL | 해소 시각(미해소 시 null) |

### 3.4 ChecklistExport

| 필드 | 타입 | 설명 |
|------|------|------|
| `export_id` | VARCHAR(36) PK | uuid4 |
| `snapshot_id` | VARCHAR(36) FK → ChecklistSnapshot | 소속 스냅샷 |
| `format` | VARCHAR(8) NOT NULL | `json`/`xlsx`/`pdf` |
| `generated_at` | TIMESTAMPTZ NOT NULL | 생성 시각 |
| `file_ref` | VARCHAR(512) NOT NULL | MinIO 경로/오브젝트 참조 |

### 3.5 상태 매핑 (업스트림 ↔ 런타임)

| AuthoringSectionEntry (SPEC-AUTHORING-001) | 런타임 ChecklistItem.status |
|--------------------------------------------|------------------------------|
| `empty` | `pending` |
| `ai_draft` / `human_edited` | `in_progress` |
| `complete` | `complete` |
| `skipped` (선택 섹션) | `waived` (정당화 = "section skipped") |

---

## 4. What NOT to Build (Exclusions 요약)

§0.4 참조. 최소 핵심 제외:

1. **TemplatePack/TemplateSection 모델 정의** — SPEC-TEMPLATE-001 책임. 본 SPEC은 런타임 동작만 확장.
2. **작성 에디터/AI 초안** — SPEC-AUTHORING-001 책임. 완성 상태만 소비.
3. **증거 파일 첨부 로직** — SPEC-EVIDENCE-001 책임. 충족 여부 추적만.
4. **문서 세트 승인 UI/플로** — FR-207 Review Workspace. blocking 차단 제약만 정의.
5. **필수 항목 waive** — [HARD] 불가. 선택 항목만.

---

## 5. EARS 요구사항

요구사항은 5개 모듈로 그룹화한다: M1(생성), M2(상태·갭), M3(waiver·증거), M4(export·불변성), M5(성능·통합).

### M1 — 체크리스트 생성

**REQ-CHECK-001 (Event-Driven, 생성)**
When a client sends `POST /checklists/generate` with a `pack_id`, the system SHALL create a ChecklistSnapshot containing one ChecklistItem per applicable section of the TemplatePack and return a `snapshot_id`.

**REQ-CHECK-002 (Ubiquitous, blocking 상속)**
The system SHALL set `blocking=true` on every ChecklistItem derived from a required section and `blocking=false` on every ChecklistItem derived from an optional section.

**REQ-CHECK-010 (State-Driven, AuthoringSession 통합)**
While generating a checklist with a provided `session_id`, the system SHALL map each AuthoringSectionEntry completion state to the corresponding ChecklistItem runtime status per the §3.5 mapping.

### M2 — 상태 머신 및 갭 도출

**REQ-CHECK-003 (Event-Driven, 상태 갱신)**
When a client sends `PATCH /checklists/{snapshot_id}/items/{item_id}` with a new status, the system SHALL apply the change only if it is a permitted transition in the runtime state machine (`pending → in_progress → complete | waived | blocked`).

**REQ-CHECK-009 (Unwanted Behavior, 잘못된 전이)**
If a requested ChecklistItem status transition is not permitted by the runtime state machine, then the system SHALL reject the request and leave the item status unchanged.

**REQ-CHECK-005 (Event-Driven, 누락 갭)**
When a checklist is generated, the system SHALL create a GapFinding with `gap_type=missing_content` and `severity=blocking` for every required-section item whose status is not `complete`.

**REQ-CHECK-006 (Ubiquitous, 심각도 구분)**
The system SHALL classify every GapFinding severity as exactly one of `blocking` (submission blocked), `warning` (needs review), or `info` (informational).

**REQ-CHECK-008 (Event-Driven, 갭 필터)**
When a client sends `GET /checklists/{snapshot_id}/gaps` with a `severity` query parameter, the system SHALL return only the GapFinding records matching that severity.

### M3 — Waiver 및 증거

**REQ-CHECK-004 (Event-Driven, waiver)**
When a client sends `POST /checklists/{snapshot_id}/items/{item_id}/waive` with a justification text for an optional (`blocking=false`) item, the system SHALL set the item status to `waived` and persist the justification.

**REQ-CHECK-012 (Unwanted Behavior, 필수 waiver 금지)**
If a waive request targets an item with `blocking=true`, then the system SHALL reject the request and leave the item unchanged.

**REQ-CHECK-016 (Unwanted Behavior, 정당화 누락)**
If a waive request is missing justification text, then the system SHALL reject the request.

**REQ-CHECK-011 (Event-Driven, 증거 갭)**
When a ChecklistItem has `evidence_required=true` and `evidence_satisfied=false`, the system SHALL create a GapFinding with `gap_type=no_evidence`.

### M4 — Export 및 불변성

**REQ-CHECK-013 (Event-Driven, XLSX export)**
When a client sends `POST /checklists/{snapshot_id}/export` with format `xlsx`, the system SHALL produce an XLSX file containing one worksheet per TemplateDocument and return a `file_ref`.

**REQ-CHECK-014 (Event-Driven, PDF export)**
When a client sends `POST /checklists/{snapshot_id}/export` with format `pdf`, the system SHALL produce a PDF gap report and return a `file_ref`.

**REQ-CHECK-017 (Unwanted Behavior, 불변 스냅샷)**
If a mutation request (item status update, waive, or regeneration) targets a ChecklistSnapshot whose status is `final`, then the system SHALL reject the request.

**REQ-CHECK-018 (Event-Driven, 확정)**
When a checklist is finalized, the system SHALL set the ChecklistSnapshot status to `final` and thereafter treat it as immutable.

### M5 — 성능 및 통합

**REQ-CHECK-007 (Event-Driven, summary)**
When a client sends `GET /checklists/{snapshot_id}/summary`, the system SHALL return the completion percentage and blocking gap count.

**REQ-CHECK-015 (State-Driven, summary 성능)**
While serving `GET /checklists/{snapshot_id}/summary`, the system SHALL respond within 200ms.

---

## 6. 보안 및 컴플라이언스

- [HARD] 고객 콘텐츠는 로컬 런타임에만 존재하며 클라우드로 전송하지 않는다 (FR-210).
- [HARD] export 파일은 로컬 MinIO에만 저장한다.
- 모든 mutation API는 인증(API Key/tenant)을 요구한다.
- waiver 정당화는 감사 추적을 위해 변경 불가하게 기록한다.

---

## 7. 전문가 자문 권장

- **expert-backend**: FastAPI 상태 머신 검증, SQLAlchemy async 집계 쿼리, summary ≤200ms 인덱싱 전략, XLSX/PDF 생성 비동기 처리.

---

## 8. 인수 기준 연결

각 REQ는 하나 이상의 AC에 대응한다. 상세 Given/When/Then 시나리오는 `acceptance.md` 참조.

| REQ | 주제 | AC |
|-----|------|-----|
| REQ-CHECK-001 | 체크리스트 생성 | AC-001 |
| REQ-CHECK-002 | blocking 상속 | AC-001 |
| REQ-CHECK-003 | 상태 갱신 | AC-002 |
| REQ-CHECK-009 | 잘못된 전이 거부 | AC-002 |
| REQ-CHECK-004 | waiver | AC-003 |
| REQ-CHECK-012 | 필수 waiver 금지 | AC-003 |
| REQ-CHECK-016 | 정당화 누락 거부 | AC-003 |
| REQ-CHECK-005 | 누락 갭(blocking) | AC-004 |
| REQ-CHECK-006 | 심각도 구분 | AC-004 |
| REQ-CHECK-008 | 갭 필터 | AC-004 |
| REQ-CHECK-011 | 증거 갭 | AC-005 |
| REQ-CHECK-013 | XLSX export | AC-006 |
| REQ-CHECK-014 | PDF export | AC-006 |
| REQ-CHECK-017 | 불변 스냅샷 | AC-007 |
| REQ-CHECK-018 | 확정 | AC-007 |
| REQ-CHECK-007 | summary | AC-008 |
| REQ-CHECK-015 | summary 성능 | AC-008 |
| REQ-CHECK-010 | AuthoringSession 통합 | AC-009 |
