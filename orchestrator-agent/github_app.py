"""GitHub App authentication - mints short-lived installation tokens."""

import os
import time
from pathlib import Path

from github import Auth, GithubIntegration

# Script directory for resolving relative paths
_SCRIPT_DIR = Path(__file__).parent


class GitHubAppAuth:
    """Wraps GitHub App credentials and produces installation tokens on demand."""

    def __init__(self, app_id: str, private_key: str, installation_id: str):
        self._app_id = int(app_id)
        self._private_key = private_key
        self._installation_id = int(installation_id)
        self._token: str | None = None
        self._expires_at: float = 0

    def token(self) -> str:
        """Return a valid installation token, refreshing if needed."""
        if self._token and time.time() < self._expires_at:
            return self._token

        print("==> Minting new GitHub App installation token")
        auth = Auth.AppAuth(self._app_id, self._private_key)
        gi = GithubIntegration(auth=auth)
        installation_auth = gi.get_access_token(self._installation_id)
        self._token = installation_auth.token
        # Expire 5 minutes early to avoid edge cases
        self._expires_at = installation_auth.expires_at.timestamp() - 300
        return self._token


def get_github_auth() -> GitHubAppAuth:
    """Create GitHubAppAuth from environment variables."""
    app_id = os.environ.get("GITHUB_APP_ID")
    installation_id = os.environ.get("GITHUB_APP_INSTALLATION_ID")

    # Private key can be inline or from file
    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY", "")
    key_file = os.environ.get("GITHUB_APP_PRIVATE_KEY_FILE")

    if key_file and not private_key:
        key_path = Path(key_file).expanduser()
        if key_path.exists():
            private_key = key_path.read_text()

    if not all([app_id, private_key, installation_id]):
        raise ValueError(
            "Missing GitHub App config. Set GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID, "
            "and either GITHUB_APP_PRIVATE_KEY or GITHUB_APP_PRIVATE_KEY_FILE"
        )

    return GitHubAppAuth(app_id, private_key, installation_id)
