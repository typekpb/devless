variable "project_name" {
  type = string
}

variable "webhook_handler_role_arn" {
  type = string
}

variable "dlq_processor_role_arn" {
  type = string
}

variable "sqs_dlq_arn" {
  type = string
}

variable "webhook_secret" {
  type      = string
  sensitive = true
}

variable "sqs_queue_url" {
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
