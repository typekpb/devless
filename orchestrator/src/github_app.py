"""GitHub App authentication — mints short-lived installation tokens."""
from __future__ import annotations

import time

from github import Auth, Github, GithubIntegration

import logger as log


class GitHubAppAuth:
    """Wraps GitHub App credentials and produces installation tokens on demand.

    Tokens are cached and refreshed automatically when they expire.
    """

    def __init__(self, app_id: str, private_key: str, installation_id: str) -> None:
        self._app_id = int(app_id)
        self._private_key = private_key
        self._installation_id = int(installation_id)
        self._token: str | None = None
        self._expires_at: float = 0

    def token(self) -> str:
        """Return a valid installation token, refreshing if needed."""
        if self._token and time.time() < self._expires_at:
            return self._token

        log.info("Minting new GitHub App installation token")
        auth = Auth.AppAuth(self._app_id, self._private_key)
        gi = GithubIntegration(auth=auth)
        installation_auth = gi.get_access_token(self._installation_id)
        self._token = installation_auth.token
        # Expire 5 minutes early to avoid edge cases
        self._expires_at = installation_auth.expires_at.timestamp() - 300
        return self._token

    def github(self) -> Github:
        """Return an authenticated Github client."""
        return Github(self.token())
