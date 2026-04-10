# Orchestrator Agent

Strands-based agent orchestrator. The agent decides what to do based on SYSTEM.md and SKILL.md instructions, using tools for git/GitHub/code operations.

## Architecture

![Architecture](../docs/agent-flow.svg)

## Project Structure

```
orchestrator-agent/
├── main.py              # SQS polling, entry point
├── agent.py             # Strands agent setup
├── sqs_consumer.py      # SQS message handling
├── github_app.py        # Token minting
├── tools/
│   ├── __init__.py      # Exports all tools
│   ├── github.py        # Issues, PRs, comments
│   ├── git.py           # Clone, branch, push
│   └── code.py          # Aider, file reading
├── .agents/
│   ├── SYSTEM.md        # Main agent instructions
│   └── skills/
│       ├── workflow/SKILL.md   # Step-by-step workflows
│       ├── github/SKILL.md     # GitHub tool usage
│       ├── git/SKILL.md        # Git tool usage
│       └── code/SKILL.md       # Aider usage
├── tests/
├── Dockerfile
└── pyproject.toml

# Infrastructure (shared with main orchestrator)
../terraform/           # ECR, ECS, IAM, etc.
../.github/workflows/   # CI/CD pipelines
```

## Security: Secrets Not Exposed to LLM

The GitHub token is:
1. Passed to `init_github()` and `init_git()` at startup
2. Stored in module-level variables
3. Used internally by tools when making API calls
4. **Never** included in tool inputs/outputs or LLM context

The LLM only sees:
- Tool names and descriptions
- Tool results (e.g., "Cloned repository", "PR created")
- Never the actual token

## Setup

### Local Development

**Note:** Requires Python 3.10-3.12 (aider-chat doesn't support Python 3.13+)

```bash
# Create and activate virtual environment (use Python 3.12)
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[test]"

# Copy and edit environment config
cp .env.example .env
# Edit .env with your values

# Run tests
pytest

# Manual test
python main.py owner/repo 123 "Issue title" "Issue body"

# SQS polling mode
python main.py
```

### Docker Build

```bash
docker build -t devless-agent .
docker run -e SQS_QUEUE_URL=xxx -e GITHUB_APP_ID=xxx ... devless-agent
```

### Deploy to AWS

```bash
cd ../terraform
terraform init
terraform apply
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SQS_QUEUE_URL` | Yes | SQS queue URL for tasks |
| `GITHUB_APP_ID` | Yes | GitHub App ID |
| `GITHUB_APP_INSTALLATION_ID` | Yes | GitHub App Installation ID |
| `GITHUB_APP_PRIVATE_KEY` | Yes* | Private key (or use _FILE) |
| `GITHUB_APP_PRIVATE_KEY_FILE` | Yes* | Path to private key file |
| `BEDROCK_MODEL` | No | Model ID (default: claude-3-haiku) |
| `AWS_REGION` | No | AWS region (default: us-east-1) |

## Customization

Edit files in `.agents/` to change behavior:
- `SYSTEM.md` - Main agent instructions
- `skills/workflow/SKILL.md` - Workflow steps
- `skills/github/SKILL.md` - GitHub conventions
- `skills/git/SKILL.md` - Git conventions
- `skills/code/SKILL.md` - Aider usage

No code changes needed for workflow modifications.

## Comparison with Original Orchestrator

| Aspect | Original | Agent-based |
|--------|----------|-------------|
| State machine | Hardcoded in Python | Agent decides via SKILL.md |
| Error handling | try/except in code | Agent handles via tools |
| Adding workflows | Code changes | Edit SKILL.md files |
| Secrets | Hidden in orchestrator | Hidden in tools |
| Code changes | Aider | Aider (via tool) |
| Lines of code | ~800 | ~400 |
