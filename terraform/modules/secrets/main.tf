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

# --- SSM Parameters ---

resource "aws_ssm_parameter" "github_app_id" {
  name  = "/${var.project_name}/github-app-id"
  type  = "String"
  value = var.github_app_id
}

resource "aws_ssm_parameter" "github_app_private_key" {
  name  = "/${var.project_name}/github-app-private-key"
  type  = "SecureString"
  value = var.github_app_private_key
}

resource "aws_ssm_parameter" "github_app_installation_id" {
  name  = "/${var.project_name}/github-app-installation-id"
  type  = "String"
  value = var.github_app_installation_id
}

resource "aws_ssm_parameter" "openai_api_key" {
  count = var.openai_api_key != "" ? 1 : 0
  name  = "/${var.project_name}/openai-api-key"
  type  = "SecureString"
  value = var.openai_api_key
}

resource "aws_ssm_parameter" "webhook_secret" {
  name  = "/${var.project_name}/webhook-secret"
  type  = "SecureString"
  value = var.webhook_secret
}

output "param_arns" {
  description = "ARNs of all SSM parameters (for IAM policies)"
  value = flatten([
    aws_ssm_parameter.github_app_id.arn,
    aws_ssm_parameter.github_app_private_key.arn,
    aws_ssm_parameter.github_app_installation_id.arn,
    aws_ssm_parameter.openai_api_key[*].arn,
    aws_ssm_parameter.webhook_secret.arn,
  ])
}

output "github_app_id_param_arn" {
  value = aws_ssm_parameter.github_app_id.arn
}

output "github_app_private_key_param_arn" {
  value = aws_ssm_parameter.github_app_private_key.arn
}

output "github_app_installation_id_param_arn" {
  value = aws_ssm_parameter.github_app_installation_id.arn
}

output "openai_api_key_param_arn" {
  value = length(aws_ssm_parameter.openai_api_key) > 0 ? aws_ssm_parameter.openai_api_key[0].arn : ""
}

output "webhook_secret_param_name" {
  value = aws_ssm_parameter.webhook_secret.name
}

output "webhook_secret_param_arn" {
  value = aws_ssm_parameter.webhook_secret.arn
}
