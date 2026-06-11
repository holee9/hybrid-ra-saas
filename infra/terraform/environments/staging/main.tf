terraform {
  backend "azurerm" {
    resource_group_name  = "rg-hybrid-ra-saas-prod"
    storage_account_name = "sthybridrasaasprod"
    container_name       = "tfstate"
    key                  = "staging.terraform.tfstate"
    use_oidc             = true
  }
}

locals {
  location = "koreacentral"
}

# Staging Resource Group (shared environment)
resource "azurerm_resource_group" "staging" {
  name     = "rg-hybrid-ra-saas-staging"
  location = local.location
}

# Container App Environment — staging (shared by prod/staging, owned here)
module "container_app_env" {
  source              = "../../modules/container_app_env"
  name                = "cae-hybrid-ra-saas-staging"
  resource_group_name = azurerm_resource_group.staging.name
  location            = local.location
}

# Key Vault (staging)
module "key_vault_staging" {
  source                    = "../../modules/key_vault"
  name                      = "kv-hybrid-ra-staging"
  resource_group_name       = azurerm_resource_group.staging.name
  location                  = local.location
  tenant_id                 = var.tenant_id
  enable_rbac_authorization = true
}

