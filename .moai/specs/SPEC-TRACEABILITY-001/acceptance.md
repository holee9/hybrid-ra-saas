# SPEC-TRACEABILITY-001 — Acceptance Criteria

연관: [spec.md](./spec.md) · [plan.md](./plan.md) · [tasks.md](./tasks.md)
형식: Given-When-Then. 통합 테스트는 CI 전용(`skip_no_docker`).

---

## AC-001 — 노드 추출 (양 흐름 동일 모델) — REQ-TRACE-001/003
- **Given** 파싱된 문서(ingestion-first)와 템플릿 작성 문서(template-first)가 존재할 때
- **When** `POST /traceability/scan`을 호출하면
- **Then** 두 출처 모두에서 requirement/risk_control/test/ifu_warning/hazard 타입의 노드가 동일한 노드 모델로 생성되고 scan_id가 반환된다.

## AC-002 — 증분 갱신 — REQ-TRACE-002
- **Given** content_hash가 직전 스캔과 동일한 노드가 있을 때
- **When** 재스캔하면
- **Then** 해당 노드의 기존 그래프 레코드가 변경되지 않는다.

## AC-003 — 규칙 기반 체인 엣지 — REQ-TRACE-004
- **Given** hazard·risk_control·test 노드가 존재할 때
- **When** 스캔하면
- **Then** hazard→risk_control→test 체인 엣지가 created_by='rule'로 생성된다.

## AC-004 — missing_link 결함 — REQ-TRACE-005
- **Given** 규칙이 두 노드 간 엣지를 기대하나 해당 엣지가 없을 때
- **When** 스캔하면
- **Then** finding_type='missing_link' 결함이 생성된다.

## AC-005 — orphan_node 결함 — REQ-TRACE-006
- **Given** 들어오고 나가는 엣지가 모두 0인 노드가 있을 때
- **When** 스캔하면
- **Then** finding_type='orphan_node' 결함이 생성된다.

## AC-006 — semantic_mismatch 탐지 (로컬 전용) — REQ-TRACE-007/008
- **Given** 연결된 노드 간 서술이 의미적으로 불일치할 때
- **When** 스캔하면
- **Then** 로컬 Ollama가 이를 탐지하여 finding_type='semantic_mismatch' 결함을 생성하고, 어떤 문서 내용도 외부 서비스나 Cloud Control Plane으로 전송되지 않는다.

## AC-007 — confidence 점수 — REQ-TRACE-009
- **Given** LLM이 엣지 또는 결함을 도출했을 때
- **When** 해당 레코드를 조회하면
- **Then** 0.000~1.000 범위의 confidence 값이 부여되어 있다.

## AC-008 — High 결함 승인 차단 — REQ-TRACE-010
- **Given** severity='high' status='open' 결함이 1건 이상 존재하는 문서 집합에서
- **When** 해당 문서 집합 승인을 시도하면
- **Then** 승인이 차단된다.

## AC-009 — 결함 해결 — REQ-TRACE-011
- **Given** open 상태 결함이 있을 때
- **When** `POST /traceability/findings/{id}/resolve`를 resolved 의도로 호출하면
- **Then** 결함 status가 'resolved'로 변경된다.

## AC-010 — 예외 승인 / justification 강제 — REQ-TRACE-012/013
- **Given** open 결함이 있을 때
- **When** justification 텍스트와 함께 예외 승인하면 status가 'exception_approved'로 변경되고 justification이 기록된다.
- **And When** justification 없이 예외 승인을 요청하면 요청이 거부되고 결함 status는 변경되지 않는다.

## AC-011 — 영향 전파 및 영속화 — REQ-TRACE-014/015
- **Given** 다운스트림 엣지를 가진 노드가 있을 때
- **When** `POST /traceability/impact`에 node_id와 change summary를 보내면
- **Then** BFS로 수집된 affected nodes(각 reason 포함)가 반환되고, ImpactAnalysis 레코드가 영속화된다.

## AC-012 — 순환 그래프 안전 — REQ-TRACE-016
- **Given** 그래프에 순환이 존재할 때
- **When** 영향 분석을 수행하면
- **Then** 각 노드는 최대 1회 방문되며 무한 루프 없이 종료된다.

## AC-013 — 그래프 시각화 — REQ-TRACE-017
- **Given** 노드와 엣지가 존재할 때
- **When** `GET /traceability/graph`를 호출하면
- **Then** D3.js 또는 cytoscape에서 소비 가능한 nodes+edges JSON이 반환된다.

## AC-014 — 스캔 성능 — REQ-TRACE-018
- **Given** 최대 10개 문서로 구성된 문서 집합에서
- **When** 전체 스캔을 수행하면
- **Then** 60초 이내에 완료된다.

---

## Definition of Done

- [ ] REQ-TRACE-001~018 전부 구현 및 AC-001~014 통과
- [ ] 4개 신규 테이블(nodes/edges/findings/impact_analyses) 마이그레이션 적용
- [ ] 5개 API 엔드포인트 동작
- [ ] 단위 테스트 커버리지 ≥85%, 통합 테스트 CI 통과
- [ ] LLM 호출 전량 로컬 Ollama (외부 전송 0건 검증)
- [ ] ruff 클린, 모든 코드 주석 영어
- [ ] open high finding 승인 차단 동작 확인
