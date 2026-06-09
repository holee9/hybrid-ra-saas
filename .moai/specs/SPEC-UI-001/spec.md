---
id: SPEC-UI-001
version: 0.1.0
status: planned
created: 2026-06-09
updated: 2026-06-09
author: drake.lee
priority: high
issue_number: 14
---

# SPEC-UI-001: 파싱 결과 교정 UI 화면

## HISTORY

- 2026-06-09 (v0.1.0): 초안 작성. SPEC-PARSER-001(완료, commit b7fdc0e)의 PATCH /parse/{job_id}/corrections 엔드포인트를 소비하는 React 기반 교정 UI 정의. (author: drake.lee)

---

## §0 범위 (Scope)

### 0.1 목적

`ParsedFields` 15개 필드를 작업자가 인라인으로 수정하고 confidence를 시각적으로 확인할 수 있는 단일 페이지 교정 UI를 제공한다. 백엔드(SPEC-PARSER-001)가 추출한 IFU 필드를 검토/승인/수정하여 PATCH API로 저장하는 것이 핵심 가치다.

### 0.2 In-Scope (포함 범위)

- 교정 화면 단일 SPA (React 18 + TypeScript + Vite)
- `GET /parse/jobs/{job_id}` 소비하여 초기 데이터 로드
- `PATCH /parse/{job_id}/corrections` 소비하여 변경 필드만 저장
- confidence 색상 시각화 (green/yellow/red) 및 추출 단계(stage) 표시
- `rejected=true` 문서에 대한 경고 배너 및 폼 비활성화
- Docker `ui` 서비스 (nginx, port 8080) 추가
- Vitest + React Testing Library 단위/컴포넌트 테스트

### 0.3 Exclusions (What NOT to Build)

다음 항목은 본 SPEC 범위에서 **명시적으로 제외**한다. 별도 SPEC에서 다룬다.

- **파싱 작업 시작/업로드 화면**: 문서 업로드 및 파싱 트리거 UI는 별도 SPEC. 본 SPEC은 이미 생성된 `job_id`를 입력으로 받는다.
- **검토 큐 화면**: 여러 작업을 목록으로 보여주는 큐/대시보드는 SPEC-UI-002(예정)에서 다룬다.
- **트레이서빌리티 그래프 / 감사 로그 뷰어**: 수정 이력의 시각화 화면은 본 SPEC 범위 밖. (로컬 undo 히스토리는 포함하나 영구 감사 뷰는 제외)
- **인증 화면(로그인/토큰 발급)**: JWT는 외부에서 주입받는다고 가정. 로그인 UI는 본 SPEC 미포함.
- **원문 PDF/문서 위치 하이라이트**: PRD FR-202의 optional 항목으로, 본 SPEC에서는 구현하지 않는다.
- **다국어(i18n) UI**: 한국어 단일 로케일만 지원. 다국어는 후행 SPEC.

### 0.4 Dependencies (의존성)

- **선행**: SPEC-PARSER-001 (완료, commit b7fdc0e) — parser_engine 및 PATCH/GET 엔드포인트 제공
- **신규**: `customer-runtime/docker-compose.yml`에 `ui` 서비스 추가 필요
- **후행**: SPEC-UI-002 (검토 큐 화면, 예정)

---

## §1 아키텍처 (Architecture)

### 디렉터리 구조

```
customer-runtime/
├── docker-compose.yml          # ui 서비스 추가
└── ui/                         # NEW: React SPA
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tailwind.config.ts
    ├── index.html
    ├── nginx.conf
    ├── docker/
    │   └── Dockerfile
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── components/
        │   ├── FieldRow.tsx          # 단일 필드: 라벨, 값, confidence, 편집
        │   ├── ConfidenceBadge.tsx   # green/yellow/red 배지
        │   ├── StageIndicator.tsx    # RULE/NER/LLM/NONE chip
        │   ├── CorrectionPanel.tsx   # 전체 ParsedFields 폼
        │   └── RejectedBanner.tsx    # rejected=true 경고
        ├── hooks/
        │   ├── useParseJob.ts        # GET /parse/jobs/{id}
        │   └── useCorrections.ts     # PATCH /parse/{id}/corrections
        ├── types/
        │   └── parse.ts              # ParsedFields 스키마 TypeScript 미러
        └── lib/
            └── api.ts                # 인증 헤더 포함 fetch 래퍼
```

### 컴포넌트 계층

```
App
└── CorrectionPanel (job_id 기반)
    ├── RejectedBanner (rejected=true 시)
    ├── overall_confidence 프로그레스바
    ├── FieldRow × 15
    │   ├── ConfidenceBadge
    │   └── StageIndicator
    └── Save 버튼
```

---

## §2 데이터 모델

