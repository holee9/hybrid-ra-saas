# SPEC-TEMPLATE-001 Tasks

대상: `cloud-control-plane/` (Azure backend API). 방법론: TDD (RED-GREEN-REFACTOR).
delta 마커: [NEW] 신규, [MODIFY] 기존 수정. spec.md v0.2.0 §7 구현 단계와 정렬.

## Milestone 0: Planning and Issue Setup

| ID | Task | Output | Status |
| --- | --- | --- | --- |
| T-000 | Create GitHub issue and update `issue_number` | Issue #29 recorded in `spec.md` | completed |
| T-001 | Confirm customer-runtime vs cloud-control-plane ownership | Cloud Control Plane 전용 결정(spec §0.6) | completed |
| T-002 | Validate seed pack scope with RA SME | 3 pathway × 4 device family 시드 범위 확정 | pending |

## P0 — Critical (Foundation)

데이터 모델 마이그레이션 + ProductProfile CRUD + 기본 pathway resolution.

| ID | Task | Output | REQ / AC | Status |
| --- | --- | --- | --- | --- |
| T-P0-01 | [NEW] 8개 ORM 모델 정의 | ProductProfile, RegulatoryPathway, TemplatePack, TemplateDocument, TemplateSection, ApplicabilityRule, SourceReference, ChecklistItem | — | pending |
| T-P0-02 | [MODIFY] 8개 테이블 신규 마이그레이션 (PK/FK/인덱스) | `migrations/` | — | pending |
| T-P0-03 | [NEW] ProductProfile pydantic 스키마 | `schemas/product_profile.py` | REQ-001 | pending |
| T-P0-04 | [NEW] `POST /product-profiles` 라우터+서비스 | `routers/product_profiles.py` | REQ-001 / AC-001 | pending |
| T-P0-05 | [NEW] pathway_resolver 기본(pack 메타데이터) | `services/pathway_resolver.py` | REQ-002 / AC-002 | pending |
| T-P0-06 | [NEW] `POST /template-packs/resolve` 라우터 | `routers/template_packs.py` | REQ-002 / AC-002 | pending |
| T-P0-07 | [NEW] `GET /template-packs` 목록 필터 | `routers/template_packs.py` | REQ-007 / AC-006 | pending |
| T-P0-08 | 단위 테스트 | AC-001, AC-002, AC-006 | — | pending |

## P1 — High

전체 섹션 트리 + SourceReference + 체크리스트 생성 + Korea MFDS 시드.

| ID | Task | Output | REQ / AC | Status |
| --- | --- | --- | --- | --- |
| T-P1-01 | [NEW] SourceReference + 문서/섹션 트리 조회 로직 | `services/pack_registry.py` | REQ-008 | pending |
| T-P1-02 | [NEW] `GET /template-packs/{pack_id}` 상세 | `routers/template_packs.py` | REQ-008 / AC-007 | pending |
| T-P1-03 | [NEW] checklist_generator (섹션 → ChecklistItem) | `services/checklist_generator.py` | REQ-009, 013 / AC-008 | pending |
| T-P1-04 | [NEW] `GET /template-packs/{pack_id}/checklist` 라우터 | `routers/checklists.py` | REQ-009 / AC-008 | pending |
| T-P1-05 | [NEW] Korea MFDS 4개 디바이스 패밀리 시드 | `seeds/kr_mfds_*.json` | — | pending |
| T-P1-06 | [NEW] is_internal 섹션 표기 처리 | `schemas/template_pack.py` | REQ-006 / AC-005 | pending |
| T-P1-07 | [MODIFY] CI 게이트: 규제 섹션 SourceReference 누락 검증 | `.github/workflows/` | REQ-004, 005 / AC-004 | pending |
| T-P1-08 | 단위 테스트 | AC-003, AC-004, AC-005, AC-007, AC-008 | — | pending |

## P2 — Medium

적용성 규칙 + FDA/EU MDR 시드 + 버전 관리 + admin 등록 + 정합.

| ID | Task | Output | REQ / AC | Status |
| --- | --- | --- | --- | --- |
| T-P2-01 | [NEW] 안전 표현식 평가기 (임의 코드 실행 금지) | `services/applicability.py` | REQ-010 | pending |
| T-P2-02 | [NEW] 적용성 평가 + 제외 사유 기록 | `services/checklist_generator.py` | REQ-010, 011 / AC-009 | pending |
| T-P2-03 | [NEW] FDA 510(k) 4개 패밀리 시드 | `seeds/fda_510k_*.json` | — | pending |
| T-P2-04 | [NEW] EU MDR Class IIa 4개 패밀리 시드 | `seeds/eu_mdr_iia_*.json` | — | pending |
| T-P2-05 | [NEW] pack 버전 관리 + diff + 버전 격리 | `services/pack_registry.py` | REQ-012 / AC-010 | pending |
| T-P2-06 | [NEW] `POST /template-packs` (admin) 등록 + 권한 검증 | `routers/template_packs.py` | REQ-016 / AC-012 | pending |
| T-P2-07 | [NEW] 미지원 경로 처리 (`status: unsupported`, speculative 금지) | `services/pathway_resolver.py` | REQ-015 / AC-011 | pending |
| T-P2-08 | [NEW] 파서 정합용 섹션 키 노출 | `services/pack_registry.py` | REQ-014 | pending |
| T-P2-09 | 단위 테스트 | AC-009, AC-010, AC-011, AC-012 | — | pending |

## Milestone V: Verification

| ID | Task | Output | Status |
| --- | --- | --- | --- |
| T-V-01 | 단위 테스트 전체 | pack 검증, 적용성, 체크리스트 생성 | pending |
| T-V-02 | API 테스트 | resolve / list / detail / checklist / register | pending |
| T-V-03 | 보안 검증 | tenant 격리, 임의 표현식 실행 금지 | pending |
| T-V-04 | 시드 검증 | 3 pathway × 4 device family fixture CI 통과 | pending |

## 완료 기준 (Definition of Done)

- REQ-TEMPLATE-001~016 구현 및 대응 AC 통과
- 커버리지 85%+ (TDD), ruff 클린
- 규제 섹션 SourceReference CI 게이트 통과
- TRUST 5 게이트 통과, 커밋에 `Refs #29` 푸터
