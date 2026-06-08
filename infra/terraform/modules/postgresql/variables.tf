variable "name" {
  description = "PostgreSQL Flexible Server name"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "pg_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "16"
}

variable "sku_name" {
  description = "PostgreSQL SKU (e.g. Standard_B1ms)"
  type        = string
  default     = "Standard_B1ms"
}

variable "storage_mb" {
  description = "Storage size in MB"
  type        = number
  default     = 32768
}

variable "administrator_login" {
  description = "PostgreSQL administrator login"
  type        = string
  sensitive   = true
}

variable "administrator_password" {
  description = "PostgreSQL administrator password"
  type        = string
  sensitive   = true
}
