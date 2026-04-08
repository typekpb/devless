"""DLQ processor Lambda — posts failure comment on GitHub Issue after 3 failed attempts."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

import boto3
from github import Auth, Github, GithubIntegration


# ---------------------------------------------------------------------------
# Structured JSON logging (consistent with orchestrator/src/logger.py)
# ---------------------------------------------------------------------------

def _log(level: str, message: str, **extra: Any) -> None:
    record: dict[str, Any] = {
        "level": level,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    record.update(extra)
    print(json.dumps(record), file=sys.stdout, flush=True)


def _info(message: str, **extra: Any) -> None:
    _log("INFO", message, **extra)


def _error(message: str, **extra: Any) -> None:
    _log("ERROR", message, **extra)


# ---------------------------------------------------------------------------
# GitHub App token helper
# ---------------------------------------------------------------------------

def _get_installation_token() -> str:
    """Mint a short-lived GitHub App installation token."""
    app_id = int(os.environ["GITHUB_APP_ID"])
    private_key = os.environ["GITHUB_APP_PRIVATE_KEY"]
    installation_id = int(os.environ["GITHUB_APP_INSTALLATION_ID"])

    auth = Auth.AppAuth(app_id, private_key)
    gi = GithubIntegration(auth=auth)
    return gi.get_access_token(installation_id).token


# ---------------------------------------------------------------------------
# GitHub comment helper
# ---------------------------------------------------------------------------

def _post_comment(repo_full_name: str, issue_number: int, body: str, token: str) -> None:
    """Post a comment on a GitHub Issue."""
    gh = Github(token)
    repo = gh.get_repo(repo_full_name)
    issue = repo.get_issue(issue_number)
    issue.create_comment(body)


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------

_FAILURE_COMMENT = (
    "\u26a0\ufe0f This task failed and has been moved to the "
    "dead letter queue. Please review the issue description and add a comment "
    "to retry."
)


def lambda_handler(event: dict, context) -> None:
    """Process messages that landed on the Dead Letter Queue."""
    token = _get_installation_token()

    for record in event.get("Records", []):
        try:
            payload = json.loads(record["body"])
            issue_number = int(payload["issue_number"])
            repo_full_name = payload["repository_full_name"]
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            _error("Failed to parse DLQ record", error=str(exc))
            continue

        _info(
            "Posting failure comment",
            issue_number=issue_number,
            repository=repo_full_name,
        )

        try:
            _post_comment(repo_full_name, issue_number, _FAILURE_COMMENT, token)
            _info("Failure comment posted", issue_number=issue_number)
        except Exception as exc:
            _error(
                "Failed to post GitHub comment",
                issue_number=issue_number,
                repository=repo_full_name,
                error=str(exc),
            )
            raise
