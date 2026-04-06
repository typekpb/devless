"""Pipeline package — state-machine-driven task processing."""

from pipeline.runner import process_message
from pipeline.stages import ClarificationNeeded

__all__ = ["process_message", "ClarificationNeeded"]
