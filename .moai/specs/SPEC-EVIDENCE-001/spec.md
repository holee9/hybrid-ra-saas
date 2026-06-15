---
id: SPEC-EVIDENCE-001
version: 0.1.0
status: planned
created_at: 2026-06-13
updated: 2026-06-13
author: moai
priority: high
issue_number: 33
labels: ["spec", "evidence", "audit", "compliance"]
---

# SPEC-EVIDENCE-001: Evidence Binder — 제출 패키지 증거 연결 및 갭 자동 도출

## HISTORY

- **v0.1.0** (2026-06-13): 최초 작성. Evidence Binder 도메인 범위 확정 — 요구사항/리스크 컨트롤/테스트/IFU 경고/첨부파일을 제출 패키지로 연결하는 데이터 모델 정의. 고위험 컨트롤 중 미검증·미연결 항목 자동 surfacing. MinIO 증거 파일 저장(원문 로컬 보관, Cloud Control Plane 미전송), SHA-256 무결성 검증, sealed binder 불변성, TemplateDocument 계층 구조 ZIP export. SPEC-TEMPLATE-001(TemplateSection/SourceReference), SPEC-CHECKLIST-001(ChecklistItem.evidence_required), SPEC-TRACEABILITY-001(TraceabilityNode/Edge) 소비. EARS 인수 기준(REQ-EVIDENCE-001~018) 정의. GitHub Issue #33.

---

## 0. 범위 및 의존성

### 0.1 SPEC 개요

| 항목 | 내용 |
|------|------|
| SPEC-ID | SPEC-EVIDENCE-001 |
| 제목 | Evidence Binder — 제출 패키지 증거 연결 및 갭 자동 도출 |
| 상태 | planned |
| 대상 디렉터리 | `customer-runtime/` (Customer Local Runtime, Python FastAPI) |
| 라이프사이클 | spec-anchored (애플리케이션 코드와 함께 유지) |
| 개발 방법론 | TDD (RED-GREEN-REFACTOR) |
| Priority | high |
| GitHub Issue | #33 |

### 0.2 비즈니스 맥락 및 페르소나

Evidence Binder는 의료기기 규제 제출(RA submission)에서 "주장(claim) ↔ 증거(evidence)" 연결을 추적하고 제출 패키지로 봉인·내보내는 도메인이다. 규제 심사는 모든 고위험 리스크 컨트롤이 검증된 증거(테스트 리포트 등)로 뒷받침되는지를 요구한다.

| 페르소나 | 역할 | 핵심 요구 |
|----------|------|-----------|
| **P3 — Quality Manager** (1차) | 품질 책임자 | "제출 감사 시 모든 고위험 컨트롤에 검증된 테스트 리포트가 첨부되었음을 확인해야 한다." |
| **P4 — Consulting Partner** | 컨설팅 파트너 | "한 고객 제출의 전체 증거를 패키징하고, 유사 기기의 다음 고객 제출에 구조를 재사용하고 싶다." |
| **P2 — RA/QA Practitioner** | 실무자 | "IFU 4.2절을 그 성능 주장을 검증하는 테스트 리포트에 연결해야 한다." |

### 0.3 PRD/MRD 추적

| 출처 | 요구사항 | 본 SPEC 대응 |
|------|----------|--------------|
| PRD FR-215 | Evidence Binder — 요구사항/리스크 컨트롤/테스트/IFU 경고/첨부를 제출 패키지로 연결. 고위험 미검증·미연결 자동 surfacing | 본 SPEC 전체 |
| PRD FR-208 | Audit & Export — 증거는 감사 export의 일부. 본 SPEC이 증거 데이터 모델 정의, FR-208 export가 이를 소비 | §3 데이터 모델 제공, ZIP export(REQ-014~016) |
| MRD REQ-MRD-115 | Evidence Binder — 고위험 컨트롤 미검증·미연결 첨부 자동 surfacing | REQ-EVIDENCE-009~013 |
| MRD REQ-MRD-107 | Audit & Evidence — export 내 증거 트레이서빌리티 | REQ-EVIDENCE-014~016 |

### 0.4 이 SPEC이 다루는 것 (In Scope)

