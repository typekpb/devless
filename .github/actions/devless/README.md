# Devless — GitHub Action

A composite GitHub Action that registers a GitHub webhook on your project repository, pointing it at the deployed Devless API Gateway endpoint. Once registered, new issues and issue comments automatically trigger the AI-powered development pipeline.

## Prerequisites

- Devless infrastructure deployed via Terraform (API Gateway, SQS, ECS, etc.)
- An AWS IAM role configured for GitHub Actions OIDC federation
- The webhook HMAC secret stored in AWS SSM Parameter Store (SecureString)

## Inputs

| Input | Required | Description |
|---|---|---|
| `aws_role_arn` | Yes | IAM role ARN to assume via OIDC (no long-lived credentials needed) |
| `api_gateway_url` | Yes | Deployed API Gateway webhook endpoint URL |
| `webhook_secret_param_name` | Yes | SSM Parameter Store name for the webhook HMAC secret |

## Usage

Create `.github/workflows/devless.yml` in your project repository:

```yaml
name: Devless Setup
on:
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  setup:
    runs-on: ubuntu-latest
    steps:
      - uses: typekpb/devless/.github/actions/devless@v1
        with:
          aws_role_arn: ${{ secrets.AWS_ROLE_ARN }}
          api_gateway_url: ${{ secrets.DEVLESS_API_URL }}
          webhook_secret_param_name: /devless/webhook-secret
```

## How It Works

1. Authenticates to AWS using OIDC federation with the provided role ARN.
2. Retrieves the webhook HMAC secret from SSM Parameter Store (SecureString, decrypted).
3. Registers (or updates) a GitHub webhook on the current repository that fires on `issues` and `issue_comment` events.

## Project Configuration

Add a `.devless/config.yml` to your project repository to customize behavior:

```yaml
model: bedrock/anthropic.claude-sonnet-4-20250514-v1:0
max_iterations: 10
test_command: "pytest"
```
