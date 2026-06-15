---
id: SPEC-TEMPLATE-001
version: 0.2.0
status: planned
created_at: 2026-06-13
updated: 2026-06-13
author: drake.lee
priority: critical
issue_number: 29
labels: ["spec", "regulatory", "templates", "checklist", "authoring", "template-first"]
---

# SPEC-TEMPLATE-001: Regulatory Template Pack Registry

## HISTORY

- **v0.2.0** (2026-06-13): plan 보강 — Template-first 전환의 **기초(Foundation) SPEC**으로 위상 확정. 8개 엔티티 데이터 모델 전체 필드 정의, EARS 요구사항 REQ-TEMPLATE-001~016 확장(이전 010 → 016), API 6개 엔드포인트(method/path/request/response/error code) 명세, AC-001~012 번호화, P0/P1/P2 산출물 정의, 트레이서빌리티 매트릭스(REQ → FR/MRD/AC) 추가. MVP 시드 데이터를 Korea MFDS / FDA 510(k) / EU MDR Class IIa 4개 디바이스 패밀리로 구체화(이전 FDA 510(k) 단일 → 3개 pathway). 신규 `cloud-control-plane/` API 영역에 데이터 모델 마이그레이션 + ProductProfile CRUD + pathway resolution 구현 범위 확정. status: draft → planned.
- **v0.1.0** (2026-06-13): Template-first strategy audit 결과를 반영한 초안 작성. 기존 ingestion-first 흐름을 유지하되, 제품 시작점을 pathway-specific template pack과 checklist로 재정렬한다.

---

## 0. 범위 및 의존성

### 0.1 SPEC 개요

| 항목 | 내용 |
|------|------|
| SPEC-ID | SPEC-TEMPLATE-001 |
| 제목 | Regulatory Template Pack Registry |
| 상태 | planned |
| 대상 디렉터리 | `cloud-control-plane/` (Azure backend API — 데이터 모델 + ProductProfile/TemplatePack/Checklist 도메인) |
| 분석 기준 | PRD §15 데이터 모델, FR-211(Pathway Resolver), FR-212(Template Pack Registry), MRD 사용자 스토리, Template-first strategy audit |
| 라이프사이클 | spec-anchored (애플리케이션 코드와 함께 유지) |
| 개발 방법론 | TDD (RED-GREEN-REFACTOR) |
| Priority | critical |
| 위상 | **Template-first 전환의 Foundation SPEC** — authoring/checklist/evidence 후속 SPEC이 본 SPEC의 데이터 모델에 의존 |

### 0.2 전략적 위상 (왜 critical인가)

제품은 ingestion-first(기존 문서 업로드 → 파싱 → 검토)에서 **template-first**(제품 프로파일 → 규제 경로 → 템플릿 팩 → 가이드 작성 → 증거 바인더 → 체크리스트/갭 → 파서 정합 → 가드레일/RAG → 감사/내보내기)로 전환했다.

SPEC-TEMPLATE-001은 이 전환의 **기초**다. 모든 작성(authoring)·체크리스트·증거(evidence) SPEC이 본 SPEC에서 정의하는 데이터 모델에 의존한다.

4x4 페르소나 분석에서 도출된 핵심 효과:

| 페르소나 | 핵심 질문 | 현재 제품 | 본 SPEC 이후 |
|----------|-----------|-----------|--------------|
| **P1 — Startup CTO** | "무엇을, 어떤 구조로 작성해야 하나?" (기존 문서 **없음**) | 서비스 불가 | **신규 해금** — 빈 페이지 대신 구체적 문서 체크리스트 제공 |
| **P2 — RA/QA 실무자** | 점검할 문서 템플릿 → 기존 문서 업로드 정합 | 부분 지원 | 템플릿 기준 정합 가능 |
| **P3 — Quality Manager** | 임의 업로드가 아닌 템플릿 기반 감사 추적 | 미지원 | 템플릿 기반 감사 추적 |
| **P4 — Consulting Partner** | 디바이스 패밀리별 재사용 템플릿 팩 | 미지원 | 재사용 가능 구조 입력 모델 |

