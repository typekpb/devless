output "repository_arn" {
  value = aws_ecr_repository.orchestrator.arn
}

output "repository_url" {
  value = aws_ecr_repository.orchestrator.repository_url
}

output "repository_agent_arn" {
  value = aws_ecr_repository.orchestrator_agent.arn
}

output "repository_agent_url" {
  value = aws_ecr_repository.orchestrator_agent.repository_url
}
