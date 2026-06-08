---
id: SPEC-INFRA-001
version: 1.0.0
status: completed
created: 2026-06-08
updated: 2026-06-08
author: drake.lee
priority: high
issue_number: 0
---

# SPEC-INFRA-001: Cloud Control Plane — Azure Terraform/IaC

## HISTORY

- **v1.0.0** (2026-06-08): 최초 작성. Cloud Control Plane 인프라의 Terraform/IaC 범위 확정. 2026-06-05 수동 프로비저닝된 9종 Azure 리소스의 선언적 import(Terraform 1.5+ import block), Azure Blob Storage state backend(`sthybridrasaasprod`/`tfstate`), Container App placeholder 2종 신규 생성, `terraform.yml` GitHub Actions 워크플로우(OIDC plan-on-PR / apply-on-merge), 기존 CI 워크플로우 Python 스택 갱신, EARS 인수 기준(REQ-INFRA-001~010) 정의.

---

## 0. 범위 및 의존성

### 0.1 SPEC 개요

| 항목 | 내용 |
|------|------|
| SPEC-ID | SPEC-INFRA-001 |
| 제목 | Cloud Control Plane — Azure Terraform/IaC |
| 상태 | planned |
| 대상 디렉터리 | `infra/terraform/` (Terraform 구성, 모듈, 환경별 디렉터리) |
| 분석 기준 | 2026-06-05 수동 프로비저닝된 Azure 리소스 인벤토리, SPEC-API-001 산출물, Product 3계층 아키텍처(Cloud Control Plane → Secure Sync Layer → Customer Local Runtime) |
| 라이프사이클 | spec-anchored (인프라 코드와 함께 유지, 리소스 변경 시 갱신) |
| 개발 방법론 | TDD (terraform validate / plan 기반 검증 우선) |

### 0.2 이 SPEC이 다루는 것 (In Scope)

- 기존 수동 프로비저닝 Azure 리소스 9종을 Terraform 1.5+ 선언적 `import` block으로 코드화
- Terraform state backend를 Azure Blob Storage(`sthybridrasaasprod`/컨테이너 `tfstate`)로 구성
- prod / staging 환경 분리 디렉터리 구조 및 재사용 가능한 module 설계
- Cloud Control Plane API용 Container App placeholder 2종(prod/staging) 신규 생성 — 초기 이미지는 hello-world, 실제 이미지는 SPEC-CRAWLER-001에서 교체
- `tfstate` storage container 신규 생성
- Key Vault 시크릿을 `data` source로만 참조(생성/관리하지 않음)
- 신규 `terraform.yml` GitHub Actions 워크플로우(OIDC 인증, PR에서 plan, main merge에서 apply, plan 결과 PR 코멘트)
- 기존 `ci.yml` / `deploy-staging.yml` / `deploy-prod.yml` 워크플로우를 Python/FastAPI 스택에 맞게 갱신

### 0.3 이 SPEC이 다루지 않는 것 (Exclusions — What NOT to Build)

[HARD] 아래 항목은 SPEC-INFRA-001 구현 범위에서 명시적으로 제외한다. spec.md는 WHAT/WHY만 다루며, 본 SPEC은 IaC 코드 생성에 한정한다.

| 제외 항목 | 사유 | 담당 SPEC |
|-----------|------|-----------|
| Regulatory Crawler 애플리케이션 코드 | 크롤러/애플리케이션 도메인 분리 | SPEC-CRAWLER-001 |
| Customer Local Runtime 애플리케이션 배포 | 이미 완료, 별도 도메인 | SPEC-API-001 (완료) |
| 기존 Service Principal(`sp-hybrid-ra-saas-github`) 및 OIDC Federated Credential 관리 | 수동 관리 자산, Terraform 비범위 | 운영 수동 관리 |
| Container App에 배포되는 실제 컨테이너 이미지 빌드/푸시 | placeholder만 생성, 이미지는 크롤러 산출물 | SPEC-CRAWLER-001 |
| Key Vault 시크릿 값 생성/회전 | 이미 프로비저닝됨, `data` source 참조만 | 운영 수동 관리 |
| Knowledge Pack 빌드 파이프라인 | 지식팩 제작 도메인 | 미래 SPEC |
| 멀티리전/DR 인프라 자동화 | 상용화 후순위 | 미정 |
| PostgreSQL 스키마/마이그레이션 | 애플리케이션 레이어 책임 | SPEC-API-001 (완료) |

