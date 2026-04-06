"""Property-based tests for pr_manager: PR description, commit message, idempotence.

# Feature: codex-dev-team, Properties 11, 12
"""
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hypothesis import given, settings
from hypothesis import strategies as st

from pr_manager import build_pr_body, create_or_update_pr


@settings(max_examples=100)
@given(
    issue_number=st.integers(min_value=1, max_value=10_000_000),
    issue_title=st.text(min_size=1, max_size=200),
)
def test_pr_description_completeness(issue_number: int, issue_title: str):
    """Property 11: PR description completeness

    Validates: Requirements 3.4
    """
    body = build_pr_body(issue_number, issue_title)
    assert str(issue_number) in body
    assert issue_title in body
    assert "## Summary" in body
    summary_start = body.index("## Summary") + len("## Summary")
    assert body[summary_start:].strip()


@settings(max_examples=100)
@given(
    issue_number=st.integers(min_value=1, max_value=10_000_000),
    issue_title=st.text(min_size=1, max_size=200),
)
def test_pr_creation_idempotence(issue_number: int, issue_title: str):
    """Property 12: PR creation idempotence

    Calling create_or_update_pr twice should result in exactly one PR created.

    Validates: Requirements 3.5
    """
    branch = f"issue-{issue_number}"
    created_prs: list[MagicMock] = []

    def _get_repo(_name):
        repo = MagicMock()
        repo.default_branch = "main"
        repo.owner.login = "owner"

        if created_prs:
            repo.get_pulls.return_value = iter([created_prs[0]])
        else:
            repo.get_pulls.return_value = iter([])
            new_pr = MagicMock()
            new_pr.html_url = "https://github.com/owner/repo/pull/1"
            repo.create_pull.return_value = new_pr
            repo.create_pull.side_effect = lambda **kw: (
                created_prs.append(new_pr) or new_pr
            )
        return repo

    with patch("pr_manager.Github") as MockGithub:
        mock_gh = MagicMock()
        mock_gh.get_repo.side_effect = _get_repo
        MockGithub.return_value = mock_gh

        url1 = create_or_update_pr("owner/repo", issue_number, issue_title, branch, "tok")
        url2 = create_or_update_pr("owner/repo", issue_number, issue_title, branch, "tok")

    assert len(created_prs) == 1
    assert url1 is not None
    assert url2 is not None
