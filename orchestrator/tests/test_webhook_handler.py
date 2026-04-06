"""Property-based tests for webhook payload enqueue behaviour.

# Feature: codex-dev-team, Property 2: Valid webhook payload triggers enqueue and 202
"""
import hashlib
import hmac
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lambda", "webhook_handler"))

from hypothesis import given, settings
from hypothesis import strategies as st

import handler as handler_module
from handler import lambda_handler


def _make_signature(payload: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


# Strategies for generating valid webhook inputs
_printable = st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd"), min_codepoint=32, max_codepoint=126)
issue_number_strategy = st.integers(min_value=1, max_value=10_000)
text_strategy = st.text(alphabet=_printable, min_size=1, max_size=200)
# env vars cannot contain null bytes — restrict to printable ASCII
secret_strategy = st.text(alphabet=_printable, min_size=1, max_size=256)
queue_url_strategy = st.text(alphabet=_printable, min_size=1, max_size=512)


@settings(max_examples=100)
@given(
    issue_number=issue_number_strategy,
    issue_title=text_strategy,
    issue_body=text_strategy,
    repo_full_name=text_strategy,
    secret=secret_strategy,
    queue_url=queue_url_strategy,
)
def test_valid_payload_enqueues_and_returns_202(
    issue_number: int,
    issue_title: str,
    issue_body: str,
    repo_full_name: str,
    secret: str,
    queue_url: str,
):
    """Property 2: Valid webhook payload triggers enqueue and 202.

    For any valid signed payload, the handler must:
    - Return HTTP 202
    - Call SQS send_message exactly once
    - Include the issue number in the enqueued MessageBody

    # Feature: codex-dev-team, Property 2: Valid webhook payload triggers enqueue and 202
    Validates: Requirements 1.5
    """
    # Build a GitHub-style webhook body
    github_payload = {
        "action": "opened",
        "issue": {
            "number": issue_number,
            "title": issue_title,
            "body": issue_body,
        },
        "repository": {
            "full_name": repo_full_name,
        },
        "sender": {
            "login": "test-user",
        },
    }
    body = json.dumps(github_payload)
    payload_bytes = body.encode("utf-8")
    signature = _make_signature(payload_bytes, secret)

    event = {
        "headers": {"x-hub-signature-256": signature, "x-github-event": "issues"},
        "body": body,
    }

    mock_sqs = MagicMock()

    with patch.dict(os.environ, {"WEBHOOK_SECRET": secret, "SQS_QUEUE_URL": queue_url}):
        with patch.object(handler_module, "_sqs", mock_sqs):
            response = lambda_handler(event, None)

    # Response must be 202
    assert response["statusCode"] == 202

    # SQS send_message must be called exactly once
    mock_sqs.send_message.assert_called_once()

    # The MessageBody must be valid JSON containing the issue number
    call_kwargs = mock_sqs.send_message.call_args
    message_body = call_kwargs.kwargs["MessageBody"]
    parsed = json.loads(message_body)
    assert parsed["issue_number"] == issue_number


# ---------------------------------------------------------------------------
# HMAC validation tests
# ---------------------------------------------------------------------------

from handler import validate_signature

payload_strategy = st.binary(min_size=0, max_size=4096)
hmac_secret_strategy = st.text(min_size=1, max_size=256)


@settings(max_examples=100)
@given(payload=payload_strategy, secret=hmac_secret_strategy)
def test_valid_signature_accepted(payload: bytes, secret: str):
    """Property 1: valid signatures are accepted."""
    header = _make_signature(payload, secret)
    assert validate_signature(payload, secret, header) is True


@settings(max_examples=100)
@given(payload=payload_strategy, correct_secret=hmac_secret_strategy, wrong_secret=hmac_secret_strategy)
def test_wrong_secret_rejected(payload: bytes, correct_secret: str, wrong_secret: str):
    """Property 1: wrong secrets are rejected."""
    header = _make_signature(payload, correct_secret)
    if correct_secret == wrong_secret:
        assert validate_signature(payload, wrong_secret, header) is True
    else:
        assert validate_signature(payload, wrong_secret, header) is False


@settings(max_examples=100)
@given(payload=payload_strategy, secret=hmac_secret_strategy, garbage=st.text(min_size=1))
def test_malformed_signature_rejected(payload: bytes, secret: str, garbage: str):
    """Property 1: malformed headers are rejected."""
    malformed = garbage.lstrip("sha256=") if garbage.startswith("sha256=") else garbage
    if not malformed.startswith("sha256="):
        assert validate_signature(payload, secret, malformed) is False


@settings(max_examples=50)
@given(payload=payload_strategy, secret=hmac_secret_strategy)
def test_empty_header_rejected(payload: bytes, secret: str):
    """Property 1: empty/missing header is rejected."""
    assert validate_signature(payload, secret, "") is False
    assert validate_signature(payload, secret, None) is False
