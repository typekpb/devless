output "api_gateway_url" {
  description = "Webhook endpoint URL (use as GitHub webhook Payload URL)"
  value       = "${module.api_gateway.api_endpoint}/webhook"
}

output "sqs_queue_url" {
  description = "SQS main queue URL"
  value       = module.sqs.main_queue_url
}

output "ecr_repository_url" {
  description = "ECR repository URL for Orchestrator image"
  value       = module.ecr.repository_url
}

output "s3_bucket_name" {
  description = "S3 workspace bucket name"
  value       = module.s3.bucket_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC federation"
  value       = module.iam.github_actions_role_arn
}

output "webhook_secret" {
  description = "Webhook HMAC secret for GitHub webhook registration"
  value       = var.webhook_secret
  sensitive   = true
}
