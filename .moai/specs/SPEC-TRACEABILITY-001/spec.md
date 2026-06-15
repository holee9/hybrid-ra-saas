---
id: SPEC-TRACEABILITY-001
version: 0.1.0
status: planned
created_at: 2026-06-13
updated: 2026-06-13
author: drake.lee
priority: high
issue_number: 34
labels: ["spec", "traceability", "guardrail", "impact-analysis"]
---

# SPEC-TRACEABILITY-001: Cross-Document Consistency Guardrail & Traceability Graph

## HISTORY

- **v0.1.0** (2026-06-13): 최초 작성. PRD FR-203(Consistency Guardrail)·FR-205(Impact Analyzer), MRD REQ-MRD-104(Cross-Document Traceability)·REQ-MRD-103(Regulatory Impact Analysis)를 충족하는 교차 문서 정합성 가드레일 및 트레이서빌리티 그래프 SPEC 확정. P2(RA/QA 실무자)·P3(품질 관리자) 핵심 JTBD 충족. ingestion-first(SPEC-PARSER-001 산출물)와 template-first(SPEC-TEMPLATE-001) 양쪽 문서 흐름 모두 지원. PostgreSQL adjacency table 패턴(전용 그래프 DB 미사용), 로컬 Ollama LLM 의미 불일치 탐지, 전량 로컬 Docker 처리(클라우드 미전송). EARS 요구사항 REQ-TRACE-001~018, 데이터 모델 4엔티티(TraceabilityNode/Edge/ConsistencyFinding/ImpactAnalysis), API 5엔드포인트, P0/P1/P2 단계 정의.

---

## 0. 범위 및 의존성

### 0.1 SPEC 개요

| 항목 | 내용 |
|------|------|
| SPEC-ID | SPEC-TRACEABILITY-001 |
| 제목 | Cross-Document Consistency Guardrail & Traceability Graph |
| 상태 | planned |
| 대상 디렉터리 | `customer-runtime/` (Customer Local Runtime, Python FastAPI) |
| 분석 기준 | PRD FR-203/FR-205, MRD REQ-MRD-103/REQ-MRD-104, SPEC-PARSER-001(파싱 산출물), SPEC-TEMPLATE-001(템플릿 작성 문서) |
| 라이프사이클 | spec-anchored (애플리케이션 코드와 함께 유지) |
| 개발 방법론 | TDD (RED-GREEN-REFACTOR) |
| Priority | high |

### 0.2 목적 및 사용자 가치 (WHY)

본 SPEC은 의료기기 규제 문서 집합(RMS·SRS·IFU·test evidence) 사이의 정합성 결함을 자동으로 발견하고, 문서 변경의 다운스트림 영향을 자동으로 분석한다.

- **P2 — RA/QA 실무자(주 사용자)**: 핵심 JTBD는 "문서 간 불일치를 자동으로 찾는 것"이다. 현재 FR-203/FR-205는 PRD에 명시되어 있으나 SPEC·GitHub Issue·구현이 전무하여 이 핵심 니즈가 미충족 상태다. 본 SPEC이 이를 해소한다.
- **P3 — 품질 관리자**: 섹션 변경 시 영향 분석을 필요로 한다 — "RMS 4.2 조항을 바꾸면 어떤 다운스트림 문서가 영향을 받는가?"

### 0.3 이 SPEC이 다루는 것 (In Scope)

- **트레이서빌리티 그래프 저장**: `traceability_nodes` / `traceability_edges` 신규 테이블 (PostgreSQL adjacency table 패턴)
- **규칙 기반 링크 탐지**: RMS hazard → risk control → test verification 체인을 규칙 쿼리로 자동 생성
- **LLM 의미 불일치 탐지**: 로컬 Ollama를 사용해 orphan requirement·불일치 서술·semantic mismatch 탐지
- **정합성 결함 관리**: `consistency_findings` 신규 테이블, 결함 목록·해결·예외 승인 워크플로
- **High 결함 차단**: open high finding이 있는 문서 집합은 승인 불가
- **영향 분석**: 변경 노드 기준 너비 우선(BFS) 다운스트림 전파, `impact_analyses` 신규 테이블
- **인간 오버라이드**: justification 텍스트와 함께 예외 승인
- **그래프 시각화 엔드포인트**: D3.js / cytoscape 호환 JSON(node+edge)
- **트레이서빌리티 매트릭스 export**: PDF / XLSX
- **양 문서 흐름 지원**: ingestion-first(upload→parse→correction, SPEC-PARSER-001) 및 template-first(SPEC-TEMPLATE-001) 모두 동일 그래프 모델로 처리
- **API 5엔드포인트**: `POST /traceability/scan`, `GET /traceability/findings`, `GET /traceability/graph`, `POST /traceability/findings/{id}/resolve`, `POST /traceability/impact`