- `EvidenceBinder` — ProductProfile에 연결된 증거 바인더(draft/sealed/archived 라이프사이클). 선택적으로 TemplatePack(pack_id)에 연결
- `EvidenceLink` — 임의 소스 엔티티(requirement/risk_control/test/ifu_section/checklist_item) → 임의 타깃(file/traceability_node/external_url) 연결. 연결 의미(satisfies/verifies/supports/warns_about)
- `EvidenceFile` — MinIO 객체 저장소에 증거 파일 업로드(파일당 최대 50MB, PDF/DOCX/XLSX/CSV/PNG/JPEG 허용), SHA-256 무결성 검증
- `EvidenceGap` — 고위험 컨트롤 중 미검증·미연결 항목 자동 도출(critical/high/medium severity)
- 고위험 컨트롤 자동 surfacing — RMS/해저드 분석의 고위험 컨트롤이 증거 0건이면 critical 갭으로 자동 등록(사용자 트리거 아님)
- Sealed binder 불변성 — 봉인 후 모든 수정 차단(HARD 제약)
- ZIP export — TemplateDocument 계층과 일치하는 폴더 구조로 증거 패키지 내보내기
- 갭 분석 성능 — 20-link 바인더 갭 분석 ≤ 3초
- 감사 추적 — 모든 link 연산 로깅

### 0.5 이 SPEC이 다루지 않는 것 (Exclusions — What NOT to Build)

[HARD] 아래 항목은 SPEC-EVIDENCE-001 구현 범위에서 명시적으로 제외한다. spec.md는 WHAT/WHY만 다루며 구현 세부(함수명/클래스 구조/세부 API 스키마)는 Run 단계로 위임한다.

| 제외 항목 | 사유 | 담당 |
|-----------|------|------|
| TemplateSection/SourceReference 데이터 모델 정의 | 본 SPEC은 이를 소비만. 정의는 선행 SPEC | SPEC-TEMPLATE-001 |
| ChecklistItem.evidence_required 플래그 자체 정의 | 본 SPEC은 플래그를 읽어 갭 도출만. 정의는 별도 | SPEC-CHECKLIST-001 |
| TraceabilityNode/Edge 그래프 구축 | 본 SPEC은 노드에 첨부 메타데이터만 추가. 그래프 자체는 별도 | SPEC-TRACEABILITY-001 |
| 리스크 컨트롤 / 해저드 분석 / RMS 데이터 모델 정의 | 고위험 컨트롤 목록을 읽어 갭 도출만. RMS 정의는 별도 도메인 | 미래 SPEC (RMS) |
| 증거 파일의 Cloud Control Plane 전송/동기화 | 증거 원문은 로컬 MinIO에만 보관(FR-210 Data Sovereignty). 클라우드 미전송 | 비범위 |
| 최종 감사 보고서(audit report) 렌더링 | 본 SPEC은 증거 데이터 모델 + ZIP export 제공. 감사 보고서 포맷은 FR-208 | SPEC (FR-208 audit export) |
| OCR / 증거 파일 내용 파싱 | 증거 파일은 바이트 저장 + 메타데이터만. 내용 추출 없음 | 비범위 |
| ra-med-bot / Vercel 통합 | 챗봇 도메인 분리 | 비범위 |
| LLM 기반 일괄 link 제안 자동 적용 | P2에서 "제안"만. 자동 적용·확정은 사용자 승인 필요 | 본 SPEC P2(제안 한정) |

### 0.6 연관 SPEC 및 의존성

- **선행 의존**: SPEC-TEMPLATE-001 — `TemplateSection`, `SourceReference`, TemplatePack/TemplateDocument 계층(ZIP export 폴더 구조 기준)
- **선행 의존**: SPEC-CHECKLIST-001 — `ChecklistItem.evidence_required` 플래그(증거 바인더 갭 도출 트리거)
- **선행 의존**: SPEC-TRACEABILITY-001 — `TraceabilityNode`/`Edge`(증거 바인더가 노드에 첨부 메타데이터 추가)
- **재사용 패턴**: `customer-runtime/src/app/services/storage.py`(MinIO/S3 호환 StorageService), `database.py`(async engine), `config.py`(pydantic-settings)

### 0.7 아키텍처 원칙 (불변 제약)

[HARD] 증거 파일 원문은 로컬 MinIO에만 저장하며 Cloud Control Plane으로 전송하지 않는다 (FR-210 Data Sovereignty).
[HARD] Sealed(봉인) 바인더는 불변이다 — 봉인 후 link 추가/삭제, 파일 업로드, 메타데이터 수정 모두 차단한다. 예외 없음.
[HARD] 고위험 컨트롤 증거 갭 surfacing은 자동이다 — 사용자가 명시적으로 트리거하지 않아도 바인더 조회/갱신 시 자동 계산한다.

