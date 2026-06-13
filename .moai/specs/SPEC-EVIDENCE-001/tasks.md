# SPEC-EVIDENCE-001 — Task Breakdown

SPEC: Evidence Binder — 제출 패키지 증거 연결 및 갭 자동 도출
대상: `customer-runtime/`
방법론: TDD (RED-GREEN-REFACTOR)

우선순위는 Priority 라벨로 표기한다. 시간 추정 금지.

---

## P0 — Critical (Foundation)

바인더 생성 + 증거 파일 업로드 + 고위험 컨트롤 갭 도출의 최소 동작 경로.

| # | Task | 파일(제안) | 대응 REQ | AC |
|---|------|-----------|----------|-----|
| P0-1 | EvidenceBinder 테이블 마이그레이션 (status draft/sealed/archived, pack_id nullable) | `models/evidence_binder.py` [NEW] | REQ-EVIDENCE-001, 002 | AC-001 |
| P0-2 | EvidenceLink 테이블 마이그레이션 (source/target enum, link_type) | `models/evidence_link.py` [NEW] | REQ-EVIDENCE-009 | AC-003 |
| P0-3 | EvidenceFile 테이블 마이그레이션 (storage_ref, sha256) | `models/evidence_file.py` [NEW] | REQ-EVIDENCE-004, 007 | AC-002 |
| P0-4 | EvidenceGap 테이블 마이그레이션 (gap_type/severity enum) | `models/evidence_gap.py` [NEW] | REQ-EVIDENCE-012, 013 | AC-004 |
| P0-5 | 바인더 생성 서비스 (product_profile_id 검증, draft 초기화) | `services/evidence/binder.py` [NEW] | REQ-EVIDENCE-001, 002 | AC-001 |
| P0-6 | MinIO 파일 업로드 + 형식/크기 검증(≤50MB, PDF/DOCX/XLSX/CSV/PNG/JPEG) + SHA-256 | `services/evidence/file_store.py` [NEW] | REQ-EVIDENCE-004, 005, 006, 007 | AC-002 |
| P0-7 | EvidenceLink 생성 서비스 (소스→타깃 검증) | `services/evidence/linker.py` [NEW] | REQ-EVIDENCE-009 | AC-003 |
| P0-8 | 고위험 컨트롤 0-증거 → critical 갭 도출 | `services/evidence/gap_engine.py` [NEW] | REQ-EVIDENCE-012 | AC-004 |
| P0-9 | `POST /evidence-binders` + `GET /evidence-binders/{id}` (gaps summary 포함) | `routers/evidence.py`, `schemas/evidence.py` [NEW] | REQ-EVIDENCE-001, 003 | AC-001 |
| P0-10 | `POST/GET /evidence-binders/{id}/files`, `POST /links` 엔드포인트 | `routers/evidence.py` [NEW] | REQ-EVIDENCE-004, 008, 009 | AC-002, AC-003 |
| P0-11 | `GET /evidence-binders/{id}/gaps` (severity 필터) | `routers/evidence.py` [NEW] | REQ-EVIDENCE-014 | AC-004 |

---

## P1 — High (자동 surfacing 확장 · seal · export)

