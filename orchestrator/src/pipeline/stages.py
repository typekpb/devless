"""TaskPipeline — state machine with on_enter callbacks for each stage."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from transitions import Machine

import logger as log
from aider_runner import run_aider
from checkpoint_store import write_checkpoint
from github_app import GitHubAppAuth
from issue_manager import IssueNotifier, build_issue_message
from models import CheckpointState, TaskPayload
from pr_manager import create_or_update_pr
from repo_manager import clone_repo, create_branch, load_devless_config, push_branch


class ClarificationNeeded(Exception):
    """Raised when Aider needs user input — not a failure."""


class TaskPipeline:
    """Drives a single issue through: pending → cloned → agent_loop → pr_created → complete.

    On resume the machine starts at the checkpoint's saved state, so
    already-completed ``on_enter_*`` callbacks are never re-executed.
    """

    states = ["pending", "cloned", "agent_loop", "pr_created", "complete"]

    transitions = [
        {"trigger": "clone", "source": "pending", "dest": "cloned"},
        {"trigger": "run_agent", "source": "cloned", "dest": "agent_loop"},
        {"trigger": "open_pr", "source": "agent_loop", "dest": "pr_created"},
        {"trigger": "finish", "source": "pr_created", "dest": "complete"},
    ]

    # state → trigger name to advance
    ADVANCE = {
        "pending": "clone",
        "cloned": "run_agent",
        "agent_loop": "open_pr",
        "pr_created": "finish",
    }

    def __init__(
        self,
        payload: TaskPayload,
        cfg: dict[str, str],
        app_auth: GitHubAppAuth,
        workspace: str,
        checkpoint: CheckpointState,
    ) -> None:
        self.payload = payload
        self.cfg = cfg
        self.app_auth = app_auth
        self.workspace = workspace
        self.checkpoint = checkpoint
        self.s3_bucket = cfg["S3_BUCKET"]
        self.notify = IssueNotifier(payload, app_auth.token())
        self.repo_path: str = ""
        self.pr_url: str = ""

        Machine(
            model=self,
            states=self.states,
            transitions=self.transitions,
            initial=checkpoint.stage,
            send_event=False,
        )

    # --- helpers ---

    def _save(self) -> None:
        self.checkpoint.stage = self.state  # type: ignore[attr-defined]
        self.checkpoint.last_updated = datetime.now(timezone.utc).isoformat()
        write_checkpoint(self.checkpoint, self.s3_bucket)

    def _fail(self, message: str) -> None:
        log.error(message)
        self.notify.comment(f"⚠️ Devless encountered an error:\n\n```\n{message}\n```")
        raise RuntimeError(message)

    def run_to_completion(self) -> None:
        """Drive the machine forward from current state to complete."""
        while self.state != "complete":  # type: ignore[attr-defined]
            trigger = self.ADVANCE.get(self.state)  # type: ignore[attr-defined]
            if trigger is None:
                break
            getattr(self, trigger)()

    # --- state callbacks ---

    def on_enter_cloned(self) -> None:
        log.info("Cloning repository", repo=self.payload.repository_full_name)
        try:
            self.repo_path = clone_repo(
                self.payload.repository_full_name, self.app_auth.token(), self.workspace,
            )
        except Exception as exc:
            self._fail(f"Failed to clone repository: {exc}")

        branch = create_branch(self.repo_path, self.payload.issue_number)
        self.checkpoint.branch_name = branch
        self._save()
        log.info("Repository cloned and branch created", branch=branch)

    def on_enter_agent_loop(self) -> None:
        log.info("Starting Aider agentic loop")
        devless_cfg = load_devless_config(self.repo_path)
        log.info("Using model", model=devless_cfg.model)
        issue_message = build_issue_message(self.payload, self.app_auth.token())

        try:
            result = run_aider(
                workspace=self.repo_path,
                issue_message=issue_message,
                test_cmd=devless_cfg.test_command,
                max_iterations=devless_cfg.max_iterations,
                model=devless_cfg.model,
            )
        except Exception as exc:
            self._fail(f"Aider runner raised an unexpected exception: {exc}")

        if result is None:
            self._fail("Aider runner returned no result")

        self._save()

        if result.needs_clarification:
            question = result.clarification_question or "Please provide more details."
            log.info("Aider needs clarification", question=question)
            self.notify.comment(
                f"🤔 Devless needs clarification before proceeding:\n\n{question}\n\n"
                f"Please reply to this issue with the requested information. "
                f"Devless will resume automatically once your response is received."
            )
            raise ClarificationNeeded()

        if not result.success:
            self._fail(
                f"Aider did not complete successfully.\n\n"
                f"Last output:\n```\n{result.output[-3000:]}\n```"
            )
        log.info("Aider completed successfully")

    def on_enter_pr_created(self) -> None:
        log.info("Pushing branch", branch=self.checkpoint.branch_name)
        try:
            push_branch(self.repo_path, self.checkpoint.branch_name, self.app_auth.token())
        except Exception as exc:
            self._fail(f"Failed to push branch: {exc}")

        log.info("Creating or updating Pull Request")
        try:
            self.pr_url = create_or_update_pr(
                repo_full_name=self.payload.repository_full_name,
                issue_number=self.payload.issue_number,
                issue_title=self.payload.issue_title,
                branch=self.checkpoint.branch_name,
                token=self.app_auth.token(),
            )
        except Exception as exc:
            self._fail(f"Failed to create/update Pull Request: {exc}")

        self._save()
        log.info("Pull Request ready", pr_url=self.pr_url)

    def on_enter_complete(self) -> None:
        self.notify.comment(
            f"✅ Devless has implemented the requested changes.\n\n"
            f"A Pull Request has been opened: {self.pr_url}\n\n"
            f"Please review and merge when ready."
        )
        self._save()
