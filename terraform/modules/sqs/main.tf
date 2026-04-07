resource "aws_sqs_queue" "dlq" {
  name = "${var.project_name}-dlq"
}

resource "aws_sqs_queue" "main" {
  name                       = "${var.project_name}-tasks"
  visibility_timeout_seconds = 1200

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}
