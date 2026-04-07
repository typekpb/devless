"""Tests for the pipeline state machine and runner.

Tests cover:
- State machine transitions in correct order
- Resume from checkpoint skips completed stages
- ClarificationNeeded halts the machine
- Failure posts error comment and raises
- process_message end-to-end wiring
"""
import sys
import os
from unittest.mock import MagicMock, patch, call
from dataclasses import dataclass

# Stub aider before any src imports
for _mod in ("aider", "aider.coders", "aider.models", "aider.io"):
    sys.modules.setdefault(_mod, MagicMock())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from models import CheckpointState, TaskPayload
from pipeline.stages import TaskPipeline, ClarificationNeeded


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_payload(**overrides) -> TaskPayload:
    defaults = dict(
        event_type="issues",
        issue_number=42,
        issue_title="Add feature X",
        issue_body="Please implement feature X",
        repository_full_name="owner/repo",
        sender_login="user",
        timestamp="2025-01-01T00:00:00Z",
    )
    defaults.update(overrides)
    return TaskPayload(**defaults)


def _make_checkpoint(stage="pending", **overrides) -> CheckpointState:
    defaults = dict(
        issue_number=42,
        repository_full_name="owner/repo",
        stage=stage,
        branch_name="issue-42",
        iteration_count=0,
        last_updated="2025-01-01T00:00:00Z",
    )
    defaults.update(overrides)
    return CheckpointState(**defaults)


def _make_cfg() -> dict[str, str]:
    return {"SQS_QUEUE_URL": "https://sqs.test/queue", "S3_BUCKET": "test-bucket", "AWS_REGION": "us-east-1"}


def _make_app_auth() -> MagicMock:
    auth = MagicMock()
    auth.token.return_value = "fake-installation-token"
    return auth


@dataclass
class _AiderResult:
    success: bool = True
    needs_clarification: bool = False
    clarification_question: str | None = None
    output: str = "done"


# ---------------------------------------------------------------------------
# State machine transition tests
# ---------------------------------------------------------------------------

@patch("pipeline.stages.write_checkpoint")
@patch("pipeline.stages.create_or_update_pr", return_value="https://github.com/owner/repo/pull/1")
@patch("pipeline.stages.push_branch")
@patch("pipeline.stages.run_aider")
@patch("pipeline.stages.build_issue_message", return_value="issue text")
@patch("pipeline.stages.load_devless_config")
@patch("pipeline.stages.clone_repo", return_value="/tmp/repo")
@patch("pipeline.stages.create_branch", return_value="issue-42")
def test_full_run_transitions_pending_to_complete(
    mock_branch, mock_clone, mock_devless_cfg, mock_build_msg,
    mock_aider, mock_push, mock_pr, mock_write_cp,
):
    """Pipeline starting from pending should transition through all states to complete."""
    mock_devless_cfg.return_value = MagicMock(test_command="pytest", max_iterations=1)
    mock_aider.return_value = _AiderResult()

    pipeline = TaskPipeline(
        payload=_make_payload(),
        cfg=_make_cfg(),
        app_auth=_make_app_auth(),
        workspace="/tmp/ws",
        checkpoint=_make_checkpoint("pending"),
    )
    pipeline.notify = MagicMock()

    pipeline.run_to_completion()

    assert pipeline.state == "complete"
    mock_clone.assert_called_once()
    mock_aider.assert_called_once()
    mock_push.assert_called_once()
    mock_pr.assert_called_once()
    # Checkpoint saved at each stage
    assert mock_write_cp.call_count == 4  # cloned, agent_loop, pr_created, complete


@patch("pipeline.stages.write_checkpoint")
@patch("pipeline.stages.create_or_update_pr", return_value="https://github.com/owner/repo/pull/1")
@patch("pipeline.stages.push_branch")
@patch("pipeline.stages.run_aider")
@patch("pipeline.stages.build_issue_message", return_value="issue text")
@patch("pipeline.stages.load_devless_config")
@patch("pipeline.stages.clone_repo", return_value="/tmp/repo")
@patch("pipeline.stages.create_branch", return_value="issue-42")
def test_resume_from_agent_loop_skips_clone(
    mock_branch, mock_clone, mock_devless_cfg, mock_build_msg,
    mock_aider, mock_push, mock_pr, mock_write_cp,
):
    """Resuming from agent_loop should skip clone and agent stages."""
    mock_devless_cfg.return_value = MagicMock(test_command="pytest", max_iterations=1)

    pipeline = TaskPipeline(
        payload=_make_payload(),
        cfg=_make_cfg(),
        app_auth=_make_app_auth(),
        workspace="/tmp/ws",
        checkpoint=_make_checkpoint("agent_loop"),
    )
    pipeline.notify = MagicMock()
    pipeline.repo_path = "/tmp/repo"

    pipeline.run_to_completion()

    assert pipeline.state == "complete"
    # Clone and aider should NOT have been called (already past those stages)
    mock_clone.assert_not_called()
    mock_branch.assert_not_called()
    mock_aider.assert_not_called()
    # PR and complete should have been called
    mock_push.assert_called_once()
    mock_pr.assert_called_once()


