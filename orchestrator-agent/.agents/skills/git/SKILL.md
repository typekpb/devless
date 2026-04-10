---
name: git
description: Git operations via tools
---

# Git Operations

## Available Tools

### clone_repository
Clone the target repository into a temporary workspace.
```
clone_repository()
```
Returns the path to the cloned repo.

### create_branch
Create and checkout a new branch.
```
create_branch(branch_name="issue-123")
```

### checkout_branch
Checkout an existing branch (for PR feedback).
```
checkout_branch(branch_name="issue-123")
```

### get_status
Check current git status.
```
get_status()
```
Returns branch name, changed files, staged files, untracked files.

### push_branch
Push a branch to remote.
```
push_branch(branch_name="issue-123")
```

## Branch Naming

Always use `issue-{number}` format for branches:
- `issue-123` for issue #123
- This allows the system to track which branches are managed by Devless

## Workflow Order

1. Always `clone_repository` first
2. Then either `create_branch` (new issue) or `checkout_branch` (existing PR)
3. Make changes via `run_aider`
4. Finally `push_branch`