[HARD] P1(기존 문서 없는 스타트업)은 현재 제품이 **전혀** 서비스할 수 없는 페르소나이며, SPEC-TEMPLATE-001이 이를 해금한다.

### 0.3 이 SPEC이 다루는 것 (In Scope)

- 경로 선택을 위한 **ProductProfile 입력 모델** 및 CRUD
- **RegulatoryPathway** 메타데이터(market/authority/submission_type/device_class/applicable_standards)
- **TemplatePack 레지스트리**(pathway/country/device_family별 버전 관리)
- **TemplateDocument / TemplateSection** 정의(문서·섹션 트리)
- **ApplicabilityRule**(섹션 적용성 규칙)
- 규제 파생 섹션마다 **SourceReference**(규정명/조항/URL/시행일)
- 템플릿 섹션으로부터 **ChecklistItem 생성**
- MVP 시드 데이터: Korea MFDS / FDA 510(k) / EU MDR Class IIa × 4개 디바이스 패밀리
- API 계약: ProductProfile 생성, pathway+pack resolve, pack 목록/상세, checklist 생성, pack 등록(admin)

### 0.4 이 SPEC이 다루지 않는 것 (Exclusions — What NOT to Build)

[HARD] 아래 항목은 SPEC-TEMPLATE-001 구현 범위에서 명시적으로 제외한다. spec.md는 WHAT/WHY만 다루며 구현 세부(함수명/클래스 구조/내부 API 스키마)는 Run 단계로 위임한다.

