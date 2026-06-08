---
id: SPEC-INFRA-001
artifact: implementation-plan
version: 1.0.0
created: 2026-06-08
author: manager-strategy
status: awaiting-approval
---

# SPEC-INFRA-001 구현 계획 — Cloud Control Plane Azure Terraform/IaC

## plan_summary

기존 수동 프로비저닝된 Azure 리소스 9종을 Terraform 1.5+ 선언적 `import` block으로 코드화하고, 재사용 가능한 5개 module + prod/staging 환경 분리 구조를 구축한다. State backend는 chicken-and-egg를 피하기 위해 로컬 state로 `tfstate` 컨테이너를 먼저 생성한 뒤 Azure Blob backend를 활성화하는 2단계 부트스트랩으로 처리한다. CI/CD는 OIDC 전용 `terraform.yml`(PR plan-comment / merge apply)을 신규 작성하고, 기존 3개 워크플로우를 Python/FastAPI 스택(ruff + pytest, 포트 8000, customer-runtime Dockerfile)으로 갱신한다. 핵심 성공 기준은 import 후 `terraform plan` drift 0이며, 이는 module 리소스 속성을 실제 Azure 상태와 정확히 일치시켜야만 달성된다.

---

## requirements list (REQ → 충족 파일)

| REQ | 충족 파일 |
|-----|-----------|
| REQ-INFRA-001 (drift-free import) | `infra/terraform/import.tf`, `modules/*/main.tf`, `environments/prod/main.tf`, `environments/staging/main.tf` |
| REQ-INFRA-002 (plan on PR) | `.github/workflows/terraform.yml` (pull_request job + github-script comment) |
| REQ-INFRA-003 (apply on merge) | `.github/workflows/terraform.yml` (push-to-main apply step) |
| REQ-INFRA-004 (state in Blob) | `infra/terraform/backend.tf`, `environments/*/backend.tf` (key 분리) |
| REQ-INFRA-005 (module reusability) | `infra/terraform/modules/{container_registry,container_app_env,postgresql,key_vault,monitoring}/` |
| REQ-INFRA-006 (secrets via data source) | `modules/key_vault/main.tf` (data "azurerm_key_vault_secret" x5), outputs.tf |
| REQ-INFRA-007 (tfvars gitignored) | 루트 `.gitignore`, `infra/terraform/.gitignore` |
| REQ-INFRA-008 (Container App placeholder) | `environments/prod/main.tf`, `environments/staging/main.tf` (azurerm_container_app) |
| REQ-INFRA-009 (CI Python stack) | `.github/workflows/ci.yml`, `deploy-staging.yml`, `deploy-prod.yml` |
| REQ-INFRA-010 (OIDC-only) | `terraform.yml`, `deploy-staging.yml`, `deploy-prod.yml` (azure/login@v2, id-token: write, no client-secret) |

---

## success_criteria (REQ별 "done" 정의)

- **REQ-INFRA-001**: import 적용 후 `terraform plan` 출력에 "No changes. Your infrastructure matches the configuration." 포함. 9종 리소스 모두 0 to add / 0 to change / 0 to destroy.
- **REQ-INFRA-002**: `infra/terraform/**` 수정 테스트 PR에서 terraform.yml 트리거 → PR에 plan 결과 코멘트 1개 이상 게시.
- **REQ-INFRA-003**: main merge 후 apply job exit 0, 원격 state 갱신.
- **REQ-INFRA-004**: `terraform init`이 azurerm backend(`sthybridrasaasprod`/`tfstate`)로 초기화, `prod.terraform.tfstate` blob 존재.
- **REQ-INFRA-005**: `modules/` 하위 5개 디렉터리 존재, prod/staging `main.tf`가 module 호출.
- **REQ-INFRA-006**: `grep -r 'resource "azurerm_key_vault_secret"' infra/` → 0건. 5개 시크릿 모두 data source 참조.
- **REQ-INFRA-007**: `.gitignore`에 `*.tfvars`, `*.tfstate`, `*.tfstate.*`, `.terraform/`, `crash.log` 존재. `git status`에 tfvars/tfstate 노출 없음.
- **REQ-INFRA-008**: apply 후 `az containerapp show -n cloud-control-plane-api`가 prod/staging 각각 성공, ingress targetPort=8000 반환.
- **REQ-INFRA-009**: ci.yml에 `ruff check` + `pytest` 포함. deploy 워크플로우 `3000` 참조 0건, `8000` 존재, Dockerfile 경로가 customer-runtime 가리킴.
- **REQ-INFRA-010**: terraform.yml + deploy 워크플로우에 `client-secret`/`password` 0건, `id-token: write` + `azure/login@v2` 존재.

