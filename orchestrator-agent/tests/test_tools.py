"""Tests for tool modules."""

import pytest
from unittest.mock import MagicMock, patch


class TestGitHubTools:
    """Tests for GitHub tools."""

    def test_init_github_sets_client(self):
        from tools.github import init_github, _github_client, _current_repo
        
        with patch('tools.github.Github') as mock_github:
            init_github("test-token", "owner/repo")
            mock_github.assert_called_once_with("test-token")

    def test_get_issue_returns_dict(self):
        from tools import github
        
        # Mock the GitHub client
        mock_issue = MagicMock()
        mock_issue.number = 123
        mock_issue.title = "Test Issue"
        mock_issue.body = "Test body"
        mock_issue.state = "open"
        mock_issue.user.login = "testuser"
        mock_issue.get_comments.return_value = []
        
        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = mock_issue
        
        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        
        github._github_client = mock_client
        github._current_repo = "owner/repo"
        
        result = github.get_issue(123)
        
        assert result["number"] == 123
        assert result["title"] == "Test Issue"
        assert result["body"] == "Test body"
        assert result["state"] == "open"


class TestGitTools:
    """Tests for Git tools."""

    def test_init_git_creates_workspace(self):
        from tools.git import init_git, _workspace
        
        init_git("test-token", "owner/repo")
        
        from tools.git import _workspace as ws
        assert ws is not None
        assert "devless-" in ws

    def test_cleanup_removes_workspace(self):
        from tools import git
        import os
        import tempfile
        
        # Create a temp workspace
        git._workspace = tempfile.mkdtemp(prefix="test-devless-")
        git._repo = None
        
        assert os.path.exists(git._workspace)
        
        git.cleanup()
        
        assert git._workspace is None


class TestCodeTools:
    """Tests for Code tools."""

    def test_read_project_config_returns_defaults(self):
        from tools import code, git
        import tempfile
        import os
        
        # Create a temp repo without config
        git._workspace = tempfile.mkdtemp()
        git._repo = MagicMock()
        git._repo.working_dir = git._workspace
        
        result = code.read_project_config()
        
        assert "model" in result
        assert "test_command" in result
        assert "max_iterations" in result
        
        # Cleanup
        import shutil
        shutil.rmtree(git._workspace)
        git._workspace = None
        git._repo = None
