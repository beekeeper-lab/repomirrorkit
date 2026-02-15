from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from repo_mirror_kit.services.clone_service import (
    CloneResult,
    check_git_available,
    clone_repository,
    validate_git_url,
    validate_project_name,
)


class TestValidateProjectName:
    """Tests for project name validation."""

    def test_empty_name_returns_error(self) -> None:
        assert validate_project_name("") is not None

    def test_whitespace_only_returns_error(self) -> None:
        assert validate_project_name("   ") is not None

    def test_valid_name_returns_none(self) -> None:
        assert validate_project_name("my-project") is None

    def test_name_with_slash_returns_error(self) -> None:
        assert validate_project_name("my/project") is not None

    def test_name_with_backslash_returns_error(self) -> None:
        assert validate_project_name("my\\project") is not None

    def test_name_with_colon_returns_error(self) -> None:
        assert validate_project_name("my:project") is not None

    def test_name_with_asterisk_returns_error(self) -> None:
        assert validate_project_name("my*project") is not None

    def test_name_with_question_mark_returns_error(self) -> None:
        assert validate_project_name("my?project") is not None

    def test_name_with_quotes_returns_error(self) -> None:
        assert validate_project_name('my"project') is not None

    def test_name_with_angle_brackets_returns_error(self) -> None:
        assert validate_project_name("my<project>") is not None

    def test_name_with_pipe_returns_error(self) -> None:
        assert validate_project_name("my|project") is not None

    def test_dot_returns_error(self) -> None:
        assert validate_project_name(".") is not None

    def test_double_dot_returns_error(self) -> None:
        assert validate_project_name("..") is not None

    def test_name_with_spaces_is_valid(self) -> None:
        assert validate_project_name("my project") is None

    def test_name_with_dashes_is_valid(self) -> None:
        assert validate_project_name("my-cool-project") is None

    def test_name_with_underscores_is_valid(self) -> None:
        assert validate_project_name("my_project") is None


class TestValidateGitUrl:
    """Tests for git URL validation."""

    def test_empty_url_returns_error(self) -> None:
        assert validate_git_url("") is not None

    def test_whitespace_only_returns_error(self) -> None:
        assert validate_git_url("   ") is not None

    def test_valid_https_url_returns_none(self) -> None:
        assert validate_git_url("https://github.com/user/repo.git") is None

    def test_valid_ssh_url_returns_none(self) -> None:
        assert validate_git_url("git@github.com:user/repo.git") is None

    def test_url_with_spaces_returns_error(self) -> None:
        assert validate_git_url("https://github.com/user/ repo.git") is not None

    def test_gitlab_url_returns_none(self) -> None:
        assert validate_git_url("https://gitlab.com/user/repo.git") is None


class TestCheckGitAvailable:
    """Tests for git availability check."""

    @patch("repo_mirror_kit.services.clone_service.shutil.which")
    def test_git_available_returns_true(self, mock_which: MagicMock) -> None:
        mock_which.return_value = "/usr/bin/git"
        assert check_git_available() is True

    @patch("repo_mirror_kit.services.clone_service.shutil.which")
    def test_git_not_available_returns_false(self, mock_which: MagicMock) -> None:
        mock_which.return_value = None
        assert check_git_available() is False


class TestCloneRepository:
    """Tests for the clone_repository generator."""

    def test_existing_directory_returns_failure(self, tmp_path: Path) -> None:
        target = tmp_path / "projects" / "existing"
        target.mkdir(parents=True)
        gen = clone_repository(
            "https://example.com/repo.git",
            "existing",
            base_dir=tmp_path / "projects",
        )
        try:
            next(gen)
            raise AssertionError("Expected StopIteration")
        except StopIteration as exc:
            result: CloneResult = exc.value
            assert result.success is False
            assert "already exists" in result.message

    def test_creates_base_dir_if_missing(self, tmp_path: Path) -> None:
        base_dir = tmp_path / "new_projects"
        assert not base_dir.exists()
        gen = clone_repository(
            "https://example.com/repo.git",
            "test-project",
            base_dir=base_dir,
        )
        # The generator will create the base_dir and then try to run git clone
        # which will fail, but the directory should exist
        try:
            while True:
                next(gen)
        except StopIteration as exc:
            result: CloneResult = exc.value
            assert base_dir.exists()
            # The clone itself will fail since the URL is fake, but the dir was created
            assert isinstance(result, CloneResult)

    @patch("repo_mirror_kit.services.clone_service.subprocess.Popen")
    def test_successful_clone(self, mock_popen: MagicMock, tmp_path: Path) -> None:
        mock_process = MagicMock()
        mock_process.stderr = iter(["Cloning into 'test'...\n", "done.\n"])
        mock_process.returncode = 0
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        base_dir = tmp_path / "projects"
        gen = clone_repository(
            "https://example.com/repo.git",
            "test-project",
            base_dir=base_dir,
        )

        lines: list[str] = []
        try:
            while True:
                lines.append(next(gen))
        except StopIteration as exc:
            result: CloneResult = exc.value

        assert len(lines) == 2
        assert result.success is True
        assert result.message == "Clone complete"

    @patch("repo_mirror_kit.services.clone_service.subprocess.Popen")
    def test_failed_clone(self, mock_popen: MagicMock, tmp_path: Path) -> None:
        mock_process = MagicMock()
        mock_process.stderr = iter(["fatal: repository not found\n"])
        mock_process.returncode = 128
        mock_process.wait.return_value = 128
        mock_popen.return_value = mock_process

        base_dir = tmp_path / "projects"
        gen = clone_repository(
            "https://example.com/repo.git",
            "test-project",
            base_dir=base_dir,
        )

        lines: list[str] = []
        try:
            while True:
                lines.append(next(gen))
        except StopIteration as exc:
            result: CloneResult = exc.value

        assert result.success is False
        assert "exit code 128" in result.message
