"""Property-based tests for structured JSON log output.

# Feature: devless, Property 14: Log output is valid JSON
"""
import io
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import logger

# Strategy: generate arbitrary string keys and values for extra log fields
_text = st.text(min_size=0, max_size=50)
_extra_fields = st.dictionaries(
    keys=_text.filter(lambda k: k not in ("level", "message", "timestamp")),
    values=_text,
    max_size=5,
)

LOG_LEVELS = [logger.info, logger.warning, logger.error, logger.debug]


@settings(max_examples=100)
@given(
    log_fn=st.sampled_from(LOG_LEVELS),
    message=_text,
    extra=_extra_fields,
)
def test_log_output_is_valid_json(log_fn, message, extra):
    """Property 14: Log output is valid JSON
    For any log event emitted by the Orchestrator, the output line should be
    parseable as valid JSON and contain at minimum the fields `level`,
    `message`, and `timestamp`.

    **Validates: Requirements 6.7**
    """
    # Feature: devless, Property 14: Log output is valid JSON
    captured = io.StringIO()
    original_stdout = sys.stdout
    sys.stdout = captured
    try:
        log_fn(message, **extra)
    finally:
        sys.stdout = original_stdout

    output = captured.getvalue().strip()
    assert output, "Logger produced no output"

    # Each emitted line must be valid JSON
    parsed = json.loads(output)

    # Must contain the required fields
    assert "level" in parsed, f"Missing 'level' field in: {parsed}"
    assert "message" in parsed, f"Missing 'message' field in: {parsed}"
    assert "timestamp" in parsed, f"Missing 'timestamp' field in: {parsed}"

    # The message value must match what was passed
    assert parsed["message"] == message

    # Any extra fields passed must appear in the output
    for key, value in extra.items():
        assert key in parsed, f"Extra field '{key}' missing from log output"
        assert parsed[key] == value
