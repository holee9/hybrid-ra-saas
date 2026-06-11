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

data "azurerm_key_vault_secret" "db_connection_string" {
  name         = "DB-CONNECTION-STRING"
  key_vault_id = azurerm_key_vault.this.id
}

data "azurerm_key_vault_secret" "db_host" {
  name         = "DB-HOST"
  key_vault_id = azurerm_key_vault.this.id
}

data "azurerm_key_vault_secret" "azure_storage_conn_string" {
  name         = "AZURE-STORAGE-CONN-STRING"
  key_vault_id = azurerm_key_vault.this.id
}

data "azurerm_key_vault_secret" "app_insights_conn_string" {
  name         = "APP-INSIGHTS-CONN-STRING"
  key_vault_id = azurerm_key_vault.this.id
}

data "azurerm_key_vault_secret" "jwt_secret" {
  name         = "JWT-SECRET"
  key_vault_id = azurerm_key_vault.this.id
}
