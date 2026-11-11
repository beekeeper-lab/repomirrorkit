"""Enrichment through headless Claude Code (`claude -p`) — no API key.

Instead of calling the Messages API, each surface is investigated by a
``claude -p`` run inside the cloned repo using the operator's Claude Code
login. Claude Code's own ``Read`` / ``Grep`` / ``Glob`` tools replace our
sandboxed ``read_file`` / ``grep`` / ``list_dir``.

Safety posture (the repo is untrusted, and so is everything the model reads):

- **read-only tools only**: ``--allowedTools Read Grep Glob``; Bash, Edit, Write,
  web tools and sub-agents are explicitly disallowed;
- secrets/`.git` paths are denied with ``Read(...)`` deny rules (best effort:
  Claude Code applies Read rules to its search tools too, but this is weaker
  than the SDK backend's path sandbox — prefer ``--llm-backend api`` for repos
  you do not trust);
- the child process gets a **scrubbed environment** — never the host's API
  keys — and ``ANTHROPIC_API_KEY`` / ``ANTHROPIC_AUTH_TOKEN`` are removed on
  purpose so Claude Code uses the subscription login;
- per-call ``--max-budget-usd`` plus a run-level cap, and a wall-clock timeout
  per call (Claude Code has no max-turns flag, so time + budget bound a run).

Cost figures reported by Claude Code are API-equivalent estimates; on a
subscription they consume plan usage rather than being billed per call.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import Surface, SurfaceCollection
from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.llm.agent import parse_agent_json
from repo_mirror_kit.harvester.llm.enrichment import (
    _emit_progress,
    _neighbor_index,
    _read_source_for_surface,
    _Telemetry,
    apply_agent_data,
)
from repo_mirror_kit.harvester.llm.prompts import (
    AGENT_SYSTEM_PROMPT,
    build_agent_prompt,
)
from repo_mirror_kit.harvester.llm.types import ENRICH_TYPES

logger = structlog.get_logger()

CALL_TIMEOUT_SECONDS = 300
PER_CALL_BUDGET_USD = 1.0

_ENV_KEEP = (
    "PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "TERM",
    "USER",
    "SHELL",
    "TMPDIR",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_CACHE_HOME",
    "CLAUDE_CONFIG_DIR",
)

_DENY = (
    "Bash",
    "Edit",
    "Write",
    "NotebookEdit",
    "WebFetch",
    "WebSearch",
    "Task",
    "Read(**/.env)",
    "Read(**/.env.*)",
    "Read(**/*.pem)",
    "Read(**/*.key)",
    "Read(**/id_rsa*)",
    "Read(**/id_ed25519*)",
    "Read(**/.git/**)",
    "Read(**/credentials*)",
)

# Claude Code's tool names replace the SDK backend's read_file/grep/list_dir.
CLI_SYSTEM_PROMPT = (
    AGENT_SYSTEM_PROMPT.replace(
        "(read_file, grep, list_dir)", "(Read, Grep, Glob)"
    ).replace(
        "<repo_file>, <repo_search>, <repo_listing>", "file reads and search results"
    )
    + "\nYou are running inside the repository root; use paths relative to it. "
    "Do not modify anything."
)


@dataclass
class CliResult:
    text: str = ""
    cost_usd: float = 0.0
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None


Runner = Callable[
    [list[str], Path, dict[str, str], int], "subprocess.CompletedProcess[str]"
]


def _default_runner(
    argv: list[str], cwd: Path, env: dict[str, str], timeout: int
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - argv is fully constructed here
        argv,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def scrubbed_env() -> dict[str, str]:
    """Environment for the child: minimal, and without any API-key auth."""
    return {k: v for k, v in os.environ.items() if k in _ENV_KEEP}


def build_argv(prompt: str, model: str | None, max_budget: float) -> list[str]:
    argv = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--no-session-persistence",
        "--append-system-prompt",
        CLI_SYSTEM_PROMPT,
        "--max-budget-usd",
        f"{max_budget:.2f}",
        "--allowedTools",
        "Read",
        "Grep",
        "Glob",
        "--disallowedTools",
        *_DENY,
    ]
    if model:
        argv += ["--model", model]
    return argv


def parse_cli_output(stdout: str) -> CliResult:
    """Parse ``claude -p --output-format json`` stdout."""
    try:
        data = json.loads(stdout.strip())
    except json.JSONDecodeError:
        return CliResult(error="claude output was not JSON")
    if not isinstance(data, dict):
        return CliResult(error="claude output was not an object")
    raw_usage = data.get("usage")
    usage: dict[str, Any] = raw_usage if isinstance(raw_usage, dict) else {}
    result = CliResult(
        text=str(data.get("result", "") or ""),
        cost_usd=float(data.get("total_cost_usd") or 0.0),
        turns=int(data.get("num_turns") or 0),
        input_tokens=int(usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
    )
    if data.get("is_error"):
        result.error = result.text[:200] or "claude reported an error"
    return result


def enrich_with_claude_cli(
    surfaces: SurfaceCollection,
    config: HarvestConfig,
    workdir: Path,
    callback: Callable[..., Any] | None = None,
    runner: Runner = _default_runner,
) -> SurfaceCollection:
    """Enrich surfaces by running headless Claude Code per surface."""
    all_surfaces = list(surfaces)
    telemetry = _Telemetry(model=config.llm_model)
    neighbors = _neighbor_index(all_surfaces)
    env = scrubbed_env()
    lock = threading.Lock()
    state = {"spent": 0.0, "done": 0}
    budget = config.llm_budget_usd
    _emit_progress(
        callback,
        f"LLM enrichment starting via claude CLI: {len(all_surfaces)} surfaces "
        f"(concurrency {config.llm_concurrency}); each call takes ~10-30s",
    )

    def work(surface: Surface) -> dict[str, Any]:
        record = telemetry.start(surface)
        if surface.surface_type not in ENRICH_TYPES:
            record["status"] = "skipped_type"
            return record
        with lock:
            remaining = (budget - state["spent"]) if budget > 0 else PER_CALL_BUDGET_USD
        if budget > 0 and remaining <= 0:
            record["status"] = "skipped_budget"
            return record
        prompt = build_agent_prompt(
            surface_type=surface.surface_type,
            surface_name=surface.name,
            surface_data=surface.to_dict(),
            source_code=_read_source_for_surface(surface, workdir),
            neighbors=neighbors.get(id(surface), "") or "(none found)",
        )
        argv = build_argv(
            prompt, config.llm_model, min(PER_CALL_BUDGET_USD, max(remaining, 0.05))
        )
        started = time.monotonic()
        try:
            proc = runner(argv, workdir, env, CALL_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            record["status"] = "failed"
            record["error"] = f"timed out after {CALL_TIMEOUT_SECONDS}s"
            return record
        except OSError as exc:
            record["status"] = "failed"
            record["error"] = f"could not launch claude: {exc}"
            return record
        result = parse_cli_output(proc.stdout)
        record.update(
            turns=result.turns,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            est_cost_usd=round(result.cost_usd, 6),
            seconds=round(time.monotonic() - started, 1),
        )
        with lock:
            state["spent"] += result.cost_usd
        data = parse_agent_json(result.text) if not result.error else None
        if proc.returncode != 0 or result.error or data is None:
            record["status"] = "failed"
            record["error"] = result.error or (
                proc.stderr.strip()[:200] or "no JSON in reply"
            )
            return record
        apply_agent_data(surface, data)
        record["status"] = "ok"
        return record

    def tick(rec: dict[str, Any]) -> None:
        with lock:
            state["done"] += 1
            n = state["done"]
        _emit_progress(
            callback,
            f"LLM enrichment {n}/{len(all_surfaces)}: {rec['surface']} "
            f"({rec['status']}{', ' + str(rec['seconds']) + 's' if rec.get('seconds') else ''})",
        )

    with ThreadPoolExecutor(max_workers=config.llm_concurrency) as pool:
        records = []
        for rec in pool.map(work, all_surfaces):
            tick(rec)
            records.append(rec)
    for rec in records:
        telemetry.add(rec)

    summary = telemetry.summary(state["spent"], budget, (0.0, 0.0))
    summary["backend"] = "claude-cli"
    summary["cost_note"] = (
        "API-equivalent estimates reported by Claude Code; on a subscription this "
        "consumes plan usage rather than per-call billing."
    )
    logger.info("llm_enrichment_complete", **summary)
    if workdir.name == "repo":
        telemetry.write(workdir.parent / "reports", summary)
    return surfaces
