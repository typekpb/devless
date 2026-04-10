"""Entry point - polls SQS and invokes the agent."""

import os
import signal
import sys

from github import Github

from agent import create_agent, handle_issue, handle_pr_feedback
from sqs_consumer import poll_message, delete_message, TaskPayload
from github_app import get_github_auth


def is_issue_closed(repo: str, issue_number: int, token: str) -> bool:
    """Check if an issue or PR is closed."""
    try:
        gh = Github(token)
        issue = gh.get_repo(repo).get_issue(issue_number)
        return issue.state == "closed"
    except Exception:
        return False


def process_task(payload: TaskPayload, github_token: str, agent) -> None:
    """Process a single task based on event type."""
    
    # Skip closed issues/PRs
    if is_issue_closed(payload.repository_full_name, payload.issue_number, github_token):
        print(f"==> Issue/PR #{payload.issue_number} is closed, skipping")
        return
    
    if payload.event_type in ("issues", "issue_comment"):
        handle_issue(
            agent=agent,
            repo=payload.repository_full_name,
            issue_number=payload.issue_number,
            issue_title=payload.issue_title,
            issue_body=payload.issue_body,
            github_token=github_token,
        )
    
    elif payload.event_type in ("pr_comment", "pr_review", "pr_issue_comment"):
        # Agent will fetch PR details and determine branch via get_pull_request tool
        handle_pr_feedback(
            agent=agent,
            repo=payload.repository_full_name,
            pr_number=payload.issue_number,
            feedback=payload.issue_body,
            github_token=github_token,
        )
    
    elif payload.event_type == "ci_fix":
        handle_pr_feedback(
            agent=agent,
            repo=payload.repository_full_name,
            pr_number=payload.issue_number,
            feedback=f"CI failed. Error:\n\n{payload.issue_body}\n\nPlease fix the failing tests.",
            github_token=github_token,
        )


def main() -> None:
    """Main loop - poll SQS and process tasks."""
    queue_url = os.environ.get("SQS_QUEUE_URL")
    if not queue_url:
        print("ERROR: SQS_QUEUE_URL not set")
        sys.exit(1)
    
    model_id = os.environ.get(
        "BEDROCK_MODEL",
        "anthropic.claude-3-haiku-20240307-v1:0"
    )
    
    github_auth = get_github_auth()
    agent = create_agent(model_id)
    
    print(f"==> Orchestrator starting, polling {queue_url}")
    print(f"==> Using model: {model_id}")
    
    shutdown = False
    
    def handle_sigterm(signum, frame):
        nonlocal shutdown
        shutdown = True
        print("==> SIGTERM received, finishing current task...")
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    while not shutdown:
        msg = poll_message(queue_url)
        if not msg:
            continue
        
        print(f"\n{'='*60}")
        print(f"==> Processing: {msg.payload.repository_full_name} #{msg.payload.issue_number}")
        print(f"==> Event type: {msg.payload.event_type}")
        print(f"{'='*60}")
        
        try:
            github_token = github_auth.token()
            process_task(msg.payload, github_token, agent)
            delete_message(queue_url, msg.receipt_handle)
            print("==> Task completed, message deleted")
        except Exception as e:
            print(f"==> Error processing task: {e}")
            # Message will return to queue after visibility timeout
    
    print("==> Orchestrator shutting down")


if __name__ == "__main__":
    # Support manual invocation for testing
    if len(sys.argv) >= 3:
        github_auth = get_github_auth()
        agent = create_agent()
        
        repo = sys.argv[1]
        issue_number = int(sys.argv[2])
        title = sys.argv[3] if len(sys.argv) > 3 else "Test issue"
        body = sys.argv[4] if len(sys.argv) > 4 else "Test body"
        
        handle_issue(
            agent=agent,
            repo=repo,
            issue_number=issue_number,
            issue_title=title,
            issue_body=body,
            github_token=github_auth.token(),
        )
    else:
        main()