---

## 1. 아키텍처

※ 본 절의 디렉터리 구조, 모듈 파일명, 클래스명, 세부 구현은 비규범적 설계 제안이며, Run 단계에서 변경될 수 있습니다. (Non-normative design note)

### 1.1 디렉터리 구조 (제안)

```
customer-runtime/src/app/
├── models/
│   ├── evidence_binder.py       # [NEW] EvidenceBinder ORM
│   ├── evidence_link.py         # [NEW] EvidenceLink ORM
│   ├── evidence_file.py         # [NEW] EvidenceFile ORM
│   └── evidence_gap.py          # [NEW] EvidenceGap ORM
├── schemas/
│   └── evidence.py              # [NEW] Pydantic 요청/응답 모델
├── routers/
│   └── evidence.py              # [NEW] /evidence-binders/* 엔드포인트
├── services/
│   └── evidence/
│       ├── binder.py            # [NEW] 바인더 CRUD + seal/archive 라이프사이클
│       ├── linker.py            # [NEW] EvidenceLink 생성/삭제 + 검증
│       ├── file_store.py        # [NEW] MinIO 업로드 + SHA-256 + 형식/크기 검증
│       ├── gap_engine.py        # [NEW] 고위험 미검증 갭 자동 도출
│       └── exporter.py          # [NEW] TemplateDocument 계층 ZIP export
└── tests/                       # [NEW] pytest 유닛 + @pytest.mark 통합
```

### 1.2 모듈 설계 원칙 (Non-normative)

- `binder.py`가 상태 라이프사이클(draft → sealed → archived)을 단일 책임으로 관리한다. seal 이후 mutation 시도는 모든 서비스에서 차단된다.
- `gap_engine.py`는 (1) 고위험 컨트롤 0-증거, (2) ChecklistItem.evidence_required & 미연결, (3) IFU 섹션 증거 누락 세 갈래를 평가하고 severity를 분류한다.
- `file_store.py`는 MinIO 업로드 전 형식/크기 검증 → 업로드 → SHA-256 계산·기록을 수행한다. `storage.py`의 S3 호환 패턴을 재사용한다.
- `exporter.py`는 TemplatePack/TemplateDocument 계층을 폴더 구조로 매핑하여 ZIP을 생성한다.

### 1.3 갭 자동 도출 흐름 (개념)

```
GET /evidence-binders/{id}  또는  link/file 변경
  → gap_engine.evaluate(binder)
      1. 고위험 컨트롤 목록 로드 (RMS/해저드 분석)
      2. 컨트롤별 verifies/satisfies link 존재 여부 검사
      3. ChecklistItem.evidence_required=true & evidence_satisfied=false 검사
      4. IFU 섹션 증거(warns_about/supports) 누락 검사
      5. severity 분류 → EvidenceGap upsert
  → 응답에 gaps summary 포함
```

### 1.4 ZIP export 폴더 구조 (개념)

```
{binder_name}.zip
├── manifest.json                      # 바인더 메타 + link 목록 + 무결성 해시
├── {TemplateDocument-1}/              # TemplateDocument 계층 매핑
│   ├── {section}/                     # TemplateSection 계층
│   │   └── {evidence_file}            # 연결된 증거 파일
└── {TemplateDocument-2}/
    └── ...
```

---

## 2. EARS 요구사항

요구사항은 5개 모듈로 그룹화한다: M1(바인더 라이프사이클), M2(증거 파일), M3(연결), M4(갭 자동 도출), M5(봉인·export·감사).

### M1 — 바인더 라이프사이클

**REQ-EVIDENCE-001 (Event-Driven, Binder creation)**
When a client sends `POST /evidence-binders` with a valid `product_profile_id`, the system shall create a new `EvidenceBinder` in `draft` status linked to that ProductProfile and return its `binder_id`.

**REQ-EVIDENCE-002 (Optional, TemplatePack linkage)**
Where a `pack_id` is provided at binder creation, the system shall link the binder to that TemplatePack so that ZIP export uses the pack's TemplateDocument hierarchy as the folder structure.