| 제외 항목 | 사유 | 담당 |
|-----------|------|------|
| 가이드 작성 에디터(WYSIWYG/섹션 작성 UI) | 본 SPEC은 데이터 모델·레지스트리·체크리스트 생성까지만 | SPEC-AUTHORING-001 (예정) |
| 증거 바인더 첨부·관리 로직 | ChecklistItem의 `evidence_required` 플래그만 정의, 첨부 처리는 별도 | SPEC-EVIDENCE-001 (예정) |
| 갭 분석/리포트 산출 | 체크리스트 상태는 정의하되 갭 분석 알고리즘은 별도 | 미래 SPEC |
| 파서 정합(reconciliation) 로직 | 템플릿 섹션 매핑 대상만 정의(REQ-TEMPLATE-014), 정합 엔진은 SPEC-PARSER 계열 | SPEC-PARSER-001 (완료) |
| eSTAR 동적 PDF 편집/임포트 자동화 | 별도 타당성 스파이크 필요 | 비범위 |
| 작성 콘텐츠 자동 생성(LLM 초안) | 미지원 경로는 speculative 생성 금지(REQ-TEMPLATE-006) | 비범위 |
| ra-med-bot / Vercel UI(Regula SaaS UI) | 읽기 전용 통합 대상, 본 리포 범위 외 | 비범위 (Lesson #4) |
| 최종 규제 결정·법적 사인오프 | 시스템은 작성 보조까지만 | 비범위 |

### 0.5 연관 SPEC 및 의존성

- **선행 의존(완료)**: SPEC-INFRA-001 — Cloud Control Plane Container App, PostgreSQL Flexible Server 프로비저닝
- **선행 의존(완료)**: SPEC-PARSER-001 — 필드 추출 엔진. 본 SPEC의 템플릿 섹션이 향후 정합 대상
- **후속 의존(예정)**: SPEC-AUTHORING-001, SPEC-EVIDENCE-001 — 본 SPEC의 데이터 모델을 소비
- **재사용 패턴**: `cloud-control-plane/src/app/`의 SQLAlchemy async 모델, pydantic-settings config, FastAPI router 패턴(SPEC-CRAWLER-001에서 확립)

### 0.6 아키텍처 원칙 (불변 제약)

[HARD] 본 SPEC의 데이터 모델·API는 Cloud Control Plane(Azure backend)에 구현하며 Customer Local Runtime 내부에는 구현하지 않는다.
[HARD] 모든 **규제 파생 섹션**은 최소 1개의 SourceReference를 가져야 한다. 내부 베스트프랙티스 섹션은 internal로 명시 표기하고 규제 요구사항으로 제시하지 않는다.
[HARD] 매칭되는 템플릿 팩이 없으면 `status: unsupported`를 반환하고 speculative(추측성) 템플릿을 생성하지 않는다.

---

## 1. 아키텍처

※ 본 절의 디렉터리 구조, 모듈 파일명, 클래스명, 내부 구현 세부는 비규범적 설계 제안이며, Run 단계에서 변경될 수 있습니다. (Non-normative design note)

### 1.1 도메인 구조 (Non-normative)

```
cloud-control-plane/src/app/
├── models/
│   ├── product_profile.py        # [NEW] ProductProfile ORM
│   ├── regulatory_pathway.py     # [NEW] RegulatoryPathway ORM
│   ├── template_pack.py          # [NEW] TemplatePack ORM
│   ├── template_document.py      # [NEW] TemplateDocument ORM
│   ├── template_section.py       # [NEW] TemplateSection ORM
│   ├── applicability_rule.py     # [NEW] ApplicabilityRule ORM
│   ├── source_reference.py       # [NEW] SourceReference ORM
│   └── checklist_item.py         # [NEW] ChecklistItem ORM
├── schemas/
│   ├── product_profile.py        # [NEW] Pydantic 요청/응답
│   ├── template_pack.py          # [NEW] resolve 요청/응답
│   └── checklist.py              # [NEW] checklist 생성/조회
├── routers/
│   ├── product_profiles.py       # [NEW] POST /product-profiles
│   ├── template_packs.py         # [NEW] resolve / list / get / register
│   └── checklists.py             # [NEW] checklist 생성·조회
├── services/
│   ├── pathway_resolver.py       # [NEW] FR-211 경로 해석
│   ├── pack_registry.py          # [NEW] FR-212 팩 레지스트리
│   ├── applicability.py          # [NEW] 안전한 적용성 표현식 평가
│   └── checklist_generator.py    # [NEW] 섹션 → 체크리스트 변환
├── seeds/                        # [NEW] 시드 팩 JSON/YAML fixtures
│   ├── kr_mfds_*.json
│   ├── fda_510k_*.json
│   └── eu_mdr_iia_*.json
└── migrations/                   # [MODIFY] 8개 테이블 신규 마이그레이션
```

### 1.2 설계 원칙

- **ApplicabilityRule 표현식**은 임의 코드 실행이 아닌 **작은 안전 표현식 언어**로 시작한다(예: `software_in_device == true`, `target_market contains "US"`).
- **시드 팩**은 DB admin UI 추가 이전에 구조화 JSON/YAML fixture로 저장하고 CI에서 검증한다(SourceReference 없는 규제 섹션은 커밋 불가).
- 첫 UI는 읽기 전용 체크리스트 뷰 + 상태 갱신 컨트롤이며, 전체 작성 에디터는 SPEC-AUTHORING-001로 분리한다.
- pack 버전 업데이트 시 기존 checklist는 원본 `source_version`을 유지하고, 신규 checklist만 갱신 버전을 사용한다(REQ-TEMPLATE-012).

### 1.3 통합 흐름

```
ProductProfile 입력
  → POST /product-profiles            (프로파일 저장 → product_id)
  → POST /template-packs/resolve      (pathway 해석 → applicable pack 후보)
  → GET  /template-packs/{pack_id}    (섹션 트리 + source refs)
  → GET  /template-packs/{pack_id}/checklist  (초기 checklist 생성)
  → (후속 SPEC) authoring / evidence / gap / parser reconciliation
```

---

## 2. 데이터 모델

8개 엔티티. 모든 `created_at`/`updated_at`은 TIMESTAMPTZ, 기본 키는 명시된 경우를 제외하고 UUID 또는 자연키.

### 2.1 ProductProfile

제품 정보 입력 — pathway 선택의 출발점.

| 필드 | 타입 | 설명 |
|------|------|------|
| `product_id` | VARCHAR(36) PK | uuid4 |
| `tenant_id` | VARCHAR(36) | 테넌트 식별자 |
| `device_name` | VARCHAR(255) NOT NULL | 디바이스명 |
| `classification` | VARCHAR(32) | 디바이스 등급(예: Class II, IIa) |
| `intended_use` | TEXT | 사용 목적 |
| `target_market` | VARCHAR[] | 대상 시장(예: `["KR", "US", "EU"]`) |
| `technology_type` | VARCHAR(64) | 기술 유형(예: X-ray, ultrasound, SW/PACS) |
| `device_family` | VARCHAR(64) | 디바이스 패밀리 |
| `software_in_device` | BOOLEAN | 소프트웨어 포함 여부(적용성 규칙 입력) |
| `created_at` | TIMESTAMPTZ | 생성 시각 |

### 2.2 RegulatoryPathway

규제 경로 메타데이터.

| 필드 | 타입 | 설명 |
|------|------|------|
| `pathway_id` | VARCHAR(48) PK | 예: `US-FDA-510K`, `KR-MFDS-MD`, `EU-MDR-IIA` |
| `market` | VARCHAR(16) NOT NULL | `KR` / `US` / `EU` |
| `authority` | VARCHAR(32) NOT NULL | `MFDS` / `FDA` / `EU` |
| `submission_type` | VARCHAR(32) | `510k` / `medical_device` / `mdr_technical_doc` |
| `device_class` | VARCHAR(16) | 대상 등급 |
| `applicable_standards` | VARCHAR[] | 적용 표준(예: `["ISO 13485", "IEC 62304"]`) |

### 2.3 TemplatePack

pathway별 버전 관리 레지스트리.

| 필드 | 타입 | 설명 |
|------|------|------|
| `pack_id` | VARCHAR(64) PK | 팩 식별자 |
| `pathway_id` | VARCHAR(48) FK → RegulatoryPathway | 소속 경로 |
| `device_family` | VARCHAR(64) NOT NULL | 디바이스 패밀리 |
| `version` | VARCHAR(32) NOT NULL | 팩 버전(semver) |
| `source_version` | VARCHAR(64) | 규제 소스 버전 라벨 |
| `status` | VARCHAR(16) NOT NULL | `draft` / `active` / `deprecated` |
| `created_at` | TIMESTAMPTZ | 생성 시각 |
| `updated_at` | TIMESTAMPTZ | 갱신 시각 |

### 2.4 TemplateDocument

팩 내 문서.

| 필드 | 타입 | 설명 |
|------|------|------|
| `document_id` | VARCHAR(48) PK | 문서 식별자 |
| `pack_id` | VARCHAR(64) FK → TemplatePack | 소속 팩 |
| `doc_type` | VARCHAR(48) NOT NULL | 문서 유형(예: DEVICE_DESCRIPTION) |
| `title` | VARCHAR(255) NOT NULL | 문서 제목 |
| `required` | BOOLEAN NOT NULL | 필수 여부 |
| `export_format` | VARCHAR(16) | `docx` / `xlsx` / `json` |
| `sort_order` | INT | 정렬 순서 |

### 2.5 TemplateSection

문서 내 섹션 트리.

| 필드 | 타입 | 설명 |
|------|------|------|
| `section_id` | VARCHAR(48) PK | 섹션 식별자 |
| `document_id` | VARCHAR(48) FK → TemplateDocument | 소속 문서 |
| `section_key` | VARCHAR(64) NOT NULL | 섹션 키(고유) |
| `title` | VARCHAR(255) NOT NULL | 섹션 제목 |
| `required` | BOOLEAN NOT NULL | 필수 여부 |
| `instructions` | TEXT | 작성 지침 |
| `placeholder` | TEXT | 플레이스홀더 텍스트 |
| `source_reference_ids` | VARCHAR[] | 규제 파생 시 SourceReference 참조(최소 1개) |
| `applicability_rule_id` | VARCHAR(48) FK → ApplicabilityRule NULL | 적용성 규칙(NULL = 항상 적용) |
| `is_internal` | BOOLEAN NOT NULL DEFAULT false | 내부 베스트프랙티스 여부 |
| `sort_order` | INT | 정렬 순서 |

### 2.6 ApplicabilityRule

섹션 적용성 규칙.

| 필드 | 타입 | 설명 |
|------|------|------|
| `rule_id` | VARCHAR(48) PK | 규칙 식별자 |
| `condition_field` | VARCHAR(64) NOT NULL | 평가 대상 ProductProfile 필드 |
| `condition_value` | VARCHAR(255) NOT NULL | 비교 값 |
| `template_pack_id` | VARCHAR(64) FK → TemplatePack | 소속 팩 |
| `explanation` | TEXT | 적용/제외 사유 설명 |

### 2.7 SourceReference

규제 출처.

| 필드 | 타입 | 설명 |
|------|------|------|
| `ref_id` | VARCHAR(48) PK | 출처 식별자 |
| `regulation_name` | VARCHAR(255) NOT NULL | 규정명 |
| `article` | VARCHAR(128) | 조항 |
| `url` | VARCHAR(1024) NOT NULL | 원문 URL |
| `effective_date` | DATE | 시행일 |

### 2.8 ChecklistItem

템플릿 섹션으로부터 생성되는 체크리스트 항목.

| 필드 | 타입 | 설명 |
|------|------|------|
| `checklist_item_id` | VARCHAR(48) PK | 항목 식별자 |
| `section_id` | VARCHAR(48) FK → TemplateSection | 원본 섹션 |
| `status` | VARCHAR(24) NOT NULL | 아래 허용 상태 |
| `blocking` | BOOLEAN NOT NULL | 차단 여부(제출 불가 항목) |
| `evidence_required` | BOOLEAN NOT NULL | 증거 첨부 필요 여부 |
| `reviewer_status` | VARCHAR(24) | 리뷰어 상태 |

허용 상태(`status`): `not_started`, `drafted`, `evidence_attached`, `needs_review`, `approved`, `not_applicable`, `blocked`.

---

## 3. API 계약

모든 응답은 JSON. 인증은 기존 Cloud Control Plane API Key(tenant allowlist) 패턴을 따른다.

### 3.1 `POST /product-profiles`

ProductProfile 생성.

- **Request body**: `device_name`(필수), `classification`, `intended_use`, `target_market[]`, `technology_type`, `device_family`, `software_in_device`
- **Response 201**: `{ product_id, created_at }`
- **Error**: `400` 필수 필드 누락, `401` 인증 실패

### 3.2 `POST /template-packs/resolve`

ProductProfile로 적용 경로·팩 후보 해석 (FR-211).

- **Request body**: `product_profile`(또는 `product_id`)
- **Response 200**: `{ matched_pathways[], pack_candidates[], applicable_documents[], applicable_sections[], excluded_sections[], source_references[] }`
- **Response 200 (unsupported)**: `{ status: "unsupported", reason }` — speculative 생성 금지
- **Error**: `400` 프로파일 무효, `401` 인증 실패

### 3.3 `GET /template-packs`

사용 가능한 팩 목록 (FR-212).

- **Query**: `market`, `pathway_id`, `device_family`, `status`
- **Response 200**: `{ packs[] }` (pack_id, pathway_id, device_family, version, status)
- **Error**: `401` 인증 실패

### 3.4 `GET /template-packs/{pack_id}`

팩 상세(섹션 트리 + SourceReference 포함).

- **Response 200**: `{ pack, documents[], sections[], source_references[] }`
- **Error**: `404` 팩 없음, `401` 인증 실패

### 3.5 `GET /template-packs/{pack_id}/checklist`

초기 체크리스트 생성.

- **Query**: `product_id`(적용성 평가용)
- **Response 200**: `{ checklist_id, items[], required_count, blocking_count }`
- **Error**: `404` 팩 없음, `400` product_id 누락, `401` 인증 실패

### 3.6 `POST /template-packs` (admin)

신규 팩 버전 등록.

- **Request body**: 팩 정의(documents/sections/source_references/applicability_rules 포함)
- **Response 201**: `{ pack_id, version }`
- **Error**: `400` 규제 섹션에 SourceReference 누락(검증 실패), `403` admin 권한 없음, `409` 동일 버전 중복

---

## 4. MVP 시드 데이터

3개 pathway × 4개 디바이스 패밀리.

### 4.1 Pathway

| pathway_id | market | authority | submission_type | device_class |
|------------|--------|-----------|-----------------|--------------|
| `KR-MFDS-MD` | KR | MFDS | medical_device (510(k) 동등) | Class II |
| `US-FDA-510K` | US | FDA | 510k | Class II |
| `EU-MDR-IIA` | EU | EU | mdr_technical_doc | Class IIa |

### 4.2 디바이스 패밀리 (3 pathway 공통)

1. X-ray System
2. Digital Detector
3. Medical SW / PACS
4. Aesthetic Ultrasound

### 4.3 SourceReference 시드 (예시)

- FDA eSTAR Program: https://www.fda.gov/medical-devices/how-study-and-market-your-device/estar-program
- FDA software submission guidance: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/content-premarket-submissions-device-software-functions
- (MFDS / EU MDR 출처는 P1 단계에서 공식 소스 맵 수집 후 확정)

---

## 5. EARS 요구사항

요구사항은 4개 모듈로 그룹화한다: M1(프로파일·경로 해석), M2(팩 레지스트리·무결성), M3(체크리스트·적용성), M4(미지원 처리·정합).

### M1 — 프로파일 및 경로 해석

**REQ-TEMPLATE-001 (Event-Driven, Profile 생성)**
When a `POST /product-profiles` request is received with a valid body, the system SHALL create a ProductProfile record and return the assigned `product_id` within 500ms.

**REQ-TEMPLATE-002 (Event-Driven, Pathway resolution)**
When a `POST /template-packs/resolve` request is received with a ProductProfile, the system SHALL resolve the applicable regulatory pathways and return the matching template pack candidates for the profile's target market and classification.

**REQ-TEMPLATE-003 (Ubiquitous, Resolve 응답 구성)**
The system SHALL include in every successful resolve response the applicable documents, applicable sections, excluded sections, and source references for the matched pack.

### M2 — 팩 레지스트리 및 무결성

**REQ-TEMPLATE-004 (Ubiquitous, Source reference 필수)**
Where a template section is derived from a regulatory source, the system SHALL attach at least one SourceReference to that section.

**REQ-TEMPLATE-005 (Unwanted Behavior, Source reference 검증)**
If a `POST /template-packs` (admin) request contains a regulatory-derived section without any SourceReference, then the system SHALL reject the registration with a `400` error and SHALL NOT persist the pack.

**REQ-TEMPLATE-006 (Where, Internal 섹션 표기)**
Where a section is an internal best practice rather than a regulatory requirement, the system SHALL mark it with `is_internal = true` and SHALL NOT present it as an authority-mandated requirement.

**REQ-TEMPLATE-007 (Event-Driven, Pack 목록 조회)**
When a `GET /template-packs` request is received, the system SHALL return the available packs filtered by the provided market, pathway, device family, and status query parameters.

**REQ-TEMPLATE-008 (Event-Driven, Pack 상세 조회)**
When a `GET /template-packs/{pack_id}` request is received for an existing pack, the system SHALL return the pack with its document tree, section tree, and source references.

### M3 — 체크리스트 및 적용성

**REQ-TEMPLATE-009 (Event-Driven, Checklist 생성)**
When a `GET /template-packs/{pack_id}/checklist` request is received with a `product_id`, the system SHALL create one ChecklistItem per applicable required or optional section.

**REQ-TEMPLATE-010 (State-Driven, 적용성 평가)**
While generating a checklist, the system SHALL evaluate each section's ApplicabilityRule against the ProductProfile and SHALL exclude sections whose rule evaluates false.

**REQ-TEMPLATE-011 (Event-Driven, 제외 사유 기록)**
When a section is excluded by an applicability rule, the system SHALL record the exclusion reason in the resolve/checklist response.

**REQ-TEMPLATE-012 (State-Driven, Pack 버전 격리)**
While a template pack source changes version, the system SHALL allow existing checklists to retain their original `source_version` and SHALL apply the updated version only to newly generated checklists.

**REQ-TEMPLATE-013 (Ubiquitous, Checklist 상태)**
The system SHALL restrict every ChecklistItem `status` to one of: `not_started`, `drafted`, `evidence_attached`, `needs_review`, `approved`, `not_applicable`, `blocked`.

### M4 — 미지원 처리 및 정합

**REQ-TEMPLATE-014 (Where, 파서 정합 매핑)**
Where an existing document is imported by a downstream parser, the system SHALL expose template section keys so that extracted fields can be mapped to template sections where possible.

**REQ-TEMPLATE-015 (Unwanted Behavior, 미지원 경로)**
If no template pack exists for the resolved pathway, then the system SHALL return `status: unsupported` with a reason and SHALL NOT generate speculative content.

**REQ-TEMPLATE-016 (Event-Driven, Pack 등록)**
When a `POST /template-packs` (admin) request is received with a valid pack definition, the system SHALL persist a new versioned pack and return its `pack_id` and `version`.

---

## 6. 인수 기준 (Acceptance Criteria)

각 REQ는 하나 이상의 AC에 대응한다. 상세 Given/When/Then 시나리오는 `acceptance.md` 참조.

- **AC-001**: Given a valid product body, when `POST /product-profiles` is called, the system returns `201` with a `product_id` within 500ms.
- **AC-002**: Given a US FDA 510(k) X-ray System profile, when the resolve endpoint is called, the system returns the FDA 510(k) pack candidate with applicable documents/sections.
- **AC-003**: Given a resolved pack, when resolve responds, the payload includes applicable_documents, applicable_sections, excluded_sections, and source_references.
- **AC-004**: Given a regulatory-derived section without a SourceReference, when `POST /template-packs` is called, registration fails with `400` and the pack is not persisted.
- **AC-005**: Given a section marked `is_internal=true`, when it appears in a response, it is not labeled as an authority-mandated requirement.
- **AC-006**: Given `GET /template-packs?market=KR&device_family=X-ray System`, when called, only matching packs are returned.
- **AC-007**: Given an existing `pack_id`, when `GET /template-packs/{pack_id}` is called, the document tree, section tree, and source references are returned.
- **AC-008**: Given `software_in_device=true`, when checklist generation runs, software description / SRS / architecture / V&V / traceability sections are included.
- **AC-009**: Given `software_in_device=false`, when checklist generation runs, software-only sections are excluded with a recorded reason.
- **AC-010**: Given a template pack version update, when an existing checklist is read, it still references the original `source_version`.
- **AC-011**: Given an unsupported jurisdiction/pathway, when resolve is called, the system returns `status: unsupported` instead of speculative content.
- **AC-012**: Given a valid admin pack definition, when `POST /template-packs` is called, a new versioned pack is persisted and `pack_id`/`version` returned.

---

## 7. 구현 단계 (Implementation Phases)

### P0 — Critical (Foundation)

- 데이터 모델 마이그레이션: 8개 테이블(ProductProfile, RegulatoryPathway, TemplatePack, TemplateDocument, TemplateSection, ApplicabilityRule, SourceReference, ChecklistItem)
- ProductProfile CRUD (`POST /product-profiles`)
- 기본 pathway resolution: pack 메타데이터 반환(`POST /template-packs/resolve`, `GET /template-packs`)
- 대응: REQ-TEMPLATE-001, 002, 007 / AC-001, 002, 006

### P1 — High

- 전체 섹션 트리 + SourceReference(`GET /template-packs/{pack_id}`)
- ChecklistItem 생성(`GET /template-packs/{pack_id}/checklist`)
- Korea MFDS 4개 디바이스 패밀리 시드 데이터
- SourceReference 검증 CI 게이트
- 대응: REQ-TEMPLATE-003, 004, 005, 006, 008, 009, 013 / AC-003, 004, 005, 007, 008

### P2 — Medium

- ApplicabilityRule 평가(안전 표현식 언어) + 제외 사유 기록
- FDA 510(k) + EU MDR Class IIa 시드 팩
- pack 버전 관리 + diff + 버전 격리
- admin pack 등록(`POST /template-packs`) + 미지원 경로 처리
- 파서 정합 섹션 키 노출
- 대응: REQ-TEMPLATE-010, 011, 012, 014, 015, 016 / AC-009, 010, 011, 012

---

## 8. 보안 및 컴플라이언스

- [HARD] 규제 파생 섹션은 SourceReference 없이 커밋 불가(CI 검증).
- [HARD] 미지원 경로는 speculative 생성 금지(환각 방지).
- 시드 팩은 구조화 JSON/YAML fixture로 저장하고 admin UI 이전에 코드 리뷰를 거친다.
- ApplicabilityRule은 임의 코드 실행이 아닌 안전한 표현식 평가만 허용한다.
- API Key 인증 + tenant allowlist는 기존 Cloud Control Plane 패턴 재사용.

---

## 9. 전문가 자문 권장

- **expert-backend**: SQLAlchemy async 8엔티티 모델 관계 설계, FastAPI 라우터·pydantic 스키마, 안전 표현식 평가기, pack 버전 격리 전략
- **expert-devops**: 8테이블 마이그레이션 배포, 시드 fixture CI 검증 게이트

---

## 10. 트레이서빌리티 매트릭스

| REQ | FR / MRD | AC | Phase |
|-----|----------|-----|-------|
| REQ-TEMPLATE-001 | FR-211 | AC-001 | P0 |
| REQ-TEMPLATE-002 | FR-211 | AC-002 | P0 |
| REQ-TEMPLATE-003 | FR-211 | AC-003 | P1 |
| REQ-TEMPLATE-004 | FR-212 | AC-004 | P1 |
| REQ-TEMPLATE-005 | FR-212 | AC-004 | P1 |
| REQ-TEMPLATE-006 | FR-212 | AC-005 | P1 |
| REQ-TEMPLATE-007 | FR-212 | AC-006 | P0 |
| REQ-TEMPLATE-008 | FR-212 | AC-007 | P1 |
| REQ-TEMPLATE-009 | FR-212 / MRD checklist | AC-008 | P1 |
| REQ-TEMPLATE-010 | FR-212 | AC-009 | P2 |
| REQ-TEMPLATE-011 | FR-212 | AC-009 | P2 |
| REQ-TEMPLATE-012 | FR-212 | AC-010 | P2 |
| REQ-TEMPLATE-013 | FR-212 / MRD checklist | AC-008 | P1 |
| REQ-TEMPLATE-014 | FR-212 / SPEC-PARSER-001 | (정합 검증) | P2 |
| REQ-TEMPLATE-015 | FR-211 | AC-011 | P2 |
| REQ-TEMPLATE-016 | FR-212 | AC-012 | P2 |

---

## 11. Open Decisions

- 템플릿 팩을 Cloud Control Plane에만 둘지, Customer Runtime과 동기화할지(현재 P0 범위는 Cloud Control Plane 전용).
- 시드 팩을 마이그레이션 데이터로 둘지, 정적 fixture로 둘지, 클라우드 전달 지식팩으로 둘지.
- nIVD 외 첫 지원 디바이스 패밀리 우선순위(현재 4개 패밀리 동시 시드).
- eSTAR XML 데이터 임포트/익스포트의 후속 직접 통합 타당성.
