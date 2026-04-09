---
name: github
description: GitHub CLI operations for issues, PRs, and comments
---

# GitHub CLI Operations

## Comment on Issue
```bash
gh issue comment $ISSUE_NUMBER --repo $REPO --body "🚀 Working on this issue..."
```

## Create Pull Request
```bash
gh pr create \
  --repo $REPO \
  --head $BRANCH \
  --title "<issue title>" \
  --body "Closes #$ISSUE_NUMBER

## Changes
- <list changes made>

Implemented by devless 🤖"
```

## Comment on PR
```bash
gh pr comment $ISSUE_NUMBER --repo $REPO --body "✅ Addressed the feedback and pushed changes."
```

## View Issue Details
```bash
gh issue view $ISSUE_NUMBER --repo $REPO
```

## View PR Details
```bash
gh pr view $ISSUE_NUMBER --repo $REPO
```

## Status Emojis
- 🚀 Starting work
- ✅ Completed successfully
- 🤔 Need clarification
- ⚠️ Error encountered
