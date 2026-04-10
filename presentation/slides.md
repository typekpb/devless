---
marp: true
theme: default
paginate: true
backgroundColor: #1a1a2e
color: #eaeaea
style: |
  section {
    font-family: 'Segoe UI', sans-serif;
  }
  h1, h2 {
    color: #00d4ff;
  }
  code {
    background: #16213e;
    color: #00d4ff;
  }
  a {
    color: #00d4ff;
  }
  table {
    font-size: 0.8em;
  }
  .columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }
---

# Devless
## AI-Powered Code Generation from GitHub Issues

*An army of AI workers at your service*

---

# The Business Problem

## What I wanted

- **Technical PO capability** — create issues, get working code
- **Scalable workforce** — handle multiple issues in parallel
- **Review-ready PRs** — not just code dumps, but mergeable changes
- **Feedback loop** — respond to PR comments, iterate

## The dream

> Open an issue → AI implements it → PR opens → Review → Merge

No context switching. No waiting. Just describe what you need.

---

# Available Tools (3rd Party)

| Tool | Status | Notes |
|------|--------|-------|
| **GitHub Copilot Workspace** | ❌ Discontinued | Sunset May 2025 |
| **Sweep AI** | ❌ Pivoted | Now JetBrains autocomplete only |
| **Devin** | ✅ Active | $500/mo, autonomous agent |
| **SWE-agent** | ✅ Open source | Research project, DIY setup |
| **CodeRabbit** | ✅ Active | PR review only, no code gen |
| **Aider** | ✅ Open source | CLI tool, no GitHub integration |

**Gap:** No open, affordable, issue-to-PR solution with AWS/Bedrock support.

---

# The Solution: Devless

![Architecture](../docs/architecture.drawio.svg)

**Flow:** Issue → Webhook → Lambda → SQS → Orchestrator → Aider/Bedrock → PR

---

# Key Components

## Webhook Handler (Lambda)
- Validates GitHub HMAC signatures
- Filters bot events (prevents loops!)
- Routes: issues, PR comments, PR reviews

## Orchestrator (ECS Fargate)
- State machine: `pending → cloned → agent_loop → pr_created → complete`
- Checkpoints to S3 (resume on failure)
- Runs Aider with Bedrock backend

## Aider Integration
- Open source CLI tool for AI coding
- Supports multiple LLM backends
- Handles git operations, test runs, retries

---

# State Machine

*(See sequence diagram in README.md)*

**States:** `pending → cloned → agent_loop → pr_created → complete`

- **pending** — waiting to start
- **cloned** — repo cloned, branch created
- **agent_loop** — Aider generating code, running tests
- **pr_created** — branch pushed, PR opened
- **complete** — success comment posted

---

# Demo Time

## Live Demo

