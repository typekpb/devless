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
