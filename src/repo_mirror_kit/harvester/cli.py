"""Command-line interface for the Requirements Harvester."""

from __future__ import annotations

import json
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
    help="Resume from a previous incomplete run. Completed stages (A, B, C, "
    "C2) are rehydrated from <out>/state/ when their artifacts are intact "
    "and the config is unchanged; later stages re-run.",
)
@click.option(
    "--from-stage",
    type=click.Choice(["A", "B", "C", "C2", "C3", "D", "E", "F", "G"]),
    default=None,
    help="Re-run from this stage onward, reusing persisted earlier stages "
    "(implies --resume). E.g. --from-stage C2 re-runs LLM enrichment only.",
)
@click.option(
    "--fail-on-gaps/--no-fail-on-gaps",
    default=True,
    help="Fail with exit code 2 if coverage gaps are found.",
    show_default=True,
)
@click.option(
    "--fail-on-fidelity/--no-fail-on-fidelity",
    default=False,
    help="Fail with exit code 4 if fidelity (recreation-readiness) gates "
    "fail. See reports/coverage.md for the per-metric breakdown.",
    show_default=True,
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
    default="claude-sonnet-5-5",
    help="Claude model to use for LLM enrichment. When --llm-base-url points "
    "at a local endpoint (e.g. Ollama), a local model tag such as "
    "'qwen2.5-coder:32b' can be used instead.",
    show_default=True,
)
@click.option(
    "--llm-agentic/--no-llm-agentic",
    default=True,
    help="Let the model trace each surface through the repo with read-only "
    "read_file/grep/list_dir tools (default). --no-llm-agentic uses the "
    "single-shot snippet prompt.",
)
@click.option(
    "--llm-max-turns",
    default=8,
    type=int,
    show_default=True,
    help="Max tool-use turns per surface in agentic mode.",
)
@click.option(
    "--llm-budget-usd",
    default=5.0,
    type=float,
    show_default=True,
    help="Estimated-spend cap for enrichment. Remaining surfaces are skipped "
    "(and recorded as skipped_budget) once reached. Local endpoints cost $0.",
)
@click.option(
    "--llm-base-url",
    "llm_base_url",
    default=None,
    envvar="HARVESTER_LLM_BASE_URL",
    help="Optional base URL override for the Anthropic SDK, used to target "
    "a local Anthropic-API-compatible endpoint such as Ollama "
    "(http://localhost:11434). May also be set via HARVESTER_LLM_BASE_URL. "
    "When set, ANTHROPIC_API_KEY is not required.",
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
    from_stage: str | None,
    fail_on_gaps: bool,
    fail_on_fidelity: bool,
    log_level: str,
    llm_enabled: bool,
    llm_model: str,
    llm_agentic: bool,
    llm_max_turns: int,
    llm_budget_usd: float,
    llm_base_url: str | None,
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
            resume=resume or from_stage is not None,
            from_stage=from_stage,
            fail_on_gaps=fail_on_gaps,
            fail_on_fidelity=fail_on_fidelity,
            log_level=log_level,
            llm_enabled=llm_enabled,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            llm_agentic=llm_agentic,
            llm_max_turns=llm_max_turns,
            llm_budget_usd=llm_budget_usd,
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

    if not result.coverage_passed and fail_on_gaps:
        sys.exit(EXIT_GAPS_FOUND)

    if not result.fidelity_passed and fail_on_fidelity:
        sys.exit(EXIT_FIDELITY_FAILED)

    sys.exit(EXIT_SUCCESS)


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


@main.command()
@click.option(
    "--from",
    "from_dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Original harvest --out directory to rebuild from.",
)
@click.option(
    "--workspace",
    required=True,
    type=click.Path(path_type=Path),
    help="Fresh directory to rebuild into (must be outside --from).",
)
@click.option(
    "--lane",
    type=click.Choice(["cloud", "local"]),
    default="cloud",
    show_default=True,
    help="Rebuild lane: 'cloud' (Claude Code headless via claude -p) or "
    "'local' (forge-loop over the requirements; --model required).",
)
@click.option(
    "--model",
    default=None,
    help="Model passed to the rebuild lane (required for 'local': an Ollama "
    "tag registered in the forge model registry, e.g. gemma4:26b).",
)
@click.option(
    "--data-class",
    type=click.Choice(["public", "internal", "client-confidential"]),
    default="internal",
    show_default=True,
    help="Local lane only: forge-loop data class for the security gate.",
)
@click.option(
    "--allow",
    "allowed_commands",
    multiple=True,
    help="Local lane only: a verify command forge-loop may run (repeatable). "
    "Defaults to forge-loop's own whitelist when omitted.",
)
@click.option(
    "--permission-mode",
    default="acceptEdits",
    show_default=True,
    help="Cloud lane only: Claude Code permission mode for the headless run. "
    "Use 'bypassPermissions' to let the agent run tests/installs unattended.",
)
@click.option(
    "--timeout",
    default=3600,
    type=int,
    show_default=True,
    help="Seconds before the rebuild invocation is killed.",
)
@click.option(
    "--out",
    default=None,
    type=click.Path(path_type=Path),
    help="Directory for score reports + the rebuild's re-harvest "
    "(default: <workspace>-eval).",
)
@click.option(
    "--score/--no-score",
    "do_score",
    default=True,
    show_default=True,
    help="Re-harvest the rebuild and score it (tier-1 surface diff) "
    "against the original.",
)
@click.option(
    "--target-stack",
    default=None,
    help="Cloud lane: rebuild in this technology stack instead of the "
    "original's (e.g. 'Node.js with Express').",
)
@click.option(
    "--start-script/--no-start-script",
    default=False,
    help="Cloud lane: require a start.sh serving HTTP on $PORT so the rebuild "
    "can be behaviour-scored with `parity-score`.",
)
def rebuild(
    target_stack: str | None,
    start_script: bool,
    from_dir: Path,
    workspace: Path,
    lane: str,
    model: str | None,
    data_class: str,
    allowed_commands: tuple[str, ...],
    permission_mode: str,
    timeout: int,
    out: Path | None,
    do_score: bool,
) -> None:
    """Rebuild an app from harvest output, then score the rebuild.

    Assembles a workspace with ONLY the requirement artifacts (never the
    original source or the surfaces.json answer key), drives the rebuild
    agent, then re-harvests the result and diffs the two surface maps.
    """
    from repo_mirror_kit.harvester.rebuild.executor import (
        RebuildError,
        RebuildLane,
        run_rebuild,
    )

    eval_dir = out or workspace.parent / f"{workspace.name}-eval"

    try:
        rebuild_result = run_rebuild(
            harvest_dir=from_dir,
            workspace=workspace,
            lane=RebuildLane(lane),
            model=model,
            timeout=timeout,
            permission_mode=permission_mode,
            data_class=data_class,
            allowed_commands=allowed_commands or None,
            target_stack=target_stack,
            require_start_script=start_script,
        )
    except RebuildError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_INVALID_INPUT)

    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / "rebuild-result.json").write_text(
        json.dumps(rebuild_result.to_dict(), indent=2), encoding="utf-8"
    )

    click.echo(f"Rebuild lane: {rebuild_result.lane}")
    click.echo(f"Duration: {rebuild_result.duration_seconds:.1f}s")
    if rebuild_result.tokens_in is not None:
        click.echo(
            f"Tokens: {rebuild_result.tokens_in} in / {rebuild_result.tokens_out} out"
        )
    if rebuild_result.cost_usd is not None:
        click.echo(f"Cost: ${rebuild_result.cost_usd:.4f}")

    if not rebuild_result.success:
        click.echo(f"Rebuild failed: {rebuild_result.error}", err=True)
        sys.exit(EXIT_UNEXPECTED)
    click.echo(f"Rebuild written to: {rebuild_result.workspace}")

    if not do_score:
        sys.exit(EXIT_SUCCESS)

    from repo_mirror_kit.harvester.pipeline import HarvestPipeline
    from repo_mirror_kit.harvester.rebuild.scoring import (
        diff_harvest_dirs,
        write_score_reports,
    )

    rebuild_harvest = eval_dir / "rebuild-harvest"
    click.echo("Re-harvesting the rebuild for scoring...")
    harvest_result = HarvestPipeline().run(
        HarvestConfig(
            repo=str(rebuild_result.workspace),
            out=rebuild_harvest,
            llm_enabled=False,
            fail_on_gaps=False,
            log_level="warn",
        )
    )
    if not harvest_result.success:
        click.echo(
            f"Re-harvest failed at stage {harvest_result.error_stage}: "
            f"{harvest_result.error_message}",
            err=True,
        )
        sys.exit(EXIT_UNEXPECTED)

    report = diff_harvest_dirs(from_dir, rebuild_harvest)
    write_score_reports(eval_dir, report)
    click.echo("")
    click.echo("Tier-1 surface re-extraction diff:")
    click.echo(
        f"  Recall:    {_pct(report.overall_recall)} "
        f"({report.total_matched}/{report.total_original})"
    )
    click.echo(
        f"  Precision: {_pct(report.overall_precision)} "
        f"({report.total_matched}/{report.total_rebuilt})"
    )
    click.echo(f"  F1:        {_pct(report.overall_f1)}")
    click.echo(f"Score reports written to: {eval_dir}")
    sys.exit(EXIT_SUCCESS)


