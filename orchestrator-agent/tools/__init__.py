"""Tools for the Devless agent."""

from tools.github import (
    init_github,
    get_issue,
    post_comment,
    create_pull_request,
    get_pull_request,
)
from tools.git import (
    init_git,
    get_workspace,
    get_repo_path,
    cleanup,
    clone_repository,
    create_branch,
    checkout_branch,
    get_status,
    push_branch,
)
from tools.code import (
    read_project_config,
    run_aider,
    list_files,
    read_file,
)

# All tools available to the agent
ALL_TOOLS = [
    # GitHub
    get_issue,
    post_comment,
    create_pull_request,
    get_pull_request,
    # Git
    clone_repository,
    create_branch,
    checkout_branch,
    get_status,
    push_branch,
    # Code
    read_project_config,
    run_aider,
    list_files,
    read_file,
]

__all__ = [
    # Init functions (called by orchestrator, not exposed to LLM)
    "init_github",
    "init_git",
    "cleanup",
    "get_workspace",
    "get_repo_path",
    # Tools (exposed to LLM)
    "ALL_TOOLS",
]
