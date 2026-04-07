variable "project_name" {
  type = string
}

variable "s3_bucket_arn" {
  type = string
}

variable "sqs_queue_arn" {
  type = string
}

variable "ecr_repository_arn" {
  type = string
}

variable "param_arns" {
  description = "ARNs of all SSM parameters (secrets + config)"
  type        = list(string)
}

variable "sqs_dlq_arn" {
  type = string
}

variable "github_actions_org" {
  type = string
}

variable "api_gateway_arn" {
  description = "ARN of the API Gateway (used for GitHub Actions role permissions)"
  type        = string
  default     = ""
}