### 0.4 이 SPEC이 다루지 않는 것 (Exclusions — What NOT to Build)

[HARD] 아래 항목은 SPEC-TRACEABILITY-001 구현 범위에서 명시적으로 제외한다. spec.md는 WHAT/WHY만 다루며 구현 세부(함수명/클래스 구조/세부 API 스키마)는 Run 단계로 위임한다.

| 제외 항목 | 사유 | 담당 |
|-----------|------|------|
| 규제 문서 15필드 파싱/추출 | 트레이서빌리티는 이미 파싱된 문서 노드를 소비. 파싱은 별도 엔진 | SPEC-PARSER-001 (완료) |
| 문서 작성/템플릿 렌더링 | 트레이서빌리티는 작성 결과 문서를 그래프화. 작성은 별도 도메인 | SPEC-TEMPLATE-001 |
| 클라우드 전송 분석 | 모든 처리는 고객 로컬 Docker 내에서만 수행. 고객 문서는 클라우드 미전송 | 본 SPEC(로컬 전용) |
| 전용 그래프 DB(Neo4j 등) 도입 | PostgreSQL adjacency table 패턴으로 충분. 인프라 단순성 유지 | 비범위 |
| 규제 변경 알림/이메일 발송 | 알림 도메인 분리 | 미래 SPEC |
| 실시간 협업 편집(동시 다중 사용자) | 결함 해결은 단일 사용자 작업 단위. CRDT/OT 미적용 | 비범위 |
| ra-med-bot / Vercel 연동 | 본 레포 범위 외 | 비범위 |
| LLM 미세조정(fine-tuning) | 로컬 Ollama 기본 모델(llama3/mistral 등) 프롬프트 기반 사용만 | 비범위 |

### 0.5 연관 SPEC 및 의존성

- **선행 의존(완료)**: SPEC-PARSER-001 — 15필드 추출 엔진. 트레이서빌리티 노드는 이 엔진이 파싱한 문서·섹션에서 생성된다.
- **연관(독립)**: SPEC-TEMPLATE-001 — template-first 작성 문서도 동일 그래프 모델로 노드화된다. 본 SPEC은 template-first pivot에 **독립적**이며 양 흐름 모두 지원한다.
- **연관(독립)**: SPEC-API-001 — 기존 FastAPI 라우터 패턴 재사용.
- **연관(독립)**: SPEC-UI-002 — 검토 큐 화면. 그래프 시각화·결함 목록 UI는 향후 이 화면 계열에서 소비 가능(본 SPEC은 API까지).
- **재사용 패턴**: `customer-runtime/src/app/services/`(서비스 계층), `database.py`(async engine), `parser_engine/llm_fallback.py`(httpx.AsyncClient로 Ollama 호출), `models/base.py`(Base, TimestampMixin).

### 0.6 아키텍처 원칙 (불변 제약)

[HARD] 모든 처리(규칙 쿼리, LLM 호출, 그래프 저장)는 고객 로컬 Docker 내에서만 수행한다. 고객 문서 내용은 클라우드 Control Plane으로 전송하지 않는다 (FR-210 Data Sovereignty 준수).
[HARD] LLM 호출은 로컬 Ollama만 사용한다(model: llama3, mistral, 또는 동급). 외부 LLM API를 호출하지 않는다.
[HARD] 그래프 저장은 PostgreSQL adjacency table 패턴으로 구현한다(전용 그래프 DB 미사용).
[HARD] open high finding이 존재하는 문서 집합은 승인할 수 없다(해결 또는 예외 승인 필수).

---

## 1. 아키텍처

※ 본 절의 디렉터리 구조, 모듈 파일명, 클래스명, 구현 세부는 비규범적 설계 제안이며, Run 단계에서 변경될 수 있습니다. (Non-normative design note)

### 1.1 디렉터리 구조 (제안, Non-normative)

