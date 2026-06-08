# Backend Bootstrap Procedure
#
# The Terraform remote state backend is configured per-environment inside
# environments/prod/main.tf and environments/staging/main.tf.
#
# This root-level file exists only to document the bootstrap sequence.
#
# Bootstrap order:
#   1. cd environments/prod
#   2. terraform init          # local state only (no backend block yet)
#   3. terraform apply         # creates azurerm_storage_account.prod + azurerm_storage_container.tfstate
#   4. terraform init          # re-run — Terraform migrates state to the Azure backend
#
# After bootstrap, all subsequent runs use the Azure backend automatically.
#
# OIDC note: ARM_USE_OIDC=true is set via env in the GitHub Actions workflow.
# Local runs require: az login (interactive) or service principal with OIDC.
