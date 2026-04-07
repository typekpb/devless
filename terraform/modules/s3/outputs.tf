output "bucket_arn" {
  value = aws_s3_bucket.workspaces.arn
}

output "bucket_name" {
  value = aws_s3_bucket.workspaces.bucket
}
