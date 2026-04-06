variable "project_name" {
  type = string
}

variable "webhook_handler_role_arn" {
  type = string
}

variable "dlq_processor_role_arn" {
  type = string
}

variable "sqs_dlq_arn" {
  type = string
}

variable "webhook_secret" {
  type      = string
  sensitive = true
}

variable "sqs_queue_url" {
  type = string
}

variable "github_token" {
  type      = string
  sensitive = true
}

data "aws_region" "current" {}

# --- Zip archives for Lambda code ---

data "archive_file" "webhook_handler" {
  type        = "zip"
  source_dir  = "${path.module}/../../../lambda/webhook_handler"
  output_path = "${path.module}/builds/webhook_handler.zip"
  excludes    = ["__pycache__"]
}

data "archive_file" "dlq_processor" {
  type        = "zip"
  source_dir  = "${path.module}/../../../lambda/dlq_processor"
  output_path = "${path.module}/builds/dlq_processor.zip"
  excludes    = ["__pycache__"]
}

# --- Webhook Handler Lambda ---

resource "aws_lambda_function" "webhook_handler" {
  function_name    = "${var.project_name}-webhook-handler"
  role             = var.webhook_handler_role_arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  memory_size      = 128
  timeout          = 10
  filename         = data.archive_file.webhook_handler.output_path
  source_code_hash = data.archive_file.webhook_handler.output_base64sha256

  environment {
    variables = {
      SQS_QUEUE_URL  = var.sqs_queue_url
      WEBHOOK_SECRET = var.webhook_secret
    }
  }
}

# --- DLQ Processor Lambda ---

resource "aws_lambda_function" "dlq_processor" {
  function_name    = "${var.project_name}-dlq-processor"
  role             = var.dlq_processor_role_arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  memory_size      = 128
  timeout          = 30
  filename         = data.archive_file.dlq_processor.output_path
  source_code_hash = data.archive_file.dlq_processor.output_base64sha256

  environment {
    variables = {
      GITHUB_TOKEN = var.github_token
    }
  }
}

# SQS event source mapping for DLQ processor
resource "aws_lambda_event_source_mapping" "dlq_processor" {
  event_source_arn = var.sqs_dlq_arn
  function_name    = aws_lambda_function.dlq_processor.arn
  batch_size       = 1
  enabled          = true
}

# --- Outputs ---

output "webhook_handler_invoke_arn" {
  value = aws_lambda_function.webhook_handler.invoke_arn
}

output "webhook_handler_function_name" {
  value = aws_lambda_function.webhook_handler.function_name
}
