"""Aider invocation via the Python API."""
from __future__ import annotations

import os
from dataclasses import dataclass

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model


# Explicit clarification signal that Aider can emit
_CLARIFICATION_SIGNAL = "CLARIFICATION_NEEDED:"

# Natural-language phrases that also indicate Aider needs clarification
_CLARIFICATION_PHRASES = (
    "I need clarification",
    "Could you clarify",
    "Please clarify",
    "need more information",
    "need clarification",
)


@dataclass
class AiderResult:
    """Result returned by :func:`run_aider`."""

    success: bool
    needs_clarification: bool
    clarification_question: str | None
    output: str


def build_issue_message(
    issue_title: str,
    issue_body: str,
    comments: list[str],
    skills_content: str,
) -> str:
    """Construct the Aider prompt from issue components.

    Combines the issue title, body, all comments in chronological order,
    and skills content into a single message string.  All four components
    are guaranteed to appear as substrings in the returned string.

    Args:
        issue_title: The GitHub issue title.
        issue_body: The GitHub issue body text.
        comments: Chronologically-ordered list of comment bodies.
        skills_content: Concatenated contents of all skills.md files.

    Returns:
        A formatted string suitable for passing to ``coder.run()``.
    """
    parts: list[str] = [issue_title, "\n\n", issue_body]

    if comments:
        parts.append("\n\n## Issue Comments\n\n")
        parts.append("\n\n---\n\n".join(comments))

    if skills_content:
        parts.append("\n\n## Skills / Guidelines\n\n")
        parts.append(skills_content)

    return "".join(parts)


def _detect_clarification(output: str) -> tuple[bool, str | None]:
    """Scan captured output for clarification signals.

    Returns a tuple of (needs_clarification, question_text).
    """
    # Check for explicit structured signal first
    if _CLARIFICATION_SIGNAL in output:
        for line in output.splitlines():
            if _CLARIFICATION_SIGNAL in line:
                question = line.split(_CLARIFICATION_SIGNAL, 1)[1].strip()
                return True, question or None

    # Check for natural-language clarification phrases
    for phrase in _CLARIFICATION_PHRASES:
        if phrase.lower() in output.lower():
            # Extract the sentence containing the phrase as the question
            for line in output.splitlines():
                if phrase.lower() in line.lower():
                    return True, line.strip() or None

    return False, None


def run_aider(
    workspace: str,
    issue_message: str,
    test_cmd: str,
    max_iterations: int = 10,
    model: str = "bedrock/eu.anthropic.claude-sonnet-4-20250514-v1:0",
) -> AiderResult:
    """Invoke Aider and return the result.

    Runs Aider with the o3 model in non-interactive mode, enabling auto-test
    with the provided test command. Skills are discovered automatically
    from `.agents/skills/` in the workspace.
    Wraps Aider's internal retry loop with an outer cap of ``max_iterations``.

    Args:
        workspace: Absolute path to the cloned repository directory.
        issue_message: The full prompt to send to Aider (issue title + body +
            comments).  Build with :func:`build_issue_message`.
        test_cmd: Shell command Aider runs after each edit to verify correctness.
        max_iterations: Maximum number of outer aider loop iterations (default 10).

    Returns:
        An :class:`AiderResult` describing the outcome.
    """
    import logger as log
    log.info("run_aider called", workspace=workspace, model=model)

    output_lines: list[str] = []
    original_dir = os.getcwd()
    success = False

    try:
        # Change to workspace directory so Aider operates on the right repo
        os.chdir(workspace)
        log.info("Changed to workspace", cwd=os.getcwd())

        log.info("Creating InputOutput")
        io_obj = InputOutput(yes=True)
        log.info("InputOutput created")

        log.info("Creating Model", model=model)
        model_obj = Model(model)
        log.info("Model created")

        log.info("Creating Aider coder instance")
        coder = Coder.create(
            main_model=model_obj,
            io=io_obj,
            fnames=[],
            auto_test=True,
            test_cmd=test_cmd,
        )
        log.info("Aider coder created, starting iterations")

        for i in range(max_iterations):
            log.info("Aider iteration starting", iteration=i + 1, max=max_iterations)
            coder.run(issue_message)
            log.info("Aider iteration finished", iteration=i + 1, max=max_iterations)

            # Check for clarification signal
            current_output = "\n".join(output_lines)
            needs_clarification, question = _detect_clarification(current_output)
            if needs_clarification:
                os.chdir(original_dir)
                return AiderResult(
                    success=False,
                    needs_clarification=True,
                    clarification_question=question,
                    output=current_output,
                )

            # Req 2.5: task is done when Aider exits with zero status and tests pass.
            # Aider signals completion via last_aider_commit_hash being set.
            if coder.last_aider_commit_hash:
                log.info("Aider committed changes", commit=coder.last_aider_commit_hash)
                success = True
                break

        # If we exhausted iterations without success, success remains False (req 2.7)

    except Exception as exc:
        log.info("Aider exception", error=str(exc))
        os.chdir(original_dir)
        return AiderResult(
            success=False,
            needs_clarification=False,
            clarification_question=None,
            output=f"Exception: {exc}",
        )
    finally:
        os.chdir(original_dir)

    output = "\n".join(output_lines)

    # Final clarification check on full output (in case it appeared in last iteration)
    needs_clarification, question = _detect_clarification(output)
    if needs_clarification:
        return AiderResult(
            success=False,
            needs_clarification=True,
            clarification_question=question,
            output=output,
        )

    return AiderResult(
        success=success,
        needs_clarification=False,
        clarification_question=None,
        output=output,
    )
