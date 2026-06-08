output "login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.this.login_server
}

output "id" {
  description = "ACR resource ID"
  value       = azurerm_container_registry.this.id
}