백엔드 `customer-runtime/src/app/schemas/parse.py`를 TypeScript로 미러링한다. (`src/types/parse.ts`)

```typescript
export enum ExtractionStage {
  RULE = "rule_based",
  NER = "spacy_ner",
  LLM = "llm_fallback",
  NONE = "none", // manual correction
}

export interface FieldExtraction {
  value: string | string[] | null;
  confidence: number; // 0.0 – 1.0
  stage: ExtractionStage;
  needs_correction: boolean;
}

export const IFU_FIELD_NAMES = [
  "device_name", "intended_use", "indications", "contraindications",
  "warnings", "device_classification", "region_targets",
  "cybersecurity_requirements", "precautions", "product_code",
  "maintenance_interval", "cleaning_disinfection", "software_version",
  "accessories", "disposal_instructions",
] as const; // 15 fields

export type IfuFieldName = (typeof IFU_FIELD_NAMES)[number];

export interface ParsedFields {
  device_name: FieldExtraction;
  intended_use: FieldExtraction;
  indications: FieldExtraction;
  contraindications: FieldExtraction;
  warnings: FieldExtraction;
  device_classification: FieldExtraction;
  region_targets: FieldExtraction;
  cybersecurity_requirements: FieldExtraction;
  precautions: FieldExtraction;
  product_code: FieldExtraction;
  maintenance_interval: FieldExtraction;
  cleaning_disinfection: FieldExtraction;
  software_version: FieldExtraction;
  accessories: FieldExtraction;
  disposal_instructions: FieldExtraction;
  overall_confidence: number;
  requires_correction: boolean;
  rejected: boolean;
}

export interface ParseJobResponse {
  job_id: string;
  status: string;
  parsed_fields?: ParsedFields | null;
}

// PATCH 요청 본문: 변경된 필드만 (partial)
export interface CorrectionRequest {
  corrections: Partial<Record<IfuFieldName, string | string[]>>;
}
```

---

## §3 UI 컴포넌트 설계

### CorrectionPanel

- 15개 필드를 `FieldRow` 목록으로 렌더링한다.
- 상단에 `overall_confidence`를 프로그레스바로 표시한다.
- dirty 상태인 필드가 하나 이상이면 Save 버튼을 활성화한다.
- Save 진행 중에는 폼 전체를 비활성화(disabled)한다.
- `rejected=true`이면 `RejectedBanner`를 최상단에 표시하고 모든 필드 편집을 비활성화한다.

### FieldRow

- 필드명 라벨(한국어 표시명) + 현재 값을 표시한다.
- 클릭-to-edit 인라인 편집: 값 영역 클릭 시 입력 필드로 전환된다.
- 우측에 `ConfidenceBadge`와 `StageIndicator`를 배치한다.
- `value`가 배열(`string[]`)이면 줄바꿈 구분 텍스트로 편집한다.
- 값이 변경되면 dirty 표시(시각적 마커)를 노출한다.

### ConfidenceBadge

confidence 수치에 따라 색상 코딩하고 수치를 함께 표시한다.

| 조건 | 색상 | 의미 |
|------|------|------|
| `confidence >= 0.85` | green | 자동 추출, 교정 불필요 |
| `0.75 <= confidence < 0.85` | yellow | 낮은 신뢰도, 검토 권장 |
| `confidence < 0.75` 또는 `needs_correction=true` | red | 교정 필수 |

### StageIndicator

추출 단계를 chip으로 표시한다.

| stage | 표시 라벨 |
|-------|-----------|
| `RULE` | 규칙 기반 |
| `NER` | NER |
| `LLM` | LLM |
| `NONE` | 수동 |

### RejectedBanner

- `rejected=true`일 때 전체 화면 상단 경고 배너를 표시한다.
- 문서 재업로드가 필요함을 안내한다.
- 교정 폼은 비활성화된다.

---

## §4 API 통합

### 엔드포인트

| 동작 | 메서드 | 경로 | 용도 |
|------|--------|------|------|
| 초기 로드 | GET | `/parse/jobs/{job_id}` | `ParseJobResponse` 로드 |
| 교정 저장 | PATCH | `/parse/{job_id}/corrections` | 변경된 필드만 partial 업데이트 |

### 인증 헤더 (`src/lib/api.ts`)

```
Authorization: Bearer {jwt}
X-Tenant-ID: {tenant_id}
Content-Type: application/json
```

- `jwt`는 메모리 스토어에서 조회 (localStorage 금지, §8 참조).
- `tenant_id`는 빌드/런타임 환경변수로 주입.

### 에러 처리

| 상태 코드 | 처리 |
|-----------|------|
| 401 | 인증 실패 토스트. 폼 비활성화 |
| 404 | "작업을 찾을 수 없음" 안내. 빈 상태 표시 |
| 422 | 검증 실패 토스트. 해당 필드값 롤백 |
| 네트워크/타임아웃 | 에러 토스트 + 재시도 안내 |

