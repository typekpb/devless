"""Property-based tests for branch naming convention.

# Feature: codex-dev-team, Property 9: Branch naming convention
"""
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hypothesis import given, settings
from hypothesis import strategies as st

from repo_manager import create_branch


@settings(max_examples=100)
@given(st.integers(min_value=1))
def test_branch_naming_convention(issue_number: int):
    """Property 9: Branch naming convention
    For any positive issue number, create_branch should return a branch
    name matching `issue-{number}` exactly.

    # Feature: codex-dev-team, Property 9: Branch naming convention
    Validates: Requirements 3.1
    """
    mock_repo = MagicMock()
    with patch("repo_manager.git.Repo", return_value=mock_repo):
        branch_name = create_branch("/fake/path", issue_number)

    assert branch_name == f"issue-{issue_number}"


from repo_manager import format_commit_message


@settings(max_examples=100)
@given(
    issue_number=st.integers(min_value=1, max_value=10_000_000),
    issue_title=st.text(min_size=1, max_size=200),
)
def test_commit_message_contains_issue_reference(issue_number: int, issue_title: str):
    """Property 10: Commit message contains issue reference

    # Feature: codex-dev-team, Property 10: Commit message contains issue reference
    Validates: Requirements 3.2
    """
    message = format_commit_message(issue_number, issue_title)
    assert str(issue_number) in message
    assert issue_title in message
