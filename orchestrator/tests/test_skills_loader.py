"""Tests for skills_loader: installation, merging, and Codex-compatible structure.

# Feature: codex-dev-team, Properties 5, 7
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import patch, MagicMock
from skills_loader import install_skills


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_clone(skills: dict[str, str], subdir: str = ".agents/skills"):
    def fake_clone(url, dest):
        for name, content in skills.items():
            skill_dir = os.path.join(dest, subdir, name)
            os.makedirs(skill_dir, exist_ok=True)
            with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
                f.write(content)
        return MagicMock()
    return fake_clone


# ---------------------------------------------------------------------------
# Discovery / structure tests
# ---------------------------------------------------------------------------

def test_merged_skills_all_have_skill_md():
    """After merging common + project skills, every skill dir has a SKILL.md."""
    with tempfile.TemporaryDirectory() as workspace:
        repo_path = os.path.join(workspace, "repo")
        os.makedirs(repo_path)

        call_count = [0]

        def fake_clone(url, dest):
            call_count[0] += 1
            skills_base = os.path.join(dest, ".agents", "skills")
            if call_count[0] == 1:
                for name in ["clean-code", "logging", "pytest"]:
                    d = os.path.join(skills_base, name)
                    os.makedirs(d, exist_ok=True)
                    with open(os.path.join(d, "SKILL.md"), "w") as f:
                        f.write(f"---\nname: {name}\ndescription: common\n---\n")
            else:
                for name in ["hypothesis", "logging"]:
                    d = os.path.join(skills_base, name)
                    os.makedirs(d, exist_ok=True)
                    with open(os.path.join(d, "SKILL.md"), "w") as f:
                        f.write(f"---\nname: {name}\ndescription: project\n---\n")
            return MagicMock()

        with patch("skills_loader.git.Repo.clone_from", side_effect=fake_clone):
            install_skills(
                repo_path,
                common_skills_repo_url="https://example.com/common.git",
                project_skills_repo_url="https://example.com/project.git",
            )

        skills_root = os.path.join(repo_path, ".agents", "skills")
        skill_dirs = sorted(
            d for d in os.listdir(skills_root)
            if os.path.isdir(os.path.join(skills_root, d))
        )
        assert skill_dirs == ["clean-code", "hypothesis", "logging", "pytest"]
        for name in skill_dirs:
            assert os.path.isfile(os.path.join(skills_root, name, "SKILL.md"))


# ---------------------------------------------------------------------------
# Installation / merging tests
# ---------------------------------------------------------------------------

def test_common_skills_installed():
    """Common skills are placed at <repo>/.agents/skills/."""
    with tempfile.TemporaryDirectory() as workspace:
        repo_path = os.path.join(workspace, "repo")
        os.makedirs(repo_path)

        fake = _make_fake_clone({"logging": "common-logging", "clean-code": "common-clean"})
        with patch("skills_loader.git.Repo.clone_from", side_effect=fake):
            install_skills(repo_path, common_skills_repo_url="https://example.com/common.git")

        assert os.path.isfile(os.path.join(repo_path, ".agents", "skills", "logging", "SKILL.md"))
        assert os.path.isfile(os.path.join(repo_path, ".agents", "skills", "clean-code", "SKILL.md"))


def test_project_skills_override_common():
    """Project-specific skills override common ones with the same name."""
    with tempfile.TemporaryDirectory() as workspace:
        repo_path = os.path.join(workspace, "repo")
        os.makedirs(repo_path)

        call_count = [0]

        def fake_clone(url, dest):
            call_count[0] += 1
            if call_count[0] == 1:
                _make_fake_clone({"logging": "common-logging", "pytest": "common-pytest"})(url, dest)
            else:
                _make_fake_clone({"logging": "project-logging", "custom": "project-custom"})(url, dest)
            return MagicMock()

        with patch("skills_loader.git.Repo.clone_from", side_effect=fake_clone):
            install_skills(
                repo_path,
                common_skills_repo_url="https://example.com/common.git",
                project_skills_repo_url="https://example.com/project.git",
            )

        with open(os.path.join(repo_path, ".agents", "skills", "logging", "SKILL.md")) as f:
            assert "project-logging" in f.read()
        with open(os.path.join(repo_path, ".agents", "skills", "pytest", "SKILL.md")) as f:
            assert "common-pytest" in f.read()
        assert os.path.isfile(os.path.join(repo_path, ".agents", "skills", "custom", "SKILL.md"))


def test_repo_own_skills_have_highest_priority():
    """Skills already in the repo take priority over both common and project."""
    with tempfile.TemporaryDirectory() as workspace:
        repo_path = os.path.join(workspace, "repo")
        repo_skill = os.path.join(repo_path, ".agents", "skills", "logging")
        os.makedirs(repo_skill)
        with open(os.path.join(repo_skill, "SKILL.md"), "w") as f:
            f.write("repo-own-logging")

        fake = _make_fake_clone({"logging": "common-logging", "pytest": "common-pytest"})
        with patch("skills_loader.git.Repo.clone_from", side_effect=fake):
            install_skills(repo_path, common_skills_repo_url="https://example.com/common.git")

        with open(os.path.join(repo_path, ".agents", "skills", "logging", "SKILL.md")) as f:
            assert "repo-own-logging" in f.read()
        with open(os.path.join(repo_path, ".agents", "skills", "pytest", "SKILL.md")) as f:
            assert "common-pytest" in f.read()


def test_no_skills_repos_is_noop():
    """When no skills repos are configured, nothing happens."""
    with tempfile.TemporaryDirectory() as workspace:
        repo_path = os.path.join(workspace, "repo")
        os.makedirs(repo_path)

        with patch("skills_loader.git.Repo.clone_from") as mock_clone:
            install_skills(repo_path)
            mock_clone.assert_not_called()
