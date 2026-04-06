"""SQS message polling, parsing, and lifecycle management."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass

import boto3
from pydantic import ValidationError

from models import TaskPayload

_sqs = boto3.client("sqs")


@dataclass
class SQSMessage:
    """Wraps a received SQS message with its payload and receipt handle."""
    payload: TaskPayload
    receipt_handle: str


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
    payload = parse_payload(msg["Body"])
    return SQSMessage(payload=payload, receipt_handle=msg["ReceiptHandle"])


def parse_payload(raw: str) -> TaskPayload:
    """Deserialize a JSON string into a TaskPayload.

    Raises:
        ValueError: if the JSON is malformed or missing required fields.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"SQS message body is not valid JSON: {exc}") from exc

    try:
        return TaskPayload.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"SQS message has invalid fields: {exc}") from exc


def delete_message(queue_url: str, receipt_handle: str) -> None:
    """Delete an SQS message after successful processing."""
    client = boto3.client("sqs")
    client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
