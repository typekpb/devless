output "ecs_execution_role_arn" {
  value = aws_iam_role.ecs_execution.arn
}

output "ecs_task_role_arn" {
  value = aws_iam_role.ecs_task.arn
}

output "lambda_webhook_role_arn" {
  value = aws_iam_role.lambda_webhook.arn
}

output "lambda_dlq_processor_role_arn" {
  value = aws_iam_role.lambda_dlq_processor.arn
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}