### PATCH 본문 (partial 전송)

변경된 필드만 전송한다. 예시:

```json
{ "corrections": { "device_name": "X-ray Model A" } }
```

---

## §5 Docker 통합

- `customer-runtime/docker-compose.yml`에 `ui` 서비스를 추가한다.
- nginx가 `dist/`를 port 8080으로 서빙한다.
- nginx에서 `/api` → `http://api:8000` 으로 same-origin 프록시하여 CORS를 회피한다.
- `CORS_ORIGINS`는 docker-compose에 이미 8080으로 설정되어 있다(PRD §10).

```yaml
# docker-compose.yml (발췌)
ui:
  build:
    context: ./ui
    dockerfile: docker/Dockerfile
  ports:
    - "8080:8080"
  depends_on:
    - api
```

```nginx
# nginx.conf (발췌)
location /api/ {
  proxy_pass http://api:8000/;
}
location / {
  root /usr/share/nginx/html;
  try_files $uri $uri/ /index.html;
}
```

---

## §6 EARS 요구사항

### REQ-UI-001 (Event-Driven)

**When** `job_id`가 URL 파라미터로 제공되면, the system **shall** `GET /parse/jobs/{job_id}`를 호출하여 `ParsedFields`를 로드한다.

### REQ-UI-002 (Ubiquitous)

The system **shall** 각 필드의 confidence 값을 색상 배지(green ≥0.85 / yellow 0.75–0.85 / red <0.75)로 표시한다.

### REQ-UI-003 (Event-Driven)

**When** 사용자가 필드 값을 수정하면, the system **shall** 해당 필드를 변경(dirty) 상태로 표시한다.

### REQ-UI-004 (Event-Driven)

**When** 사용자가 Save 버튼을 클릭하면, the system **shall** 변경된 필드만 포함하여 `PATCH /parse/{job_id}/corrections`를 호출한다.

### REQ-UI-005 (Event-Driven)

**When** PATCH 응답이 성공이면, the system **shall** `ParsedFields`를 갱신하고 성공 토스트를 표시한다.

### REQ-UI-006 (Unwanted Behavior)

**If** PATCH 응답이 실패이면, **then** the system **shall** 에러 토스트를 표시하고 해당 필드값을 직전 값으로 롤백한다.

### REQ-UI-007 (State-Driven)

**While** `rejected=true`이면, the system **shall** `RejectedBanner`를 표시하고 교정 폼을 비활성화한다.

### REQ-UI-008 (Ubiquitous)

The system **shall** 수정 전후 값을 로컬 히스토리로 저장하여 undo(되돌리기)를 지원한다.

---

## §7 인수 기준 (Acceptance Criteria)

전체 Given-When-Then 시나리오는 `acceptance.md`에 정의한다. 모든 시나리오는 Vitest + React Testing Library로 검증 가능해야 한다.

핵심 요약:

- 정상 로드: `job_id` 제공 시 15개 필드가 confidence 배지와 함께 렌더링된다.
- 부분 저장: 1개 필드만 수정 후 Save 시 PATCH 본문에 해당 필드만 포함된다.
- 실패 롤백: PATCH 422 응답 시 필드값이 롤백되고 에러 토스트가 노출된다.
- rejected 처리: `rejected=true` 시 폼이 비활성화되고 배너가 표시된다.

---

## §8 보안 (Security)

- **JWT 보관**: 토큰은 `localStorage`/`sessionStorage`가 아닌 메모리 스토어(in-memory)에 보관한다. XSS 탈취 표면을 줄인다.
- **테넌트 격리**: `X-Tenant-ID`는 환경변수로 주입하며 사용자 입력으로 받지 않는다.
- **XSS 방지**: 필드값은 React 기본 escaping에 의존한다. `dangerouslySetInnerHTML` 사용 금지. 원문 HTML 렌더링이 필요하면 DOMPurify로 sanitize한다.
- **CORS**: nginx 프록시(`/api → api:8000`)를 통해 same-origin으로 처리하여 브라우저 CORS 노출을 최소화한다.
- **입력 검증**: PATCH 전송 전 필드명을 `IFU_FIELD_NAMES` whitelist로 클라이언트 측 검증한다(서버 whitelist의 1차 방어).

---

## §9 의존성

- **선행**: SPEC-PARSER-001 (완료, commit b7fdc0e)
- **후행**: SPEC-UI-002 (검토 큐 화면, 예정)

---

## 전문가 자문 권장

본 SPEC은 프론트엔드(React 컴포넌트, 상태관리, API 통합) 중심이므로 구현 단계에서 **expert-frontend** 자문을 권장한다.
