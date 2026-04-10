"""GitHub tools - secrets never exposed to LLM, only tool results."""

from strands import tool
from github import Github

# Token injected at runtime, never passed to LLM
_github_client: Github | None = None
_current_repo: str | None = None


def init_github(token: str, repo: str) -> None:
    """Initialize GitHub client with token. Called by orchestrator, not LLM."""
    global _github_client, _current_repo
    _github_client = Github(token)
    _current_repo = repo


def _get_repo():
    if not _github_client or not _current_repo:
        raise RuntimeError("GitHub not initialized")
    return _github_client.get_repo(_current_repo)


@tool
def get_issue(issue_number: int) -> dict:
    """Get details of a GitHub issue.
    
    Args:
        issue_number: The issue number to fetch
        
    Returns:
        Issue details including title, body, state, and comments
    """
    repo = _get_repo()
    issue = repo.get_issue(issue_number)
    comments = [
        {"author": c.user.login, "body": c.body, "created_at": c.created_at.isoformat()}
        for c in issue.get_comments()
    ]
    return {
        "number": issue.number,
        "title": issue.title,
        "body": issue.body or "",
        "state": issue.state,
        "author": issue.user.login,
        "comments": comments,
    }


@tool
def post_comment(issue_number: int, body: str) -> str:
    """Post a comment on a GitHub issue or PR.
    
    Args:
        issue_number: The issue/PR number
        body: The comment text (supports markdown)
        
    Returns:
        Confirmation message
    """
    repo = _get_repo()
    issue = repo.get_issue(issue_number)
    issue.create_comment(body)
    return f"Comment posted on #{issue_number}"


@tool
def create_pull_request(
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = "main",
) -> dict:
    """Create a pull request.
    
    Args:
        title: PR title
        body: PR description (supports markdown)
        head_branch: Branch with changes
        base_branch: Target branch (default: main)
        
    Returns:
        PR details including number and URL
    """
    repo = _get_repo()
    pr = repo.create_pull(
        title=title,
        body=body,
        head=head_branch,
        base=base_branch,
    )
    # Try to enable auto-merge
    try:
        pr.enable_automerge(merge_method="SQUASH")
    except Exception:
        pass  # Repo may not support auto-merge
    
    return {
        "number": pr.number,
        "url": pr.html_url,
        "state": pr.state,
    }


@tool
def get_pull_request(pr_number: int) -> dict:
    """Get details of a pull request.
    
    Args:
        pr_number: The PR number
        
    Returns:
        PR details including branch, state, and review comments
    """
    repo = _get_repo()
    pr = repo.get_pull(pr_number)
    review_comments = [
        {"author": c.user.login, "body": c.body, "path": c.path}
        for c in pr.get_review_comments()
    ]
    return {
        "number": pr.number,
        "title": pr.title,
        "body": pr.body or "",
        "state": pr.state,
        "head_branch": pr.head.ref,
        "base_branch": pr.base.ref,
        "review_comments": review_comments,
    }
