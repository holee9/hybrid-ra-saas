# SPEC-TRACEABILITY-001 — Implementation Plan

연관: [spec.md](./spec.md) · [tasks.md](./tasks.md) · [acceptance.md](./acceptance.md)

## 1. 기술 접근

| 영역 | 접근 |
|------|------|
| 그래프 저장 | PostgreSQL adjacency table (`traceability_nodes` + `traceability_edges`). `source_node_id`/`target_node_id` 인덱스로 BFS 순회. 전용 그래프 DB 미사용. |
| 노드 정규화 | `graph_builder`가 SPEC-PARSER-001 파싱 산출물과 SPEC-TEMPLATE-001 작성 문서를 단일 노드 모델로 변환. 출처 무관 동일 모델. |
| 규칙 링크 | `rule_linker` 결정론적 규칙(hazard→risk_control→test). created_by='rule'. |
| LLM 탐지 | 로컬 Ollama(llama3/mistral 등) httpx async 호출(`parser_engine/llm_fallback.py` 패턴 재사용). created_by='llm' + confidence. |
| 영향 분석 | `impact_service` BFS. visited set으로 순환 그래프 무한 루프 차단. |
| 승인 차단 | `approval_guard` 훅이 open high finding 존재 시 승인 거부. |
| 시각화 | `GET /traceability/graph`가 cytoscape/D3.js 호환 node+edge JSON 반환. |
| Export | `exporter`가 트레이서빌리티 매트릭스를 PDF/XLSX로 생성. |

## 2. 마일스톤 (우선순위 기반, 시간 추정 없음)

1. **P0 — Foundation (High)**: 노드/엣지 테이블, 규칙 기반 엣지, missing_link·orphan 결함, scan/findings API. P2 사용자 핵심 JTBD("불일치 자동 발견") 최소 충족.
2. **P1 — Intelligence (High)**: LLM semantic_mismatch + confidence, 영향 분석 API, high 차단, 예외 승인. P2·P3 사용자 완전 충족.
3. **P2 — Visualization & Export (Medium)**: 그래프 시각화 JSON, PDF/XLSX 매트릭스, 성능 검증, bulk resolve.

마일스톤 순서: P0 완료 후 P1 시작, P1 완료 후 P2 시작.

## 3. 재사용 자산

- `customer-runtime/src/app/database.py` — async SQLAlchemy engine
- `customer-runtime/src/app/models/base.py` — Base, TimestampMixin
- `customer-runtime/src/app/parser_engine/llm_fallback.py` — Ollama httpx.AsyncClient 패턴
- 기존 FastAPI 라우터 등록 패턴 (SPEC-API-001)

## 4. 리스크 및 완화

| 리스크 | 영향 | 완화 |
|--------|------|------|
| LLM semantic mismatch 오탐(false positive) 다수 | 실무자 신뢰 저하 | confidence 임계값으로 결함 노출 필터링, 인간 예외 승인 경로 제공 |
| 대규모 그래프 BFS 성능 저하 | 영향 분석 지연 | source/target 인덱스, visited set, 깊이 상한 옵션 |
| Ollama 모델 응답 비결정성 | 테스트 불안정 | 단위 테스트는 LLM 응답 모킹, 실제 호출은 CI 통합 테스트 한정 |
| adjacency 테이블 순환 그래프 | 무한 루프 | REQ-TRACE-016 visited 방문 표시 강제 |
| 10문서 60초 초과 | 성능 AC 실패 | LLM 호출 배치/병렬화, 규칙 링크와 LLM 탐지 단계 분리 |

## 5. 전문가 자문

- expert-backend: BFS 쿼리 최적화, async 그래프 모델, Ollama 비동기 호출
- expert-security: 예외 승인 감사 추적, 로컬 데이터 격리 검증
