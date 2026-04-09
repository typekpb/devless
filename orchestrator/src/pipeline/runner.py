"""Entry point: wires up checkpoint, workspace, and drives the state machine."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

import logger as log
from aider_runner import run_aider
from checkpoint_store import read_checkpoint, delete_checkpoint
from github_app import GitHubAppAuth
from issue_manager import IssueNotifier, get_pr_branch
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
    elif msg.payload.event_type in ("pr_comment", "pr_review"):
        _process_pr_feedback(msg, cfg, app_auth, openai_api_key)
    elif msg.payload.event_type == "pr_issue_comment":
        _process_pr_issue_comment(msg, cfg, app_auth, openai_api_key)
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
            try:
                pipeline.repo_path = clone_repo(
                    payload.repository_full_name, token, workspace,
                )
                import git as _git
                _git.Repo(pipeline.repo_path).git.checkout(checkpoint.branch_name)
            except Exception:
                log.warning("Failed to resume from checkpoint, starting fresh")
                delete_checkpoint(payload.issue_number, payload.repository_full_name, s3_bucket)
                checkpoint.stage = "pending"
                # Clean workspace so clone_repo can start fresh
                import shutil
                repo_dir = os.path.join(workspace, "repo")
                if os.path.exists(repo_dir):
                    shutil.rmtree(repo_dir)
                pipeline = TaskPipeline(
                    payload=payload, cfg=cfg, app_auth=app_auth,
                    workspace=workspace, checkpoint=checkpoint,
                )

        pipeline.notify.comment("🚀 Devless is working on this issue. This may take a few minutes.")
        try:
            pipeline.run_to_completion()
        except Exception:
            delete_checkpoint(payload.issue_number, payload.repository_full_name, s3_bucket)
            raise

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
            f"the test command `{devless_cfg.test_command}` passes.\n\n"
            f"## Commit Message Guidelines\n\n"
            f"Use this format: `fix: <description>\\n\\nCloses #{payload.issue_number}`"
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


def _process_pr_feedback(
    msg: SQSMessage,
    cfg: dict[str, str],
    app_auth: GitHubAppAuth,
    openai_api_key: str,
) -> None:
    """Process feedback on a PR (comments or reviews) and update the same PR."""
    payload = msg.payload
    queue_url = cfg["SQS_QUEUE_URL"]
    branch = payload.branch or f"issue-{payload.issue_number}"

    os.environ["OPENAI_API_KEY"] = openai_api_key

    log.info("Processing PR feedback", issue_number=payload.issue_number, branch=branch)

    token = app_auth.token()
    notify = IssueNotifier(payload, token)
    notify.comment(
        f"📝 Devless received your feedback and is making changes to the PR."
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

        feedback_message = (
            f"The reviewer provided feedback on the PR for issue #{payload.issue_number}.\n\n"
            f"## Feedback\n\n{payload.issue_body}\n\n"
            f"Please address this feedback by making the necessary code changes.\n\n"
            f"## Commit Message Guidelines\n\n"
            f"Use this format: `fix: address review feedback\\n\\nCloses #{payload.issue_number}`"
        )

        try:
            result = run_aider(
                workspace=repo_path,
                issue_message=feedback_message,
                test_cmd=devless_cfg.test_command,
                max_iterations=devless_cfg.max_iterations,
                model=devless_cfg.model,
            )
        except Exception as exc:
            notify.comment(f"⚠️ Aider failed to address feedback: {exc}")
            raise

        if result and result.success:
            try:
                push_branch(repo_path, branch, app_auth.token())
                notify.comment(
                    f"✅ Devless has addressed the feedback and pushed changes to `{branch}`."
                )
            except Exception as exc:
                notify.comment(f"⚠️ Failed to push changes: {exc}")
                raise
        else:
            output = result.output[-2000:] if result else "no output"
            notify.comment(
                f"⚠️ Devless could not address the feedback automatically.\n\n"
                f"```\n{output}\n```"
            )

    try:
        delete_message(queue_url, msg.receipt_handle)
    except Exception as exc:
        log.warning("Failed to delete SQS message", error=str(exc))

    log.info("PR feedback processed", issue_number=payload.issue_number, branch=branch)


def _process_pr_issue_comment(
    msg: SQSMessage,
    cfg: dict[str, str],
    app_auth: GitHubAppAuth,
    openai_api_key: str,
) -> None:
    """Process a comment on a PR (via issue_comment event) and update the same PR."""
    payload = msg.payload
    queue_url = cfg["SQS_QUEUE_URL"]

    os.environ["OPENAI_API_KEY"] = openai_api_key

    token = app_auth.token()
    
    # Fetch the PR to get the branch name
    branch = get_pr_branch(payload.repository_full_name, payload.issue_number, token)
    if not branch:
        log.warning("Could not get PR branch", issue_number=payload.issue_number)
        try:
            delete_message(queue_url, msg.receipt_handle)
        except Exception:
            pass
        return

    # Check if this is a Devless-managed branch
    import re
    if not re.match(r"^issue-\d+$", branch):
        log.info("PR branch is not Devless-managed, ignoring", branch=branch)
        try:
            delete_message(queue_url, msg.receipt_handle)
        except Exception:
            pass
        return

    log.info("Processing PR comment", issue_number=payload.issue_number, branch=branch)

    notify = IssueNotifier(payload, token)
    notify.comment(
        f"📝 Devless received your feedback and is making changes to the PR."
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

        feedback_message = (
            f"The user commented on the PR for issue #{payload.issue_number}.\n\n"
            f"## Comment\n\n{payload.issue_body}\n\n"
            f"Please address this feedback by making the necessary code changes.\n\n"
            f"## Commit Message Guidelines\n\n"
            f"Use this format: `fix: address review feedback\\n\\nCloses #{payload.issue_number}`"
        )

        try:
            result = run_aider(
                workspace=repo_path,
                issue_message=feedback_message,
                test_cmd=devless_cfg.test_command,
                max_iterations=devless_cfg.max_iterations,
                model=devless_cfg.model,
            )
        except Exception as exc:
            notify.comment(f"⚠️ Aider failed to address feedback: {exc}")
            raise

        if result and result.success:
            try:
                push_branch(repo_path, branch, app_auth.token())
                notify.comment(
                    f"✅ Devless has addressed the feedback and pushed changes to `{branch}`."
                )
            except Exception as exc:
                notify.comment(f"⚠️ Failed to push changes: {exc}")
                raise
        else:
            output = result.output[-2000:] if result else "no output"
            notify.comment(
                f"⚠️ Devless could not address the feedback automatically.\n\n"
                f"```\n{output}\n```"
            )

    try:
        delete_message(queue_url, msg.receipt_handle)
    except Exception as exc:
        log.warning("Failed to delete SQS message", error=str(exc))

    log.info("PR comment processed", issue_number=payload.issue_number, branch=branch)
