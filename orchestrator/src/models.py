"""Data models for the Codex Dev Team Orchestrator."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class TaskPayload(BaseModel):
    """Represents the SQS message payload from a GitHub webhook event."""

    event_type: Literal["issues", "issue_comment", "ci_fix"]
    issue_number: int
    issue_title: str
    issue_body: str
    repository_full_name: str
    sender_login: str
    timestamp: str  # ISO 8601
    branch: str | None = None  # set for ci_fix events


class CheckpointState(BaseModel):
    """Tracks the current processing stage for a given issue."""

    issue_number: int
    repository_full_name: str
    stage: Literal["pending", "cloned", "agent_loop", "pr_created", "complete"]
    branch_name: str
    iteration_count: int
    last_updated: str  # ISO 8601
