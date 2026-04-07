output "webhook_handler_invoke_arn" {
  value = aws_lambda_function.webhook_handler.invoke_arn
}

output "webhook_handler_function_name" {
  value = aws_lambda_function.webhook_handler.function_name
}
