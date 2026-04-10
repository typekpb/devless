"""Strands-based agent for handling GitHub issues."""

from pathlib import Path
from strands import Agent
from strands.models import BedrockModel

from tools import ALL_TOOLS, init_github, init_git, cleanup

AGENTS_DIR = Path(__file__).parent / ".agents"
SYSTEM_PROMPT_FILE = AGENTS_DIR / "SYSTEM.md"
SKILLS_DIR = AGENTS_DIR / "skills"


def load_system_prompt() -> str:
    """Load the system prompt and all skills."""
    parts = []
    
    # Load main system prompt
    if SYSTEM_PROMPT_FILE.exists():
        parts.append(SYSTEM_PROMPT_FILE.read_text())
    else:
        parts.append("You are an AI coding agent.")
    
    # Load all skills
    if SKILLS_DIR.exists():
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    parts.append(f"\n\n---\n\n{skill_file.read_text()}")
    
    return "".join(parts)


def create_agent(model_id: str = "anthropic.claude-3-haiku-20240307-v1:0") -> Agent:
    """Create a Strands agent with all tools."""
    model = BedrockModel(
        model_id=model_id,
        region_name="us-east-1",
    )
    
    return Agent(
        model=model,
        system_prompt=load_system_prompt(),
        tools=ALL_TOOLS,
    )


def handle_issue(
    agent: Agent,
    repo: str,
    issue_number: int,
    issue_title: str,
    issue_body: str,
    github_token: str,
) -> str:
    """Handle a new issue or issue comment."""
    # Initialize tools with secrets (never exposed to LLM)
    init_github(github_token, repo)
    init_git(github_token, repo)
    
    try:
        prompt = f"""Handle this GitHub issue:

Repository: {repo}
Issue #{issue_number}: {issue_title}

{issue_body}

Follow the workflow for new issues: acknowledge, clone, branch, config, implement, push, create PR, complete."""

        response = agent(prompt)
        return response.message
    finally:
        cleanup()


def handle_pr_feedback(
    agent: Agent,
    repo: str,
    pr_number: int,
    feedback: str,
    branch: str,
    github_token: str,
) -> str:
    """Handle PR feedback (review comments, etc.)."""
    # Initialize tools with secrets (never exposed to LLM)
    init_github(github_token, repo)
    init_git(github_token, repo)
    
    try:
        prompt = f"""Handle this PR feedback:

Repository: {repo}
PR #{pr_number}
Branch: {branch}

Feedback:
{feedback}

Follow the workflow for PR feedback: acknowledge, clone, checkout branch, config, implement, push, complete."""

        response = agent(prompt)
        return response.message
    finally:
        cleanup()
