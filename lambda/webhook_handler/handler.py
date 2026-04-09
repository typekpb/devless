"""Webhook handler Lambda — validates GitHub HMAC signature and enqueues to SQS."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re

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

    if "comment" in event:
        msg_event_type = "issue_comment"
        body = comment.get("body", "")
    else:
        msg_event_type = "issues"
        body = issue.get("body", "") or ""

    from datetime import datetime, timezone

    return {
        "event_type": msg_event_type,
        "issue_number": issue.get("number", 0),
        "issue_title": issue.get("title", ""),
        "issue_body": body,
        "repository_full_name": repository.get("full_name", ""),
        "sender_login": sender.get("login", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _build_ci_fix_message(event: dict) -> dict | None:
    """Build SQS message from a check_run failure on a Devless branch.

    Returns None if the event is not a completed failure on an issue-N branch.
    """
    check_run = event.get("check_run", {})
    if check_run.get("conclusion") not in ("failure", "timed_out"):
        return None

    # Only process check runs on branches created by the orchestrator
    head_branch = ""
    
    # Try to get branch from pull_requests first
    for pr in check_run.get("pull_requests", []):
        head_branch = pr.get("head", {}).get("ref", "")
        if head_branch:
            break

    # Fallback: try to get branch from check_suite
    if not head_branch:
        check_suite = check_run.get("check_suite", {})
        head_branch = check_suite.get("head_branch", "")

    if not head_branch:
        logger.info("Could not determine branch from check_run event")
        return None

    match = _DEVLESS_BRANCH_RE.match(head_branch)
    if not match:
        logger.info("Branch %s is not a Devless-managed branch", head_branch)
        return None  # not a Devless-managed branch

    issue_number = int(match.group(1))
    repository = event.get("repository", {})
    output = check_run.get("output", {})
    summary = output.get("summary", "") or output.get("text", "") or ""
    check_name = check_run.get("name", "CI")

    from datetime import datetime, timezone

    return {
        "event_type": "ci_fix",
        "issue_number": issue_number,
        "issue_title": f"CI fix: {check_name} failed on {head_branch}",
        "issue_body": (
            f"The check `{check_name}` failed on branch `{head_branch}`.\n\n"
            f"## Failure details\n\n{summary[:3000]}"
        ),
        "repository_full_name": repository.get("full_name", ""),
        "sender_login": "github-actions",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "branch": head_branch,
    }


def _build_workflow_run_fix_message(event: dict) -> dict | None:
    """Build SQS message from a workflow_run failure on a Devless branch.

    Returns None if the event is not a completed failure on an issue-N branch.
    """
    workflow_run = event.get("workflow_run", {})
    
    # Only process completed failures
    if workflow_run.get("status") != "completed":
        return None
    if workflow_run.get("conclusion") not in ("failure", "timed_out"):
        return None

    head_branch = workflow_run.get("head_branch", "")
    if not head_branch:
        return None

    match = _DEVLESS_BRANCH_RE.match(head_branch)
    if not match:
        logger.info("Branch %s is not a Devless-managed branch", head_branch)
        return None

    issue_number = int(match.group(1))
    repository = event.get("repository", {})
    workflow_name = workflow_run.get("name", "CI")
    html_url = workflow_run.get("html_url", "")

    from datetime import datetime, timezone

    return {
        "event_type": "ci_fix",
        "issue_number": issue_number,
        "issue_title": f"CI fix: {workflow_name} failed on {head_branch}",
        "issue_body": (
            f"The workflow `{workflow_name}` failed on branch `{head_branch}`.\n\n"
            f"[View workflow run]({html_url})\n\n"
            f"Please analyze the failure and fix the code."
        ),
        "repository_full_name": repository.get("full_name", ""),
        "sender_login": "github-actions",
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

    # Determine event type from GitHub header
    gh_event = headers.get("x-github-event", "")

    # Ignore events from bots (e.g. our own GitHub App posting comments)
    sender = github_payload.get("sender", {})
    if sender.get("type") == "Bot":
        logger.info("Ignoring event from bot: %s", sender.get("login", ""))
        return {"statusCode": 200, "body": json.dumps({"status": "ignored"})}

    sqs_message = None
    if gh_event == "check_run":
        sqs_message = _build_ci_fix_message(github_payload)
    elif gh_event == "workflow_run":
        sqs_message = _build_workflow_run_fix_message(github_payload)
    elif gh_event in ("issues", "issue_comment"):
        sqs_message = _build_issue_message(github_payload)

    if sqs_message is None:
        logger.info("Event ignored (not actionable): %s", gh_event)
        return {"statusCode": 200, "body": json.dumps({"status": "ignored"})}

    queue_url = os.environ["SQS_QUEUE_URL"]
    _sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(sqs_message))
    logger.info("Enqueued message for issue %s", sqs_message.get("issue_number"))

    return {"statusCode": 202, "body": json.dumps({"status": "accepted"})}