### 0.4 연관 SPEC 및 의존성

- **선행 의존(완료)**: SPEC-API-001 — Customer Local Runtime(`customer-runtime/`, FastAPI + Docker, 7 endpoints, 82% coverage)
- **선행 의존(완료)**: 2026-06-05 수동 프로비저닝된 Azure 리소스 인벤토리
- **활성화 대상(후속)**: SPEC-CRAWLER-001 — 본 SPEC이 생성한 Container App placeholder에 실제 크롤러 이미지를 배포

### 0.5 아키텍처 원칙 (불변 제약)

[HARD] 기존 수동 프로비저닝 리소스는 import로만 코드화하며, import 직후 `terraform plan`은 변경(drift) 0이어야 한다.
[HARD] Service Principal 인증은 OIDC(passwordless)만 사용한다. 클라이언트 시크릿/암호를 코드 또는 CI에 두지 않는다.
[HARD] `*.tfvars`, `terraform.tfstate*`는 절대 버전 관리에 커밋하지 않는다.

---

## 1. 아키텍처

### 1.1 디렉터리 구조

```
infra/
└── terraform/
    ├── versions.tf              # Terraform + AzureRM provider 버전 핀
    ├── backend.tf               # Azure Blob Storage backend (placeholder, 수동 활성화)
    ├── import.tf                # Terraform 1.5+ 선언적 import block 선언
    ├── modules/
    │   ├── container_registry/  # ACR module
    │   ├── container_app_env/   # Container App Environment module
    │   ├── postgresql/          # PostgreSQL Flexible Server module
    │   ├── key_vault/           # Key Vault + secrets data source module
    │   └── monitoring/          # Application Insights module
    └── environments/
        ├── prod/
        │   ├── main.tf          # import 대상 + 신규 리소스 (prod)
        │   ├── variables.tf
        │   └── terraform.tfvars # gitignored
        └── staging/
            ├── main.tf          # import 대상 + 신규 리소스 (staging)
            ├── variables.tf
            └── terraform.tfvars # gitignored
```

### 1.2 module 조직 원칙

- 각 module은 단일 리소스 관심사를 캡슐화하고 `variables.tf`(입력) / `outputs.tf`(출력) / `main.tf`(리소스)로 구성한다.
- prod / staging `environments/*/main.tf`는 module을 호출하고 환경별 입력값만 주입한다.
- 환경 간 공유 리소스(예: Container App Environment는 free tier 제약상 region당 1개)는 staging 환경에서 정의하고 prod는 `data` source로 참조한다.

### 1.3 환경 분리(prod / staging)

| 환경 | Resource Group | state 파일 키 | 특이사항 |
|------|----------------|---------------|----------|
| prod | `rg-hybrid-ra-saas-prod` | `prod.terraform.tfstate` | 대부분 리소스 import 대상 |
| staging | `rg-hybrid-ra-saas-staging` | `staging.terraform.tfstate` | Container App Environment 정의 보유(공유) |

---

## 2. Terraform 버전 및 프로바이더

[HARD] `import` block(선언적 import)은 Terraform 1.5+에서 도입되었다. 본 SPEC은 안정성을 위해 1.9.0 이상을 핀한다.

```hcl
# infra/terraform/versions.tf
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
  use_oidc        = true
}
```

---

## 3. State Backend

[HARD] Terraform state는 Azure Blob Storage에 저장한다. backend는 신규 `tfstate` 컨테이너 생성 이후 수동으로 활성화한다(chicken-and-egg 회피).