**REQ-EVIDENCE-003 (Event-Driven, Binder retrieval with gaps)**
When a client sends `GET /evidence-binders/{id}`, the system shall return the binder with its links and a gaps summary (counts by severity).

### M2 — 증거 파일

**REQ-EVIDENCE-004 (Event-Driven, File upload)**
When a client sends `POST /evidence-binders/{id}/files` with a file, the system shall store the file in MinIO under a binder-scoped storage path and create an `EvidenceFile` record with original_filename, content_type, size_bytes, storage_ref, and uploaded_at.

**REQ-EVIDENCE-005 (Unwanted Behavior, File size limit)**
If an uploaded evidence file exceeds 50 MB, then the system shall reject the upload and shall NOT store the file.

**REQ-EVIDENCE-006 (Unwanted Behavior, File format restriction)**
If an uploaded evidence file's content type is not one of PDF, DOCX, XLSX, CSV, PNG, or JPEG, then the system shall reject the upload and shall NOT store the file.

**REQ-EVIDENCE-007 (Event-Driven, Content integrity hash)**
When an evidence file is successfully uploaded, the system shall compute the SHA-256 hash of the file's byte content and persist it on the `EvidenceFile` record.

**REQ-EVIDENCE-008 (Event-Driven, File listing)**
When a client sends `GET /evidence-binders/{id}/files`, the system shall return the list of evidence files for that binder.

### M3 — 연결 (Linking)

**REQ-EVIDENCE-009 (Event-Driven, Link creation)**
When a client sends `POST /evidence-binders/{id}/links` with a source entity (requirement/risk_control/test/ifu_section/checklist_item) and a target (file/traceability_node/external_url), the system shall create an `EvidenceLink` with the specified link_type (satisfies/verifies/supports/warns_about).

**REQ-EVIDENCE-010 (Event-Driven, Link removal)**
When a client sends `DELETE /evidence-binders/{id}/links/{link_id}` on a non-sealed binder, the system shall remove that `EvidenceLink`.

### M4 — 갭 자동 도출

**REQ-EVIDENCE-011 (State-Driven, Auto gap surfacing)**
While a binder is in `draft` status, the system shall automatically compute evidence gaps whenever the binder is retrieved or its links/files change, without requiring an explicit user trigger.

**REQ-EVIDENCE-012 (Event-Driven, Critical gap — zero evidence)**
When gap evaluation finds a high-risk control with zero linked verifying evidence, the system shall create or update an `EvidenceGap` of gap_type `unverified_high_risk` with severity `critical`.

**REQ-EVIDENCE-013 (Event-Driven, High gap — missing required evidence)**
When gap evaluation finds a ChecklistItem with `evidence_required=true` that has no linked file, the system shall create or update an `EvidenceGap` of gap_type `missing_test_report` or `missing_ifu_evidence` with severity `high`.

**REQ-EVIDENCE-013b (Event-Driven, Unlinked risk control)**
When gap evaluation finds a risk control that exists in the hazard analysis but has no `EvidenceLink` of any kind, the system shall create or update an `EvidenceGap` of gap_type `unlinked_risk_control` with severity `high` (or `critical` when the control is high-risk per REQ-EVIDENCE-012).

**REQ-EVIDENCE-014 (Event-Driven, Gap listing by severity)**
When a client sends `GET /evidence-binders/{id}/gaps`, the system shall return the binder's `EvidenceGap` records ordered or filterable by severity (critical → high → medium).

**REQ-EVIDENCE-015 (Ubiquitous, Gap analysis performance)**
The system shall complete gap analysis for a binder with up to 20 links within 3 seconds.

### M5 — 봉인 · Export · 감사

**REQ-EVIDENCE-016 (Event-Driven, Seal)**
When a client sends `POST /evidence-binders/{id}/seal`, the system shall transition the binder to `sealed` status and record `sealed_at`.

**REQ-EVIDENCE-017 (Unwanted Behavior, Sealed immutability)**
If any modification (link create/delete, file upload, or metadata change) is attempted on a `sealed` binder, then the system shall reject the operation and leave the binder unchanged.

**REQ-EVIDENCE-018 (Event-Driven, ZIP export)**
When a client sends `POST /evidence-binders/{id}/export`, the system shall produce a ZIP archive whose folder structure mirrors the linked TemplatePack's TemplateDocument hierarchy and shall include a manifest listing each evidence file with its SHA-256 hash.

