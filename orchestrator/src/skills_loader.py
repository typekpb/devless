"""Skills installation into the Codex-discoverable location.

Codex automatically discovers skills from `.agents/skills/` relative to
the working directory. This module:

1. Clones the common (org-wide) skills repo into `.agents/skills/`
2. Merges any project-specific skills from the repo's own `.agents/skills/`

Project-specific skills override common ones when they share the same
directory name.
"""

import os
import shutil

import git

_SKILLS_REL = os.path.join(".agents", "skills")


def install_skills(
    repo_path: str,
    common_skills_repo_url: str | None = None,
    project_skills_repo_url: str | None = None,
) -> None:
    """Install and merge common + project-specific skills.

    The final `.agents/skills/` directory in the workspace will contain:
    - All skills from the common repo
    - All skills from the project-specific repo (overriding common ones
      with the same directory name)
    - Any skills already present in the target repo itself

    Args:
        repo_path: Path to the cloned target repository.
        common_skills_repo_url: Git URL of the org-wide common skills repo.
        project_skills_repo_url: Git URL of a project-specific skills repo
            (typically from .codex/config.yml).
    """
    dest = os.path.join(repo_path, _SKILLS_REL)

    # Snapshot any skills already in the repo (highest priority)
    existing_backup: str | None = None
    if os.path.isdir(dest):
        existing_backup = dest + "__repo_backup"
        shutil.copytree(dest, existing_backup)

    # 1. Install common skills first (base layer)
    if common_skills_repo_url:
        _clone_skills_into(common_skills_repo_url, dest, "common")

    # 2. Install project-specific skills (override layer)
    if project_skills_repo_url:
        _clone_skills_into(project_skills_repo_url, dest, "project")

    # 3. Restore repo's own skills on top (highest priority)
    if existing_backup:
        for name in os.listdir(existing_backup):
            src_skill = os.path.join(existing_backup, name)
            if not os.path.isdir(src_skill):
                continue
            dest_skill = os.path.join(dest, name)
            if os.path.exists(dest_skill):
                shutil.rmtree(dest_skill)
            shutil.copytree(src_skill, dest_skill)
        shutil.rmtree(existing_backup, ignore_errors=True)


def _clone_skills_into(repo_url: str, dest: str, label: str) -> None:
    """Clone a skills repo and copy its .agents/skills/ content into dest."""
    tmp = dest + f"__{label}_clone"
    try:
        git.Repo.clone_from(repo_url, tmp)

        src = os.path.join(tmp, _SKILLS_REL)
        if not os.path.isdir(src):
            # Fallback: repo root contains skill directories directly
            src = tmp

        os.makedirs(dest, exist_ok=True)

        for name in os.listdir(src):
            src_skill = os.path.join(src, name)
            if not os.path.isdir(src_skill):
                continue
            dest_skill = os.path.join(dest, name)
            # Later layers overwrite earlier ones
            if os.path.exists(dest_skill):
                shutil.rmtree(dest_skill)
            shutil.copytree(src_skill, dest_skill)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