```hcl
# infra/terraform/backend.tf
# 초기 apply로 tfstate 컨테이너를 생성한 뒤 본 backend를 활성화하고
# `terraform init -migrate-state` 로 로컬 state를 원격으로 이관한다.
terraform {
  backend "azurerm" {
    resource_group_name  = "rg-hybrid-ra-saas-prod"
    storage_account_name = "sthybridrasaasprod"
    container_name       = "tfstate"
    key                  = "prod.terraform.tfstate" # staging: staging.terraform.tfstate
    use_oidc             = true
  }
}
```

backend 활성화 절차(구현 시 수행, 코드 외 운영 단계):
1. `tfstate` 컨테이너를 로컬 state로 먼저 apply하여 생성
2. `backend.tf` 활성화
3. `terraform init -migrate-state` 실행으로 원격 이관

---

## 4. 기존 리소스 Import

[HARD] 9종 리소스를 Terraform 1.5+ 선언적 `import` block으로 코드화한다. import 후 `terraform plan`은 drift 0이어야 한다.

공통 식별자:
- Subscription ID: `a49390df-1886-495c-9fb0-cf8faf1aa5ef`
- Tenant ID: `42580dce-4bd2-4556-b531-4843eba6431d`

### 4.1 import 대상 리소스 목록

| # | 리소스 타입 | 이름 | Resource Group | 비고 |
|---|-------------|------|----------------|------|
| 1 | azurerm_resource_group | rg-hybrid-ra-saas-prod | — | Production |
| 2 | azurerm_resource_group | rg-hybrid-ra-saas-staging | — | Staging |
| 3 | azurerm_container_registry | acrhybridrasaasprod | prod | `acrhybridrasaasprod.azurecr.io` |
| 4 | azurerm_container_app_environment | cae-hybrid-ra-saas-staging | staging | prod/staging 공유(free tier 1/region) |
| 5 | azurerm_key_vault | kv-hybrid-ra-prod | prod | RBAC mode |
| 6 | azurerm_key_vault | kv-hybrid-ra-staging | staging | RBAC mode |
| 7 | azurerm_postgresql_flexible_server | psql-hybrid-ra-saas-prod | prod | PostgreSQL 16, Burstable B1ms |
| 8 | azurerm_storage_account | sthybridrasaasprod | prod | Standard LRS, public access blocked |
| 9 | azurerm_application_insights | appi-hybrid-ra-saas-prod | prod | connection string Key Vault 보관 |

### 4.2 import block 구문 예시 (infra/terraform/import.tf)

```hcl
# Resource Groups
import {
  to = azurerm_resource_group.prod
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod"
}

import {
  to = azurerm_resource_group.staging
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-staging"
}

# Container Registry
import {
  to = module.container_registry.azurerm_container_registry.this
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod/providers/Microsoft.ContainerRegistry/registries/acrhybridrasaasprod"
}

# Container App Environment (staging, 공유)
import {
  to = module.container_app_env.azurerm_container_app_environment.this
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-staging/providers/Microsoft.App/managedEnvironments/cae-hybrid-ra-saas-staging"
}

# Key Vaults
import {
  to = module.key_vault_prod.azurerm_key_vault.this
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod/providers/Microsoft.KeyVault/vaults/kv-hybrid-ra-prod"
}

import {
  to = module.key_vault_staging.azurerm_key_vault.this
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-staging/providers/Microsoft.KeyVault/vaults/kv-hybrid-ra-staging"
}

# PostgreSQL Flexible Server
import {
  to = module.postgresql.azurerm_postgresql_flexible_server.this
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-hybrid-ra-saas-prod"
}

# Storage Account
import {
  to = azurerm_storage_account.prod
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod/providers/Microsoft.Storage/storageAccounts/sthybridrasaasprod"
}

# Application Insights
import {
  to = module.monitoring.azurerm_application_insights.this
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod/providers/Microsoft.Insights/components/appi-hybrid-ra-saas-prod"
}
```

