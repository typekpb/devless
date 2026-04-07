terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-central-1"
}

# --- Module calls ---

module "s3" {
  source       = "./modules/s3"
  project_name = var.project_name
}

module "secrets" {
  source                  = "./modules/secrets"
  project_name            = var.project_name
  github_app_id           = var.github_app_id
  github_app_private_key  = var.github_app_private_key
  github_app_installation_id = var.github_app_installation_id
  openai_api_key          = var.openai_api_key
  webhook_secret          = var.webhook_secret
  common_skills_repo_url  = var.common_skills_repo_url
}

module "sqs" {
  source       = "./modules/sqs"
  project_name = var.project_name
}

module "ecr" {
  source       = "./modules/ecr"
  project_name = var.project_name
}

module "iam" {
  source                        = "./modules/iam"
  project_name                  = var.project_name
  s3_bucket_arn                 = module.s3.bucket_arn
  sqs_queue_arn                 = module.sqs.main_queue_arn
  sqs_dlq_arn                   = module.sqs.dlq_arn
  ecr_repository_arn            = module.ecr.repository_arn
  param_arns                    = module.secrets.param_arns
  github_actions_org            = var.github_actions_org
}

module "ecs" {
  source                        = "./modules/ecs"
  project_name                  = var.project_name
  ecr_repository_url            = module.ecr.repository_url
  ecr_image_tag                 = var.ecr_image_tag
  execution_role_arn            = module.iam.ecs_execution_role_arn
  task_role_arn                 = module.iam.ecs_task_role_arn
  sqs_queue_url                 = module.sqs.main_queue_url
  sqs_queue_arn                 = module.sqs.main_queue_arn
  s3_bucket_name                = module.s3.bucket_name
  github_app_id_param_arn             = module.secrets.github_app_id_param_arn
  openai_api_key_param_arn      = module.secrets.openai_api_key_param_arn
  common_skills_repo_param_arn  = module.secrets.common_skills_repo_param_arn
  github_app_private_key_param_arn = module.secrets.github_app_private_key_param_arn
  github_app_installation_id_param_arn = module.secrets.github_app_installation_id_param_arn
}

module "lambda" {
  source                      = "./modules/lambda"
  project_name                = var.project_name
  webhook_handler_role_arn    = module.iam.lambda_webhook_role_arn
  dlq_processor_role_arn      = module.iam.lambda_dlq_processor_role_arn
  sqs_dlq_arn                 = module.sqs.dlq_arn
  sqs_queue_url               = module.sqs.main_queue_url
  webhook_secret              = var.webhook_secret
  github_app_id               = var.github_app_id
  github_app_private_key      = var.github_app_private_key
  github_app_installation_id  = var.github_app_installation_id
}

module "api_gateway" {
  source                       = "./modules/api_gateway"
  project_name                 = var.project_name
  webhook_handler_invoke_arn   = module.lambda.webhook_handler_invoke_arn
  webhook_handler_function_name = module.lambda.webhook_handler_function_name
}
