"""Property-based tests for exponential backoff retry sequence.

# Feature: codex-dev-team, Property 15: Exponential backoff retry sequence
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st
from github import GithubException

from retry import retry_with_backoff

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

failures_before_success_strategy = st.integers(min_value=0, max_value=5)


def _make_rate_limit_error() -> GithubException:
    return GithubException(403, {"message": "API rate limit exceeded"}, None)


# ---------------------------------------------------------------------------
# Property 15: Exponential backoff retry sequence
# ---------------------------------------------------------------------------

@settings(max_examples=200, deadline=None)
@given(failures_before_success_strategy)
def test_exponential_backoff_retry_sequence(num_failures):
    """Property 15: Exponential backoff retry sequence

    For any sequence of GitHub API rate-limit errors followed by a success,
    the retry logic should attempt the call up to 3 times. If the function
    succeeds within 3 attempts, the result is returned. Otherwise, the
    rate-limit error propagates.

    Validates: Requirements 11.5
    """
    # Feature: codex-dev-team, Property 15: Exponential backoff retry sequence

    max_attempts = 3
    call_count = 0

    def fn() -> str:
        nonlocal call_count
        call_count += 1
        if call_count <= num_failures:
            raise _make_rate_limit_error()
        return "ok"

    with patch("tenacity.nap.time.sleep", return_value=None):
        if num_failures < max_attempts:
            result = retry_with_backoff(fn)
            assert result == "ok"
            assert call_count == num_failures + 1
        else:
            call_count = 0
            try:
                retry_with_backoff(fn)
                assert False, "Expected GithubException"
            except GithubException:
                assert call_count == max_attempts


@settings(max_examples=100)
@given(st.text(min_size=1, max_size=100))
def test_non_rate_limit_errors_propagate_immediately(error_msg):
    """Non-rate-limit exceptions should propagate without retry."""
    call_count = 0

    def fn() -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError(error_msg)

    try:
        retry_with_backoff(fn)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == error_msg
        assert call_count == 1
