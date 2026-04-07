resource "aws_ecr_repository" "orchestrator" {
  name                 = "${var.project_name}-orchestrator"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