```
customer-runtime/src/app/
├── models/
│   ├── traceability_node.py     # [NEW] TraceabilityNode ORM
│   ├── traceability_edge.py     # [NEW] TraceabilityEdge ORM
│   ├── consistency_finding.py   # [NEW] ConsistencyFinding ORM
│   └── impact_analysis.py       # [NEW] ImpactAnalysis ORM
├── schemas/
│   └── traceability.py          # [NEW] Pydantic 요청/응답 모델
├── routers/
│   └── traceability.py          # [NEW] /traceability/* 라우터
├── services/
│   └── traceability/
│       ├── graph_builder.py     # [NEW] 파싱/템플릿 문서 → 노드/엣지 추출
│       ├── rule_linker.py       # [NEW] 규칙 기반 엣지 생성(hazard→control→test)
│       ├── llm_detector.py      # [NEW] Ollama 기반 semantic mismatch 탐지
│       ├── finding_service.py   # [NEW] 결함 생성·해결·예외 승인
│       ├── impact_service.py    # [NEW] BFS 다운스트림 영향 전파
│       └── exporter.py          # [NEW] PDF/XLSX 매트릭스 export
└── core/
    └── approval_guard.py        # [NEW] high finding 승인 차단 훅
```

### 1.2 모듈 설계 원칙

- `graph_builder.py`는 SPEC-PARSER-001 파싱 산출물과 SPEC-TEMPLATE-001 작성 문서를 **단일 노드 모델**로 정규화한다. 입력 출처(ingestion vs template)는 그래프 모델에 영향을 주지 않는다.
- `rule_linker.py`는 결정론적 규칙으로 엣지를 생성하며 `created_by='rule'`로 표기한다. LLM 미사용.
- `llm_detector.py`는 Ollama를 `parser_engine/llm_fallback.py`의 httpx.AsyncClient 패턴으로 호출하고, 도출 엣지/결함에 confidence 점수를 부여하며 `created_by='llm'`로 표기한다.
- `impact_service.py`는 트리거 노드에서 출발하는 BFS 순회로 다운스트림 노드를 수집한다(순환 그래프 방문 표시로 무한 루프 방지).

### 1.3 처리 흐름

```
POST /traceability/scan
  → graph_builder: 파싱/템플릿 문서 → 노드 upsert (content_hash 변경 시만 갱신)
  → rule_linker: hazard→control→test 규칙 엣지 생성 (created_by='rule')
  → llm_detector: orphan / semantic mismatch 탐지 → finding 생성 (created_by='llm', confidence)
  → consistency_findings INSERT
  → scan_id 반환

문서 승인 시도
  → approval_guard: open high finding 존재 검사
  → 존재 시 승인 차단 (해결 또는 예외 승인 요구)

POST /traceability/impact { node_id, change_summary }
  → impact_service: BFS 다운스트림 순회
  → impact_analyses INSERT (affected_nodes[] + reason)
```

---

## 2. 데이터 모델

PostgreSQL adjacency table 패턴. 전용 그래프 DB 미사용.

### 2.1 `traceability_nodes` (신규)

```sql
CREATE TABLE traceability_nodes (
    node_id      VARCHAR(36)  PRIMARY KEY,            -- uuid4
    document_id  VARCHAR(36)  NOT NULL,               -- 출처 문서(파싱 또는 템플릿)
    section_id   VARCHAR(64)  NULL,                   -- 섹션 식별자(nullable)
    node_type    VARCHAR(16)  NOT NULL,               -- requirement|risk_control|test|ifu_warning|hazard
    content_hash VARCHAR(64)  NOT NULL,               -- SHA-256, 변경 감지용
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_tracenode_document ON traceability_nodes (document_id);
CREATE INDEX ix_tracenode_type ON traceability_nodes (node_type);
```

### 2.2 `traceability_edges` (신규)

```sql
CREATE TABLE traceability_edges (
    edge_id        VARCHAR(36)  PRIMARY KEY,          -- uuid4
    source_node_id VARCHAR(36)  NOT NULL REFERENCES traceability_nodes(node_id),
    target_node_id VARCHAR(36)  NOT NULL REFERENCES traceability_nodes(node_id),
    edge_type      VARCHAR(16)  NOT NULL,             -- satisfies|mitigates|verifies|warns_about|references
    confidence     NUMERIC(4,3) NULL,                 -- 0.000~1.000 (LLM 도출 시), rule 도출 시 NULL/1.000
    created_by     VARCHAR(8)   NOT NULL,             -- rule|llm|human
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_traceedge_source ON traceability_edges (source_node_id);
CREATE INDEX ix_traceedge_target ON traceability_edges (target_node_id);
```

- adjacency table: BFS 순회는 `source_node_id`/`target_node_id` 인덱스로 수행한다.

### 2.3 `consistency_findings` (신규)

