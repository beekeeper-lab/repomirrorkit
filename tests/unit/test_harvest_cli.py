"""Tests for the harvest CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from repo_mirror_kit.harvester.cli import (
    EXIT_GAPS_FOUND,
    EXIT_INVALID_INPUT,
    EXIT_SUCCESS,
    EXIT_UNEXPECTED,
    main,
)
from repo_mirror_kit.harvester.pipeline import HarvestResult


def _make_success_result(tmp_path: Path | None = None) -> HarvestResult:
    """Build a successful HarvestResult."""
    return HarvestResult(
        success=True,
        coverage_passed=True,
        bean_count=5,
        gap_count=0,
        output_dir=tmp_path or Path("/tmp/out"),
    )


def _make_gaps_result(tmp_path: Path | None = None) -> HarvestResult:
    """Build a result with coverage gaps."""
    return HarvestResult(
        success=True,
        coverage_passed=False,
        bean_count=5,
        gap_count=3,
        output_dir=tmp_path or Path("/tmp/out"),
    )


def _make_failure_result() -> HarvestResult:
    """Build a failure result."""
    return HarvestResult(
        success=False,
        coverage_passed=False,
        bean_count=0,
        gap_count=0,
        error_stage="A",
        error_message="clone failed",
    )


_PIPELINE_RUN = "repo_mirror_kit.harvester.pipeline.HarvestPipeline"


class TestHarvestCommand:
    """Verify the harvest CLI command argument parsing and exit codes."""

    def test_harvest_missing_repo_exits_invalid(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["harvest"])
        assert result.exit_code == EXIT_INVALID_INPUT

    def test_harvest_missing_repo_shows_error_message(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["harvest"])
        assert "repo" in result.output.lower()

    def test_harvest_with_repo_runs_pipeline(self) -> None:
        runner = CliRunner()
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.run.return_value = _make_success_result()

        with patch(_PIPELINE_RUN, mock_pipeline):
            result = runner.invoke(
                main, ["harvest", "--repo", "https://example.com/r.git"]
            )
        assert result.exit_code == EXIT_SUCCESS
        assert "Beans generated: 5" in result.output

    def test_harvest_pipeline_failure_exits_unexpected(self) -> None:
        runner = CliRunner()
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.run.return_value = _make_failure_result()

        with patch(_PIPELINE_RUN, mock_pipeline):
            result = runner.invoke(
                main, ["harvest", "--repo", "https://example.com/r.git"]
            )
        assert result.exit_code == EXIT_UNEXPECTED
        assert "clone failed" in result.output

    def test_harvest_gaps_with_fail_on_gaps_exits_2(self) -> None:
        runner = CliRunner()
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.run.return_value = _make_gaps_result()

        with patch(_PIPELINE_RUN, mock_pipeline):
            result = runner.invoke(
                main, ["harvest", "--repo", "https://example.com/r.git"]
            )
        assert result.exit_code == EXIT_GAPS_FOUND
        assert "FAILED" in result.output

    def test_harvest_gaps_without_fail_on_gaps_exits_success(self) -> None:
        runner = CliRunner()
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.run.return_value = _make_gaps_result()

        with patch(_PIPELINE_RUN, mock_pipeline):
            result = runner.invoke(
                main,
                [
                    "harvest",
                    "--repo",
                    "https://example.com/r.git",
                    "--no-fail-on-gaps",
                ],
            )
        assert result.exit_code == EXIT_SUCCESS

    def test_harvest_all_arguments(self) -> None:
        runner = CliRunner()
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.run.return_value = _make_success_result()

        with patch(_PIPELINE_RUN, mock_pipeline):
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
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.run.return_value = _make_success_result()

        for level in ("DEBUG", "Info", "WARN", "Error"):
            with patch(_PIPELINE_RUN, mock_pipeline):
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

    def test_harvest_resume_flag(self) -> None:
        runner = CliRunner()
        mock_pipeline = MagicMock()
        mock_pipeline.return_value.run.return_value = _make_success_result()

        with patch(_PIPELINE_RUN, mock_pipeline):
            result = runner.invoke(
                main,
                ["harvest", "--repo", "https://example.com/r.git", "--resume"],
            )
        assert result.exit_code == EXIT_SUCCESS

        # Verify resume=True was passed to config
        call_args = mock_pipeline.return_value.run.call_args
        config = call_args[0][0]
        assert config.resume is True

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
