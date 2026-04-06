variable "project_name" {
  type = string
}

resource "aws_s3_bucket" "workspaces" {
  bucket = "${var.project_name}-workspaces"
}

resource "aws_s3_bucket_lifecycle_configuration" "workspaces" {
  bucket = aws_s3_bucket.workspaces.id

  rule {
    id     = "expire-workspaces"
    status = "Enabled"

    filter {
      prefix = "workspaces/"
    }

    expiration {
      days = 30
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "workspaces" {
  bucket = aws_s3_bucket.workspaces.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "workspaces" {
  bucket                  = aws_s3_bucket.workspaces.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_arn" {
  value = aws_s3_bucket.workspaces.arn
}

output "bucket_name" {
  value = aws_s3_bucket.workspaces.bucket
}