```sql
CREATE TABLE consistency_findings (
    finding_id     VARCHAR(36)  PRIMARY KEY,          -- uuid4
    finding_type   VARCHAR(20)  NOT NULL,             -- missing_link|broken_link|semantic_mismatch|orphan_node
    severity       VARCHAR(8)   NOT NULL,             -- high|medium|low
    source_node_id VARCHAR(36)  NOT NULL REFERENCES traceability_nodes(node_id),
    target_node_id VARCHAR(36)  NULL  REFERENCES traceability_nodes(node_id),
    description    TEXT         NOT NULL,
    status         VARCHAR(20)  NOT NULL DEFAULT 'open', -- open|resolved|exception_approved
    justification  TEXT         NULL,                 -- 예외 승인 시 필수
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_finding_status_severity ON consistency_findings (status, severity);
```

### 2.4 `impact_analyses` (신규)

```sql
CREATE TABLE impact_analyses (
    analysis_id          VARCHAR(36) PRIMARY KEY,     -- uuid4
    trigger_node_id      VARCHAR(36) NOT NULL REFERENCES traceability_nodes(node_id),
    trigger_change_summary TEXT      NOT NULL,
    affected_nodes       JSONB       NOT NULL,        -- [{node_id, reason}, ...]
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_impact_trigger ON impact_analyses (trigger_node_id);
```

---

## 3. API 엔드포인트 (계약 개요, 세부 스키마는 Run 위임)

| 메서드 | 경로 | 목적 |
|--------|------|------|
| POST | `/traceability/scan` | 업로드/작성 문서 전체 스캔 트리거, `scan_id` 반환 |
| GET | `/traceability/findings` | status/severity 필터로 ConsistencyFinding 목록 |
| GET | `/traceability/graph` | 시각화용 node+edge 그래프(D3.js/cytoscape 호환 JSON) |
| POST | `/traceability/findings/{id}/resolve` | 결함 해결 또는 예외 승인(justification) |
| POST | `/traceability/impact` | node_id + change summary → affected nodes 반환 |

---

## 4. EARS 요구사항

요구사항은 6개 모듈로 그룹화한다: M1(노드·엣지 그래프), M2(규칙 기반 링크), M3(LLM 의미 탐지), M4(결함·차단·오버라이드), M5(영향 분석), M6(API·시각화·성능).

### M1 — 노드 및 엣지 그래프

**REQ-TRACE-001 (Event-Driven, Node extraction)**
When a traceability scan runs, the system shall extract traceability nodes from each parsed or template-authored document, assigning each node a node_type of one of: requirement, risk_control, test, ifu_warning, hazard.

**REQ-TRACE-002 (State-Driven, Incremental node update)**
While a node's source content_hash is unchanged since the last scan, the system shall not modify that node's existing graph record.

**REQ-TRACE-003 (Ubiquitous, Unified model)**
The system shall represent ingestion-first documents and template-first documents using the same traceability node and edge model, independent of document origin.

### M2 — 규칙 기반 링크

**REQ-TRACE-004 (Event-Driven, Rule-based chain detection)**
When a traceability scan runs, the system shall create rule-based edges for the RMS hazard → risk_control → test verification chain, marking each created edge with created_by = 'rule'.

**REQ-TRACE-005 (Event-Driven, Missing link finding)**
When a rule expects an edge between two nodes but no such edge exists, the system shall create a ConsistencyFinding of finding_type = 'missing_link'.

**REQ-TRACE-006 (Event-Driven, Orphan node detection)**
When a node has zero incoming and zero outgoing edges after a scan, the system shall create a ConsistencyFinding of finding_type = 'orphan_node'.

### M3 — LLM 의미 탐지

**REQ-TRACE-007 (Event-Driven, Semantic mismatch detection)**
When a traceability scan runs, the system shall use the local Ollama LLM to detect semantic mismatches between linked nodes and create a ConsistencyFinding of finding_type = 'semantic_mismatch' for each detected inconsistency.

**REQ-TRACE-008 (Ubiquitous, Local-only LLM)**
The system shall perform all LLM inference using a local Ollama model and shall NOT send document content to any external LLM service or the Cloud Control Plane.

**REQ-TRACE-009 (Ubiquitous, Confidence scoring)**
The system shall assign a confidence score between 0.000 and 1.000 to every LLM-derived edge and every LLM-derived finding.

### M4 — 결함, 차단, 오버라이드

**REQ-TRACE-010 (State-Driven, High finding approval block)**
While at least one ConsistencyFinding with severity = 'high' and status = 'open' exists for a document set, the system shall not allow that document set to be approved.

**REQ-TRACE-011 (Event-Driven, Resolve finding)**
When a user resolves a finding via `POST /traceability/findings/{id}/resolve` with resolution intent 'resolved', the system shall set that finding's status to 'resolved'.