> import block의 `to` 주소는 module 호출 구조에 맞추어 작성한다. import 실행은 `terraform plan -generate-config-out=generated.tf`로 초기 리소스 구성 골격을 생성한 뒤, 수동으로 module 구조에 맞게 정리한다.

---

## 5. 신규 리소스

[HARD] import 대상이 아닌 신규 Terraform 관리 리소스 3종.

| # | 리소스 타입 | 논리명 | 환경 | 비고 |
|---|-------------|--------|------|------|
| 1 | azurerm_storage_container | tfstate | prod | `sthybridrasaasprod` 내 Terraform state 컨테이너 |
| 2 | azurerm_container_app | cloud-control-plane-api | prod | placeholder, 초기 hello-world 이미지 |
| 3 | azurerm_container_app | cloud-control-plane-api | staging | placeholder, 초기 hello-world 이미지 |

신규 리소스 구문 골격:

```hcl
# tfstate 컨테이너
resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.prod.id
  container_access_type = "private"
}

# Cloud Control Plane API placeholder (prod / staging 공통 패턴)
resource "azurerm_container_app" "cloud_control_plane_api" {
  name                         = "cloud-control-plane-api"
  container_app_environment_id = module.container_app_env.environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  template {
    container {
      name   = "cloud-control-plane-api"
      image  = "mcr.microsoft.com/k8se/quickstart:latest" # placeholder, SPEC-CRAWLER-001에서 교체
      cpu    = 0.25
      memory = "0.5Gi"
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}
```

---

## 6. 모듈 설계

각 module의 핵심 입력(variables)과 출력(outputs) 요약. 상세 리소스 속성은 구현 단계에서 import drift 0 기준으로 확정한다.

| Module | 주요 variables | 주요 outputs |
|--------|----------------|--------------|
| `container_registry` | `name`, `resource_group_name`, `location`, `sku` | `login_server`, `id` |
| `container_app_env` | `name`, `resource_group_name`, `location`, `log_analytics_workspace_id`(optional) | `environment_id` |
| `postgresql` | `name`, `resource_group_name`, `location`, `version`, `sku_name`, `storage_mb` | `fqdn`, `id` |
| `key_vault` | `name`, `resource_group_name`, `location`, `tenant_id`, `enable_rbac_authorization` | `vault_id`, `vault_uri`, `secrets`(data source map) |
| `monitoring` | `name`, `resource_group_name`, `location`, `application_type` | `connection_string`(sensitive), `instrumentation_key`(sensitive), `id` |

`key_vault` module의 시크릿 참조 패턴(생성 아님, data source):

```hcl
data "azurerm_key_vault_secret" "db_connection_string" {
  name         = "DB-CONNECTION-STRING"
  key_vault_id = azurerm_key_vault.this.id
}
# 동일 패턴: DB-HOST, AZURE-STORAGE-CONN-STRING, APP-INSIGHTS-CONN-STRING, JWT-SECRET
```

---

## 7. CI/CD — terraform.yml

[HARD] 신규 `terraform.yml` 워크플로우는 기존 워크플로우와 분리된 별도 파일로 생성한다. 기존 OIDC Federated Credential(`sp-hybrid-ra-saas-github`)을 재사용한다.

동작 요약:
- PR(대상 main) → `terraform plan` 실행 후 결과를 PR 코멘트로 게시
- push to main → `terraform apply -auto-approve`
- 인증: `azure/login@v2` + OIDC(passwordless), `permissions: id-token: write`

