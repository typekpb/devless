"""Code tools - run aider for code changes, read project config."""

import os
from strands import tool
from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model
import yaml

from tools.git import get_repo_path


@tool
def read_project_config() -> dict:
    """Read the .devless/config.yml from the repository.
    
    Returns:
        Project configuration including model, test_command, max_iterations
    """
    repo_path = get_repo_path()
    if not repo_path:
        raise RuntimeError("Repository not cloned")
    
    config_path = os.path.join(repo_path, ".devless", "config.yml")
    defaults = {
        "model": os.environ.get("AIDER_MODEL", "bedrock/anthropic.claude-3-haiku-20240307-v1:0"),
        "test_command": os.environ.get("TEST_COMMAND", "pytest"),
        "max_iterations": int(os.environ.get("MAX_ITERATIONS", "10")),
    }
    
    if os.path.isfile(config_path):
        with open(config_path, "r") as f:
            raw = yaml.safe_load(f) or {}
        return {
            "model": raw.get("model", defaults["model"]),
            "test_command": raw.get("test_command", defaults["test_command"]),
            "max_iterations": raw.get("max_iterations", defaults["max_iterations"]),
        }
    
    return defaults


@tool
def run_aider(
    message: str,
    test_command: str = "pytest",
    max_iterations: int = 10,
    model: str = "bedrock/anthropic.claude-3-haiku-20240307-v1:0",
) -> dict:
    """Run Aider to make code changes based on the given instructions.
    
    Aider will analyze the codebase, make changes, and run tests to verify.
    
    Args:
        message: Instructions for what code changes to make
        test_command: Command to run tests (default: pytest)
        max_iterations: Maximum attempts to make changes pass tests
        model: LLM model to use for code generation
        
    Returns:
        Result including success status, output, and any clarification needed
    """
    repo_path = get_repo_path()
    if not repo_path:
        raise RuntimeError("Repository not cloned")
    
    original_dir = os.getcwd()
    output_lines = []
    success = False
    needs_clarification = False
    clarification_question = None
    
    try:
        os.chdir(repo_path)
        
        io_obj = InputOutput(yes=True)
        model_obj = Model(model)
        
        coder = Coder.create(
            main_model=model_obj,
            io=io_obj,
            fnames=[],
            auto_test=True,
            test_cmd=test_command,
        )
        
        for i in range(max_iterations):
            coder.run(message)
            
            # Check if Aider committed changes (success signal)
            if coder.last_aider_commit_hash:
                success = True
                break
        
        # Check for clarification signals in output
        output = "\n".join(output_lines)
        clarification_phrases = [
            "I need clarification",
            "Could you clarify",
            "Please clarify",
            "need more information",
        ]
        for phrase in clarification_phrases:
            if phrase.lower() in output.lower():
                needs_clarification = True
                for line in output.splitlines():
                    if phrase.lower() in line.lower():
                        clarification_question = line.strip()
                        break
                break
        
    except Exception as exc:
        return {
            "success": False,
            "needs_clarification": False,
            "clarification_question": None,
            "output": f"Error: {exc}",
        }
    finally:
        os.chdir(original_dir)
    
    return {
        "success": success,
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_question,
        "output": "\n".join(output_lines)[-3000:] if output_lines else "Completed",
    }


@tool
def list_files(path: str = ".") -> list[str]:
    """List files in the repository.
    
    Args:
        path: Relative path within the repository (default: root)
        
    Returns:
        List of file paths
    """
    repo_path = get_repo_path()
    if not repo_path:
        raise RuntimeError("Repository not cloned")
    
    full_path = os.path.join(repo_path, path)
    if not os.path.exists(full_path):
        return []
    
    files = []
    for root, dirs, filenames in os.walk(full_path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in filenames:
            if not filename.startswith("."):
                rel_path = os.path.relpath(os.path.join(root, filename), repo_path)
                files.append(rel_path)
    
    return files[:100]  # Limit to avoid huge outputs


@tool
def read_file(path: str) -> str:
    """Read a file from the repository.
    
    Args:
        path: Relative path to the file
        
    Returns:
        File contents
    """
    repo_path = get_repo_path()
    if not repo_path:
        raise RuntimeError("Repository not cloned")
    
    full_path = os.path.join(repo_path, path)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"File not found: {path}")
    
    with open(full_path, "r") as f:
        content = f.read()
    
    # Truncate very large files
    if len(content) > 50000:
        content = content[:50000] + "\n... (truncated)"
    
    return content
