"""Tests for the DLQ processor Lambda handler."""
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import handler as handler_module


def _make_sqs_event(*payloads: dict) -> dict:
    return {
        "Records": [{"body": json.dumps(p)} for p in payloads],
    }


def _make_payload(issue_number=42, repo="owner/repo"):
    return {
        "issue_number": issue_number,
        "repository_full_name": repo,
        "event_type": "issues",
        "issue_title": "Test",
        "issue_body": "body",
        "sender_login": "user",
        "timestamp": "2025-01-01T00:00:00Z",
    }


@patch.object(handler_module, "_get_installation_token", return_value="fake-token")
@patch.object(handler_module, "_post_comment")
def test_posts_failure_comment(mock_comment, mock_token):
    """Handler posts a failure comment for each DLQ record."""
    event = _make_sqs_event(_make_payload(42, "owner/repo"))

    handler_module.lambda_handler(event, None)

    mock_comment.assert_called_once()
    args = mock_comment.call_args
    assert args[0][0] == "owner/repo"
    assert args[0][1] == 42
    assert "failed and has been moved" in args[0][2]
    assert args[0][3] == "fake-token"


@patch.object(handler_module, "_get_installation_token", return_value="fake-token")
@patch.object(handler_module, "_post_comment")
def test_processes_multiple_records(mock_comment, mock_token):
    """Handler processes all records in the batch."""
    event = _make_sqs_event(
        _make_payload(1, "org/repo-a"),
        _make_payload(2, "org/repo-b"),
    )

    handler_module.lambda_handler(event, None)

    assert mock_comment.call_count == 2


@patch.object(handler_module, "_get_installation_token", return_value="fake-token")
@patch.object(handler_module, "_post_comment")
def test_skips_malformed_records(mock_comment, mock_token):
    """Handler skips records with invalid JSON or missing fields."""
    event = {
        "Records": [
            {"body": "not json"},
            {"body": json.dumps({"issue_number": 1})},  # missing repo
            {"body": json.dumps(_make_payload(99, "org/good"))},
        ],
    }

    handler_module.lambda_handler(event, None)

    # Only the valid record should trigger a comment
    mock_comment.assert_called_once()
    assert mock_comment.call_args[0][1] == 99


@patch.object(handler_module, "_get_installation_token", return_value="fake-token")
@patch.object(handler_module, "_post_comment", side_effect=Exception("API error"))
def test_raises_on_comment_failure(mock_comment, mock_token):
    """Handler re-raises when posting a comment fails."""
    event = _make_sqs_event(_make_payload())

    try:
        handler_module.lambda_handler(event, None)
        assert False, "Should have raised"
    except Exception as exc:
        assert "API error" in str(exc)


@patch.object(handler_module, "_get_installation_token", return_value="fake-token")
@patch.object(handler_module, "_post_comment")
def test_empty_event_is_noop(mock_comment, mock_token):
    """Handler does nothing when there are no records."""
    handler_module.lambda_handler({"Records": []}, None)
    mock_comment.assert_not_called()
