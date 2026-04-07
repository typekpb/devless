"""Entry point: wires up checkpoint, workspace, and drives the state machine."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

import logger as log
from aider_runner import run_aider
from checkpoint_store import read_checkpoint
from github_app import GitHubAppAuth
from github_client import IssueNotifier
from models import CheckpointState
from pipeline.stages import TaskPipeline
from repo_manager import clone_repo, load_devless_config, push_branch
from sqs_consumer import SQSMessage, delete_message


def process_message(
    msg: SQSMessage,
    cfg: dict[str, str],
    app_auth: GitHubAppAuth,
    openai_api_key: str,
) -> None:
    """Route to the right handler based on event type."""
    if msg.payload.event_type == "ci_fix":
        _process_ci_fix(msg, cfg, app_auth, openai_api_key)
    else:
        _process_issue(msg, cfg, app_auth, openai_api_key)


def _process_issue(
    msg: SQSMessage,
    cfg: dict[str, str],
    app_auth: GitHubAppAuth,
    openai_api_key: str,
) -> None:
    """Run the full pipeline for a new issue or issue comment."""
    payload = msg.payload
    queue_url = cfg["SQS_QUEUE_URL"]
    s3_bucket = cfg["S3_BUCKET"]

    os.environ["OPENAI_API_KEY"] = openai_api_key

    log.info("Processing issue", issue_number=payload.issue_number, repo=payload.repository_full_name)

    checkpoint = read_checkpoint(payload.issue_number, payload.repository_full_name, s3_bucket)
    if checkpoint:
        log.info("Resuming from checkpoint", stage=checkpoint.stage)
    else:
        checkpoint = CheckpointState(
            issue_number=payload.issue_number,
            repository_full_name=payload.repository_full_name,
            stage="pending",
            branch_name=f"issue-{payload.issue_number}",
            iteration_count=0,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    with tempfile.TemporaryDirectory() as workspace:
        token = app_auth.token()
        pipeline = TaskPipeline(
            payload=payload,
            cfg=cfg,
            app_auth=app_auth,
            workspace=workspace,
            checkpoint=checkpoint,
        )

        if checkpoint.stage != "pending":
            pipeline.repo_path = clone_repo(
                payload.repository_full_name, token, workspace,
            )
            import git as _git
            _git.Repo(pipeline.repo_path).git.checkout(checkpoint.branch_name)

        pipeline.notify.comment("🚀 Devless has picked up this issue and is starting work.")
        pipeline.run_to_completion()

    try:
        delete_message(queue_url, msg.receipt_handle)
        log.info("SQS message deleted")
    except Exception as exc:
        log.warning("Failed to delete SQS message", error=str(exc))

    log.info("Task completed successfully", issue_number=payload.issue_number)


def _process_ci_fix(
    msg: SQSMessage,
    cfg: dict[str, str],
    app_auth: GitHubAppAuth,
    openai_api_key: str,
) -> None:
    """Fix a CI failure on an existing Devless branch."""
    payload = msg.payload
    queue_url = cfg["SQS_QUEUE_URL"]
    branch = payload.branch or f"issue-{payload.issue_number}"

    os.environ["OPENAI_API_KEY"] = openai_api_key

    log.info("Processing CI fix", issue_number=payload.issue_number, branch=branch)

    token = app_auth.token()
    notify = IssueNotifier(payload, token)
    notify.comment(
        f"🔄 CI failed on `{branch}`. Devless is analyzing the failure and pushing a fix."
    )

    with tempfile.TemporaryDirectory() as workspace:
        try:
            repo_path = clone_repo(payload.repository_full_name, token, workspace)
            import git as _git
            _git.Repo(repo_path).git.checkout(branch)
        except Exception as exc:
            notify.comment(f"⚠️ Failed to checkout branch `{branch}`: {exc}")
            raise

        devless_cfg = load_devless_config(repo_path)

        fix_message = (
            f"The CI pipeline failed on branch `{branch}`.\n\n"
            f"{payload.issue_body}\n\n"
            f"Please analyze the failure, fix the code, and make sure "
            f"the test command `{devless_cfg.test_command}` passes."
        )

        try:
            result = run_aider(
                workspace=repo_path,
                issue_message=fix_message,
                test_cmd=devless_cfg.test_command,
                max_iterations=devless_cfg.max_iterations,
                model=devless_cfg.model,
            )
        except Exception as exc:
            notify.comment(f"⚠️ Aider failed to fix CI: {exc}")
            raise

        if result and result.success:
            try:
                push_branch(repo_path, branch, app_auth.token())
                notify.comment(
                    f"🔧 Devless has pushed a fix to `{branch}`. "
                    f"CI should re-run automatically."
                )
            except Exception as exc:
                notify.comment(f"⚠️ Failed to push fix: {exc}")
                raise
        else:
            output = result.output[-2000:] if result else "no output"
            notify.comment(
                f"⚠️ Devless could not fix the CI failure automatically.\n\n"
                f"```\n{output}\n```"
            )

    try:
        delete_message(queue_url, msg.receipt_handle)
    except Exception as exc:
        log.warning("Failed to delete SQS message", error=str(exc))

    log.info("CI fix completed", issue_number=payload.issue_number, branch=branch)
