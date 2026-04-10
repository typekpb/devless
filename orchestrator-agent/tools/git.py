"""Git tools - secrets never exposed to LLM, only tool results."""

import os
import shutil
import tempfile
from pathlib import Path
from strands import tool
import git as gitpython

# Workspace state - managed by orchestrator, not LLM
_workspace: str | None = None
_repo: gitpython.Repo | None = None
_token: str | None = None
_repo_full_name: str | None = None

# Path to default .aiderignore
_AIDERIGNORE_DEFAULT = Path(__file__).parent.parent / ".aiderignore.default"


def init_git(token: str, repo_full_name: str) -> None:
    """Initialize git context. Called by orchestrator, not LLM."""
    global _token, _repo_full_name, _workspace
    _token = token
    _repo_full_name = repo_full_name
    _workspace = tempfile.mkdtemp(prefix="devless-")


def get_workspace() -> str:
    """Get the workspace path. Used by aider tool."""
    if not _workspace:
        raise RuntimeError("Git not initialized")
    return _workspace


def get_repo_path() -> str | None:
    """Get the cloned repo path if available."""
    if _repo:
        return _repo.working_dir
    return None


def cleanup() -> None:
    """Clean up workspace. Called by orchestrator on completion."""
    global _workspace, _repo
    if _workspace and os.path.exists(_workspace):
        shutil.rmtree(_workspace, ignore_errors=True)
    _workspace = None
    _repo = None


@tool
def clone_repository() -> str:
    """Clone the target repository into the workspace.
    
    Returns:
        Path to the cloned repository
    """
    global _repo
    if not _token or not _repo_full_name or not _workspace:
        raise RuntimeError("Git not initialized")
    
    repo_dir = os.path.join(_workspace, "repo")
    # Token embedded in URL - never shown to LLM, only used internally
    clone_url = f"https://x-access-token:{_token}@github.com/{_repo_full_name}.git"
    
    _repo = gitpython.Repo.clone_from(clone_url, repo_dir)
    _repo.config_writer().set_value("user", "name", "Devless Bot").release()
    _repo.config_writer().set_value("user", "email", "devless-bot@users.noreply.github.com").release()
    
    # Add default .aiderignore if repo doesn't have one
    aiderignore_path = os.path.join(repo_dir, ".aiderignore")
    if not os.path.exists(aiderignore_path) and _AIDERIGNORE_DEFAULT.exists():
        shutil.copy(_AIDERIGNORE_DEFAULT, aiderignore_path)
        # Add to local git exclude so it won't appear in PRs
        exclude_path = os.path.join(repo_dir, ".git", "info", "exclude")
        with open(exclude_path, "a") as f:
            f.write("\n.aiderignore\n")
    
    return repo_dir


@tool
def create_branch(branch_name: str) -> str:
    """Create and checkout a new branch, or checkout if it already exists.
    
    Args:
        branch_name: Name for the new branch
        
    Returns:
        Confirmation message
    """
    if not _repo:
        raise RuntimeError("Repository not cloned")
    
    # Check if branch exists locally or remotely
    try:
        _repo.git.checkout("-b", branch_name)
        return f"Created and checked out branch: {branch_name}"
    except gitpython.GitCommandError:
        # Branch might exist, try to checkout
        try:
            _repo.git.checkout(branch_name)
            return f"Checked out existing branch: {branch_name}"
        except gitpython.GitCommandError:
            # Try fetching and checking out remote branch
            _repo.git.fetch("origin", branch_name)
            _repo.git.checkout(branch_name)
            return f"Checked out remote branch: {branch_name}"


@tool
def checkout_branch(branch_name: str) -> str:
    """Checkout an existing branch.
    
    Args:
        branch_name: Name of the branch to checkout
        
    Returns:
        Confirmation message
    """
    if not _repo:
        raise RuntimeError("Repository not cloned")
    _repo.git.checkout(branch_name)
    return f"Checked out branch: {branch_name}"


@tool
def get_status() -> dict:
    """Get the current git status.
    
    Returns:
        Status including branch name, changed files, and staged files
    """
    if not _repo:
        raise RuntimeError("Repository not cloned")
    
    return {
        "branch": _repo.active_branch.name,
        "changed_files": [item.a_path for item in _repo.index.diff(None)],
        "staged_files": [item.a_path for item in _repo.index.diff("HEAD")],
        "untracked_files": _repo.untracked_files,
    }


@tool
def push_branch(branch_name: str, force: bool = False) -> str:
    """Push a branch to the remote repository.
    
    Args:
        branch_name: Name of the branch to push
        force: Force push (use when branch already exists remotely)
        
    Returns:
        Confirmation message
    """
    if not _repo or not _token:
        raise RuntimeError("Repository not cloned or token not set")
    
    remote = _repo.remote("origin")
    original_url = remote.url
    
    # Inject token for push - never exposed to LLM
    if "x-access-token" not in original_url:
        authed_url = original_url.replace("https://", f"https://x-access-token:{_token}@")
        remote.set_url(authed_url)
    
    try:
        if force:
            remote.push(refspec=f"{branch_name}:{branch_name}", force=True)
        else:
            # Try normal push first, force if it fails
            try:
                remote.push(refspec=f"{branch_name}:{branch_name}")
            except gitpython.GitCommandError:
                remote.push(refspec=f"{branch_name}:{branch_name}", force=True)
    finally:
        remote.set_url(original_url)
    
    return f"Pushed branch: {branch_name}"
