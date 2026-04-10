"""SQS message polling and lifecycle management."""

import json
from dataclasses import dataclass
from typing import Literal

import boto3
from pydantic import BaseModel, ValidationError


class TaskPayload(BaseModel):
    """Represents the SQS message payload from a GitHub webhook event."""

    event_type: Literal[
        "issues", "issue_comment", "ci_fix", "pr_comment", "pr_review", "pr_issue_comment"
    ]
    issue_number: int
    issue_title: str
    issue_body: str
    repository_full_name: str
    sender_login: str
    timestamp: str  # ISO 8601
    branch: str | None = None


@dataclass
class SQSMessage:
    """Wraps a received SQS message with its payload and receipt handle."""

    payload: TaskPayload
    receipt_handle: str


_sqs = boto3.client("sqs")


def poll_message(queue_url: str, wait_seconds: int = 20) -> SQSMessage | None:
    """Long-poll SQS for a single message."""
    resp = _sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=wait_seconds,
    )
    messages = resp.get("Messages", [])
    if not messages:
        return None

    msg = messages[0]
    try:
        data = json.loads(msg["Body"])
        payload = TaskPayload.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        print(f"==> Invalid message, skipping: {e}")
        delete_message(queue_url, msg["ReceiptHandle"])
        return None

    return SQSMessage(payload=payload, receipt_handle=msg["ReceiptHandle"])


def delete_message(queue_url: str, receipt_handle: str) -> None:
    """Delete an SQS message after successful processing."""
    _sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