```yaml
# .github/workflows/terraform.yml
name: Terraform

on:
  pull_request:
    branches: [main]
    paths: ['infra/terraform/**']
  push:
    branches: [main]
    paths: ['infra/terraform/**']

permissions:
  id-token: write       # OIDC 토큰 발급
  contents: read
  pull-requests: write  # plan 결과 PR 코멘트

env:
  ARM_SUBSCRIPTION_ID: a49390df-1886-495c-9fb0-cf8faf1aa5ef
  ARM_TENANT_ID: 42580dce-4bd2-4556-b531-4843eba6431d
  ARM_CLIENT_ID: 6620dc2b-93af-453c-b1b8-20f9582d7354
  ARM_USE_OIDC: "true"
  TF_WORKING_DIR: infra/terraform/environments/prod

jobs:
  terraform:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ${{ env.TF_WORKING_DIR }}
    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ env.ARM_CLIENT_ID }}
          tenant-id: ${{ env.ARM_TENANT_ID }}
          subscription-id: ${{ env.ARM_SUBSCRIPTION_ID }}

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ">= 1.9.0"

      - name: Terraform Init
        run: terraform init

      - name: Terraform Format Check
        run: terraform fmt -check -recursive

      - name: Terraform Validate
        run: terraform validate

      - name: Terraform Plan
        if: github.event_name == 'pull_request'
        id: plan
        run: terraform plan -no-color -out=tfplan
        continue-on-error: true

      - name: Comment Plan on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const output = `#### Terraform Plan \`${{ steps.plan.outcome }}\`
            <details><summary>Plan 결과 보기</summary>

            \`\`\`
            ${{ steps.plan.outputs.stdout }}
            \`\`\`
            </details>`;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: output
            });

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: terraform apply -auto-approve
```

> staging 환경은 동일 패턴의 matrix 또는 별도 job으로 `environments/staging` 작업 디렉터리를 대상으로 구성한다.

---

## 8. 기존 CI 워크플로우 업데이트

[HARD] 기존 워크플로우의 TODO를 Python/FastAPI 스택에 맞게 갱신한다. SPEC-API-001 산출물(`customer-runtime/`)을 대상으로 한다.

| 파일 | 갱신 내용 |
|------|-----------|
| `ci.yml` | PR(main/develop) 시 `customer-runtime/`에서 `ruff check` + `pytest --cov`(커버리지 게이트) 실행. Python 3.12 setup. |
| `deploy-staging.yml` | push to develop 시 Container App 배포. Dockerfile 경로를 `customer-runtime/Dockerfile`로, 노출 포트를 `8000`(기존 3000 제거)으로 수정. |
| `deploy-prod.yml` | tag `v*` 시 production 배포 + auto-rollback. Dockerfile 경로/포트 8000 동일 적용. |

> 본 SPEC은 위 워크플로우의 Python/포트 관련 수정만 포함한다. 워크플로우 신규 기능 추가는 비범위.

---

## 9. EARS 요구사항

### REQ-INFRA-001 — Drift-free import
WHEN 9종 기존 리소스에 대해 `terraform plan`을 import 직후 실행하면, the system SHALL 어떤 리소스에 대해서도 생성/수정/삭제 계획(drift)을 출력하지 않는다(plan: 0 to add, 0 to change, 0 to destroy).

### REQ-INFRA-002 — Plan on PR
WHEN `infra/terraform/**` 경로를 변경하는 PR이 main을 대상으로 열리면, the system SHALL `terraform plan`을 실행하고 그 결과를 해당 PR 코멘트로 게시한다.

### REQ-INFRA-003 — Apply on merge
WHEN main 브랜치에 push(merge)가 발생하면, the system SHALL `terraform apply -auto-approve`를 실행한다.

### REQ-INFRA-004 — State in Blob
The system SHALL Terraform state를 Azure Blob Storage(`sthybridrasaasprod` 스토리지 계정의 `tfstate` 컨테이너)에 저장한다.

### REQ-INFRA-005 — Module reusability
The system SHALL 각 인프라 관심사(container_registry, container_app_env, postgresql, key_vault, monitoring)를 재사용 가능한 module로 분리하고, prod/staging 환경에서 입력값만 달리하여 호출한다.

### REQ-INFRA-006 — Secrets via Key Vault data source
The system SHALL Key Vault 시크릿(`DB-CONNECTION-STRING`, `DB-HOST`, `AZURE-STORAGE-CONN-STRING`, `APP-INSIGHTS-CONN-STRING`, `JWT-SECRET`)을 `azurerm_key_vault_secret` data source로만 참조하며, Terraform에서 시크릿 값을 생성하거나 변경하지 않는다.

### REQ-INFRA-007 — tfvars gitignored
The system SHALL `*.tfvars` 및 `terraform.tfstate*` 파일을 `.gitignore`로 배제하여 버전 관리에 커밋되지 않도록 한다.

### REQ-INFRA-008 — Container App placeholder deployed
WHEN prod 및 staging 환경에 대해 `terraform apply`가 성공하면, the system SHALL 각 환경에 `cloud-control-plane-api` Container App(포트 8000, placeholder 이미지)을 생성한다.

### REQ-INFRA-009 — CI updated for Python stack
The system SHALL `ci.yml`이 `customer-runtime/`에 대해 `ruff` 린트와 `pytest` 커버리지를 실행하고, deploy 워크플로우가 Dockerfile 경로 및 포트 8000을 사용하도록 갱신한다.

### REQ-INFRA-010 — OIDC-only authentication
IF CI 파이프라인이 Azure에 인증해야 하면, THEN the system SHALL OIDC(`azure/login@v2`, `id-token: write`)만 사용하며 클라이언트 시크릿/암호를 사용하지 않는다.

---

## 10. 인수 기준

| REQ | 인수 기준 (검증 가능) |
|-----|------------------------|
| REQ-INFRA-001 | import block 적용 후 `terraform plan` 출력이 "No changes. Your infrastructure matches the configuration."를 포함한다. 9종 리소스 모두 drift 0. |
| REQ-INFRA-002 | `infra/terraform/**`를 수정한 테스트 PR에서 terraform.yml이 트리거되고, PR에 plan 결과 코멘트가 1개 이상 게시된다. |
| REQ-INFRA-003 | main merge 후 terraform.yml의 apply job이 성공(exit 0)하고 state가 갱신된다. |
| REQ-INFRA-004 | `terraform init` 시 backend가 azurerm(`sthybridrasaasprod`/`tfstate`)으로 초기화되고, `prod.terraform.tfstate` blob이 존재한다. |
| REQ-INFRA-005 | `infra/terraform/modules/` 하위에 5개 module 디렉터리가 존재하고, prod/staging `main.tf`가 module을 호출한다. |
| REQ-INFRA-006 | 5개 시크릿이 `data "azurerm_key_vault_secret"`으로 참조되며, `resource "azurerm_key_vault_secret"` 선언이 없다(grep 0건). |
| REQ-INFRA-007 | `.gitignore`에 `*.tfvars`, `*.tfstate`, `*.tfstate.*` 패턴이 존재하고, `git status`에 tfvars/tfstate 미추적 노출이 없다. |
| REQ-INFRA-008 | apply 후 `az containerapp show -n cloud-control-plane-api`가 prod/staging 각 환경에서 성공하고 ingress targetPort=8000을 반환한다. |
| REQ-INFRA-009 | `ci.yml`이 `ruff check`와 `pytest`를 포함하고, deploy 워크플로우에서 `3000` 포트 참조가 0건, `8000` 참조가 존재한다. Dockerfile 경로가 `customer-runtime/`를 가리킨다. |
| REQ-INFRA-010 | terraform.yml과 deploy 워크플로우에 `client-secret`/`password` 항목이 없고 `id-token: write` 권한과 `azure/login@v2`가 존재한다. |

---

## 11. 보안

[HARD] 보안 제약:

- **gitignore 강제**: `infra/terraform/.gitignore` 및 루트 `.gitignore`에 `*.tfvars`, `*.tfstate`, `*.tfstate.*`, `.terraform/`, `crash.log` 패턴 포함.
- **하드코딩 금지**: 시크릿/패스워드/연결 문자열을 `.tf` 또는 워크플로우 평문에 두지 않는다. subscription/tenant/client ID는 식별자(비밀 아님)로 허용한다.
- **Key Vault 참조 패턴**: 모든 시크릿은 `data "azurerm_key_vault_secret"`으로만 조회한다. Terraform state에 시크릿 평문이 누적되므로 가능한 한 Container App의 `secret`/Key Vault reference로 런타임 주입을 우선한다.
- **OIDC 전용 인증**: CI는 OIDC Federated Credential만 사용. 클라이언트 시크릿 발급/저장 금지.
- **state 보호**: `tfstate` 컨테이너는 `private` access. 스토리지 계정은 public access blocked(기존 설정 유지).
- **RBAC mode Key Vault**: 두 Key Vault 모두 RBAC mode 유지. access policy 방식으로 회귀 금지.

---

## 12. 의존성

```
선행(완료):
  SPEC-API-001 (Customer Local Runtime, customer-runtime/)
  Azure 리소스 9종 (2026-06-05 수동 프로비저닝)
        │
        ▼
  SPEC-INFRA-001 (본 SPEC — Terraform/IaC, Container App placeholder)
        │
        ▼
활성화(후속):
  SPEC-CRAWLER-001 (Regulatory Crawler — placeholder에 실제 이미지 배포)
```

- **Depends on**: SPEC-API-001(완료), Azure 프로비저닝 리소스(완료), 기존 OIDC Service Principal(운영 관리)
- **Enables**: SPEC-CRAWLER-001 — Container App placeholder가 크롤러 배포 타겟을 제공
- **Repository**: `https://github.com/holee9/hybrid-ra-saas.git` (branch: main)

---

## 부록 A. 구현 단계 권장 순서

1. `versions.tf`, module 5종 골격 작성 → `terraform validate` 통과
2. `import.tf` 작성 → `terraform plan` drift 0 확인 (REQ-INFRA-001)
3. `tfstate` 컨테이너 신규 생성 → backend 활성화 + `init -migrate-state` (REQ-INFRA-004)
4. Container App placeholder 2종 추가 → apply (REQ-INFRA-008)
5. `terraform.yml` 작성 → 테스트 PR로 plan 코멘트 검증 (REQ-INFRA-002, 003, 010)
6. `ci.yml`/deploy 워크플로우 Python/포트 8000 갱신 (REQ-INFRA-009)
7. `.gitignore` 정비 + 시크릿 data source 검증 (REQ-INFRA-006, 007)

---

## 13. 구현 노트 (Implementation Notes)

- **구현 완료**: 2026-06-08 (커밋: 7ec6aa4)
- **SPEC lifecycle**: spec-first (v1.0.0 기준 설계, 구현 후 완료 처리)

### 실제 구현 vs 계획 차이점

| 항목 | 계획 | 실제 | 사유 |
|------|------|------|------|
| import.tf 위치 | `infra/terraform/import.tf` (루트) | `environments/prod/import.tf`, `environments/staging/import.tf` (환경별) | module `to` 주소 정합성 — prod 리소스는 prod 환경에서, staging 리소스는 staging 환경에서 import |
| Dockerfile 경로 | `customer-runtime/Dockerfile` | `customer-runtime/docker/Dockerfile` | 실제 파일 위치 기준. SPEC 오기 수정. |
| 마이그레이션 step | deploy 워크플로우 별도 `alembic upgrade head` | 제거 (entrypoint.sh가 이미 실행) | 이중 실행 방지 |

### 미해결 항목 (운영 수동 필요)

- `terraform plan` drift 0 검증: Azure 인증 환경에서 실행 필요 (REQ-INFRA-001)
- State backend 활성화: tfstate 컨테이너 생성 후 `terraform init -migrate-state` 수동 실행 (REQ-INFRA-004)
- OIDC federated credential subject 검증: 실제 PR/merge 트리거 시 확인
