"""GitHub issue interaction — fetching comments, building context, posting updates."""
from __future__ import annotations

from github import Github

import logger as log
from models import TaskPayload
from retry import retry_with_backoff


def fetch_issue_comments(payload: TaskPayload, token: str) -> str:
    """Fetch all comments on the issue and format them as markdown.

    Returns an empty string if fetching fails or there are no comments.
    """
    try:
        gh = Github(token)
        repo = gh.get_repo(payload.repository_full_name)
        issue = repo.get_issue(payload.issue_number)
        comments = list(issue.get_comments())
        if not comments:
            return ""
        return "\n\n## Issue Comments\n\n" + "\n\n---\n\n".join(
            f"**{c.user.login}** ({c.created_at.isoformat()}):\n{c.body}"
            for c in comments
        )
    except Exception as exc:
        log.warning("Failed to fetch issue comments", error=str(exc))
        return ""


def build_issue_message(payload: TaskPayload, token: str) -> str:
    """Build the full Aider prompt from issue title, body, and comments."""
    comments_text = fetch_issue_comments(payload, token)
    commit_instructions = (
        f"\n\n## Commit Message Guidelines\n\n"
        f"When committing changes, use this format for commit messages:\n"
        f"```\n"
        f"<type>: <description>\n\n"
        f"Closes #{payload.issue_number}\n"
        f"```\n"
        f"Where <type> is one of: feat, fix, docs, style, refactor, test, chore\n"
        f"The 'Closes #{payload.issue_number}' line is required to auto-close the issue when the PR is merged."
    )
    return (
        f"Issue #{payload.issue_number}: {payload.issue_title}\n\n"
        f"{payload.issue_body}\n"
        f"{comments_text}"
        f"{commit_instructions}"
    )


def post_comment(
    repo_full_name: str,
    issue_number: int,
    body: str,
    token: str,
) -> None:
    """Post a comment on a GitHub Issue or PR."""

    def _do_post_comment() -> None:
        gh = Github(token)
        repo = gh.get_repo(repo_full_name)
        issue = repo.get_issue(issue_number)
        issue.create_comment(body)

    retry_with_backoff(_do_post_comment)


def get_pr_branch(repo_full_name: str, pr_number: int, token: str) -> str | None:
    """Get the head branch name for a PR. Returns None if not found."""
    try:
        gh = Github(token)
        repo = gh.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        return pr.head.ref
    except Exception as exc:
        log.warning("Failed to get PR branch", error=str(exc))
        return None


class IssueNotifier:
    """Posts status comments on a GitHub issue/PR. Swallows failures."""

    def __init__(self, payload: TaskPayload, token: str) -> None:
        self._repo = payload.repository_full_name
        self._issue = payload.issue_number
        self._token = token

    def comment(self, body: str) -> None:
        try:
            post_comment(self._repo, self._issue, body, self._token)
        except Exception as exc:
            log.warning("Failed to post comment", error=str(exc))
