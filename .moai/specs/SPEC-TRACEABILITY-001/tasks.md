# SPEC-TRACEABILITY-001 — Task Breakdown (P0/P1/P2)

연관: [spec.md](./spec.md) · [plan.md](./plan.md) · [acceptance.md](./acceptance.md)
방법론: TDD (RED-GREEN-REFACTOR). 통합 테스트는 CI 전용(`skip_no_docker` 마커).

---

## P0 — Foundation: 그래프 저장 + 규칙 링크 + 결함 목록

목표: 파싱된 문서에서 노드/엣지를 추출하고, 규칙 기반 엣지를 생성하며, 기본 결함 목록 API를 제공한다.

| # | 작업 | 대상(제안) | REQ | AC |
|---|------|-----------|-----|-----|
| P0-1 | `traceability_nodes`/`traceability_edges` 테이블 + ORM 모델 + 마이그레이션 | `models/traceability_node.py`, `models/traceability_edge.py` [NEW] | REQ-TRACE-001/002 | AC-001/002 |
| P0-2 | `consistency_findings` 테이블 + ORM 모델 + 마이그레이션 | `models/consistency_finding.py` [NEW] | REQ-TRACE-005/006 | AC-004/005 |
| P0-3 | graph_builder: 파싱/템플릿 문서 → 노드 upsert(content_hash 증분) | `services/traceability/graph_builder.py` [NEW] | REQ-TRACE-001/002/003 | AC-001/002 |
| P0-4 | rule_linker: hazard→risk_control→test 규칙 엣지 생성(created_by='rule') | `services/traceability/rule_linker.py` [NEW] | REQ-TRACE-004 | AC-003 |
| P0-5 | missing_link / orphan_node 결함 생성 | `services/traceability/finding_service.py` [NEW] | REQ-TRACE-005/006 | AC-004/005 |
| P0-6 | `POST /traceability/scan` (스캔 트리거, scan_id 반환) | `routers/traceability.py`, `schemas/traceability.py` [NEW] | REQ-TRACE-001/004 | AC-001/003 |
| P0-7 | `GET /traceability/findings` (status/severity 필터) | `routers/traceability.py` [NEW] | REQ-TRACE-005/006 | AC-004/005 |

P0 완료 기준: 파싱 문서 집합 스캔 시 노드/규칙 엣지/missing_link·orphan 결함 생성, findings API 동작. 커버리지 ≥85%.

---

## P1 — Intelligence: LLM 탐지 + 영향 분석 + High 차단

목표: 로컬 Ollama로 의미 불일치를 탐지하고, 영향 분석 API와 승인 워크플로 차단을 추가한다.

| # | 작업 | 대상(제안) | REQ | AC |
|---|------|-----------|-----|-----|
| P1-1 | llm_detector: Ollama 호출로 semantic_mismatch 탐지(httpx async) | `services/traceability/llm_detector.py` [NEW] | REQ-TRACE-007/008 | AC-006 |
| P1-2 | LLM 도출 엣지/결함 confidence 점수 부여 | `services/traceability/llm_detector.py` [NEW] | REQ-TRACE-009 | AC-007 |
| P1-3 | `impact_analyses` 테이블 + ORM + BFS 다운스트림 순회(순환 안전) | `models/impact_analysis.py`, `services/traceability/impact_service.py` [NEW] | REQ-TRACE-014/015/016 | AC-011/012 |
| P1-4 | `POST /traceability/impact` 엔드포인트 | `routers/traceability.py` [NEW] | REQ-TRACE-014 | AC-011 |
| P1-5 | finding resolve / exception 승인(justification 필수) | `services/traceability/finding_service.py` [MODIFY] | REQ-TRACE-011/012/013 | AC-009/010 |
| P1-6 | `POST /traceability/findings/{id}/resolve` 엔드포인트 | `routers/traceability.py` [MODIFY] | REQ-TRACE-011/012/013 | AC-009/010 |
| P1-7 | approval_guard: open high finding 시 승인 차단 훅 | `core/approval_guard.py` [NEW] | REQ-TRACE-010 | AC-008 |

P1 완료 기준: LLM semantic_mismatch 탐지+confidence, 영향 분석 영속화, high 차단, 예외 승인 justification 강제. 커버리지 ≥85%.

---

## P2 — Visualization & Export

목표: 그래프 시각화 엔드포인트와 트레이서빌리티 매트릭스 export, 성능 검증.

| # | 작업 | 대상(제안) | REQ | AC |
|---|------|-----------|-----|-----|
| P2-1 | `GET /traceability/graph` (D3.js/cytoscape 호환 JSON) | `routers/traceability.py` [MODIFY] | REQ-TRACE-017 | AC-013 |
| P2-2 | exporter: PDF/XLSX 트레이서빌리티 매트릭스 | `services/traceability/exporter.py` [NEW] | REQ-TRACE-017 (확장) | AC-013 |
| P2-3 | 10문서 스캔 ≤60초 성능 테스트 | `tests/` [NEW] | REQ-TRACE-018 | AC-014 |
| P2-4 | bulk resolution(다중 결함 일괄 해결) | `services/traceability/finding_service.py` [MODIFY] | REQ-TRACE-011 (확장) | AC-009 |

P2 완료 기준: 그래프 JSON 시각화 가능, PDF/XLSX export, 10문서 60초 이내, bulk resolve 동작.

---

## 통합 테스트 정책

- 백엔드 통합 테스트는 `skip_no_docker` 마커로 CI 전용 실행(로컬 Docker 비의존).
- Ollama 호출 단위 테스트는 LLM 응답 모킹. 실제 Ollama 호출은 CI 통합 테스트에서만.
