variable "name" {
  description = "Application Insights name"
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

variable "application_type" {
  description = "Application Insights type (web, other, etc.)"
  type        = string
  default     = "web"
}

variable "workspace_id" {
  description = "Log Analytics Workspace ID (optional)"
  type        = string
  default     = null
}
