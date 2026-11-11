"""Tests for Stage H source cleanup (BEAN-080)."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_mirror_kit.harvester.cleanup import (
    CleanupError,
    remove_source,
)
from repo_mirror_kit.harvester.state import StateManager


def _make_state(output_dir: Path, *, stage_a_done: bool = True) -> StateManager:
    """Build a StateManager with Stage A optionally marked done."""
    state = StateManager(output_dir)
    state.initialize(["A", "B"])
    if stage_a_done:
        state.complete_stage("A")
    return state


def _make_clone(output_dir: Path) -> Path:
    """Create a plausible cloned working copy under <output_dir>/repo."""
    repo = output_dir / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("print('hello')\n")
    return repo


class TestRemoveSource:
    """Happy path and outcome recording."""

    def test_removes_repo_including_git(self, tmp_path: Path) -> None:
        repo = _make_clone(tmp_path)
        state = _make_state(tmp_path)

        result = remove_source(tmp_path, state)

        assert result.removed is True
        assert not repo.exists()
        assert result.files_removed == 2  # HEAD + app.py
        assert result.bytes_freed > 0

    def test_no_git_remains_anywhere(self, tmp_path: Path) -> None:
        _make_clone(tmp_path)
        state = _make_state(tmp_path)

        remove_source(tmp_path, state)

        assert list(tmp_path.rglob(".git")) == []

    def test_stray_gitlink_in_project_folder_is_removed(self, tmp_path: Path) -> None:
        # copytree can carry a submodule gitlink file into project-folder/
        # (e.g. .claude/shared/.git). Cleanup must remove it, not fail.
        _make_clone(tmp_path)
        stray_parent = tmp_path / "project-folder" / ".claude" / "shared"
        stray_parent.mkdir(parents=True)
        (stray_parent / ".git").write_text("gitdir: ../../../.git/modules/x\n")
        state = _make_state(tmp_path)

        result = remove_source(tmp_path, state)

        assert list(tmp_path.rglob(".git")) == []
        assert result.stray_git_removed == ["project-folder/.claude/shared/.git"]

    def test_missing_git_dir_proceeds_with_state_confirmation(
        self, tmp_path: Path
    ) -> None:
        # State confirms the clone but .git is absent — warn and proceed.
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "app.py").write_text("x = 1\n")
        state = _make_state(tmp_path)

        result = remove_source(tmp_path, state)

        assert result.removed is True
        assert not repo.exists()


class TestSafetyInvariants:
    """Every refusal path — cleanup must never delete the wrong thing."""

    def test_refuses_when_repo_missing(self, tmp_path: Path) -> None:
        state = _make_state(tmp_path)
        with pytest.raises(CleanupError, match="does not exist"):
            remove_source(tmp_path, state)

    def test_refuses_when_repo_is_a_file(self, tmp_path: Path) -> None:
        (tmp_path / "repo").write_text("not a directory\n")
        state = _make_state(tmp_path)
        with pytest.raises(CleanupError, match="not a directory"):
            remove_source(tmp_path, state)

    def test_refuses_symlinked_repo(self, tmp_path: Path) -> None:
        # A symlink at <out>/repo pointing elsewhere must never be followed.
        victim = tmp_path / "victim"
        (victim / ".git").mkdir(parents=True)
        output_dir = tmp_path / "out"
        output_dir.mkdir()
        (output_dir / "repo").symlink_to(victim)
        state = _make_state(output_dir)

        with pytest.raises(CleanupError, match="symlink"):
            remove_source(output_dir, state)
        assert victim.exists()

    def test_refuses_without_stage_a_in_state(self, tmp_path: Path) -> None:
        # Never delete a repo/ the harvester did not create.
        repo = _make_clone(tmp_path)
        state = _make_state(tmp_path, stage_a_done=False)

        with pytest.raises(CleanupError, match="Stage A"):
            remove_source(tmp_path, state)
        assert repo.exists()

    def test_refuses_with_empty_state(self, tmp_path: Path) -> None:
        repo = _make_clone(tmp_path)
        state = StateManager(tmp_path)  # nothing initialized/loaded

        with pytest.raises(CleanupError, match="Stage A"):
            remove_source(tmp_path, state)
        assert repo.exists()
