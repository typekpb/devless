"""Repository cloning, branching, committing, and pushing."""
from __future__ import annotations

import os
from dataclasses import dataclass

import git
import yaml


@dataclass
class DevlessProjectConfig:
    """Per-project configuration read from ``.devless/config.yml``."""

    skills_path: str
    max_iterations: int
    test_command: str
    model: str


def load_devless_config(repo_path: str) -> DevlessProjectConfig:
    """Read ``.devless/config.yml`` from a cloned repo.

    Falls back to environment variables and sensible defaults when the
    file is absent or individual keys are missing.
    """
    config_path = os.path.join(repo_path, ".devless", "config.yml")
    raw: dict = {}
    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

    return DevlessProjectConfig(
        skills_path=str(raw.get("skills_path", "")),
        max_iterations=int(raw.get("max_iterations", os.environ.get("MAX_ITERATIONS", 10))),
        test_command=str(raw.get("test_command", os.environ.get("TEST_COMMAND", "pytest"))),
        model=str(raw.get("model", os.environ.get("AIDER_MODEL", "bedrock/eu.anthropic.claude-sonnet-4-20250514-v1:0"))),
    )


def clone_repo(repo_full_name: str, token: str, workspace: str) -> str:
    """Clone the target repository into the workspace. Returns local path."""
    repo_dir = os.path.join(workspace, "repo")
    clone_url = f"https://x-access-token:{token}@github.com/{repo_full_name}.git"
    git.Repo.clone_from(clone_url, repo_dir)
    return repo_dir


def create_branch(repo_path: str, issue_number: int) -> str:
    """Create a branch named issue-{number}. Returns branch name."""
    branch_name = f"issue-{issue_number}"
    repo = git.Repo(repo_path)
    repo.git.checkout("-b", branch_name)
    return branch_name


def format_commit_message(issue_number: int, issue_title: str) -> str:
    """Return a commit message referencing the issue number and title."""
    return f"[Issue #{issue_number}] {issue_title}"


def push_branch(repo_path: str, branch: str, token: str) -> None:
    """Push the branch to the remote repository."""
    repo = git.Repo(repo_path)
    # Update remote URL to include token for auth
    remote = repo.remote("origin")
    original_url = remote.url
    # Inject token into URL if not already present
    if "x-access-token" not in original_url:
        authed_url = original_url.replace(
            "https://", f"https://x-access-token:{token}@"
        )
        remote.set_url(authed_url)
    try:
        remote.push(refspec=f"{branch}:{branch}")
    finally:
        # Restore original URL to avoid leaking token in git config
        remote.set_url(original_url)
