"""Tests for the harvest CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from repo_mirror_kit.harvester.cli import (
    EXIT_INVALID_INPUT,
    EXIT_SUCCESS,
    main,
)


class TestHarvestCommand:
    """Verify the harvest CLI command argument parsing and exit codes."""

    def test_harvest_with_repo_exits_success(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["harvest", "--repo", "https://example.com/r.git"])
        assert result.exit_code == EXIT_SUCCESS
        assert "Harvest configured for" in result.output

    def test_harvest_missing_repo_exits_invalid(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["harvest"])
        assert result.exit_code == EXIT_INVALID_INPUT

    def test_harvest_missing_repo_shows_error_message(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["harvest"])
        assert "repo" in result.output.lower()

    def test_harvest_all_arguments(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "harvest",
                "--repo",
                "https://example.com/r.git",
                "--ref",
                "main",
                "--out",
                "/tmp/output",
                "--include",
                "*.py,*.md",
                "--exclude",
                "*.log",
                "--max-file-bytes",
                "500000",
                "--resume",
                "--no-fail-on-gaps",
                "--log-level",
                "debug",
            ],
        )
        assert result.exit_code == EXIT_SUCCESS

    def test_harvest_ref_optional(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["harvest", "--repo", "https://example.com/r.git"])
        assert result.exit_code == EXIT_SUCCESS

    def test_harvest_invalid_log_level_exits_invalid(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "harvest",
                "--repo",
                "https://example.com/r.git",
                "--log-level",
                "verbose",
            ],
        )
        assert result.exit_code == EXIT_INVALID_INPUT

    def test_harvest_log_level_case_insensitive(self) -> None:
        runner = CliRunner()
        for level in ("DEBUG", "Info", "WARN", "Error"):
            result = runner.invoke(
                main,
                [
                    "harvest",
                    "--repo",
                    "https://example.com/r.git",
                    "--log-level",
                    level,
                ],
            )
            assert result.exit_code == EXIT_SUCCESS, f"Failed for log level: {level}"

    def test_harvest_include_comma_separated(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "harvest",
                "--repo",
                "https://example.com/r.git",
                "--include",
                "*.py, *.md, *.txt",
            ],
        )
        assert result.exit_code == EXIT_SUCCESS

    def test_harvest_exclude_comma_separated(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "harvest",
                "--repo",
                "https://example.com/r.git",
                "--exclude",
                "*.log, *.tmp",
            ],
        )
        assert result.exit_code == EXIT_SUCCESS

    def test_harvest_fail_on_gaps_default_true(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["harvest", "--repo", "https://example.com/r.git"],
        )
        assert result.exit_code == EXIT_SUCCESS

    def test_harvest_no_fail_on_gaps(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["harvest", "--repo", "https://example.com/r.git", "--no-fail-on-gaps"],
        )
        assert result.exit_code == EXIT_SUCCESS

    def test_harvest_resume_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["harvest", "--repo", "https://example.com/r.git", "--resume"],
        )
        assert result.exit_code == EXIT_SUCCESS

    def test_harvest_max_file_bytes_custom(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "harvest",
                "--repo",
                "https://example.com/r.git",
                "--max-file-bytes",
                "2000000",
            ],
        )
        assert result.exit_code == EXIT_SUCCESS

    def test_harvest_invalid_max_file_bytes_type(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "harvest",
                "--repo",
                "https://example.com/r.git",
                "--max-file-bytes",
                "abc",
            ],
        )
        assert result.exit_code == EXIT_INVALID_INPUT
