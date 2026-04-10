---
name: workflow
description: High-level workflows for handling GitHub events
---

# Workflow Instructions

## New Issue Workflow

When handling a new issue (`issues` or `issue_comment` event):

1. **Acknowledge** - Post comment: "🚀 Devless is working on this issue..."
2. **Clone** - Use `clone_repository` tool
3. **Branch** - Use `create_branch` with name `issue-{number}`
4. **Config** - Use `read_project_config` to get test command and model
5. **Implement** - Use `run_aider` with issue details and config
6. **Push** - Use `push_branch` to push changes
7. **PR** - Use `create_pull_request` with "Closes #{number}" in body
8. **Complete** - Post comment: "✅ Created PR: {url}"

## PR Feedback Workflow

When handling PR feedback (`pr_comment`, `pr_review`, `pr_issue_comment` events):

1. **Get PR** - Use `get_pull_request` to get PR details including `head_branch`
2. **Validate** - Check if branch matches `issue-N` pattern (devless-managed)
   - If NOT devless-managed: Post comment "This PR was not created by Devless, skipping" and stop
3. **Acknowledge** - Post comment: "📝 Addressing your feedback..."
4. **Clone** - Use `clone_repository` tool
5. **Checkout** - Use `checkout_branch` with the PR's head branch
6. **Config** - Use `read_project_config`
7. **Implement** - Use `run_aider` with the feedback
8. **Push** - Use `push_branch` to push changes
9. **Complete** - Post comment: "✅ Pushed changes addressing feedback"

## CI Fix Workflow

When handling CI failures (`ci_fix` event):

1. **Acknowledge** - Post comment: "🔄 Analyzing CI failure..."
2. **Clone** - Use `clone_repository` tool
3. **Checkout** - Use `checkout_branch` with the failing branch
4. **Config** - Use `read_project_config`
5. **Implement** - Use `run_aider` with CI error details
6. **Push** - Use `push_branch`
7. **Complete** - Post comment: "🔧 Pushed fix for CI failure"

## Error Handling

If any step fails:
1. Post comment with ⚠️ emoji explaining the error
2. Include relevant error details (truncated if long)
3. Ask for help if the error is unclear
