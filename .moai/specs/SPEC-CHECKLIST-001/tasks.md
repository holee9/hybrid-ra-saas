# SPEC-CHECKLIST-001 — Task Breakdown

SPEC: Checklist & Gap Engine
대상: `customer-runtime/`
방법론: TDD (RED-GREEN-REFACTOR)

우선순위는 Priority 라벨로 표기한다. 시간 추정 금지.

---

## P0 — Critical (Foundation)

체크리스트 생성 + blocking 갭 도출의 최소 동작 경로.

| # | Task | 파일(제안) | 대응 REQ | AC |
|---|------|-----------|----------|-----|
| P0-1 | ChecklistItem 런타임 테이블 마이그레이션 (status/blocking/evidence_required/evidence_satisfied/reviewer_status/waiver_justification) | `models/checklist_item.py` [NEW] | REQ-CHECK-002 | AC-001 |
| P0-2 | ChecklistSnapshot 테이블 마이그레이션 (집계 필드 포함) | `models/checklist_snapshot.py` [NEW] | REQ-CHECK-001 | AC-001 |
| P0-3 | GapFinding 테이블 마이그레이션 | `models/gap_finding.py` [NEW] | REQ-CHECK-005, 006 | AC-004 |
| P0-4 | TemplatePack 섹션 → ChecklistSnapshot 생성기 (적용 섹션 순회, blocking 상속) | `services/checklist/generator.py` [NEW] | REQ-CHECK-001, 002 | AC-001 |
| P0-5 | 필수 미완료 섹션 → blocking GapFinding 도출(`gap_type=missing_content`) | `services/checklist/gap_engine.py` [NEW] | REQ-CHECK-005, 006 | AC-004 |
| P0-6 | `POST /checklists/generate` + `GET /checklists/{snapshot_id}` 엔드포인트 | `routers/checklist.py`, `schemas/checklist.py` [NEW] | REQ-CHECK-001 | AC-001 |
| P0-7 | `GET /checklists/{snapshot_id}/gaps` (severity 필터) | `routers/checklist.py` [NEW] | REQ-CHECK-008 | AC-004 |

---

## P1 — High (상태 머신 · waiver · export · 통합)

| # | Task | 파일(제안) | 대응 REQ | AC |
|---|------|-----------|----------|-----|
| P1-1 | 항목 상태 머신 검증 (`pending → in_progress → complete \| waived \| blocked`) | `services/checklist/state_machine.py` [NEW] | REQ-CHECK-003, 009 | AC-002 |
| P1-2 | `PATCH /checklists/{snapshot_id}/items/{item_id}` 상태 갱신 + 잘못된 전이 거부 | `routers/checklist.py` [NEW] | REQ-CHECK-003, 009 | AC-002 |
| P1-3 | Waiver 워크플로 (선택 항목 한정, 정당화 필수, 필수 항목 거부) | `services/checklist/waiver.py` [NEW] | REQ-CHECK-004, 012, 016 | AC-003 |
| P1-4 | `POST /checklists/{snapshot_id}/items/{item_id}/waive` 엔드포인트 | `routers/checklist.py` [NEW] | REQ-CHECK-004, 012, 016 | AC-003 |
| P1-5 | 증거 갭 도출(`evidence_required=true & evidence_satisfied=false` → `no_evidence`) | `services/checklist/gap_engine.py` [MODIFY] | REQ-CHECK-011 | AC-005 |
| P1-6 | XLSX export (TemplateDocument당 시트 1개) + ChecklistExport 기록 | `services/export/xlsx.py`, `models/checklist_export.py` [NEW] | REQ-CHECK-013 | AC-006 |
| P1-7 | `POST /checklists/{snapshot_id}/export` 엔드포인트 (xlsx) + MinIO 저장 | `routers/checklist.py` [NEW] | REQ-CHECK-013 | AC-006 |
| P1-8 | AuthoringSession 완성 상태 → 항목 상태 매핑(§3.5) | `services/checklist/authoring_sync.py` [NEW] | REQ-CHECK-010 | AC-009 |
| P1-9 | `GET /checklists/{snapshot_id}/summary` (진행률 % + blocking 갭 수) | `routers/checklist.py` [NEW] | REQ-CHECK-007 | AC-008 |

---

## P2 — Medium (불변성 · PDF · 성능 · 일괄)

| # | Task | 파일(제안) | 대응 REQ | AC |
|---|------|-----------|----------|-----|
| P2-1 | 스냅샷 불변성 가드(`final` 상태 mutation 거부) | `services/checklist/state_machine.py` [MODIFY] | REQ-CHECK-017, 018 | AC-007 |
| P2-2 | 스냅샷 확정(finalize) 경로 | `routers/checklist.py` [MODIFY] | REQ-CHECK-018 | AC-007 |
| P2-3 | PDF export (규제 포맷) | `services/export/pdf.py` [NEW] | REQ-CHECK-014 | AC-006 |
| P2-4 | summary ≤200ms 성능 보장(인덱스/집계 캐시) | `models/checklist_snapshot.py` [MODIFY] | REQ-CHECK-015 | AC-008 |
| P2-5 | 일괄 waiver 도구(admin, 선택 항목 한정) | `services/checklist/waiver.py` [MODIFY] | REQ-CHECK-004, 012 | AC-003 |
| P2-6 | TemplatePack 갱신 시 체크리스트 버전 처리(재생성 vs 기존 보존) | `services/checklist/generator.py` [MODIFY] | REQ-CHECK-001, 017 | AC-007 |

---

## 테스트 전략

- [HARD] TDD: 각 Task는 RED(실패 테스트) → GREEN(최소 구현) → REFACTOR.
- 단위 테스트: 상태 머신 전이 매트릭스, blocking/optional 분기, severity 분류, waiver 거부 케이스.
- 통합 테스트: CI 전용 — `@pytest.mark.skip_no_docker` 마커(PostgreSQL/MinIO 의존).
- 성능 테스트: summary 엔드포인트 ≤200ms 검증(REQ-CHECK-015).
- 커버리지 목표: 85%+.

## 의존성 순서

1. SPEC-TEMPLATE-001 데이터 모델(TemplateSection/ChecklistItem) 구현 선행 필수.
2. P0 → P1 순. P1-8(AuthoringSession 매핑)은 SPEC-AUTHORING-001 구현 후 활성화.
3. P2-1/P2-2(불변성)는 P0/P1 mutation 경로 완성 후.
