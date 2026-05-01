"""Shared fixtures for harvester integration tests."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

FIXTURES_ROOT = Path(__file__).parent.parent / "fixtures" / "sample-projects"


@pytest.fixture
def local_git_repo(tmp_path: Path) -> Callable[[str], Path]:
    """Return a factory that copies a fixture project into ``tmp_path`` and
    initializes it as a git repository.

    The harvester clones via ``git clone`` (see ``git_ops.clone_repository``),
    which only accepts real git sources. We keep fixtures as plain directories
    in source control for ease of inspection, then promote them to git repos
    on demand here.
    """

    def _make(fixture_name: str) -> Path:
        src = FIXTURES_ROOT / fixture_name
        if not src.is_dir():
            raise FileNotFoundError(f"Fixture not found: {src}")
        dst = tmp_path / fixture_name
        shutil.copytree(src, dst)
        subprocess.run(["git", "init", "-q"], cwd=dst, check=True)
        subprocess.run(["git", "add", "."], cwd=dst, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=fixture",
                "-c",
                "user.email=fixture@example.com",
                "commit",
                "-q",
                "-m",
                "fixture initial commit",
            ],
            cwd=dst,
            check=True,
        )
        return dst

    return _make
