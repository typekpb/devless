"""GitHub issue interaction — fetching comments and building context."""
from __future__ import annotations

from github import Github

import logger as log
from models import TaskPayload
from pr_manager import post_comment


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
    return (
        f"Issue #{payload.issue_number}: {payload.issue_title}\n\n"
        f"{payload.issue_body}\n"
        f"{comments_text}"
    )


class IssueNotifier:
    """Posts status comments on a GitHub issue. Swallows failures."""

    def __init__(self, payload: TaskPayload, token: str) -> None:
        self._repo = payload.repository_full_name
        self._issue = payload.issue_number
        self._token = token

    def comment(self, body: str) -> None:
        try:
            post_comment(self._repo, self._issue, body, self._token)
        except Exception as exc:
            log.warning("Failed to post comment", error=str(exc))
