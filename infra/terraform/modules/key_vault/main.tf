data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "this" {
  name                       = var.name
  resource_group_name        = var.resource_group_name
  location                   = var.location
  tenant_id                  = var.tenant_id
  sku_name                   = var.sku_name
  soft_delete_retention_days = var.soft_delete_retention_days
  enable_rbac_authorization  = var.enable_rbac_authorization

  lifecycle {
    ignore_changes = [soft_delete_retention_days]
  }
}

