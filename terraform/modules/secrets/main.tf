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
