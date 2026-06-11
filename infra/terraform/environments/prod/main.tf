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

# Shared Container App Environment (owned by staging, referenced here as data)
data "azurerm_container_app_environment" "shared" {
  name                = "cae-hybrid-ra-saas-staging"
  resource_group_name = "rg-hybrid-ra-saas-staging"
}

# Customer Runtime API — prod (api-prod, placeholder image; deploy-prod.yml updates to real image)
import {
  to = azurerm_container_app.api_prod
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod/providers/Microsoft.App/containerApps/api-prod"
}

resource "azurerm_container_app" "api_prod" {
  name                         = "api-prod"
  container_app_environment_id = data.azurerm_container_app_environment.shared.id
  resource_group_name          = azurerm_resource_group.prod.name
  revision_mode                = "Single"

  template {
    min_replicas = 1
    container {
      name   = "api"
      image  = "mcr.microsoft.com/k8se/quickstart:latest"
      cpu    = 0.5
      memory = "1Gi"
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8080
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

# Cloud Control Plane API — prod (REQ-CRAWLER-014)
# image is set via var.crawler_image; CI overrides this on v* tag push (REQ-CRAWLER-015)
resource "azurerm_container_app" "cloud_control_plane_api" {
  name                         = "cloud-control-plane-api"
  container_app_environment_id = data.azurerm_container_app_environment.shared.id
  resource_group_name          = azurerm_resource_group.prod.name
  revision_mode                = "Single"

  template {
    container {
      name   = "cloud-control-plane-api"
      image  = var.crawler_image
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

# Crawler scheduled job — daily 02:00 UTC (REQ-CRAWLER-013, AC-008)
resource "azurerm_container_app_job" "crawler_job" {
  name                         = "crawler-job"
  container_app_environment_id = data.azurerm_container_app_environment.shared.id
  resource_group_name          = azurerm_resource_group.prod.name
  location                     = local.location

  replica_timeout_in_seconds = 1800

  schedule_trigger_config {
    cron_expression          = "0 2 * * *"
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name   = "crawler"
      image  = var.crawler_image
      cpu    = 0.5
      memory = "1Gi"
    }
  }
}
