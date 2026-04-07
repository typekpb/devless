"""Property-based tests for CheckpointState serialization round-trip.

# Feature: devless, Property 8: Checkpoint round-trip
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hypothesis import given, settings
from hypothesis import strategies as st

from models import CheckpointState

STAGES = ["pending", "cloned", "agent_loop", "pr_created", "complete"]

checkpoint_strategy = st.builds(
    CheckpointState,
    issue_number=st.integers(min_value=1, max_value=10_000_000),
    repository_full_name=st.from_regex(r"[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+", fullmatch=True),
    stage=st.sampled_from(STAGES),
    branch_name=st.from_regex(r"issue-[0-9]+", fullmatch=True),
    iteration_count=st.integers(min_value=0, max_value=10),
    last_updated=st.datetimes().map(lambda dt: dt.isoformat()),
)


@settings(max_examples=100)
@given(checkpoint_strategy)
def test_checkpoint_round_trip(state: CheckpointState):
    """Property 8: Checkpoint round-trip
    For any valid CheckpointState, serializing to JSON and deserializing
    should produce an equivalent CheckpointState object.

    Validates: Requirements 2.9, 2.10
    """
    # Feature: devless, Property 8: Checkpoint round-trip
    serialized = state.model_dump_json()
    restored = CheckpointState.model_validate_json(serialized)
    assert restored == state


from checkpoint_store import _s3_key

repo_strategy = st.from_regex(r"[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+", fullmatch=True)
issue_number_strategy = st.integers(min_value=1, max_value=10_000_000)


@settings(max_examples=100)
@given(repo=repo_strategy, issue_a=issue_number_strategy, issue_b=issue_number_strategy)
def test_workspace_isolation_distinct_issues(repo: str, issue_a: int, issue_b: int):
    """Property 4: Workspace isolation — distinct issues get distinct S3 keys.

    Validates: Requirements 2.1, 5.4
    """
    if issue_a == issue_b:
        return
    assert _s3_key(repo, issue_a) != _s3_key(repo, issue_b)


@settings(max_examples=100)
@given(repo_a=repo_strategy, repo_b=repo_strategy, issue=issue_number_strategy)
def test_workspace_isolation_distinct_repos(repo_a: str, repo_b: str, issue: int):
    """Property 4: Workspace isolation — distinct repos get distinct S3 keys.

    Validates: Requirements 2.1, 5.4
    """
    if repo_a == repo_b:
        return
    assert _s3_key(repo_a, issue) != _s3_key(repo_b, issue)
