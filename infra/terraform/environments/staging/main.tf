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

# Cloud Control Plane API — staging (placeholder image)
resource "azurerm_container_app" "cloud_control_plane_api" {
  name                         = "cloud-control-plane-api"
  container_app_environment_id = module.container_app_env.environment_id
  resource_group_name          = azurerm_resource_group.staging.name
  revision_mode                = "Single"

  template {
    container {
      name   = "cloud-control-plane-api"
      image  = "mcr.microsoft.com/k8se/quickstart:latest"
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