@main.command()
@click.option(
    "--original",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Original project's harvest --out directory.",
)
@click.option(
    "--rebuilt",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Rebuilt project's harvest --out directory.",
)
@click.option(
    "--out",
    default=None,
    type=click.Path(path_type=Path),
    help="Directory for score reports (default: the --rebuilt directory).",
)
def score(original: Path, rebuilt: Path, out: Path | None) -> None:
    """Score one harvest against another (tier-1 surface re-extraction diff).

    Both arguments are harvest --out directories containing surfaces.json.
    """
    from repo_mirror_kit.harvester.rebuild.scoring import (
        ScoringError,
        diff_harvest_dirs,
        write_score_reports,
    )

    try:
        report = diff_harvest_dirs(original, rebuilt)
    except ScoringError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_INVALID_INPUT)

    write_score_reports(out or rebuilt, report)
    click.echo("Tier-1 surface re-extraction diff:")
    click.echo(
        f"  Recall:    {_pct(report.overall_recall)} "
        f"({report.total_matched}/{report.total_original})"
    )
    click.echo(
        f"  Precision: {_pct(report.overall_precision)} "
        f"({report.total_matched}/{report.total_rebuilt})"
    )
    click.echo(f"  F1:        {_pct(report.overall_f1)}")
    sys.exit(EXIT_SUCCESS)


