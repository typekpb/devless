"""Entry point for the Codex Dev Team Orchestrator.

Runs as a long-lived ECS service that long-polls SQS for tasks.
See pipeline.py for the per-message processing logic.
"""
from __future__ import annotations

import os
import signal
import sys

import logger as log
from config import load_config
from pipeline import process_message, ClarificationNeeded
from sqs_consumer import poll_message


def main() -> None:
    """Poll SQS, process messages, repeat. Exits cleanly on SIGTERM."""
    cfg = load_config()
    queue_url = cfg["SQS_QUEUE_URL"]

    log.info("Orchestrator starting — polling SQS", queue_url=queue_url)

    _shutdown = False

    def _handle_sigterm(signum, frame):
        nonlocal _shutdown
        _shutdown = True
        log.info("SIGTERM received — finishing current task then exiting")

    signal.signal(signal.SIGTERM, _handle_sigterm)

    github_token = os.environ.get("GITHUB_TOKEN", "")
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")

    if not github_token or not openai_api_key:
        log.error("Missing GITHUB_TOKEN or OPENAI_API_KEY environment variables")
        sys.exit(1)

    while not _shutdown:
        msg = poll_message(queue_url)
        if msg is None:
            continue

        try:
            process_message(msg, cfg, github_token, openai_api_key)
        except ClarificationNeeded:
            log.info("Awaiting user clarification", issue_number=msg.payload.issue_number)
        except Exception as exc:
            log.error(
                "Failed to process message",
                issue_number=msg.payload.issue_number,
                error=str(exc),
            )

    log.info("Orchestrator shutting down gracefully")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as _top_exc:  # pragma: no cover
        import traceback
        log.error("Unhandled exception escaped main()", error=traceback.format_exc())
        sys.exit(1)