**REQ-EVIDENCE-019 (Ubiquitous, Audit trail)**
The system shall log every link create and delete operation with binder_id, link_id, actor, and timestamp for audit purposes.

---

## 3. 데이터 모델

### 3.1 `evidence_binders` 테이블 (신규)

```sql
CREATE TABLE evidence_binders (
    binder_id          VARCHAR(36)  PRIMARY KEY,            -- uuid4
    product_profile_id VARCHAR(36)  NOT NULL,               -- ProductProfile FK
    pack_id            VARCHAR(36)  NULL,                   -- TemplatePack FK (nullable: standalone)
    name               VARCHAR(255) NOT NULL,
    status             VARCHAR(16)  NOT NULL DEFAULT 'draft', -- draft | sealed | archived
    created_by         VARCHAR(128) NOT NULL,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    sealed_at          TIMESTAMPTZ  NULL,
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_evbinder_profile ON evidence_binders (product_profile_id);
```

### 3.2 `evidence_links` 테이블 (신규)

```sql
CREATE TABLE evidence_links (
    link_id            VARCHAR(36)  PRIMARY KEY,
    binder_id          VARCHAR(36)  NOT NULL REFERENCES evidence_binders(binder_id),
    source_entity_type VARCHAR(24)  NOT NULL,  -- requirement|risk_control|test|ifu_section|checklist_item
    source_entity_id   VARCHAR(64)  NOT NULL,
    target_entity_type VARCHAR(24)  NOT NULL,  -- file|traceability_node|external_url
    target_ref         VARCHAR(1024) NOT NULL, -- file_id | node_id | URL
    link_type          VARCHAR(16)  NOT NULL,  -- satisfies|verifies|supports|warns_about
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_evlink_binder ON evidence_links (binder_id);
CREATE INDEX ix_evlink_source ON evidence_links (source_entity_type, source_entity_id);
```

### 3.3 `evidence_files` 테이블 (신규)

```sql
CREATE TABLE evidence_files (
    file_id           VARCHAR(36)  PRIMARY KEY,
    binder_id         VARCHAR(36)  NOT NULL REFERENCES evidence_binders(binder_id),
    original_filename VARCHAR(255) NOT NULL,
    content_type      VARCHAR(128) NOT NULL,
    size_bytes        BIGINT       NOT NULL,
    storage_ref       VARCHAR(512) NOT NULL,  -- MinIO 경로
    sha256            VARCHAR(64)  NOT NULL,  -- 무결성 검증
    uploaded_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    uploaded_by       VARCHAR(128) NOT NULL
);
CREATE INDEX ix_evfile_binder ON evidence_files (binder_id);
```

### 3.4 `evidence_gaps` 테이블 (신규)

```sql
CREATE TABLE evidence_gaps (
    gap_id      VARCHAR(36)  PRIMARY KEY,
    binder_id   VARCHAR(36)  NOT NULL REFERENCES evidence_binders(binder_id),
    entity_type VARCHAR(24)  NOT NULL,  -- risk_control|checklist_item|ifu_section
    entity_id   VARCHAR(64)  NOT NULL,
    gap_type    VARCHAR(32)  NOT NULL,  -- missing_test_report|unlinked_risk_control|missing_ifu_evidence|unverified_high_risk
    severity    VARCHAR(8)   NOT NULL,  -- critical|high|medium
    surfaced_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_evgap_binder_sev ON evidence_gaps (binder_id, severity);
```

- `evidence_gaps`는 자동 도출 결과로 upsert된다. 사용자 직접 입력 없음.
- 증거 파일 원문 바이트 컬럼은 없다(MinIO에만 저장, FR-210 준수).

---

## 4. API 엔드포인트 요약

※ 세부 요청/응답 스키마는 Run 단계 위임. WHAT만 기술.

| 메서드 | 경로 | REQ | 설명 |
|--------|------|-----|------|
| POST | `/evidence-binders` | 001, 002 | product_profile_id로 바인더 생성(pack_id 선택) |
| GET | `/evidence-binders/{id}` | 003 | 바인더 + links + gaps summary |
| POST | `/evidence-binders/{id}/files` | 004~007 | 증거 파일 업로드(MinIO) |
| GET | `/evidence-binders/{id}/files` | 008 | 업로드 파일 목록 |
| POST | `/evidence-binders/{id}/links` | 009 | 증거 link 생성 |
| DELETE | `/evidence-binders/{id}/links/{link_id}` | 010, 017 | link 삭제(sealed 거부) |
| GET | `/evidence-binders/{id}/gaps` | 014 | severity별 갭 목록 |
| POST | `/evidence-binders/{id}/seal` | 016 | 바인더 봉인(이후 불변) |
| POST | `/evidence-binders/{id}/export` | 018 | TemplateDocument 계층 ZIP export |

