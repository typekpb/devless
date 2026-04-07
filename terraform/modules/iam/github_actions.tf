# --- GitHub Actions OIDC Provider + Role ---

resource "aws_iam_openid_connect_provider" "github_actions" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_actions" {
  name = "${var.project_name}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = aws_iam_openid_connect_provider.github_actions.arn }
      Condition = {
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_actions_org}/*:*"
        }
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_actions" {
  name = "${var.project_name}-github-actions"
  role = aws_iam_role.github_actions.id

  policy = templatefile("${path.module}/policies/github_actions.json.tpl", {
    project_name       = var.project_name
    region             = data.aws_region.current.name
    account_id         = data.aws_caller_identity.current.account_id
    ecr_repository_arn = var.ecr_repository_arn
    s3_bucket_arn      = var.s3_bucket_arn
  })
}
