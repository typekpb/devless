"""Tests for the webhook handler Lambda."""
import hashlib
import hmac
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import handler as handler_module
from handler import lambda_handler, validate_signature


def _sign(body: str, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def _make_event(body: dict, secret: str, gh_event: str = "issues") -> dict:
    raw = json.dumps(body)
    return {
        "headers": {
            "x-hub-signature-256": _sign(raw, secret),
            "x-github-event": gh_event,
        },
        "body": raw,
    }


ISSUE_PAYLOAD = {
    "action": "opened",
    "issue": {"number": 7, "title": "Bug", "body": "Fix it"},
    "repository": {"full_name": "org/repo"},
    "sender": {"login": "user"},
}

SECRET = "test-secret"
QUEUE_URL = "https://sqs.test/queue"


@patch.object(handler_module, "_sqs", MagicMock())
def test_valid_issue_returns_202():
    event = _make_event(ISSUE_PAYLOAD, SECRET)
    with patch.dict(os.environ, {"WEBHOOK_SECRET": SECRET, "SQS_QUEUE_URL": QUEUE_URL}):
        resp = lambda_handler(event, None)
    assert resp["statusCode"] == 202


@patch.object(handler_module, "_sqs", MagicMock())
def test_invalid_signature_returns_401():
    event = _make_event(ISSUE_PAYLOAD, SECRET)
    with patch.dict(os.environ, {"WEBHOOK_SECRET": "wrong-secret", "SQS_QUEUE_URL": QUEUE_URL}):
        resp = lambda_handler(event, None)
    assert resp["statusCode"] == 401


@patch.object(handler_module, "_sqs", MagicMock())
def test_bad_json_returns_400():
    event = {
        "headers": {"x-hub-signature-256": _sign("not json{", SECRET), "x-github-event": "issues"},
        "body": "not json{",
    }
    with patch.dict(os.environ, {"WEBHOOK_SECRET": SECRET, "SQS_QUEUE_URL": QUEUE_URL}):
        resp = lambda_handler(event, None)
    assert resp["statusCode"] == 400


@patch.object(handler_module, "_sqs", MagicMock())
def test_unknown_event_returns_200_ignored():
    event = _make_event({"action": "ping"}, SECRET, gh_event="ping")
    with patch.dict(os.environ, {"WEBHOOK_SECRET": SECRET, "SQS_QUEUE_URL": QUEUE_URL}):
        resp = lambda_handler(event, None)
    assert resp["statusCode"] == 200
    assert "ignored" in resp["body"]


@patch.object(handler_module, "_sqs", MagicMock())
def test_enqueued_message_contains_issue_number():
    mock_sqs = MagicMock()
    event = _make_event(ISSUE_PAYLOAD, SECRET)
    with patch.dict(os.environ, {"WEBHOOK_SECRET": SECRET, "SQS_QUEUE_URL": QUEUE_URL}):
        with patch.object(handler_module, "_sqs", mock_sqs):
            lambda_handler(event, None)
    body = json.loads(mock_sqs.send_message.call_args.kwargs["MessageBody"])
    assert body["issue_number"] == 7


def test_validate_signature_accepts_valid():
    payload = b"hello"
    sig = "sha256=" + hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
    assert validate_signature(payload, "secret", sig) is True


def test_validate_signature_rejects_wrong_secret():
    payload = b"hello"
    sig = "sha256=" + hmac.new(b"secret", payload, hashlib.sha256).hexdigest()
    assert validate_signature(payload, "wrong", sig) is False


def test_validate_signature_rejects_empty():
    assert validate_signature(b"hello", "secret", "") is False
    assert validate_signature(b"hello", "secret", None) is False


@patch.object(handler_module, "_sqs", MagicMock())
def test_check_run_failure_on_devless_branch_enqueues():
    check_run_payload = {
        "check_run": {
            "conclusion": "failure",
            "name": "CI",
            "head_sha": "abc123",
            "pull_requests": [{"head": {"ref": "issue-42"}}],
            "output": {"summary": "Tests failed"},
        },
        "repository": {"full_name": "org/repo"},
    }
    mock_sqs = MagicMock()
    event = _make_event(check_run_payload, SECRET, gh_event="check_run")
    with patch.dict(os.environ, {"WEBHOOK_SECRET": SECRET, "SQS_QUEUE_URL": QUEUE_URL}):
        with patch.object(handler_module, "_sqs", mock_sqs):
            resp = lambda_handler(event, None)
    assert resp["statusCode"] == 202
    body = json.loads(mock_sqs.send_message.call_args.kwargs["MessageBody"])
    assert body["event_type"] == "ci_fix"
    assert body["issue_number"] == 42
