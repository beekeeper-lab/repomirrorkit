"""Command-line interface for the Requirements Harvester."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import click

from repo_mirror_kit.harvester.config import (
    DEFAULT_LLM_ENABLED,
    ConfigValidationError,
    HarvestConfig,
    merge_exclude_globs,
    parse_glob_patterns,
)

# Exit codes per spec
EXIT_SUCCESS: int = 0
EXIT_GAPS_FOUND: int = 2
EXIT_INVALID_INPUT: int = 3
EXIT_FIDELITY_FAILED: int = 4
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
    "--max-total-bytes",
    default=500 * 1024 * 1024,
    type=int,
    help="Maximum total on-disk size of the cloned repo (excluding .git). "
    "Cloning aborts and the partial clone is removed if exceeded.",
    show_default=True,
)
@click.option(
    "--resume",
    is_flag=True,
    default=False,
    help="Resume from a previous incomplete run. Skips the clone (Stage A) "
    "if the working copy already exists; analysis stages always re-run.",
)
@click.option(
    "--fail-on-gaps/--no-fail-on-gaps",
    default=True,
    help="Fail with exit code 2 if coverage gaps are found.",
    show_default=True,
)
@click.option(
    "--fail-on-fidelity/--no-fail-on-fidelity",
    default=None,
    help="Fail with exit code 4 if fidelity (recreation-readiness) gates "
    "fail. See reports/coverage.md for the per-metric breakdown. "
    "[default: off; on in --mirror mode]",
)
@click.option(
    "--log-level",
    default="info",
    help="Logging level: debug, info, warn, error (case-insensitive).",
    show_default=True,
)
@click.option(
    "--llm/--no-llm",
    "llm_enabled",
    default=DEFAULT_LLM_ENABLED,
    help="Enable LLM enrichment of surfaces using Claude (default ON). "
    "Reads the API key from ANTHROPIC_API_KEY (env var only). "
    "If --llm is on but the env var is missing, the harvester emits a "
    "warning and falls back to structural-only output. Use --no-llm to "
    "skip enrichment without warning.",
)
@click.option(
    "--llm-model",
    default="claude-sonnet-4-6",
    help="Claude model to use for LLM enrichment.",
    show_default=True,
)
@click.option(
    "--mirror",
    is_flag=True,
    default=False,
    help="Mirror mode (BEAN-080): emit a self-contained requirements "
    "package. Requires ANTHROPIC_API_KEY (fails fast without it), turns "
    "--fail-on-fidelity on by default, and removes the cloned source "
    "(repo/, including .git) after a fully successful run.",
)
@click.option(
    "--keep-source",
    is_flag=True,
    default=False,
    help="Keep the cloned working copy (repo/) after the run. Overrides "
    "the cleanup implied by --mirror or --cleanup.",
)
@click.option(
    "--cleanup",
    "cleanup_flag",
    is_flag=True,
    default=False,
    help="Remove the cloned source (repo/, including .git) after a fully "
    "successful run, without enabling full --mirror mode.",
)
def harvest(
    repo: str,
    ref: str | None,
    out: Path | None,
    include: str | None,
    exclude: str | None,
    max_file_bytes: int,
    max_total_bytes: int,
    resume: bool,
    fail_on_gaps: bool,
    fail_on_fidelity: bool | None,
    log_level: str,
    llm_enabled: bool,
    llm_model: str,
    mirror: bool,
    keep_source: bool,
    cleanup_flag: bool,
) -> None:
    """Run the requirements harvester against a repository."""
    # API key is sourced from the environment only — never accepted on
    # argv (would leak into shell history and ps output). If --llm is on
    # without ANTHROPIC_API_KEY, HarvestConfig downgrades to structural-only
    # output with a warning (BEAN-056).
    llm_api_key = os.environ.get("ANTHROPIC_API_KEY")
    try:
        config = HarvestConfig(
            repo=repo,
            ref=ref,
            out=out,
            include=parse_glob_patterns(include) if include else (),
            exclude=merge_exclude_globs(exclude),
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_total_bytes,
            resume=resume,
            fail_on_gaps=fail_on_gaps,
            fail_on_fidelity=fail_on_fidelity,
            log_level=log_level,
            llm_enabled=llm_enabled,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
            mirror=mirror,
            keep_source=keep_source,
            # None lets HarvestConfig resolve the mirror-mode default.
            cleanup=True if cleanup_flag else None,
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
    click.echo(f"Fidelity gates: {'PASSED' if result.fidelity_passed else 'FAILED'}")
    if result.cleanup_performed:
        click.echo("Source removed: repo/ (including .git) — see state.json")

    if not result.coverage_passed and config.fail_on_gaps:
        sys.exit(EXIT_GAPS_FOUND)

    # config.fail_on_fidelity is resolved (None → mirror) by HarvestConfig.
    if not result.fidelity_passed and config.fail_on_fidelity:
        sys.exit(EXIT_FIDELITY_FAILED)

    sys.exit(EXIT_SUCCESS)
