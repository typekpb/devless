"""Webhook handler Lambda — validates GitHub HMAC signature and enqueues to SQS."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
from datetime import datetime, timezone

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_sqs = boto3.client("sqs")

# Branch pattern created by the orchestrator
_DEVLESS_BRANCH_RE = re.compile(r"^issue-(\d+)$")


def validate_signature(payload: bytes, secret: str, header: str) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header)


def _build_issue_message(event: dict) -> dict | None:
    """Build SQS message from an issue or issue_comment event."""
    issue = event.get("issue", {})
    comment = event.get("comment", {})
    repository = event.get("repository", {})
    sender = event.get("sender", {})

    # Check if this is a comment on a PR (PRs have a pull_request key in the issue object)
    is_pr_comment = "pull_request" in issue and "comment" in event

    if is_pr_comment:
        msg_event_type = "pr_issue_comment"
        body = comment.get("body", "")
    elif "comment" in event:
        msg_event_type = "issue_comment"
        body = comment.get("body", "")
    else:
        msg_event_type = "issues"
        body = issue.get("body", "") or ""

    return {
        "event_type": msg_event_type,
        "issue_number": issue.get("number", 0),
        "issue_title": issue.get("title", ""),
        "issue_body": body,
        "repository_full_name": repository.get("full_name", ""),
        "sender_login": sender.get("login", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _build_pr_comment_message(event: dict) -> dict | None:
    """Build SQS message from a PR review comment. Returns None if not Devless-managed."""
    pull_request = event.get("pull_request", {})
    comment = event.get("comment", {})
    repository = event.get("repository", {})
    sender = event.get("sender", {})

    head_branch = pull_request.get("head", {}).get("ref", "")
    match = _DEVLESS_BRANCH_RE.match(head_branch) if head_branch else None
    if not match:
        return None

    return {
        "event_type": "pr_comment",
        "issue_number": int(match.group(1)),
        "issue_title": pull_request.get("title", ""),
        "issue_body": comment.get("body", ""),
        "repository_full_name": repository.get("full_name", ""),
        "sender_login": sender.get("login", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "branch": head_branch,
    }


def _build_pr_review_message(event: dict) -> dict | None:
    """Build SQS message from a PR review. Returns None if not Devless-managed."""
    pull_request = event.get("pull_request", {})
    review = event.get("review", {})
    repository = event.get("repository", {})
    sender = event.get("sender", {})

    head_branch = pull_request.get("head", {}).get("ref", "")
    match = _DEVLESS_BRANCH_RE.match(head_branch) if head_branch else None
    if not match:
        return None

    review_state = review.get("state", "")
    return {
        "event_type": "pr_review",
        "issue_number": int(match.group(1)),
        "issue_title": pull_request.get("title", ""),
        "issue_body": f"Review ({review_state}): {review.get('body', '')}",
        "repository_full_name": repository.get("full_name", ""),
        "sender_login": sender.get("login", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "branch": head_branch,
    }


def lambda_handler(event: dict, context) -> dict:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    signature_header = headers.get("x-hub-signature-256", "")
    raw_body: str = event.get("body") or ""
    payload_bytes = raw_body.encode("utf-8")

    webhook_secret = os.environ.get("WEBHOOK_SECRET", "")

    if not validate_signature(payload_bytes, webhook_secret, signature_header):
        logger.warning("HMAC validation failed")
        return {"statusCode": 401, "body": json.dumps({"error": "Unauthorized"})}

    try:
        github_payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.error("Failed to parse webhook body as JSON")
        return {"statusCode": 400, "body": json.dumps({"error": "Bad Request"})}

    gh_event = headers.get("x-github-event", "")

    # Ignore bots
    sender = github_payload.get("sender", {})
    sender_login = sender.get("login", "")
    if sender.get("type") == "Bot" or sender_login.endswith("[bot]"):
        logger.info("Ignoring event from bot: %s", sender_login)
        return {"statusCode": 200, "body": json.dumps({"status": "ignored"})}

    # Route to appropriate handler
    sqs_message = None
    if gh_event == "pull_request_review_comment":
        sqs_message = _build_pr_comment_message(github_payload)
    elif gh_event == "pull_request_review":
        if github_payload.get("review", {}).get("body"):
            sqs_message = _build_pr_review_message(github_payload)
    elif gh_event in ("issues", "issue_comment"):
        sqs_message = _build_issue_message(github_payload)

    if sqs_message is None:
        logger.info("Event ignored: %s", gh_event)
        return {"statusCode": 200, "body": json.dumps({"status": "ignored"})}

    queue_url = os.environ["SQS_QUEUE_URL"]
    _sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(sqs_message))
    logger.info("Enqueued message for issue %s", sqs_message.get("issue_number"))

    return {"statusCode": 202, "body": json.dumps({"status": "accepted"})}
