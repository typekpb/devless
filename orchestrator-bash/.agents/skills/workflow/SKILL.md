---
name: workflow
description: High-level workflow for handling GitHub events
---

# Workflow Instructions

You are an AI coding agent that handles GitHub issues and PR feedback.

## For `issue` or `issue_comment` Events

1. Clone repo and create feature branch (see `git` skill)
2. Comment on issue: "🚀 Working on this issue..." (see `github` skill)
3. Check for target repo skills in `/workspace/.agents/skills/`
4. Implement the requested changes (see `files` skill)
5. Run tests if configured (see `testing` skill)
6. Commit and push changes (see `git` skill)
7. Create PR (see `github` skill)
8. Comment on issue with PR link

## For `pr_comment`, `pr_review`, or `pr_issue_comment` Events

1. Clone repo and checkout existing branch (see `git` skill)
2. Address the review feedback
3. Run tests if configured (see `testing` skill)
4. Commit and push changes (see `git` skill)
5. Comment on PR: "✅ Addressed the feedback"

## Environment Variables

- `$REPO` - full repo name (owner/repo)
- `$BRANCH` - branch to work on (issue-N)
- `$ISSUE_NUMBER` - issue or PR number
- `$OWNER` - repo owner
- `$REPO_NAME` - repo name without owner

Note: GitHub authentication is handled at the network layer - no token env var needed.

## Important Rules

1. Always work in `/workspace` directory
2. Never hardcode credentials - use environment variables
3. Run tests before pushing if configured
4. Keep commits atomic and well-described
5. If unclear, ask for clarification instead of guessing
6. Check command output after each step
7. Follow target repo skills if present in `.agents/skills/`

## Error Handling

If stuck after 3 attempts:
```bash
gh issue comment $ISSUE_NUMBER --repo $REPO --body "🤔 I encountered an issue: <description>. Could you provide more details?"
```