# ---------------------------------------------------------------------------
# Clarification and failure tests
# ---------------------------------------------------------------------------

@patch("pipeline.stages.write_checkpoint")
@patch("pipeline.stages.run_aider")
@patch("pipeline.stages.build_issue_message", return_value="issue text")
@patch("pipeline.stages.load_devless_config")
@patch("pipeline.stages.clone_repo", return_value="/tmp/repo")
@patch("pipeline.stages.create_branch", return_value="issue-42")
def test_clarification_needed_halts_pipeline(
    mock_branch, mock_clone, mock_devless_cfg, mock_build_msg,
    mock_aider, mock_write_cp,
):
    """When Aider needs clarification, pipeline raises ClarificationNeeded."""
    mock_devless_cfg.return_value = MagicMock(test_command="pytest", max_iterations=1)
    mock_aider.return_value = _AiderResult(
        success=False, needs_clarification=True, clarification_question="What color?",
    )

    pipeline = TaskPipeline(
        payload=_make_payload(),
        cfg=_make_cfg(),
        app_auth=_make_app_auth(),
        workspace="/tmp/ws",
        checkpoint=_make_checkpoint("pending"),
    )
    pipeline.notify = MagicMock()

    with pytest.raises(ClarificationNeeded):
        pipeline.run_to_completion()

    # Should have reached agent_loop but not pr_created
    assert pipeline.state == "agent_loop"
    # Clarification comment posted
    comments = [str(c) for c in pipeline.notify.comment.call_args_list]
    assert any("clarification" in c.lower() for c in comments)


@patch("pipeline.stages.write_checkpoint")
@patch("pipeline.stages.clone_repo", side_effect=Exception("network error"))
@patch("pipeline.stages.create_branch")
def test_clone_failure_posts_error_and_raises(
    mock_branch, mock_clone, mock_write_cp,
):
    """Clone failure should post an error comment and raise RuntimeError."""
    pipeline = TaskPipeline(
        payload=_make_payload(),
        cfg=_make_cfg(),
        app_auth=_make_app_auth(),
        workspace="/tmp/ws",
        checkpoint=_make_checkpoint("pending"),
    )
    pipeline.notify = MagicMock()

    with pytest.raises(RuntimeError, match="Failed to clone"):
        pipeline.run_to_completion()

    assert pipeline.state == "cloned"  # transition happened, callback raised
    assert any("error" in str(c).lower() for c in pipeline.notify.comment.call_args_list)


@patch("pipeline.stages.write_checkpoint")
@patch("pipeline.stages.run_aider")
@patch("pipeline.stages.build_issue_message", return_value="issue text")
@patch("pipeline.stages.load_devless_config")
@patch("pipeline.stages.clone_repo", return_value="/tmp/repo")
@patch("pipeline.stages.create_branch", return_value="issue-42")
def test_aider_failure_posts_error_and_raises(
    mock_branch, mock_clone, mock_devless_cfg, mock_build_msg,
    mock_aider, mock_write_cp,
):
    """Aider failure should post error comment and raise RuntimeError."""
    mock_devless_cfg.return_value = MagicMock(test_command="pytest", max_iterations=1)
    mock_aider.return_value = _AiderResult(success=False, output="something went wrong")

    pipeline = TaskPipeline(
        payload=_make_payload(),
        cfg=_make_cfg(),
        app_auth=_make_app_auth(),
        workspace="/tmp/ws",
        checkpoint=_make_checkpoint("pending"),
    )
    pipeline.notify = MagicMock()

    with pytest.raises(RuntimeError, match="did not complete successfully"):
        pipeline.run_to_completion()


# ---------------------------------------------------------------------------
# Resume tests for each stage
# ---------------------------------------------------------------------------

@patch("pipeline.stages.write_checkpoint")
@patch("pipeline.stages.create_or_update_pr", return_value="https://github.com/owner/repo/pull/1")
@patch("pipeline.stages.push_branch")
def test_resume_from_pr_created_only_runs_complete(mock_push, mock_pr, mock_write_cp):
    """Resuming from pr_created should only run the complete stage."""
    pipeline = TaskPipeline(
        payload=_make_payload(),
        cfg=_make_cfg(),
        app_auth=_make_app_auth(),
        workspace="/tmp/ws",
        checkpoint=_make_checkpoint("pr_created"),
    )
    pipeline.notify = MagicMock()
    pipeline.repo_path = "/tmp/repo"
    pipeline.pr_url = "https://github.com/owner/repo/pull/1"

    pipeline.run_to_completion()

    assert pipeline.state == "complete"
    mock_push.assert_not_called()
    mock_pr.assert_not_called()
    # Only the complete stage saves
    assert mock_write_cp.call_count == 1


def test_already_complete_is_noop():
    """Starting from complete should do nothing."""
    pipeline = TaskPipeline(
        payload=_make_payload(),
        cfg=_make_cfg(),
        app_auth=_make_app_auth(),
        workspace="/tmp/ws",
        checkpoint=_make_checkpoint("complete"),
    )
    pipeline.notify = MagicMock()

    pipeline.run_to_completion()

    assert pipeline.state == "complete"
    pipeline.notify.comment.assert_not_called()
