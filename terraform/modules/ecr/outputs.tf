output "repository_arn" {
  value = aws_ecr_repository.orchestrator.arn
}

output "repository_url" {
  value = aws_ecr_repository.orchestrator.repository_url
}
