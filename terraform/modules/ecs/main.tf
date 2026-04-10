data "aws_region" "current" {}

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "orchestrator" {
  name              = "/ecs/${var.project_name}-orchestrator"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "orchestrator" {
  family                   = "${var.project_name}-orchestrator"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name      = "orchestrator"
    image     = "${var.ecr_repository_url}:${var.ecr_image_tag}"
    essential = true

    environment = [
      { name = "SQS_QUEUE_URL", value = var.sqs_queue_url },
      { name = "S3_BUCKET", value = var.s3_bucket_name },
      { name = "AWS_REGION", value = data.aws_region.current.name },
    ]

    secrets = concat(
      [
        { name = "GITHUB_APP_ID", valueFrom = var.github_app_id_param_arn },
        { name = "GITHUB_APP_PRIVATE_KEY", valueFrom = var.github_app_private_key_param_arn },
        { name = "GITHUB_APP_INSTALLATION_ID", valueFrom = var.github_app_installation_id_param_arn },
      ],
      var.openai_api_key_param_arn != "" ? [{ name = "OPENAI_API_KEY", valueFrom = var.openai_api_key_param_arn }] : [],
    )

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.orchestrator.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "ecs"
      }
    }

    stopTimeout = 120
  }])
}

# --- ECS Service (long-running, polls SQS) ---

resource "aws_security_group" "orchestrator" {
  name        = "${var.project_name}-orchestrator"
  description = "Orchestrator ECS tasks - egress only"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_ecs_service" "orchestrator" {
  name            = "${var.project_name}-orchestrator"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.orchestrator.arn
  desired_count   = 0
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.orchestrator.id]
    assign_public_ip = true
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}

# --- Auto Scaling (scale-to-zero based on SQS depth) ---

resource "aws_appautoscaling_target" "orchestrator" {
  max_capacity       = 1
  min_capacity       = 0
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.orchestrator.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "scale_out" {
  name               = "${var.project_name}-scale-out"
  policy_type        = "StepScaling"
  resource_id        = aws_appautoscaling_target.orchestrator.resource_id
  scalable_dimension = aws_appautoscaling_target.orchestrator.scalable_dimension
  service_namespace  = aws_appautoscaling_target.orchestrator.service_namespace

  step_scaling_policy_configuration {
    adjustment_type         = "ExactCapacity"
    cooldown                = 30
    metric_aggregation_type = "Average"

    step_adjustment {
      metric_interval_lower_bound = 0
      scaling_adjustment          = 1
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "sqs_messages_high" {
  alarm_name          = "${var.project_name}-sqs-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Average"
  threshold           = 0
  alarm_actions       = [aws_appautoscaling_policy.scale_out.arn]

  dimensions = {
    QueueName = var.sqs_queue_name
  }
}

resource "aws_appautoscaling_policy" "scale_in_zero" {
  name               = "${var.project_name}-scale-in-zero"
  policy_type        = "StepScaling"
  resource_id        = aws_appautoscaling_target.orchestrator.resource_id
  scalable_dimension = aws_appautoscaling_target.orchestrator.scalable_dimension
  service_namespace  = aws_appautoscaling_target.orchestrator.service_namespace

  step_scaling_policy_configuration {
    adjustment_type         = "ExactCapacity"
    cooldown                = 300
    metric_aggregation_type = "Average"

    step_adjustment {
      metric_interval_upper_bound = 0
      scaling_adjustment          = 0
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "sqs_messages_zero" {
  alarm_name          = "${var.project_name}-sqs-zero"
  comparison_operator = "LessThanOrEqualToThreshold"
  evaluation_periods  = 30
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Average"
  threshold           = 0
  alarm_actions       = [aws_appautoscaling_policy.scale_in_zero.arn]

  dimensions = {
    QueueName = var.sqs_queue_name
  }
}


# --- Orchestrator Agent (Strands-based implementation) ---

resource "aws_cloudwatch_log_group" "orchestrator_agent" {
  name              = "/ecs/${var.project_name}-orchestrator-agent"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "orchestrator_agent" {
  family                   = "${var.project_name}-orchestrator-agent"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name      = "orchestrator-agent"
    image     = "${var.ecr_repository_agent_url}:${var.ecr_image_tag}"
    essential = true

    environment = [
      { name = "SQS_QUEUE_URL", value = var.sqs_queue_url },
      { name = "S3_BUCKET", value = var.s3_bucket_name },
      { name = "AWS_REGION", value = data.aws_region.current.name },
    ]

    secrets = concat(
      [
        { name = "GITHUB_APP_ID", valueFrom = var.github_app_id_param_arn },
        { name = "GITHUB_APP_PRIVATE_KEY", valueFrom = var.github_app_private_key_param_arn },
        { name = "GITHUB_APP_INSTALLATION_ID", valueFrom = var.github_app_installation_id_param_arn },
      ],
      var.openai_api_key_param_arn != "" ? [{ name = "OPENAI_API_KEY", valueFrom = var.openai_api_key_param_arn }] : [],
    )

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.orchestrator_agent.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "ecs"
      }
    }

    stopTimeout = 120
  }])
}

resource "aws_ecs_service" "orchestrator_agent" {
  name            = "${var.project_name}-orchestrator-agent"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.orchestrator_agent.arn
  desired_count   = 0  # Disabled by default, enable manually to switch from Python orchestrator
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.orchestrator.id]
    assign_public_ip = true
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
}
