variable "project_name" {
  type = string
}

variable "github_token" {
  type      = string
  sensitive = true
}

variable "openai_api_key" {
  type      = string
  sensitive = true
}

variable "webhook_secret" {
  type      = string
  sensitive = true
}

variable "common_skills_repo_url" {
  description = "Git URL of the shared/common skills repository"
  type        = string
  default     = ""
}

# --- SSM Parameters (SecureString for secrets, String for config) ---

resource "aws_ssm_parameter" "github_token" {
  name  = "/${var.project_name}/github-token"
  type  = "SecureString"
  value = var.github_token
}

resource "aws_ssm_parameter" "openai_api_key" {
  name  = "/${var.project_name}/openai-api-key"
  type  = "SecureString"
  value = var.openai_api_key
}

resource "aws_ssm_parameter" "webhook_secret" {
  name  = "/${var.project_name}/webhook-secret"
  type  = "SecureString"
  value = var.webhook_secret
}

resource "aws_ssm_parameter" "common_skills_repo_url" {
  name  = "/${var.project_name}/common-skills-repo-url"
  type  = "String"
  value = var.common_skills_repo_url
}

# --- Outputs ---

output "param_arns" {
  description = "ARNs of all SSM parameters (for IAM policies)"
  value = [
    aws_ssm_parameter.github_token.arn,
    aws_ssm_parameter.openai_api_key.arn,
    aws_ssm_parameter.webhook_secret.arn,
    aws_ssm_parameter.common_skills_repo_url.arn,
  ]
}

output "github_token_param_name" {
  value = aws_ssm_parameter.github_token.name
}

output "github_token_param_arn" {
  value = aws_ssm_parameter.github_token.arn
}

output "openai_api_key_param_name" {
  value = aws_ssm_parameter.openai_api_key.name
}

output "openai_api_key_param_arn" {
  value = aws_ssm_parameter.openai_api_key.arn
}

output "webhook_secret_param_name" {
  value = aws_ssm_parameter.webhook_secret.name
}

output "webhook_secret_param_arn" {
  value = aws_ssm_parameter.webhook_secret.arn
}

output "common_skills_repo_param_name" {
  value = aws_ssm_parameter.common_skills_repo_url.name
}

output "common_skills_repo_param_arn" {
  value = aws_ssm_parameter.common_skills_repo_url.arn
}
