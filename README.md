# Codex Dev Team — Infrastructure

Automated coding agent that picks up GitHub issues, generates code changes with
Aider, and opens Pull Requests. Automatically fixes CI failures on its
own branches. PRs auto-merge after passing review and checks.

## Architecture

![Architecture](docs/architecture.drawio.svg)

> To edit: open [`docs/architecture.drawio`](docs/architecture.drawio) in [draw.io](https://app.diagrams.net), then export as `architecture.drawio.svg` to update the rendered diagram.

Events handled:
- `issues` / `issue_comment` → full pipeline (clone → Aider → PR)
- `check_run` (failure on `issue-N` branches) → CI fix pipeline (checkout → Aider fix → push)

## How it works end-to-end

1. You open a GitHub issue describing a feature or bug fix
2. Webhook fires → Lambda validates HMAC → SQS message queued
3. ECS auto-scales from 0 → orchestrator picks up the message
4. Orchestrator clones repo, installs skills, runs Aider, opens PR
5. CI runs on the PR — if it fails, orchestrator auto-fixes and pushes
6. You review the PR — once approved + CI green, it auto-merges
7. ECS scales back to 0 when the queue is empty

---

## Deployment

There are two ways to deploy: automated via GitHub Actions (recommended) or
manually from your local machine.

### Option A: GitHub Actions (recommended)

Push to `main` and everything deploys automatically. One-time setup:

1. Create the S3 state bucket:

```bash
aws s3 mb s3://codex-dev-team-tf-state --region eu-central-1
```

2. Do an initial `terraform apply` locally to create the OIDC role (chicken-and-egg):

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values (private key is handled separately)

# Save your GitHub App private key PEM file:
# pbpaste > github-app-private-key.pem   (or copy it however you prefer)

export TF_VAR_github_app_private_key="$(cat github-app-private-key.pem)"
terraform init
terraform apply
```

3. Note the `github_actions_role_arn` output and add these GitHub Actions secrets to this repo:

| Secret | Value |
|---|---|
| `AWS_REGION` | `eu-central-1` |
| `AWS_ROLE_ARN` | the `github_actions_role_arn` output |
| `TF_VAR_github_app_id` | your GitHub App ID |
| `TF_VAR_github_app_private_key` | your GitHub App private key (PEM) |
| `TF_VAR_github_app_installation_id` | your GitHub App installation ID |
| `TF_VAR_openai_api_key` | your OpenAI API key (optional, only for OpenAI backend) |
| `TF_VAR_webhook_secret` | your webhook HMAC secret |
| `TF_VAR_github_actions_org` | your GitHub org name |
| `TF_VAR_common_skills_repo_url` | your common skills repo URL |

4. Push to `main`. The `deploy.yml` workflow handles everything from now on:
   - `terraform apply` (infra changes)
   - Docker build + push to ECR
   - ECS redeployment

Every subsequent push to `main` deploys automatically. No manual steps.

### Option B: Manual deployment

If you prefer to deploy without CI/CD:

1. Create the S3 state bucket:

```bash
aws s3 mb s3://codex-dev-team-tf-state --region eu-central-1
```

2. Create `terraform/terraform.tfvars` from the example:

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

3. Deploy infrastructure:

```bash
cd terraform
export TF_VAR_github_app_private_key="$(cat github-app-private-key.pem)"
terraform init
terraform apply
```

4. Build and push the orchestrator image:

```bash
ECR_URL=$(terraform output -raw ecr_repository_url)

aws ecr get-login-password --region eu-central-1 | \
  docker login --username AWS --password-stdin "$ECR_URL"

docker build -t "$ECR_URL:latest" ../orchestrator/
docker push "$ECR_URL:latest"
```

5. Trigger ECS redeployment:

```bash
aws ecs update-service \
  --cluster codex-dev-team-cluster \
  --service codex-dev-team-orchestrator \
  --force-new-deployment \
  --region eu-central-1
```

Repeat steps 3–5 for every change.

---

## Bootstrapping a target repository

Once the infrastructure is deployed, each repo you want Codex to work on
needs a one-time webhook registration and a CI workflow.

### Required: CI workflow

`.github/workflows/ci.yml` — must run on pull requests so Codex can detect
failures and auto-fix them. The actual steps depend on your language/stack:

```yaml
name: CI
on:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # Add your language-specific build/test steps here, e.g.:
      # Python:  pip install ".[test]" && pytest
      # Node.js: npm ci && npm test
      # Go:      go test ./...
      # Java:    mvn verify
      # Rust:    cargo test
      - run: <your-test-command>
```

### One-time: webhook registration

`.github/workflows/codex-setup.yml` — run once via Actions → Run workflow:

```yaml
name: Codex Dev Team Setup
on:
  workflow_dispatch:
permissions:
  id-token: write
  contents: read
jobs:
  setup:
    runs-on: ubuntu-latest
    steps:
      - uses: typekpb/codex-infra/.github/actions/codex-dev-team@main
        with:
          aws_role_arn: ${{ secrets.AWS_ROLE_ARN }}
          api_gateway_url: ${{ secrets.CODEX_API_URL }}
          webhook_secret_param_name: /codex-dev-team/webhook-secret
```

Add `AWS_ROLE_ARN` and `CODEX_API_URL` (the `api_gateway_url` terraform output)
as secrets in the target repo, then run the workflow.

### Optional: project config

`.codex/config.yml` — customize how Codex processes your repo:

```yaml
# Amazon Bedrock backend (default — uses ECS task role, no API key needed)
model: bedrock/anthropic.claude-sonnet-4-20250514-v1:0
test_command: npm test   # command Aider runs to verify changes (default: pytest)
max_iterations: 10       # max Aider retry loops (default: 10)
skills_repo: https://github.com/typekpb/project-skills.git  # optional
```

```yaml
# OpenAI backend (requires OPENAI_API_KEY on the orchestrator)
model: o3                # or: gpt-4o, o1, gpt-4-turbo
test_command: npm test   # command Aider runs to verify changes (default: pytest)
max_iterations: 10       # max Aider retry loops (default: 10)
skills_repo: https://github.com/typekpb/project-skills.git  # optional
```

See [`examples/`](examples/) for ready-to-copy config files.

The `model` field uses Aider's model naming: `bedrock/<model-id>` for Bedrock
(default), or plain name for OpenAI (e.g. `o3`). When using Bedrock, the ECS
task role authenticates automatically — no API key needed. For OpenAI, set
`OPENAI_API_KEY` on the orchestrator via SSM.

The `test_command` should match whatever your CI runs. Examples:
- Python: `pytest`
- Node.js: `npm test`
- Go: `go test ./...`
- Java: `mvn test`
- Rust: `cargo test`
- Generic: `make test`

### Optional: repo-specific skills

```
.agents/skills/
  my-skill/
    SKILL.md
```

### Auto-merge setup

In the target repo settings:
1. Enable "Allow auto-merge" under General → Pull Requests
2. Add a branch protection rule on the default branch:
   - Require pull request reviews (at least 1 approval)
   - Require status checks to pass (select your CI workflow)

### Expected repo structure

Any language, any framework — just needs a CI workflow and optionally a config:

```
your-project/
├── .codex/config.yml           # Optional: test_command, skills_repo, max_iterations
├── .agents/skills/             # Optional: repo-specific Codex skills
├── .github/workflows/
│   ├── ci.yml                  # Required: runs your tests on PRs
│   └── codex-setup.yml         # One-time: registers the webhook
└── ...                         # Your code (any language/structure)
```

Then open an issue — Codex picks it up, posts status comments, opens a PR,
auto-fixes CI failures, and auto-merges after approval.

---

## Prerequisites

- AWS account with CLI configured
- Terraform >= 1.10
- Docker
- GitHub App (with permissions: issues, pull requests, contents, checks)
- OpenAI API key (only if using OpenAI backend instead of Bedrock)
