variable "project_name" {
  type = string
}

variable "github_app_id" {
  type = string
}

variable "github_app_private_key" {
  type      = string
  sensitive = true
}

variable "github_app_installation_id" {
  type = string
}

variable "openai_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "webhook_secret" {
  type      = string
  sensitive = true
}
