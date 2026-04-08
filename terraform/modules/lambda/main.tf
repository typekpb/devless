data "aws_region" "current" {}

# --- Build Lambda packages (install deps + zip) ---

resource "null_resource" "webhook_handler_build" {
  triggers = {
    handler = filesha256("${path.module}/../../../lambda/webhook_handler/handler.py")
    deps    = filesha256("${path.module}/../../../lambda/webhook_handler/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      rm -rf ${path.module}/builds/webhook_handler
      mkdir -p ${path.module}/builds/webhook_handler
      pip install -r ${path.module}/../../../lambda/webhook_handler/requirements.txt \
        -t ${path.module}/builds/webhook_handler --quiet
      cp ${path.module}/../../../lambda/webhook_handler/handler.py \
        ${path.module}/builds/webhook_handler/
    EOT
  }
}

data "archive_file" "webhook_handler" {
  type        = "zip"
  source_dir  = "${path.module}/builds/webhook_handler"
  output_path = "${path.module}/builds/webhook_handler.zip"
  depends_on  = [null_resource.webhook_handler_build]
}

resource "null_resource" "dlq_processor_build" {
  triggers = {
    handler = filesha256("${path.module}/../../../lambda/dlq_processor/handler.py")
    deps    = filesha256("${path.module}/../../../lambda/dlq_processor/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      rm -rf ${path.module}/builds/dlq_processor
      mkdir -p ${path.module}/builds/dlq_processor
      pip install -r ${path.module}/../../../lambda/dlq_processor/requirements.txt \
        -t ${path.module}/builds/dlq_processor --quiet
      cp ${path.module}/../../../lambda/dlq_processor/handler.py \
        ${path.module}/builds/dlq_processor/
    EOT
  }
}

data "archive_file" "dlq_processor" {
  type        = "zip"
  source_dir  = "${path.module}/builds/dlq_processor"
  output_path = "${path.module}/builds/dlq_processor.zip"
  depends_on  = [null_resource.dlq_processor_build]
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
      GITHUB_APP_ID              = var.github_app_id
      GITHUB_APP_PRIVATE_KEY     = var.github_app_private_key
      GITHUB_APP_INSTALLATION_ID = var.github_app_installation_id
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