| # | Task | 파일(제안) | 대응 REQ | AC |
|---|------|-----------|----------|-----|
| P1-1 | ChecklistItem.evidence_required & 미연결 → high 갭(missing_test_report/missing_ifu_evidence) | `services/evidence/gap_engine.py` [MODIFY] | REQ-EVIDENCE-013 | AC-004 |
| P1-2 | 미연결 리스크 컨트롤 → unlinked_risk_control 갭 | `services/evidence/gap_engine.py` [MODIFY] | REQ-EVIDENCE-013b | AC-004 |
| P1-3 | draft 상태 자동 갭 재계산 (link/file 변경 시 트리거) | `services/evidence/gap_engine.py` [MODIFY] | REQ-EVIDENCE-011 | AC-004 |
| P1-4 | TraceabilityNode 첨부 메타데이터 연결(target_entity_type=traceability_node) | `services/evidence/linker.py` [MODIFY] | REQ-EVIDENCE-009 | AC-003 |
| P1-5 | seal 워크플로 (draft → sealed, sealed_at 기록) | `services/evidence/binder.py` [MODIFY] | REQ-EVIDENCE-016 | AC-006 |
| P1-6 | sealed 불변성 가드 (link 삭제/파일 업로드/메타 수정 거부) | `services/evidence/binder.py` [MODIFY] | REQ-EVIDENCE-010, 017 | AC-006 |
| P1-7 | `DELETE /links/{link_id}` (sealed 거부) + `POST /seal` 엔드포인트 | `routers/evidence.py` [MODIFY] | REQ-EVIDENCE-010, 016, 017 | AC-003, AC-006 |
| P1-8 | TemplateDocument 계층 ZIP export + manifest(SHA-256 포함) | `services/evidence/exporter.py` [NEW] | REQ-EVIDENCE-018 | AC-007 |
| P1-9 | `POST /evidence-binders/{id}/export` (ZIP 스트리밍) | `routers/evidence.py` [MODIFY] | REQ-EVIDENCE-018 | AC-007 |
| P1-10 | link 연산 감사 로깅 (create/delete: binder_id/link_id/actor/timestamp) | `services/evidence/linker.py` [MODIFY] | REQ-EVIDENCE-019 | AC-008 |

---

## P2 — Medium (성능 · 일괄 제안 · archive · external URL)

| # | Task | 파일(제안) | 대응 REQ | AC |
|---|------|-----------|----------|-----|
| P2-1 | 갭 분석 ≤3초 성능 보장 (20-link, 인덱스/배치 쿼리) | `services/evidence/gap_engine.py` [MODIFY] | REQ-EVIDENCE-015 | AC-005 |
| P2-2 | IFU 섹션 증거 누락 갭(missing_ifu_evidence) 세분화 | `services/evidence/gap_engine.py` [MODIFY] | REQ-EVIDENCE-013 | AC-004 |
| P2-3 | LLM 보조 일괄 link 제안 (업로드 파일 ↔ 리스크 컨트롤 매칭, 제안만) | `services/evidence/linker.py` [MODIFY] | REQ-EVIDENCE-009 | AC-003 |
| P2-4 | external_url link 타입 검증(SSRF/URL 화이트리스트) | `services/evidence/linker.py` [MODIFY] | REQ-EVIDENCE-009 | AC-003 |
| P2-5 | archive 워크플로 (sealed → archived) | `services/evidence/binder.py` [MODIFY] | REQ-EVIDENCE-016 | AC-006 |
| P2-6 | 바인더 구조 재사용(유사 기기 다음 고객 제출, P4 페르소나) | `services/evidence/binder.py` [MODIFY] | REQ-EVIDENCE-001 | AC-001 |

---

## 테스트 전략

- [HARD] TDD: 각 Task는 RED(실패 테스트) → GREEN(최소 구현) → REFACTOR.
- 단위 테스트: 형식/크기 검증 거부 케이스, SHA-256 계산, severity 분류 매트릭스, sealed 불변성 거부, link enum 조합 검증.
- 통합 테스트: CI 전용 — MinIO/PostgreSQL 의존 마커(`@pytest.mark` skip_no_docker 패턴).
- 성능 테스트: 20-link 바인더 갭 분석 ≤3초 검증(REQ-EVIDENCE-015).
- 보안 테스트: MIME 스푸핑 업로드 거부, external_url SSRF 방어.
- 커버리지 목표: 85%+.

## 의존성 순서

1. **선행 필수**: SPEC-TEMPLATE-001(TemplateSection/TemplateDocument), SPEC-CHECKLIST-001(ChecklistItem.evidence_required), SPEC-TRACEABILITY-001(TraceabilityNode) 데이터 모델 구현.
2. P0 → P1 순. P1-1(evidence_required 갭)은 SPEC-CHECKLIST-001 구현 후 활성화. P1-4(TraceabilityNode 연결)는 SPEC-TRACEABILITY-001 구현 후.
3. P1-6(불변성 가드)는 P0/P1 mutation 경로 완성 후.
4. P1-8(ZIP export)는 SPEC-TEMPLATE-001 TemplateDocument 계층 확정 후.
