variable "project_name" {
  type = string
}

resource "aws_ecr_repository" "orchestrator" {
  name                 = "${var.project_name}-orchestrator"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

output "repository_arn" {
  value = aws_ecr_repository.orchestrator.arn
}

output "repository_url" {
  value = aws_ecr_repository.orchestrator.repository_url
}