**Repository:** [github.com/typekpb/devless-demo](https://github.com/typekpb/devless-demo)

**Deployed App:** [typekpb.github.io/devless-demo](https://typekpb.github.io/devless-demo)

### What we'll see:
1. Open an issue describing a feature
2. Devless picks it up, posts status
3. PR opens with implementation
4. Review, comment, iterate
5. Merge

---

# Target Repo Setup

Minimal config in `.devless/config.yml`:

```yaml
model: bedrock/eu.anthropic.claude-sonnet-4-20250514-v1:0
test_command: npm test
max_iterations: 10
```

Webhook events needed:
- `Issues`, `Issue comments`
- `Pull request review comments`, `Pull request reviews`

That's it. No agents to install, no tokens in the repo.

---

# Development Journey

## Tools Used

| Tool | Purpose | Cost |
|------|---------|------|
| **Kiro** | Specs + vibe coding | $20/mo subscription |
| **Bedrock** | LLM backend (Claude) | AWS sandbox (free for us) |
| **Aider** | Code generation engine | Open source |
| **Terraform** | Infrastructure | Open source |

## Why Kiro?
- Spec-driven development worked well for architecture
- "Vibe coding" for rapid iteration
- Free tier credits ran out fast → subscription needed

---

# Why Bedrock?

## Advantages
- **AWS sandbox available** — no credit card, no approvals
- **IAM authentication** — no API keys to manage
- **Claude Sonnet 4** — excellent for code generation
- **Regional endpoints** — EU data residency

## Aider Integration
```bash
aider --model bedrock/eu.anthropic.claude-sonnet-4-20250514-v1:0
```

Just works. No OpenAI key needed.

---

# Running Locally

## Test Aider directly
```bash
cd /tmp && git clone https://github.com/typekpb/devless-demo.git
cd devless-demo

export AWS_REGION=eu-central-1
aider --model bedrock/eu.anthropic.claude-sonnet-4-20250514-v1:0 \
  --message "Add a dark mode toggle"
```

## Run the orchestrator
```bash
cd orchestrator
pip install -e .
export SQS_QUEUE_URL=... S3_BUCKET=... GITHUB_APP_ID=...
python -m main
```

Polls SQS, processes issues exactly like ECS.

---

# Lessons Learned

## What Worked Well ✅

- **Aider** — battle-tested, handles edge cases
- **State machine** — clean separation, easy to debug
- **Checkpoints** — resume after failures, no lost work
- **GitHub App auth** — short-lived tokens, no PATs
- **Bedrock** — zero config with IAM roles

## What I'd Do Differently 🔄

- Start with simpler event handling (disabled CI auto-fix)
- More upfront time on prompt engineering
- Consider LangGraph for complex workflows (future)

---

# What I Didn't Have Time For

- **OpenAI / Azure backends** — code is there, not tested
- **Codex integration** — would be interesting to compare
- **Multi-repo orchestration** — one repo at a time for now
- **Cost optimization** — Bedrock pricing is fine, but could cache
- **Better error messages** — Aider output can be cryptic

---

# Architecture Diagram

![Architecture](../docs/architecture.drawio.svg)

*Editable source: `docs/architecture.drawio` — open in [draw.io](https://app.diagrams.net)*

---

# Infrastructure (Terraform)

```
terraform/
├── main.tf              # Root module
├── modules/
│   ├── api_gateway/     # Webhook endpoint
│   ├── lambda/          # Webhook handler
│   ├── sqs/             # Task queue + DLQ
│   ├── ecs/             # Orchestrator service
│   ├── ecr/             # Container registry
│   ├── iam/             # Roles & policies
│   └── s3/              # Checkpoints
└── terraform.tfvars     # Your config
```

One `terraform apply` deploys everything.

---

# Cost Breakdown (Estimate)

| Service | Usage | Cost/month |
|---------|-------|------------|
| Lambda | ~1000 invocations | ~$0 |
| SQS | ~1000 messages | ~$0 |
| ECS Fargate | 0.25 vCPU, 0.5GB | ~$10 |
| Bedrock (Claude) | ~100 issues | ~$5-20 |
| S3 | Checkpoints | ~$0 |

**Total:** ~$15-30/month for moderate usage

*Sandbox account = $0 for us*

---

# Alternative Architectures Explored

## just-bash (WASM sandbox)

| Aspect | Feasibility | Notes |
|--------|-------------|-------|
| GitHub API (curl) | ✅ Works | Issues, PRs, comments |
| Read files (API) | ✅ Works | Base64 decode from Contents API |
| Write files (API) | ✅ Works | One commit per file |
| Run tests | ❌ No | No binaries (pytest, npm) |
| Git clone | ❌ No | No git binary |

**Verdict:** Great for API-only workflows (triage, comments, simple file edits). Not viable when tests/builds needed.

---

# Alternative: Docker Sandbox

| Aspect | Original Orchestrator | Docker Sandbox | Docker + Auth Proxy |
|--------|----------------------|----------------|---------------------|
| Code complexity | ~800 lines | ~300 lines | ~300 lines + proxy |
| Git/GitHub ops | Orchestrator handles | LLM via bash | LLM via bash |
| Secret exposure | ✅ Hidden | ⚠️ Exposed | ✅ Hidden (proxy injects) |
| Adding features | Code changes | Add SKILL.md | Add SKILL.md |
| Test execution | Orchestrator runs | LLM runs | LLM runs |
| Infra complexity | Python only | + Docker | + Docker + proxy |

**Auth Proxy approach:** Network proxy intercepts requests, injects auth headers. Token never enters sandbox.

---

# Security: Why Secrets Matter

## Risks of LLM seeing secrets

| Risk | Example | Impact |
|------|---------|--------|
| Accidental logging | LLM runs `env` or `echo $TOKEN` | Token in logs/output |
| Prompt injection | Malicious issue body tricks LLM | Exfiltrate to attacker URL |
| Training data | Token sent to LLM provider | Potential leak in future models |
| Repo secrets | `.env` files in cloned repo | Exposed to LLM context |

## Mitigations

- **Original orchestrator:** Secrets never reach LLM ✅
- **Docker + proxy:** Network-level auth injection ✅
- **Docker (simple):** Accept risk, use short-lived scoped tokens ⚠️

---

# Comparison: GitHub Copilot Coding Agent

| Aspect | Devless | GitHub Copilot Agent |
|--------|---------|---------------------|
| Setup | Deploy infra (Terraform) | ✅ Zero setup |
| Cost | ~$15-30/mo + Bedrock | GitHub subscription |
| LLM choice | Any (Bedrock, OpenAI) | GitHub's models only |
| Customization | Full control (skills, prompts) | Limited |
| Self-hosted | ✅ Yes | ❌ No |
| Data residency | Your AWS region | GitHub's infra |
| Open source | ✅ Yes | ❌ No |

**When to use Devless:** Need control, custom models, or data residency.
**When to use Copilot:** Just want it to work, no infra to manage.

---

# Future Ideas

- **LangGraph / Instructor** — smarter routing based on issue content
- **Multi-agent** — planner + coder + reviewer
- **PR auto-merge** — after approval + CI pass
- **Slack integration** — notifications, approvals
- **Cost tracking** — per-issue token usage
- **Fine-tuning** — on our codebase patterns

---

# Q&A

## Links

- **Devless repo:** [github.com/typekpb/devless](https://github.com/typekpb/devless)
- **Demo repo:** [github.com/typekpb/devless-demo](https://github.com/typekpb/devless-demo)
- **Live demo:** [typekpb.github.io/devless-demo](https://typekpb.github.io/devless-demo)
- **Aider:** [aider.chat](https://aider.chat)
- **Kiro:** [kiro.dev](https://kiro.dev)

---

# Backup: Event Flow Detail

*(Refer to sequence diagram in README.md for detailed flow)*

**Summary:**
1. GitHub Issue → API Gateway → Lambda (validate HMAC)
2. Lambda → SQS (buffer, retry)
3. ECS polls SQS → runs Aider with Bedrock
4. Aider generates code → ECS pushes branch → opens PR
