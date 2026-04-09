---
name: git
description: Git operations for cloning, branching, committing, and pushing
---

# Git Operations

## Clone Repository
```bash
# Token is injected at network layer - no need to configure credentials
git clone https://github.com/$REPO.git /workspace
cd /workspace
```

## Configure Identity
```bash
git config user.name "devless[bot]"
git config user.email "devless[bot]@users.noreply.github.com"
```

## Create Feature Branch
```bash
git checkout -b $BRANCH
```

## Checkout Existing Branch
```bash
git checkout $BRANCH
```

## Stage and Commit
```bash
git add -A
git commit -m "feat: <short description>

<detailed explanation if needed>

Closes #$ISSUE_NUMBER"
```

## Push Branch
```bash
git push -u origin $BRANCH
```

## Commit Message Guidelines
- `feat:` for new features
- `fix:` for bug fixes or addressing feedback
- Include `Closes #$ISSUE_NUMBER` in the body
