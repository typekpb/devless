"""Configuration loader for the Devless Orchestrator."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Required environment variables — validated at startup."""

    SQS_QUEUE_URL: str
    S3_BUCKET: str
    AWS_REGION: str
    GITHUB_APP_ID: str
    GITHUB_APP_PRIVATE_KEY: str = ""
    GITHUB_APP_PRIVATE_KEY_FILE: str = ""
    GITHUB_APP_INSTALLATION_ID: str


def load_config() -> dict[str, str]:
    """Read and validate required environment variables.

    Supports loading GITHUB_APP_PRIVATE_KEY from a file via
    GITHUB_APP_PRIVATE_KEY_FILE env var.

    Raises ``pydantic.ValidationError`` if any are missing.
    """
    s = Settings()  # type: ignore[call-arg]
    result = s.model_dump()

    # Load private key from file if specified
    if s.GITHUB_APP_PRIVATE_KEY_FILE and not s.GITHUB_APP_PRIVATE_KEY:
        key_path = Path(s.GITHUB_APP_PRIVATE_KEY_FILE).expanduser()
        result["GITHUB_APP_PRIVATE_KEY"] = key_path.read_text()
    
    if not result["GITHUB_APP_PRIVATE_KEY"]:
        raise ValueError("Either GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_FILE must be set")

    return result
