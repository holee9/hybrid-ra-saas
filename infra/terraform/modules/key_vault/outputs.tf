output "vault_id" {
  description = "Key Vault resource ID"
  value       = azurerm_key_vault.this.id
}

output "vault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.this.vault_uri
}

output "db_connection_string" {
  description = "DB connection string secret value"
  value       = data.azurerm_key_vault_secret.db_connection_string.value
  sensitive   = true
}

output "db_host" {
  description = "DB host secret value"
  value       = data.azurerm_key_vault_secret.db_host.value
  sensitive   = true
}

output "azure_storage_conn_string" {
  description = "Azure Storage connection string secret value"
  value       = data.azurerm_key_vault_secret.azure_storage_conn_string.value
  sensitive   = true
}

output "app_insights_conn_string" {
  description = "Application Insights connection string secret value"
  value       = data.azurerm_key_vault_secret.app_insights_conn_string.value
  sensitive   = true
}

output "jwt_secret" {
  description = "JWT secret value"
  value       = data.azurerm_key_vault_secret.jwt_secret.value
  sensitive   = true
}
