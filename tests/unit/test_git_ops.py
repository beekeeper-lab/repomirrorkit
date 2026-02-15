"""Unit tests for harvester git operations."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from repo_mirror_kit.harvester.git_ops import (
    CloneResult,
    GitCloneError,
    GitNotFoundError,
    GitRefError,
    _check_symlinks,
    _normalize_file,
    _normalize_line_endings,
    clone_repository,
)


class TestCheckGitAvailable:
    """Tests for git availability checking."""

    @patch("repo_mirror_kit.harvester.git_ops.shutil.which", return_value=None)
    def test_missing_git_raises_clear_error(self, mock_which: MagicMock) -> None:
        with pytest.raises(GitNotFoundError, match="git is not installed"):
            clone_repository("https://example.com/repo.git", None, Path("/tmp/test"))

    @patch(
        "repo_mirror_kit.harvester.git_ops.shutil.which", return_value="/usr/bin/git"
    )
    @patch("repo_mirror_kit.harvester.git_ops.subprocess.run")
    def test_git_available_proceeds(
        self,
        mock_run: MagicMock,
        mock_which: MagicMock,
        tmp_path: Path,
    ) -> None:
        workdir = tmp_path / "repo"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        # Create the workdir to simulate a successful clone
        workdir.mkdir()

        result = clone_repository("https://example.com/repo.git", None, workdir)
        assert isinstance(result, CloneResult)


class TestCloneRepository:
    """Tests for successful clone operations."""

    @patch(
        "repo_mirror_kit.harvester.git_ops.shutil.which", return_value="/usr/bin/git"
    )
    @patch("repo_mirror_kit.harvester.git_ops.subprocess.run")
    def test_successful_clone_returns_result(
        self,
        mock_run: MagicMock,
        mock_which: MagicMock,
        tmp_path: Path,
    ) -> None:
        workdir = tmp_path / "repo"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        workdir.mkdir()

        result = clone_repository("https://example.com/repo.git", None, workdir)

        assert result.repo_dir == workdir
        assert result.skipped_symlinks == []
        assert result.normalized_files == 0

    @patch(
        "repo_mirror_kit.harvester.git_ops.shutil.which", return_value="/usr/bin/git"
    )
    @patch("repo_mirror_kit.harvester.git_ops.subprocess.run")
    def test_clone_calls_git_with_correct_args(
        self,
        mock_run: MagicMock,
        mock_which: MagicMock,
        tmp_path: Path,
    ) -> None:
        workdir = tmp_path / "repo"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        workdir.mkdir()

        clone_repository("https://example.com/repo.git", None, workdir)

        clone_call = mock_run.call_args_list[0]
        cmd = clone_call[0][0]
        assert cmd == [
            "git",
            "clone",
            "--progress",
            "https://example.com/repo.git",
            str(workdir),
        ]

    @patch(
        "repo_mirror_kit.harvester.git_ops.shutil.which", return_value="/usr/bin/git"
    )
    @patch("repo_mirror_kit.harvester.git_ops.subprocess.run")
    def test_clone_failure_raises_clone_error(
        self,
        mock_run: MagicMock,
        mock_which: MagicMock,
        tmp_path: Path,
    ) -> None:
        workdir = tmp_path / "repo"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=128,
            stdout="",
            stderr="fatal: repository not found",
        )

        with pytest.raises(GitCloneError, match="git clone failed"):
            clone_repository("https://example.com/bad.git", None, workdir)

    @patch(
        "repo_mirror_kit.harvester.git_ops.shutil.which", return_value="/usr/bin/git"
    )
    @patch(
        "repo_mirror_kit.harvester.git_ops.subprocess.run",
        side_effect=FileNotFoundError("No such file"),
    )
    def test_clone_file_not_found_raises_git_not_found(
        self,
        mock_run: MagicMock,
        mock_which: MagicMock,
        tmp_path: Path,
    ) -> None:
        workdir = tmp_path / "repo"

        with pytest.raises(GitNotFoundError, match="git is not installed"):
            clone_repository("https://example.com/repo.git", None, workdir)


class TestRefCheckout:
    """Tests for ref checkout after clone."""

    @patch(
        "repo_mirror_kit.harvester.git_ops.shutil.which", return_value="/usr/bin/git"
    )
    @patch("repo_mirror_kit.harvester.git_ops.subprocess.run")
    def test_ref_checkout_called_when_ref_provided(
        self,
        mock_run: MagicMock,
        mock_which: MagicMock,
        tmp_path: Path,
    ) -> None:
        workdir = tmp_path / "repo"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        workdir.mkdir()

        clone_repository("https://example.com/repo.git", "v1.0.0", workdir)

        # First call is clone, second call is checkout
        assert mock_run.call_count == 2
        checkout_call = mock_run.call_args_list[1]
        cmd = checkout_call[0][0]
        assert cmd == ["git", "checkout", "v1.0.0"]
        assert checkout_call[1]["cwd"] == str(workdir)

    @patch(
        "repo_mirror_kit.harvester.git_ops.shutil.which", return_value="/usr/bin/git"
    )
    @patch("repo_mirror_kit.harvester.git_ops.subprocess.run")
    def test_no_checkout_when_ref_is_none(
        self,
        mock_run: MagicMock,
        mock_which: MagicMock,
        tmp_path: Path,
    ) -> None:
        workdir = tmp_path / "repo"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        workdir.mkdir()

        clone_repository("https://example.com/repo.git", None, workdir)

        # Only clone, no checkout
        assert mock_run.call_count == 1

    @patch(
        "repo_mirror_kit.harvester.git_ops.shutil.which", return_value="/usr/bin/git"
    )
    @patch("repo_mirror_kit.harvester.git_ops.subprocess.run")
    def test_invalid_ref_raises_ref_error(
        self,
        mock_run: MagicMock,
        mock_which: MagicMock,
        tmp_path: Path,
    ) -> None:
        workdir = tmp_path / "repo"

        def side_effect(
            *args: object, **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            cmd = args[0]
            if isinstance(cmd, list) and "checkout" in cmd:
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=1,
                    stdout="",
                    stderr="error: pathspec 'nonexistent' did not match",
                )
            return subprocess.CompletedProcess(
                args=cmd if isinstance(cmd, list) else [],
                returncode=0,
                stdout="",
                stderr="",
            )

        mock_run.side_effect = side_effect
        workdir.mkdir()

        with pytest.raises(GitRefError, match="Failed to checkout ref 'nonexistent'"):
            clone_repository("https://example.com/repo.git", "nonexistent", workdir)

    @patch(
        "repo_mirror_kit.harvester.git_ops.shutil.which", return_value="/usr/bin/git"
    )
    @patch("repo_mirror_kit.harvester.git_ops.subprocess.run")
    def test_invalid_ref_error_includes_stderr(
        self,
        mock_run: MagicMock,
        mock_which: MagicMock,
        tmp_path: Path,
    ) -> None:
        workdir = tmp_path / "repo"

        def side_effect(
            *args: object, **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            cmd = args[0]
            if isinstance(cmd, list) and "checkout" in cmd:
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=1,
                    stdout="",
                    stderr="error: pathspec 'bad-ref' did not match any files",
                )
            return subprocess.CompletedProcess(
                args=cmd if isinstance(cmd, list) else [],
                returncode=0,
                stdout="",
                stderr="",
            )

        mock_run.side_effect = side_effect
        workdir.mkdir()

        with pytest.raises(GitRefError, match="did not match"):
            clone_repository("https://example.com/repo.git", "bad-ref", workdir)


class TestSymlinkSafety:
    """Tests for symlink boundary checking."""

    def test_symlink_inside_repo_is_safe(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        target = repo / "real_file.txt"
        target.write_text("content", encoding="utf-8")
        link = repo / "link.txt"
        link.symlink_to(target)

        skipped = _check_symlinks(repo)
        assert skipped == []

    def test_symlink_outside_repo_is_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("external", encoding="utf-8")
        link = repo / "bad_link.txt"
        link.symlink_to(outside_file)

        skipped = _check_symlinks(repo)
        assert "bad_link.txt" in skipped

    def test_symlink_dir_outside_repo_is_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        outside_dir = tmp_path / "outside_dir"
        outside_dir.mkdir()
        link = repo / "bad_dir_link"
        link.symlink_to(outside_dir)

        skipped = _check_symlinks(repo)
        assert "bad_dir_link" in skipped

    def test_no_symlinks_returns_empty(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "file.txt").write_text("content", encoding="utf-8")

        skipped = _check_symlinks(repo)
        assert skipped == []

    def test_git_directory_symlinks_ignored(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        git_dir = repo / ".git" / "refs"
        git_dir.mkdir(parents=True)
        # Create a symlink inside .git (should be ignored)
        outside = tmp_path / "outside.txt"
        outside.write_text("x", encoding="utf-8")
        link = git_dir / "link.txt"
        link.symlink_to(outside)

        skipped = _check_symlinks(repo)
        assert skipped == []


class TestLineEndingNormalization:
    """Tests for CRLF to LF normalization."""

    def test_crlf_normalized_to_lf(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        f = repo / "file.txt"
        f.write_bytes(b"line1\r\nline2\r\nline3\r\n")

        count = _normalize_line_endings(repo)

        assert count == 1
        assert f.read_bytes() == b"line1\nline2\nline3\n"

    def test_lf_only_not_modified(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        f = repo / "file.txt"
        f.write_bytes(b"line1\nline2\n")

        count = _normalize_line_endings(repo)
        assert count == 0

    def test_binary_files_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        f = repo / "binary.dat"
        content = b"\x00\x01\x02\r\n\x03"
        f.write_bytes(content)

        count = _normalize_line_endings(repo)

        assert count == 0
        assert f.read_bytes() == content

    def test_git_directory_skipped(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        git_dir = repo / ".git" / "objects"
        git_dir.mkdir(parents=True)
        f = git_dir / "file.txt"
        f.write_bytes(b"line1\r\nline2\r\n")

        count = _normalize_line_endings(repo)
        assert count == 0

    def test_symlinks_skipped_during_normalization(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        target = repo / "real.txt"
        target.write_bytes(b"line1\r\nline2\r\n")
        link = repo / "link.txt"
        link.symlink_to(target)

        count = _normalize_line_endings(repo)

        # Only the real file should be normalized, not the symlink
        assert count == 1

    def test_normalize_file_returns_true_when_modified(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_bytes(b"hello\r\nworld\r\n")

        assert _normalize_file(f) is True
        assert f.read_bytes() == b"hello\nworld\n"

    def test_normalize_file_returns_false_when_no_crlf(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_bytes(b"hello\nworld\n")

        assert _normalize_file(f) is False

    def test_multiple_files_normalized(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "a.txt").write_bytes(b"a\r\n")
        (repo / "b.txt").write_bytes(b"b\r\n")
        (repo / "c.txt").write_bytes(b"c\n")  # No CRLF

        count = _normalize_line_endings(repo)
        assert count == 2


class TestCloneResultDataclass:
    """Tests for the CloneResult dataclass."""

    def test_clone_result_fields(self, tmp_path: Path) -> None:
        result = CloneResult(
            repo_dir=tmp_path,
            skipped_symlinks=["link1", "link2"],
            normalized_files=5,
        )
        assert result.repo_dir == tmp_path
        assert result.skipped_symlinks == ["link1", "link2"]
        assert result.normalized_files == 5


class TestIntegrationWithState:
    """Tests verifying state checkpoint integration."""

    @patch(
        "repo_mirror_kit.harvester.git_ops.shutil.which", return_value="/usr/bin/git"
    )
    @patch("repo_mirror_kit.harvester.git_ops.subprocess.run")
    def test_stage_a_checkpoint_written(
        self,
        mock_run: MagicMock,
        mock_which: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Verify that StateManager can checkpoint after clone_repository."""
        from repo_mirror_kit.harvester.state import StateManager

        workdir = tmp_path / "repo"
        output_dir = tmp_path / "output"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        workdir.mkdir()

        # Run clone
        result = clone_repository("https://example.com/repo.git", None, workdir)
        assert result.repo_dir == workdir

        # Write checkpoint via StateManager
        mgr = StateManager(output_dir)
        mgr.initialize(["A", "B", "C"])
        mgr.complete_stage("A")

        assert mgr.is_stage_done("A")
        assert not mgr.is_stage_done("B")

    @patch(
        "repo_mirror_kit.harvester.git_ops.shutil.which", return_value="/usr/bin/git"
    )
    @patch("repo_mirror_kit.harvester.git_ops.subprocess.run")
    def test_clone_and_ref_checkout_with_state(
        self,
        mock_run: MagicMock,
        mock_which: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Verify clone + ref checkout works end-to-end with state tracking."""
        from repo_mirror_kit.harvester.state import StateManager

        workdir = tmp_path / "repo"
        output_dir = tmp_path / "output"
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        workdir.mkdir()

        result = clone_repository(
            "https://example.com/repo.git", "feature-branch", workdir
        )
        assert result.repo_dir == workdir

        # Verify checkout was called
        assert mock_run.call_count == 2

        # Checkpoint
        mgr = StateManager(output_dir)
        mgr.initialize(["A"])
        mgr.complete_stage("A")
        assert mgr.is_stage_done("A")
