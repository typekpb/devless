variable "project_name" {
  type = string
}

variable "ecr_repository_url" {
  type = string
}

variable "ecr_image_tag" {
  type    = string
  default = "latest"
}

variable "execution_role_arn" {
  type = string
}

variable "task_role_arn" {
  type = string
}

variable "sqs_queue_url" {
  type = string
}

variable "s3_bucket_name" {
  type = string
}

variable "sqs_queue_arn" {
  type = string
}

variable "github_app_id_param_arn" {
  description = "SSM parameter ARN for the GitHub App ID"
  type        = string
}

variable "openai_api_key_param_arn" {
  description = "SSM parameter ARN for the OpenAI API key (empty if not using OpenAI)"
  type        = string
  default     = ""
}

variable "github_app_private_key_param_arn" {
  description = "SSM parameter ARN for the GitHub App private key"
  type        = string
}

variable "github_app_installation_id_param_arn" {
  description = "SSM parameter ARN for the GitHub App installation ID"
  type        = string
}

variable "sqs_queue_name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}