---

## implementation_phases (TDD: validate/fmt/plan 우선)

> 검증 방법론: 각 HCL 작성 단계마다 `terraform fmt -check` → `terraform validate` → (해당 시) `terraform plan` 순으로 게이트 통과. 인프라 특성상 RED는 "validate/plan 실패", GREEN은 "통과"로 매핑.

### T-001 — versions.tf + provider 핀
- 설명: `versions.tf` 작성. Terraform >= 1.9.0, azurerm ~> 4.0, provider use_oidc=true, subscription/tenant 변수화.
- 파일: `infra/terraform/versions.tf` (+ 환경별 심볼릭/복제 처리 결정)
- REQ: REQ-INFRA-010 (use_oidc 기반)
- 의존성: 없음
- 완료기준: `terraform init -backend=false` + `validate` 통과.

### T-002 — 5개 module 골격 작성
- 설명: container_registry, container_app_env, postgresql, key_vault, monitoring 각각 main.tf/variables.tf/outputs.tf 작성. SPEC 6장 variables/outputs 표 기준.
- 파일: `infra/terraform/modules/{container_registry,container_app_env,postgresql,key_vault,monitoring}/{main,variables,outputs}.tf` (15개 파일)
- REQ: REQ-INFRA-005, REQ-INFRA-006 (key_vault data source x5)
- 의존성: T-001
- 완료기준: `terraform validate` 통과, key_vault에 `resource "azurerm_key_vault_secret"` 0건.

### T-003 — environments/prod + staging main.tf (module 호출, 신규 리소스)
- 설명: prod/staging `main.tf`에서 module 호출 + 환경별 입력 주입. 공유 Container App Environment는 staging 정의, prod는 data source 참조. tfstate 컨테이너(prod) + Container App placeholder 2종 추가. variables.tf + terraform.tfvars.example.
- 파일: `infra/terraform/environments/prod/{main,variables}.tf`, `environments/staging/{main,variables}.tf`, `*/terraform.tfvars.example`
- REQ: REQ-INFRA-005, REQ-INFRA-008
- 의존성: T-002
- 완료기준: `terraform validate` 양 환경 통과. tfvars.example만 커밋(실제 tfvars gitignored).

### T-004 — import.tf 작성 + drift 0 검증 (핵심 게이트)
- 설명: 9종 리소스 import block 작성. `to` 주소를 T-003 module 구조에 정렬. `terraform plan -generate-config-out`로 골격 생성 후 실제 Azure 상태와 속성 정합. drift 0까지 module 리소스 속성 반복 보정.
- 파일: `infra/terraform/import.tf`, 보정 대상 `modules/*/main.tf`
- REQ: REQ-INFRA-001
- 의존성: T-003, Azure 인증(OIDC/az login) 가능 환경
- 완료기준: `terraform plan` → "No changes". (가장 반복 가능성 높은 단계)

### T-005 — backend.tf + tfstate 부트스트랩
- 설명: backend.tf를 주석 placeholder로 작성. 운영 절차: 로컬 state로 tfstate 컨테이너 apply → backend 활성화 → `init -migrate-state`. prod/staging state key 분리(`prod.terraform.tfstate` / `staging.terraform.tfstate`).
- 파일: `infra/terraform/backend.tf` (+ 환경별 key)
- REQ: REQ-INFRA-004
- 의존성: T-003 (tfstate 컨테이너 리소스), T-004 (apply 가능 상태)
- 완료기준: tfstate 컨테이너 생성 후 `terraform init` azurerm backend 초기화 성공, prod blob 존재.

