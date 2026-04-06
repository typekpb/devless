terraform {
  backend "s3" {
    bucket       = "codex-dev-team-tf-state"
    key          = "codex-dev-team/terraform.tfstate"
    region       = "eu-central-1"
    use_lockfile = true
    encrypt      = true
  }
}
