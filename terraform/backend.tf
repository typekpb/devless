terraform {
  backend "s3" {
    bucket       = "devless-tf-state"
    key          = "devless/terraform.tfstate"
    region       = "eu-central-1"
    use_lockfile = true
    encrypt      = true
  }
}
