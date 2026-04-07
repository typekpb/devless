variable "project_name" {
  description = "Short name used to prefix all resources"
  type        = string
  default     = "codex-dev-team"
}

variable "github_app_id" {
  description = "GitHub App ID"
  type        = string
}

variable "github_app_private_key" {
  description = "GitHub App private key (PEM format)"
  type        = string
  sensitive   = true
}

variable "github_app_installation_id" {
  description = "GitHub App installation ID for the target org/account"
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "webhook_secret" {
  description = "Shared HMAC secret for GitHub webhook validation"
  type        = string
  sensitive   = true
}

variable "ecr_image_tag" {
  description = "Docker image tag for the Orchestrator in ECR"
  type        = string
  default     = "latest"
}

variable "github_actions_org" {
  description = "GitHub organization for OIDC federation (e.g. your-org)"
  type        = string
}

variable "common_skills_repo_url" {
  description = "Git URL of the shared/common skills repository (e.g. https://github.com/org/codex-skills.git)"
  type        = string
  default     = ""
}
