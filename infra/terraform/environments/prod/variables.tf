variable "subscription_id" {
  description = "Azure Subscription ID"
  type        = string
}

variable "tenant_id" {
  description = "Azure Tenant ID"
  type        = string
}

variable "db_admin_login" {
  description = "PostgreSQL admin login"
  type        = string
  sensitive   = true
}

variable "db_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

variable "crawler_image" {
  description = "Docker image for cloud-control-plane crawler (ACR). Defaults to quickstart placeholder; overridden by CI on v* tag push."
  type        = string
  default     = "mcr.microsoft.com/k8se/quickstart:latest"
}
