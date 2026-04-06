"""S3-backed checkpoint read/write for resumable pipeline stages."""
from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from models import CheckpointState


def _s3_key(repo: str, issue_number: int) -> str:
    owner, name = repo.split("/", 1)
    return f"workspaces/{owner}/{name}/{issue_number}/checkpoint.json"


def write_checkpoint(state: CheckpointState, bucket: str) -> None:
    """Serialize *state* to JSON and write to S3."""
    key = _s3_key(state.repository_full_name, state.issue_number)
    client = boto3.client("s3")
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=state.model_dump_json().encode(),
        ContentType="application/json",
    )


def read_checkpoint(
    issue_number: int, repo: str, bucket: str
) -> CheckpointState | None:
    """Read checkpoint from S3. Returns None if not found."""
    key = _s3_key(repo, issue_number)
    client = boto3.client("s3")
    try:
        response = client.get_object(Bucket=bucket, Key=key)
        raw = response["Body"].read().decode()
        return CheckpointState.model_validate_json(raw)
    except ClientError as exc:
        if exc.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        raise
