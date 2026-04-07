"""Property-based tests for Aider message completeness.

# Feature: devless, Property 6: System prompt / Aider message completeness
"""
import sys
import os
from unittest.mock import MagicMock

# Stub out the aider package before importing aider_runner so the module can
# be imported in environments where aider-chat is not installed.
for _mod in ("aider", "aider.coders", "aider.models", "aider.io"):
    sys.modules.setdefault(_mod, MagicMock())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hypothesis import given, settings
from hypothesis import strategies as st

from aider_runner import build_issue_message


@settings(max_examples=100)
@given(
    issue_title=st.text(min_size=1),
    issue_body=st.text(min_size=1),
    comments=st.lists(st.text(min_size=1), min_size=0, max_size=10),
    skills_content=st.text(min_size=1),
)
def test_aider_message_contains_all_components(
    issue_title: str,
    issue_body: str,
    comments: list[str],
    skills_content: str,
) -> None:
    """Property 6: System prompt / Aider message completeness

    For any combination of issue title, issue body, comment list, and skills
    content, the constructed Aider message must contain all four as substrings.

    # Feature: devless, Property 6: System prompt / Aider message completeness
    Validates: Requirements 2.3
    """
    message = build_issue_message(
        issue_title=issue_title,
        issue_body=issue_body,
        comments=comments,
        skills_content=skills_content,
    )

    assert issue_title in message, "issue_title must appear in the Aider message"
    assert issue_body in message, "issue_body must appear in the Aider message"
    for comment in comments:
        assert comment in message, f"comment {comment!r} must appear in the Aider message"
    assert skills_content in message, "skills_content must appear in the Aider message"


@settings(max_examples=50)
@given(
    issue_title=st.text(min_size=1),
    issue_body=st.text(min_size=1),
)
def test_aider_message_without_optional_components(
    issue_title: str,
    issue_body: str,
) -> None:
    """Property 6 (edge case): Message still contains title and body when
    comments and skills are empty.

    # Feature: devless, Property 6: System prompt / Aider message completeness
    Validates: Requirements 2.3
    """
    message = build_issue_message(
        issue_title=issue_title,
        issue_body=issue_body,
        comments=[],
        skills_content="",
    )

    assert issue_title in message, "issue_title must appear even without comments/skills"
    assert issue_body in message, "issue_body must appear even without comments/skills"
