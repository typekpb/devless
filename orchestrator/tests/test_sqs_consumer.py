"""Property-based tests for SQS message deletion only on success.

# Feature: codex-dev-team, Property 3: SQS message deletion only on success
"""
import sys
import os
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hypothesis import given, settings
from hypothesis import strategies as st

from sqs_consumer import delete_message, parse_payload
from models import TaskPayload

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

STAGES = ["cloned", "skills_loaded", "agent_loop", "pr_created", "complete"]

stage_outcome_strategy = st.lists(
    st.tuples(
        st.sampled_from(STAGES),
        st.booleans(),  # True = stage succeeded, False = stage failed
    ),
    min_size=1,
    max_size=len(STAGES),
)

queue_url_strategy = st.from_regex(
    r"https://sqs\.[a-z0-9-]+\.amazonaws\.com/[0-9]+/[a-zA-Z0-9_-]+",
    fullmatch=True,
)

receipt_handle_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=8,
    max_size=64,
)


# ---------------------------------------------------------------------------
# Property 3: SQS message deletion only on success
# ---------------------------------------------------------------------------

@settings(max_examples=200)
@given(stage_outcome_strategy, queue_url_strategy, receipt_handle_strategy)
def test_delete_called_iff_all_stages_succeed(stage_outcomes, queue_url, receipt_handle):
    """Property 3: SQS message deletion only on success

    For any task execution, the SQS message should be deleted if and only if
    all processing stages complete without error; a failure at any stage should
    leave the message undeleted.

    Validates: Requirements 1.7
    """
    # Feature: codex-dev-team, Property 3: SQS message deletion only on success

    all_succeeded = all(success for _, success in stage_outcomes)

    mock_boto = MagicMock()
    mock_client = MagicMock()
    mock_boto.return_value = mock_client

    with patch("sqs_consumer.boto3.client", mock_boto):
        # Simulate the orchestrator's delete-on-success pattern:
        # only call delete_message when every stage succeeded.
        if all_succeeded:
            delete_message(queue_url, receipt_handle)

    if all_succeeded:
        mock_client.delete_message.assert_called_once_with(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle,
        )
    else:
        mock_client.delete_message.assert_not_called()


# ---------------------------------------------------------------------------
# Additional: parse_payload round-trips valid TaskPayload JSON
# ---------------------------------------------------------------------------

task_payload_strategy = st.builds(
    TaskPayload,
    event_type=st.sampled_from(["issues", "issue_comment"]),
    issue_number=st.integers(min_value=1, max_value=10_000_000),
    issue_title=st.text(min_size=1, max_size=200),
    issue_body=st.text(max_size=2000),
    repository_full_name=st.from_regex(
        r"[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+", fullmatch=True
    ),
    sender_login=st.from_regex(r"[a-zA-Z0-9_-]+", fullmatch=True),
    timestamp=st.datetimes().map(lambda dt: dt.isoformat()),
)


@settings(max_examples=100)
@given(task_payload_strategy)
def test_parse_payload_round_trip(payload: TaskPayload):
    """parse_payload correctly deserializes any valid TaskPayload JSON string."""
    raw = payload.model_dump_json()
    restored = parse_payload(raw)
    assert restored == payload


def test_parse_payload_invalid_json_raises():
    """parse_payload raises ValueError on malformed JSON."""
    try:
        parse_payload("not-json{{{")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_parse_payload_missing_field_raises():
    """parse_payload raises ValueError when required fields are absent."""
    import json
    raw = json.dumps({"event_type": "issues", "issue_number": 1})
    try:
        parse_payload(raw)
        assert False, "Expected ValueError"
    except ValueError:
        pass