---

## 5. What NOT to Build (Exclusions 요약)

§0.5 참조. 최소 핵심 제외:

1. **TemplateSection/SourceReference/ChecklistItem/TraceabilityNode 정의** — 선행 SPEC(TEMPLATE/CHECKLIST/TRACEABILITY) 책임. 본 SPEC은 소비만.
2. **리스크 컨트롤/RMS/해저드 분석 데이터 모델** — 본 SPEC은 고위험 컨트롤 목록을 읽어 갭 도출만. RMS 정의는 별도.
3. **증거 파일 Cloud 전송/동기화** — 원문은 로컬 MinIO에만(FR-210). 클라우드 미전송.
4. **감사 보고서 렌더링** — 증거 데이터 모델 + ZIP export 제공. 보고서 포맷은 FR-208.
5. **LLM 일괄 link 자동 적용** — P2에서 "제안"만. 확정은 사용자 승인 필요.

---

## 6. 보안 및 컴플라이언스

- [HARD] 증거 파일 원문은 로컬 MinIO에만 저장. Cloud Control Plane 미전송 (FR-210 Data Sovereignty).
- [HARD] Sealed 바인더 불변성 — 봉인 후 mutation 전면 차단.
- [HARD] SHA-256 무결성 검증 — 업로드 시 해시 계산·기록, export manifest에 포함.
- 업로드 파일 형식/크기 화이트리스트 검증(PDF/DOCX/XLSX/CSV/PNG/JPEG, ≤50MB).
- 모든 link 연산 감사 로깅(REQ-EVIDENCE-019).
- MinIO/PostgreSQL 자격 증명은 환경 변수로만 주입.

---

## 7. 전문가 자문 권장

- **expert-backend**: FastAPI 파일 업로드(multipart), MinIO/boto3 스트리밍 업로드 + SHA-256 동시 계산, SQLAlchemy async upsert(갭 도출), ZIP 스트리밍 생성
- **expert-security**: 파일 업로드 검증(MIME 스푸핑 방지), sealed 불변성 가드, 무결성 해시 검증 경로

---

## 8. 인수 기준 연결

각 REQ는 하나 이상의 AC에 대응한다. 상세 Given/When/Then 시나리오는 `acceptance.md` 참조.

| REQ | AC |
|-----|-----|
| REQ-EVIDENCE-001 | AC-001 (바인더 생성) |
| REQ-EVIDENCE-002 | AC-001 (pack 연결) |
| REQ-EVIDENCE-003 | AC-001 (조회 + gaps summary) |
| REQ-EVIDENCE-004 | AC-002 (파일 업로드) |
| REQ-EVIDENCE-005 | AC-002 (50MB 초과 거부) |
| REQ-EVIDENCE-006 | AC-002 (형식 거부) |
| REQ-EVIDENCE-007 | AC-002 (SHA-256) |
| REQ-EVIDENCE-008 | AC-002 (파일 목록) |
| REQ-EVIDENCE-009 | AC-003 (link 생성) |
| REQ-EVIDENCE-010 | AC-003 (link 삭제) |
| REQ-EVIDENCE-011 | AC-004 (자동 갭 계산) |
| REQ-EVIDENCE-012 | AC-004 (critical: 고위험 0증거) |
| REQ-EVIDENCE-013 | AC-004 (high: 필수 증거 누락) |
| REQ-EVIDENCE-013b | AC-004 (미연결 컨트롤) |
| REQ-EVIDENCE-014 | AC-004 (severity별 목록) |
| REQ-EVIDENCE-015 | AC-005 (20-link ≤3초) |
| REQ-EVIDENCE-016 | AC-006 (seal) |
| REQ-EVIDENCE-017 | AC-006 (sealed 불변) |
| REQ-EVIDENCE-018 | AC-007 (ZIP export) |
| REQ-EVIDENCE-019 | AC-008 (감사 로깅) |
