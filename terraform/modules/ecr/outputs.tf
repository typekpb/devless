output "repository_arn" {
  value = aws_ecr_repository.orchestrator.arn
}

output "repository_url" {
  value = aws_ecr_repository.orchestrator.repository_url
}

output "repository_bash_arn" {
  value = aws_ecr_repository.orchestrator_bash.arn
}

output "repository_bash_url" {
  value = aws_ecr_repository.orchestrator_bash.repository_url
}