def _parse_kv(pairs: tuple[str, ...], sep: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in pairs:
        key, found, value = item.partition(sep)
        if not found or not key.strip():
            raise click.BadParameter(f"expected KEY{sep}VALUE, got {item!r}")
        out[key.strip()] = value.strip()
    return out


@main.command("parity-capture")
@click.option(
    "--app-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory of the app to record.",
)
@click.option(
    "--script",
    "script_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Request script (JSON).",
)
@click.option(
    "--out",
    "out_file",
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Golden file to write.",
)
@click.option(
    "--start-command",
    default="bash start.sh",
    show_default=True,
    help="Shell command that starts the app on $PORT.",
)
@click.option(
    "--env",
    "env_pairs",
    multiple=True,
    help="Environment variable KEY=VALUE for the app (repeatable).",
)
@click.option(
    "--auth-header",
    "auth_pairs",
    multiple=True,
    help="Header 'Name: value' added to requests marked auth:true (repeatable).",
)
@click.option("--captured-from", default="", help="Label recorded in the golden file.")
def parity_capture(
    app_dir: Path,
    script_path: Path,
    out_file: Path,
    start_command: str,
    env_pairs: tuple[str, ...],
    auth_pairs: tuple[str, ...],
    captured_from: str,
) -> None:
    """Record golden request/response pairs from a running app (BEAN-077)."""
    from repo_mirror_kit.harvester.parity.goldens import capture, load_script
    from repo_mirror_kit.harvester.parity.server import AppProcess, AppStartError

    script = load_script(script_path)
    try:
        with AppProcess(app_dir, start_command, _parse_kv(env_pairs, "=")) as app:
            golden = capture(
                app.base_url,
                script,
                _parse_kv(auth_pairs, ":"),
                captured_from or app_dir.name,
            )
    except AppStartError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_UNEXPECTED)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(golden, indent=2) + "\n", encoding="utf-8")
    click.echo(f"Recorded {len(golden['interactions'])} interactions -> {out_file}")


