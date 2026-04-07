"""Configuration loader for the Devless Orchestrator."""
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Required environment variables — validated at startup."""

    SQS_QUEUE_URL: str
    S3_BUCKET: str
    AWS_REGION: str
    GITHUB_APP_ID: str
    GITHUB_APP_PRIVATE_KEY: str
    GITHUB_APP_INSTALLATION_ID: str


def load_config() -> dict[str, str]:
    """Read and validate required environment variables.

    Raises ``pydantic.ValidationError`` if any are missing.
    """
    s = Settings()  # type: ignore[call-arg]
    return s.model_dump()
