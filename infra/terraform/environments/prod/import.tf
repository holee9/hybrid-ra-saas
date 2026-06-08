# Terraform 1.5+ declarative import blocks
# Run: terraform plan to verify drift = 0 after applying imports

import {
  to = azurerm_resource_group.prod
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod"
}

import {
  to = module.container_registry.azurerm_container_registry.this
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod/providers/Microsoft.ContainerRegistry/registries/acrhybridrasaasprod"
}

import {
  to = module.key_vault_prod.azurerm_key_vault.this
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod/providers/Microsoft.KeyVault/vaults/kv-hybrid-ra-prod"
}

import {
  to = module.postgresql.azurerm_postgresql_flexible_server.this
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-hybrid-ra-saas-prod"
}

import {
  to = azurerm_storage_account.prod
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod/providers/Microsoft.Storage/storageAccounts/sthybridrasaasprod"
}

import {
  to = module.monitoring.azurerm_application_insights.this
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-prod/providers/Microsoft.Insights/components/appi-hybrid-ra-saas-prod"
}
