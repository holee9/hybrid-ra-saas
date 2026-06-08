# Terraform 1.5+ declarative import blocks
# Run: terraform plan to verify drift = 0 after applying imports

import {
  to = azurerm_resource_group.staging
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-staging"
}

import {
  to = module.container_app_env.azurerm_container_app_environment.this
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-staging/providers/Microsoft.App/managedEnvironments/cae-hybrid-ra-saas-staging"
}

import {
  to = module.key_vault_staging.azurerm_key_vault.this
  id = "/subscriptions/a49390df-1886-495c-9fb0-cf8faf1aa5ef/resourceGroups/rg-hybrid-ra-saas-staging/providers/Microsoft.KeyVault/vaults/kv-hybrid-ra-staging"
}