@main.command("parity-score")
@click.option(
    "--harvest-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Harvest output of the ORIGINAL app.",
)
@click.option(
    "--rebuild-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="The rebuilt app (must provide the start command).",
)
@click.option(
    "--out",
    "out_dir",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory for parity-report.{json,md}.",
)
@click.option(
    "--golden",
    "golden_file",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Golden file from parity-capture.",
)
@click.option(
    "--original-dir",
    default=None,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Original app directory (enables Gherkin calibration).",
)
@click.option("--original-start-command", default="bash start.sh", show_default=True)
@click.option(
    "--start-command",
    default="bash start.sh",
    show_default=True,
    help="Start command for the rebuild.",
)
@click.option(
    "--env",
    "env_pairs",
    multiple=True,
    help="Environment KEY=VALUE for both apps (repeatable).",
)
@click.option(
    "--auth-header",
    "auth_pairs",
    multiple=True,
    help="Header 'Name: value' for authenticated scenarios (repeatable).",
)
@click.option(
    "--rebuild-harvest",
    default=None,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Existing harvest of the rebuild (else it is harvested, LLM off).",
)
@click.option(
    "--rebuild-result",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="rebuild-result.json whose telemetry is embedded.",
)
@click.option(
    "--threshold",
    default=0.90,
    type=float,
    show_default=True,
    help="Overall parity required to pass.",
)
def parity_score(
    harvest_dir: Path,
    rebuild_dir: Path,
    out_dir: Path,
    golden_file: Path | None,
    original_dir: Path | None,
    original_start_command: str,
    start_command: str,
    env_pairs: tuple[str, ...],
    auth_pairs: tuple[str, ...],
    rebuild_harvest: Path | None,
    rebuild_result: Path | None,
    threshold: float,
) -> None:
    """Score a rebuild's behavioural parity against the original (BEAN-078)."""
    from repo_mirror_kit.harvester.parity.score import score_rebuild, write_report
    from repo_mirror_kit.harvester.parity.server import AppStartError
    from repo_mirror_kit.harvester.pipeline import HarvestPipeline

    golden = (
        json.loads(golden_file.read_text(encoding="utf-8")) if golden_file else None
    )
    telemetry = (
        json.loads(rebuild_result.read_text(encoding="utf-8"))
        if rebuild_result
        else None
    )
    if rebuild_harvest is None:
        rebuild_harvest = out_dir / "rebuild-harvest"
        click.echo("Harvesting the rebuild (LLM off) for the schema diff...")
        result = HarvestPipeline().run(
            HarvestConfig(
                repo=str(rebuild_dir),
                out=rebuild_harvest,
                llm_enabled=False,
                fail_on_gaps=False,
                log_level="warn",
            )
        )
        if not result.success:
            click.echo(
                f"Warning: re-harvest failed at stage {result.error_stage}; "
                "schema family will be scored as missing.",
                err=True,
            )
    try:
        report = score_rebuild(
            golden=golden,
            original_harvest=harvest_dir,
            rebuild_dir=rebuild_dir,
            rebuild_harvest=rebuild_harvest,
            auth_headers=_parse_kv(auth_pairs, ":"),
            env=_parse_kv(env_pairs, "="),
            start_command=start_command,
            original_dir=original_dir,
            original_start_command=original_start_command,
            telemetry=telemetry,
            threshold=threshold,
        )
    except AppStartError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_UNEXPECTED)
    _jpath, mpath = write_report(out_dir, report)
    overall = report.overall
    click.echo(
        f"Overall parity: {'N/A' if overall is None else f'{100 * overall:.1f}%'}"
    )
    for family, score in report.family_scores().items():
        click.echo(f"  {family}: {'N/A' if score is None else f'{100 * score:.1f}%'}")
    click.echo(f"Report: {mpath}")
    sys.exit(EXIT_SUCCESS if report.passed else EXIT_FIDELITY_FAILED)