**REQ-TRACE-012 (Event-Driven, Exception approval)**
When a user exception-approves a finding, the system shall set that finding's status to 'exception_approved' and shall record the supplied justification text.

**REQ-TRACE-013 (Unwanted Behavior, Exception without justification)**
If an exception approval request omits justification text, then the system shall reject the request and leave the finding's status unchanged.

### M5 — 영향 분석

**REQ-TRACE-014 (Event-Driven, Impact propagation)**
When a client sends `POST /traceability/impact` with a node_id and a change summary, the system shall perform a breadth-first traversal of downstream edges from that node and return the set of affected nodes, each with a reason.

**REQ-TRACE-015 (Event-Driven, Impact persistence)**
When an impact analysis completes, the system shall persist an ImpactAnalysis record containing the trigger node, the change summary, and the affected nodes.

**REQ-TRACE-016 (Unwanted Behavior, Cyclic graph safety)**
If the traceability graph contains a cycle, then the impact traversal shall visit each node at most once and terminate without infinite looping.

### M6 — API, 시각화, 성능

**REQ-TRACE-017 (Event-Driven, Graph visualization)**
When a client sends `GET /traceability/graph`, the API shall return a JSON payload containing nodes and edges in a format consumable by D3.js or cytoscape.

**REQ-TRACE-018 (State-Driven, Scan performance)**
While scanning a document set of up to 10 documents, the system shall complete the full scan within 60 seconds.

---

## 5. What NOT to Build (Exclusions 요약)

§0.4 참조. 최소 4개 핵심 제외:

1. **문서 파싱/추출** — SPEC-PARSER-001 책임. 트레이서빌리티는 파싱된 노드를 소비.
2. **문서 작성/템플릿 렌더링** — SPEC-TEMPLATE-001 책임. 트레이서빌리티는 작성 결과를 그래프화.
3. **클라우드 전송 분석** — 전량 로컬 Docker 처리. 고객 문서는 클라우드 미전송.
4. **전용 그래프 DB** — PostgreSQL adjacency table 패턴으로 충분. Neo4j 등 미도입.

---

## 6. 보안 및 컴플라이언스

- [HARD] 고객 문서 내용은 로컬에서만 처리하며 클라우드로 전송하지 않는다(FR-210 Data Sovereignty).
- [HARD] LLM 추론은 로컬 Ollama만 사용한다(외부 API 호출 금지).
- [HARD] 예외 승인은 justification 텍스트 없이는 불가하다(감사 추적 보장).
- DB 자격 증명은 환경 변수로만 주입한다.
- 모든 코드 주석은 영어로 작성한다.

---

## 7. 전문가 자문 권장

- **expert-backend**: PostgreSQL adjacency table BFS 순회 쿼리 최적화, SQLAlchemy async 그래프 모델, Ollama httpx 비동기 호출, FastAPI 라우터 설계
- **expert-security**: 예외 승인 감사 추적, justification 무결성, 로컬 데이터 격리 검증

---

## 8. 인수 기준 연결

각 REQ는 하나 이상의 AC에 대응한다. 상세 Given/When/Then 시나리오는 `acceptance.md` 참조.

| REQ | AC |
|-----|-----|
| REQ-TRACE-001 | AC-001 (노드 추출) |
| REQ-TRACE-002 | AC-002 (증분 갱신) |
| REQ-TRACE-003 | AC-001 (양 흐름 동일 모델) |
| REQ-TRACE-004 | AC-003 (규칙 체인 엣지) |
| REQ-TRACE-005 | AC-004 (missing_link) |
| REQ-TRACE-006 | AC-005 (orphan_node) |
| REQ-TRACE-007 | AC-006 (semantic_mismatch) |
| REQ-TRACE-008 | AC-006 (로컬 전용 검증) |
| REQ-TRACE-009 | AC-007 (confidence) |
| REQ-TRACE-010 | AC-008 (high 차단) |
| REQ-TRACE-011 | AC-009 (resolve) |
| REQ-TRACE-012 | AC-010 (exception 승인) |
| REQ-TRACE-013 | AC-010 (justification 누락 거부) |
| REQ-TRACE-014 | AC-011 (영향 전파) |
| REQ-TRACE-015 | AC-011 (영향 영속화) |
| REQ-TRACE-016 | AC-012 (순환 안전) |
| REQ-TRACE-017 | AC-013 (그래프 시각화) |
| REQ-TRACE-018 | AC-014 (성능 60초) |
