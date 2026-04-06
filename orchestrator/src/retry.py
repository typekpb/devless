"""Retry utility for GitHub API calls using tenacity."""
from __future__ import annotations

from typing import Any, Callable, TypeVar

from github import GithubException
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T")


def _is_rate_limit_error(exc: BaseException) -> bool:
    """Return True if the exception represents a GitHub API rate-limit error."""
    return isinstance(exc, GithubException) and exc.status in (403, 429)


class RetriesExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, last_exception: Exception, attempts: int) -> None:
        self.last_exception = last_exception
        self.attempts = attempts
        super().__init__(
            f"All {attempts} retry attempts exhausted. "
            f"Last error: {last_exception}"
        )


_retry_decorator = retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    stop=stop_after_attempt(3),
    reraise=True,
)


def retry_with_backoff(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Call *fn* with retry on GitHub rate-limit errors (exponential backoff).

    Non-rate-limit exceptions propagate immediately.
    """
    return _retry_decorator(fn)(*args, **kwargs)
