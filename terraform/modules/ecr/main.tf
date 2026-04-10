resource "aws_ecr_repository" "orchestrator" {
  name                 = "${var.project_name}-orchestrator"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "orchestrator_agent" {
  name                 = "${var.project_name}-orchestrator-agent"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
