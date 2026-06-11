terraform {
  # Backend configured via terraform init -backend-config
  # Activate after tfstate container is created:
  # terraform init -backend-config="key=prod.terraform.tfstate"
  backend "azurerm" {
    resource_group_name  = "rg-hybrid-ra-saas-prod"
    storage_account_name = "sthybridrasaasprod"
    container_name       = "tfstate"
    key                  = "prod.terraform.tfstate"
    use_oidc             = true
  }
}

locals {
  location = "koreacentral"
}

# Resource Groups
resource "azurerm_resource_group" "prod" {
  name     = "rg-hybrid-ra-saas-prod"
  location = local.location
}

# ACR module
module "container_registry" {
  source              = "../../modules/container_registry"
  name                = "acrhybridrasaasprod"
  resource_group_name = azurerm_resource_group.prod.name
  location            = local.location
  sku                 = "Basic"
}

# Key Vault (prod)
module "key_vault_prod" {
  source                    = "../../modules/key_vault"
  name                      = "kv-hybrid-ra-prod"
  resource_group_name       = azurerm_resource_group.prod.name
  location                  = local.location
  tenant_id                 = var.tenant_id
  enable_rbac_authorization = true
}

# PostgreSQL
module "postgresql" {
  source                 = "../../modules/postgresql"
  name                   = "psql-hybrid-ra-saas-prod"
  resource_group_name    = azurerm_resource_group.prod.name
  location               = local.location
  pg_version             = "16"
  sku_name               = "B_Standard_B1ms"
  storage_mb             = 32768
  administrator_login    = var.db_admin_login
  administrator_password = var.db_admin_password
}

# Storage Account
resource "azurerm_storage_account" "prod" {
  name                     = "sthybridrasaasprod"
  resource_group_name      = azurerm_resource_group.prod.name
  location                 = local.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  blob_properties {
    versioning_enabled = false
  }

  public_network_access_enabled = true
}

# Terraform State Container (bootstrapped manually, imported here)
import {
  to = azurerm_storage_container.tfstate
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod/providers/Microsoft.Storage/storageAccounts/sthybridrasaasprod/blobServices/default/containers/tfstate"
}

# NOTE: Container Apps (api-prod, cloud-control-plane-api, crawler-job) are managed
# exclusively by deploy-prod.yml CI workflow. Terraform does NOT manage these resources.

resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.prod.id
  container_access_type = "private"
}

# Application Insights
module "monitoring" {
  source              = "../../modules/monitoring"
  name                = "appi-hybrid-ra-saas-prod"
  resource_group_name = azurerm_resource_group.prod.name
  location            = local.location
  application_type    = "web"
}

