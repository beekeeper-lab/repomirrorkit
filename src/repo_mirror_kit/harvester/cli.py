"""Command-line interface for the Requirements Harvester."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import click

from repo_mirror_kit.harvester.config import (
    ConfigValidationError,
    HarvestConfig,
    merge_exclude_globs,
    parse_glob_patterns,
)

# Exit codes per spec
EXIT_SUCCESS: int = 0
EXIT_GAPS_FOUND: int = 2
EXIT_INVALID_INPUT: int = 3
EXIT_UNEXPECTED: int = 5


class HarvesterGroup(click.Group):
    """Custom Click group that uses spec exit codes for usage errors."""

    def main(
        self,
        args: Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        **extra: Any,
    ) -> Any:
        """Override main to map Click usage errors to exit code 3."""
        try:
            return super().main(
                args,
                prog_name=prog_name,
                complete_var=complete_var,
                standalone_mode=False,
                **extra,
            )
        except click.UsageError as exc:
            click.echo(f"Error: {exc.format_message()}", err=True)
            click.echo(f"Try '{self.name} harvest --help' for help.", err=True)
            sys.exit(EXIT_INVALID_INPUT)
        except SystemExit:
            raise
        except Exception as exc:
            click.echo(f"Unexpected error: {exc}", err=True)
            sys.exit(EXIT_UNEXPECTED)


@click.group(cls=HarvesterGroup, name="requirements-harvester")
def main() -> None:
    """Requirements Harvester — analyze repositories for requirements coverage."""


@main.command()
@click.option(
    "--repo",
    required=True,
    help="Repository URL to clone and analyze.",
)
@click.option(
    "--ref",
    default=None,
    help="Git ref (branch, tag, or commit SHA) to check out.",
)
@click.option(
    "--out",
    default=None,
    type=click.Path(path_type=Path),
    help="Output directory for reports and artifacts.",
)
@click.option(
    "--include",
    default=None,
    help="Comma-separated glob patterns to include.",
)
@click.option(
    "--exclude",
    default=None,
    help="Comma-separated glob patterns to add to default excludes.",
)
@click.option(
    "--max-file-bytes",
    default=1_000_000,
    type=int,
    help="Maximum file size to process in bytes.",
    show_default=True,
)
@click.option(
    "--resume",
    is_flag=True,
    default=False,
    help="Resume from a previous incomplete run.",
)
@click.option(
    "--fail-on-gaps/--no-fail-on-gaps",
    default=True,
    help="Fail with exit code 2 if coverage gaps are found.",
    show_default=True,
)
@click.option(
    "--log-level",
    default="info",
    help="Logging level: debug, info, warn, error (case-insensitive).",
    show_default=True,
)
def harvest(
    repo: str,
    ref: str | None,
    out: Path | None,
    include: str | None,
    exclude: str | None,
    max_file_bytes: int,
    resume: bool,
    fail_on_gaps: bool,
    log_level: str,
) -> None:
    """Run the requirements harvester against a repository."""
    try:
        config = HarvestConfig(
            repo=repo,
            ref=ref,
            out=out,
            include=parse_glob_patterns(include) if include else (),
            exclude=merge_exclude_globs(exclude),
            max_file_bytes=max_file_bytes,
            resume=resume,
            fail_on_gaps=fail_on_gaps,
            log_level=log_level,
        )
    except ConfigValidationError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_INVALID_INPUT)

    from repo_mirror_kit.harvester.pipeline import HarvestPipeline

    pipeline = HarvestPipeline()
    result = pipeline.run(config)

    if not result.success:
        click.echo(
            f"Pipeline failed at stage {result.error_stage}: {result.error_message}",
            err=True,
        )
        sys.exit(EXIT_UNEXPECTED)

    click.echo(f"Beans generated: {result.bean_count}")
    click.echo(f"Gaps found: {result.gap_count}")
    click.echo(f"Coverage gates: {'PASSED' if result.coverage_passed else 'FAILED'}")

    if not result.coverage_passed and fail_on_gaps:
        sys.exit(EXIT_GAPS_FOUND)

    sys.exit(EXIT_SUCCESS)
