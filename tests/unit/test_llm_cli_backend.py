"""Tests for the claude-cli enrichment backend (injected runner; no real CLI)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    ConfigSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.config import ConfigValidationError, HarvestConfig
from repo_mirror_kit.harvester.llm.cli_backend import (
    build_argv,
    enrich_with_claude_cli,
    parse_cli_output,
    scrubbed_env,
)

REPLY = {
    "behavioral_description": "Creates an order.",
    "inferred_intent": "ordering",
    "given_when_then": [],
    "data_flow": "x",
    "priority": "high",
    "dependencies": [],
    "confidence": "high",
    "gaps": ["tax rules unknown"],
    "traced_flow": [],
}


def _stdout(reply: dict | str, cost: float = 0.1, error: bool = False) -> str:
    text = reply if isinstance(reply, str) else json.dumps(reply)
    return json.dumps(
        {
            "result": text,
            "total_cost_usd": cost,
            "num_turns": 3,
            "usage": {"input_tokens": 10, "output_tokens": 20},
            "is_error": error,
        }
    )


def _cfg(**kw: object) -> HarvestConfig:
    return HarvestConfig(
        repo="https://github.com/example/repo",
        llm_enabled=True,
        llm_backend="claude-cli",
        llm_model="sonnet",
        **kw,  # type: ignore[arg-type]
    )


def _api(name: str) -> ApiSurface:
    return ApiSurface(
        name=name,
        method="GET",
        path="/x",
        source_refs=[SourceRef(file_path="a.py", start_line=1)],
    )


def test_argv_is_read_only_and_has_no_api_key_flags() -> None:
    argv = build_argv("PROMPT", "sonnet", 0.5)
    assert argv[:3] == ["claude", "-p", "PROMPT"]
    allowed = argv[argv.index("--allowedTools") + 1 : argv.index("--disallowedTools")]
    assert allowed == ["Read", "Grep", "Glob"]
    denied = set(argv[argv.index("--disallowedTools") + 1 : argv.index("--model")])
    assert {
        "Bash",
        "Edit",
        "Write",
        "WebFetch",
        "Read(**/.env)",
        "Read(**/.git/**)",
    } <= denied
    assert "--no-session-persistence" in argv and "--max-budget-usd" in argv
    assert argv[argv.index("--max-budget-usd") + 1] == "0.50"


def test_child_env_drops_secrets_and_api_key_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "OPENAI_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
    ):
        monkeypatch.setenv(name, "secret")
    monkeypatch.setenv("HOME", "/home/x")
    env = scrubbed_env()
    assert "HOME" in env and "PATH" in env
    assert not any(k.endswith(("_KEY", "_TOKEN", "_SECRET_ACCESS_KEY")) for k in env)


def test_parse_cli_output_variants() -> None:
    ok = parse_cli_output(_stdout(REPLY, cost=0.25))
    assert (
        ok.error is None
        and ok.cost_usd == 0.25
        and ok.turns == 3
        and ok.output_tokens == 20
    )
    assert parse_cli_output(_stdout("boom", error=True)).error == "boom"
    assert parse_cli_output("not json").error


def test_enrichment_applies_reply_and_writes_telemetry(tmp_path: Path) -> None:
    out = tmp_path / "out"
    repo = out / "repo"
    repo.mkdir(parents=True)
    (repo / "a.py").write_text("x = 1\n")
    seen: list[list[str]] = []

    def runner(argv, cwd, env, timeout):  # type: ignore[no-untyped-def]
        seen.append(argv)
        assert cwd == repo and "ANTHROPIC_API_KEY" not in env
        return subprocess.CompletedProcess(argv, 0, _stdout(REPLY), "")

    api = _api("GET /x")
    cfg_surface = ConfigSurface(name="DATABASE_URL")
    coll = SurfaceCollection(apis=[api], config=[cfg_surface])
    enrich_with_claude_cli(coll, _cfg(), repo, runner=runner)

    assert api.enrichment["behavioral_description"] == "Creates an order."
    assert api.enrichment["gaps"] == ["tax rules unknown"]
    assert cfg_surface.enrichment == {}  # config surfaces are not sent to the model
    assert len(seen) == 1
    tele = json.loads((out / "reports" / "enrichment-telemetry.json").read_text())
    assert [r["status"] for r in tele["surfaces"]] == ["ok", "skipped_type"]
    assert tele["summary"]["backend"] == "claude-cli"


def test_failures_are_isolated_and_budget_stops_the_run(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x\n")
    calls = {"n": 0}

    def runner(argv, cwd, env, timeout):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 1:
            return subprocess.CompletedProcess(
                argv, 0, _stdout("no json here", cost=0.6), ""
            )
        if calls["n"] == 2:
            raise subprocess.TimeoutExpired(argv, 1)
        return subprocess.CompletedProcess(argv, 0, _stdout(REPLY, cost=0.6), "")

    apis = [_api("A"), _api("B"), _api("C"), _api("D")]
    enrich_with_claude_cli(
        SurfaceCollection(apis=apis), _cfg(llm_budget_usd=1.0), tmp_path, runner=runner
    )
    statuses = [bool(a.enrichment) for a in apis]
    assert statuses == [
        False,
        False,
        True,
        False,
    ]  # A bad JSON, B timeout, C ok (spent now 1.2), D skipped
    assert calls["n"] == 3


def test_concurrency_validation_and_backend_validation() -> None:
    with pytest.raises(ConfigValidationError):
        _cfg(llm_concurrency=0)
    with pytest.raises(ConfigValidationError):
        HarvestConfig(repo="https://github.com/example/repo", llm_backend="nope")


def test_system_prompt_forbids_copying_secret_values() -> None:
    from repo_mirror_kit.harvester.llm.cli_backend import CLI_SYSTEM_PROMPT
    from repo_mirror_kit.harvester.llm.prompts import AGENT_SYSTEM_PROMPT

    for prompt in (CLI_SYSTEM_PROMPT, AGENT_SYSTEM_PROMPT):
        assert "Never reproduce secret or credential VALUES" in prompt
    assert (
        "Read, Grep, Glob" in CLI_SYSTEM_PROMPT and "read_file" not in CLI_SYSTEM_PROMPT
    )


def test_placeholder_gate_counts_only_behavioural_beans(tmp_path: Path) -> None:
    from repo_mirror_kit.harvester.reports.fidelity import compute_fidelity

    beans = tmp_path / "beans"
    beans.mkdir()
    (beans / "BEAN-001-a.md").write_text("---\ntype: api\n---\nDescribed.\n")
    (beans / "BEAN-002-b.md").write_text("---\ntype: api\n---\nTODO: x\n")
    (beans / "BEAN-003-c.md").write_text("---\ntype: dependency\n---\nTODO: x\n")
    metric = next(
        m
        for m in compute_fidelity(SurfaceCollection(), beans_dir=beans).metrics
        if m.name == "placeholder_free_beans"
    )
    assert (metric.covered, metric.total) == (1, 2)  # the dependency bean is ignored