### T-006 — terraform.yml 워크플로우 신규
- 설명: SPEC 7장 기준 작성. PR(main, paths infra/terraform/**) → fmt/validate/plan + PR 코멘트. push main → apply. OIDC env(SUB/TENANT/CLIENT ID, USE_OIDC). prod/staging 작업 디렉터리 처리(matrix 또는 별도 job).
- 파일: `.github/workflows/terraform.yml`
- REQ: REQ-INFRA-002, REQ-INFRA-003, REQ-INFRA-010
- 의존성: T-005 (backend 활성화 후 init 동작)
- 완료기준: 테스트 PR에서 plan 코멘트 게시, merge 시 apply 성공.

### T-007 — ci.yml Python 스택 재작성
- 설명: Docker build/test/npm TODO 제거. Python 3.12 setup → `ruff check customer-runtime/` → `pytest --cov customer-runtime/`. pyproject가 `--cov=app`/`source=["src/app"]`이므로 working-directory를 customer-runtime로 설정. 통합 테스트는 CI 전용(integration marker) — Lesson #2.
- 파일: `.github/workflows/ci.yml`
- REQ: REQ-INFRA-009
- 의존성: 없음 (병렬 가능)
- 완료기준: `ruff check` + `pytest` 포함, npm 참조 0건.

### T-008 — deploy-staging.yml / deploy-prod.yml 갱신
- 설명: targetPort 3000→8000. Dockerfile 경로 결정(아래 위험 R-4 참조: 실제는 `customer-runtime/docker/Dockerfile`). 마이그레이션 명령 npm run migrate→처리 결정(R-5: entrypoint가 이미 alembic 실행). 컨테이너명/APP_NAME 정합.
- 파일: `.github/workflows/deploy-staging.yml`, `.github/workflows/deploy-prod.yml`
- REQ: REQ-INFRA-009, REQ-INFRA-010
- 의존성: 없음 (병렬 가능, T-007과 함께)
- 완료기준: `3000` 참조 0건, `8000` 존재, Dockerfile 경로 customer-runtime, client-secret 0건.

### T-009 — .gitignore 정비 + 보안 grep 검증
- 설명: 루트 + `infra/terraform/.gitignore`에 Terraform 패턴 추가. 하드코딩 시크릿 grep, `resource azurerm_key_vault_secret` grep, client-secret grep 최종 검증.
- 파일: 루트 `.gitignore`, `infra/terraform/.gitignore`
- REQ: REQ-INFRA-006, REQ-INFRA-007
- 의존성: T-002~T-008 (검증 대상 존재 후)
- 완료기준: 패턴 존재, 모든 보안 grep 0건.

**구현 순서**: T-001 → T-002 → T-003 → T-004 → T-005 → T-006 (Terraform 체인, 순차) / T-007, T-008 (워크플로우, 병렬 가능) / T-009 (최종 검증). 총 9개 태스크 (상한 10 이내).

---

## risk_assessment

| ID | 위험 | 심각도 | 완화책 |
|----|------|--------|--------|
| R-1 | **import drift 0 미달성** — module 리소스 속성이 실제 Azure 상태와 불일치 시 plan에 change 발생 | High | `plan -generate-config-out`로 실제 속성 추출 후 module에 반영. tag/sku/network 등 기본값 누락 주의. T-004를 반복 보정 단계로 설계. |
| R-2 | **state chicken-and-egg** — backend가 tfstate 컨테이너를 요구하나 컨테이너는 apply로 생성됨 | High | SPEC 3장 2단계 부트스트랩: 로컬 state apply로 컨테이너 생성 → backend 활성화 → `init -migrate-state`. backend.tf는 초기 주석 placeholder. |
| R-3 | **공유 Container App Environment 충돌** — prod/staging 양쪽이 동일 cae를 관리하면 이중 소유 | Med | staging이 리소스 소유(import), prod는 `data` source 참조. import block은 staging에만. |
| R-4 | **Dockerfile 경로 불일치** — SPEC/spec.md는 `customer-runtime/Dockerfile`이라 명시하나 실제 파일은 `customer-runtime/docker/Dockerfile` | Med | 구현 시 실제 경로(`customer-runtime/docker/Dockerfile`)와 build context(`customer-runtime/`) 사용. 승인 질문 필요(아래). |
| R-5 | **이중 마이그레이션** — deploy 워크플로우 별도 마이그레이션 step이 있으나 Dockerfile entrypoint가 이미 `alembic upgrade head` 실행 | Med | 별도 마이그레이션 step 제거하고 entrypoint에 위임, 또는 entrypoint를 API-only로 변경. 승인 질문 필요. alembic은 멱등이라 즉시 장애는 아니나 중복은 정리 대상. |
| R-6 | **staging 트리거 분기** — deploy-staging은 `develop` push, terraform.yml은 `main` 기준. 브랜치 전략 혼재 | Low | 본 SPEC은 기존 deploy 트리거 변경 비범위. develop 유지, terraform만 main. 문서화로 충분. |
| R-7 | **OIDC Federated Credential 미설정** — ARM_CLIENT_ID(6620dc2b...)에 terraform.yml용 subject 미등록 시 apply 실패 | Med | SP/OIDC는 운영 수동 관리(비범위). 단, 구현 전 federated credential subject(repo:holee9/hybrid-ra-saas:ref:refs/heads/main 등) 확인 필요. |
| R-8 | **secret이 state 평문 누적** — key_vault_secret data source 값이 state에 평문 저장 | Low→Med | SPEC 11장 권고대로 Container App runtime은 Key Vault reference/secret 주입 우선. state backend는 private 컨테이너 + RBAC로 접근 제한. |

---

## proportionality_check

**판정: 대체로 비례적(proportional). 과설계 위험 1건, 단순화 권고 2건.**

- **적정**: 5개 module 분리는 REQ-INFRA-005가 명시적으로 요구 — 과설계 아님. import block 9종, 신규 3종, 워크플로우 4개 모두 REQ에 1:1 대응.
- **과설계 주의 (1)**: `container_registry` module은 ACR 1개(prod)만 사용하고 재사용처가 없다. REQ-INFRA-005가 5개 module을 명시하므로 SPEC 준수상 유지하나, 실질 재사용은 key_vault(prod/staging 2회)뿐. monitoring/postgresql/acr은 단일 호출 — module 추상화가 "earning its complexity"한지 구현 시 재확인. SPEC 요구라 제거는 불가, 단 module 내부는 최소 속성만.
- **단순화 권고 (1)**: T-005 backend는 환경별 별도 backend.tf 대신 `terraform init -backend-config=key=...`로 key만 주입하면 파일 중복 제거 가능.
- **단순화 권고 (2)**: deploy 워크플로우의 별도 마이그레이션 step(R-5)은 entrypoint와 중복 — 제거가 단순화 + 이중 실행 방지 양쪽에 기여.
- **범위 규율**: customer-runtime 애플리케이션 코드, SP/OIDC credential, Key Vault secret 값은 모두 비범위(SPEC 0.3). 워크플로우 신규 기능 추가 금지(8장). 계획은 이 경계를 준수.

---

## 승인 전 확인 필요 항목 (orchestrator → 사용자 질의 대상)

1. **Dockerfile 경로 (R-4)**: 실제 `customer-runtime/docker/Dockerfile` 사용 확정? (spec.md 명시는 `customer-runtime/Dockerfile`)
2. **마이그레이션 처리 (R-5)**: deploy 워크플로우 별도 alembic step을 제거하고 entrypoint에 위임? 아니면 entrypoint를 API-only로 변경하고 워크플로우에서 명시 실행?
3. **staging 배포 트리거 (R-6)**: deploy-staging `develop` 트리거 유지? (terraform.yml은 main)
4. **OIDC federated credential (R-7)**: ARM_CLIENT_ID 6620dc2b에 main 브랜치/PR subject 사전 등록 상태 확인.

---

## handover (승인 시 manager-tdd 전달 패키지)

- TAG chain: T-001 → T-009 (위 순서, T-007/T-008 병렬)
- 버전 핀: Terraform >= 1.9.0, azurerm ~> 4.0, OIDC, azure/login@v2, hashicorp/setup-terraform@v3, actions/github-script@v7, actions/checkout@v4, setup-python (3.12)
- 핵심 결정: import drift 0 우선 / 2단계 backend 부트스트랩 / 공유 cae는 staging 소유+prod data / key_vault secret은 data source 전용
- 식별자(비밀 아님): SUB a49390df..., TENANT 42580dce..., CLIENT 6620dc2b...
- 미해결 4건은 위 승인 질의로 선결
