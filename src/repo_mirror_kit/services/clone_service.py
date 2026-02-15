from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CloneResult:
    """Result of a git clone operation."""

    success: bool
    message: str


def validate_project_name(name: str) -> str | None:
    """Validate a project name for use as a directory name.

    Args:
        name: The project name to validate.

    Returns:
        An error message if invalid, or None if valid.
    """
    if not name or not name.strip():
        return "Project name is required."
    name = name.strip()
    if re.search(r'[/\\:*?"<>|]', name):
        return "Project name contains invalid characters."
    if name in (".", ".."):
        return "Project name cannot be '.' or '..'."
    return None


def validate_git_url(url: str) -> str | None:
    """Validate a git URL for basic format.

    Args:
        url: The git URL to validate.

    Returns:
        An error message if invalid, or None if valid.
    """
    if not url or not url.strip():
        return "Git URL is required."
    url = url.strip()
    if " " in url:
        return "Git URL cannot contain spaces."
    return None


def check_git_available() -> bool:
    """Check if git is available on the system PATH."""
    return shutil.which("git") is not None


def clone_repository(
    url: str,
    project_name: str,
    base_dir: Path | None = None,
) -> Generator[str, None, CloneResult]:
    """Clone a git repository, yielding output lines as they arrive.

    Args:
        url: The git repository URL to clone.
        project_name: The name for the project directory.
        base_dir: Base directory for projects. Defaults to ./projects/.

    Yields:
        Lines of git clone output (stdout and stderr).

    Returns:
        A CloneResult indicating success or failure.
    """
    if base_dir is None:
        base_dir = Path("projects")

    base_dir.mkdir(parents=True, exist_ok=True)
    target_dir = base_dir / project_name

    if target_dir.exists():
        return CloneResult(
            success=False,
            message=f"Directory already exists: {target_dir}",
        )

    try:
        process = subprocess.Popen(
            ["git", "clone", "--progress", url, str(target_dir)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        return CloneResult(
            success=False, message="git is not installed or not on PATH."
        )

    if process.stderr is None:
        process.kill()
        process.wait()
        return CloneResult(success=False, message="Failed to capture git output.")

    try:
        for line in process.stderr:
            stripped = line.rstrip("\n")
            if stripped:
                yield stripped

        process.wait()

        if process.returncode == 0:
            return CloneResult(success=True, message="Clone complete")
        return CloneResult(
            success=False,
            message=f"git clone failed with exit code {process.returncode}",
        )
    except Exception as exc:
        process.kill()
        process.wait()
        return CloneResult(success=False, message=str(exc))
