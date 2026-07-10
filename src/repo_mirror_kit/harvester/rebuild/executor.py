"""Rebuild executor: drive an agentic rebuild from harvest output (WP-3.4).

Takes a harvest ``--out`` directory, assembles a clean rebuild workspace that
contains ONLY the requirement artifacts, and drives a rebuild agent over them.
Records run telemetry (wall time, tokens, cost, turns), then ``git init``s the
result so :mod:`.scoring` can re-harvest and diff it.

**Isolation is the whole point.** A rebuild eval only measures fidelity if the
agent never sees the original source or the extraction it is being scored
against. The workspace is assembled by *allowlist* — only requirement
artifacts are copied — and a post-condition check refuses to proceed if the
original ``repo/`` or the ``surfaces.json`` answer key leaked in.

Cloud lane: Claude Code headless (``claude -p``). Local lane (forge-loop,
IMP-03) is stubbed pending WP-3.5; the seam is here so it can drop in.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

# Requirement artifacts copied from the harvest output into the rebuild
# workspace. Allowlist, not denylist: anything not named here (notably the
# original source clone `repo/`, `surfaces.json`, `reports/`, `traceability/`)
# is never handed to the rebuild agent.
REBUILD_INPUT_DIRS: tuple[str, ...] = ("project-folder", "beans")
REBUILD_INPUT_FILES: tuple[str, ...] = (
    "REQUIREMENTS.md",
    "RUNBOOK.md",
    ".env.example",
)
REBUILD_INPUT_GLOBS: tuple[str, ...] = ("openapi.*",)

# Artifacts that MUST NOT reach the rebuild workspace — their presence means
# the eval is contaminated (the agent could copy the answer instead of
# rebuilding from requirements).
FORBIDDEN_IN_WORKSPACE: tuple[str, ...] = ("repo", "surfaces.json")

DEFAULT_TIMEOUT_SECONDS = 3600


class RebuildLane(StrEnum):
    """Which harness performs the rebuild."""

    CLOUD = "cloud"  # Claude Code headless (`claude -p`)
    LOCAL = "local"  # forge-loop over the beans (IMP-03) — WP-3.5


class RebuildError(Exception):
    """Raised when workspace assembly or the rebuild invocation fails."""


@dataclass(frozen=True)
class RebuildResult:
    """Outcome + telemetry of one rebuild run."""

    lane: str
    model: str | None
    workspace: Path
    success: bool
    duration_seconds: float
    exit_code: int | None = None
    intervention_count: int = 0  # human interventions; 0 for a clean headless run
    turns: int | None = None  # agent's internal turns, when reported
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    copied_inputs: tuple[str, ...] = ()
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "model": self.model,
            "workspace": str(self.workspace),
            "success": self.success,
            "duration_seconds": round(self.duration_seconds, 2),
            "exit_code": self.exit_code,
            "intervention_count": self.intervention_count,
            "turns": self.turns,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": self.cost_usd,
            "copied_inputs": list(self.copied_inputs),
            "error": self.error,
        }


# A runner takes (argv, cwd, timeout) and returns a CompletedProcess. Injectable
# so the orchestration is testable without spawning a real agent.
Runner = Callable[[list[str], Path, int], "subprocess.CompletedProcess[str]"]


def _default_runner(
    argv: list[str], cwd: Path, timeout: int
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def prepare_rebuild_workspace(harvest_dir: Path, workspace: Path) -> list[str]:
    """Copy requirement artifacts from ``harvest_dir`` into a fresh ``workspace``.

    Returns the names of the copied items. Raises :class:`RebuildError` if a
    forbidden artifact (original source, answer key) would end up in the
    workspace, or if no requirement artifacts were found.
    """
    harvest_dir = harvest_dir.resolve()
    workspace = workspace.resolve()
    if not harvest_dir.is_dir():
        raise RebuildError(f"harvest directory not found: {harvest_dir}")
    if workspace == harvest_dir or harvest_dir in workspace.parents:
        raise RebuildError("workspace must be outside the harvest directory")

    workspace.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for name in REBUILD_INPUT_DIRS:
        src = harvest_dir / name
        if src.is_dir():
            shutil.copytree(src, workspace / name, dirs_exist_ok=True)
            copied.append(name)
    for name in REBUILD_INPUT_FILES:
        src = harvest_dir / name
        if src.is_file():
            shutil.copy2(src, workspace / name)
            copied.append(name)
    for pattern in REBUILD_INPUT_GLOBS:
        for src in sorted(harvest_dir.glob(pattern)):
            if src.is_file():
                shutil.copy2(src, workspace / src.name)
                copied.append(src.name)

    if not copied:
        raise RebuildError(
            f"no requirement artifacts found in {harvest_dir}; "
            "was this a completed harvest --out directory?"
        )

    # Post-condition: the eval is only valid if the answer key never leaked in.
    for forbidden in FORBIDDEN_IN_WORKSPACE:
        if (workspace / forbidden).exists():
            raise RebuildError(
                f"forbidden artifact '{forbidden}' present in rebuild workspace "
                "— the rebuild would be contaminated by the original/answer key"
            )
    return copied


def build_rebuild_prompt(workspace: Path, copied_inputs: list[str]) -> str:
    """Compose the standard rebuild instruction handed to the agent."""
    have_reqs = "REQUIREMENTS.md" in copied_inputs
    have_beans = "beans" in copied_inputs
    have_runbook = "RUNBOOK.md" in copied_inputs
    inputs_desc = []
    if have_reqs:
        inputs_desc.append("`REQUIREMENTS.md` (the requirements narrative)")
    if have_beans:
        inputs_desc.append("`beans/` (per-surface requirement files)")
    if any(i.startswith("openapi") for i in copied_inputs):
        inputs_desc.append("`openapi.*` (API contract)")
    if have_runbook:
        inputs_desc.append("`RUNBOOK.md` (how the app is run)")
    inputs_line = "; ".join(inputs_desc) if inputs_desc else "the files in this directory"

    return (
        "You are rebuilding an application from its extracted requirements. "
        "This working directory contains ONLY requirement artifacts — there is "
        "no original source to copy from, by design.\n\n"
        f"Available inputs: {inputs_line}. The `project-folder/` directory holds "
        "a Claude Code project scaffold (CLAUDE.md, conventions, agents) derived "
        "from the original.\n\n"
        "Build a working implementation that satisfies these requirements: "
        "reproduce the routes, API endpoints, data models, auth surfaces, and "
        "behaviour described. You may choose an idiomatic project layout and "
        "framework consistent with the stack conventions. Write real, runnable "
        "code and tests. Do not stop until the app is buildable and its tests "
        "pass. Commit nothing — leave the tree as files on disk."
    )


def _parse_claude_json(stdout: str) -> dict[str, Any]:
    """Best-effort parse of ``claude -p --output-format json`` output.

    The CLI emits a single JSON result object. Returns extracted telemetry
    keys; missing fields come back as None.
    """
    telemetry: dict[str, Any] = {
        "turns": None,
        "tokens_in": None,
        "tokens_out": None,
        "cost_usd": None,
    }
    stripped = stdout.strip()
    if not stripped:
        return telemetry
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return telemetry
    if not isinstance(data, dict):
        return telemetry
    telemetry["cost_usd"] = data.get("total_cost_usd")
    telemetry["turns"] = data.get("num_turns")
    usage = data.get("usage")
    if isinstance(usage, dict):
        telemetry["tokens_in"] = usage.get("input_tokens")
        telemetry["tokens_out"] = usage.get("output_tokens")
    return telemetry


def _git_init_commit(path: Path) -> None:
    """Initialise ``path`` as a git repo and commit its contents.

    Re-harvesting a rebuild goes through the harvester's clone step, which
    requires a git repository (a plain directory fails ``git clone``).
    """
    env_args = [
        "-c",
        "user.name=rebuild-executor",
        "-c",
        "user.email=rebuild@repomirrorkit.local",
    ]
    subprocess.run(["git", "init", "-q"], cwd=str(path), check=True)
    subprocess.run(["git", *env_args, "add", "-A"], cwd=str(path), check=True)
    subprocess.run(
        ["git", *env_args, "commit", "-q", "-m", "rebuild output"],
        cwd=str(path),
        check=True,
    )


def run_rebuild(
    harvest_dir: Path,
    workspace: Path,
    lane: RebuildLane = RebuildLane.CLOUD,
    model: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    permission_mode: str = "acceptEdits",
    git_init: bool = True,
    runner: Runner = _default_runner,
) -> RebuildResult:
    """Assemble a workspace, drive a rebuild, and record telemetry.

    Args:
        harvest_dir: a completed harvest ``--out`` directory.
        workspace: a fresh directory to build in (created; must be outside
            ``harvest_dir``).
        lane: CLOUD (``claude -p``) or LOCAL (forge-loop, not yet wired).
        model: optional model id passed to the lane.
        timeout: seconds before the rebuild invocation is killed.
        permission_mode: Claude Code permission mode for the headless run.
        git_init: ``git init`` + commit the result so it can be re-harvested.
        runner: subprocess boundary (injectable for tests).

    Returns:
        A :class:`RebuildResult`. Non-zero exit or timeout yields
        ``success=False`` with ``error`` set rather than raising.
    """
    copied = prepare_rebuild_workspace(harvest_dir, workspace)
    workspace = workspace.resolve()

    if lane is RebuildLane.LOCAL:
        raise RebuildError(
            "local lane (forge-loop) is not yet wired — pending WP-3.5. "
            "Use lane=RebuildLane.CLOUD for now."
        )

    prompt = build_rebuild_prompt(workspace, copied)
    argv = ["claude", "-p", prompt, "--output-format", "json",
            "--permission-mode", permission_mode]
    if model:
        argv += ["--model", model]

    start = time.monotonic()
    try:
        proc = runner(argv, workspace, timeout)
    except subprocess.TimeoutExpired:
        return RebuildResult(
            lane=lane.value, model=model, workspace=workspace, success=False,
            duration_seconds=time.monotonic() - start,
            copied_inputs=tuple(copied),
            error=f"rebuild timed out after {timeout}s",
        )
    except (OSError, FileNotFoundError) as exc:
        return RebuildResult(
            lane=lane.value, model=model, workspace=workspace, success=False,
            duration_seconds=time.monotonic() - start,
            copied_inputs=tuple(copied),
            error=f"could not launch rebuild agent: {exc}",
        )
    duration = time.monotonic() - start

    telemetry = _parse_claude_json(proc.stdout)
    success = proc.returncode == 0
    error = None if success else (proc.stderr.strip() or f"exit code {proc.returncode}")

    if success and git_init:
        try:
            _git_init_commit(workspace)
        except (subprocess.CalledProcessError, OSError) as exc:
            success = False
            error = f"rebuild succeeded but git init failed: {exc}"

    return RebuildResult(
        lane=lane.value,
        model=model,
        workspace=workspace,
        success=success,
        duration_seconds=duration,
        exit_code=proc.returncode,
        intervention_count=0,
        turns=telemetry["turns"],
        tokens_in=telemetry["tokens_in"],
        tokens_out=telemetry["tokens_out"],
        cost_usd=telemetry["cost_usd"],
        copied_inputs=tuple(copied),
        error=error,
    )
