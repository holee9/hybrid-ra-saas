resource "azurerm_postgresql_flexible_server" "this" {
  name                   = var.name
  resource_group_name    = var.resource_group_name
  location               = var.location
  version                = var.pg_version
  sku_name               = var.sku_name
  administrator_login    = var.administrator_login
  administrator_password = var.administrator_password
  zone                   = "1"

  storage_mb = var.storage_mb

  lifecycle {
    ignore_changes = [zone]
  }
}
