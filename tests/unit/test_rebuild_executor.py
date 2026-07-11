"""Unit tests for the rebuild executor (workspace isolation + orchestration)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repo_mirror_kit.harvester.rebuild.executor import (
    RebuildError,
    RebuildLane,
    RebuildResult,
    build_rebuild_prompt,
    prepare_rebuild_workspace,
    run_rebuild,
)


def _make_harvest_dir(root: Path) -> Path:
    """A minimal harvest --out directory with both inputs and forbidden files."""
    harvest = root / "harvest"
    (harvest / "project-folder").mkdir(parents=True)
    (harvest / "project-folder" / "CLAUDE.md").write_text("scaffold", encoding="utf-8")
    (harvest / "beans").mkdir()
    (harvest / "beans" / "BEAN-001.md").write_text("a bean", encoding="utf-8")
    (harvest / "REQUIREMENTS.md").write_text("reqs", encoding="utf-8")
    (harvest / "RUNBOOK.md").write_text("runbook", encoding="utf-8")
    (harvest / ".env.example").write_text("KEY=", encoding="utf-8")
    (harvest / "openapi.yaml").write_text("openapi: 3.1.0", encoding="utf-8")
    # Forbidden — must never be copied:
    (harvest / "repo").mkdir()
    (harvest / "repo" / "secret_source.py").write_text("answer", encoding="utf-8")
    (harvest / "surfaces.json").write_text("{}", encoding="utf-8")
    return harvest


def test_prepare_workspace_copies_only_requirement_artifacts(tmp_path: Path) -> None:
    harvest = _make_harvest_dir(tmp_path)
    workspace = tmp_path / "ws"
    copied = prepare_rebuild_workspace(harvest, workspace)

    assert (workspace / "project-folder" / "CLAUDE.md").is_file()
    assert (workspace / "beans" / "BEAN-001.md").is_file()
    assert (workspace / "REQUIREMENTS.md").is_file()
    assert (workspace / "openapi.yaml").is_file()
    # The answer key and original source must NOT be present.
    assert not (workspace / "repo").exists()
    assert not (workspace / "surfaces.json").exists()
    assert set(copied) >= {"project-folder", "beans", "REQUIREMENTS.md", "openapi.yaml"}


def test_prepare_workspace_rejects_nested_workspace(tmp_path: Path) -> None:
    harvest = _make_harvest_dir(tmp_path)
    with pytest.raises(RebuildError, match="outside the harvest"):
        prepare_rebuild_workspace(harvest, harvest / "inside")


def test_prepare_workspace_empty_harvest_raises(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(RebuildError, match="no requirement artifacts"):
        prepare_rebuild_workspace(empty, tmp_path / "ws")


def test_build_prompt_mentions_available_inputs(tmp_path: Path) -> None:
    prompt = build_rebuild_prompt(tmp_path, ["REQUIREMENTS.md", "beans", "openapi.yaml"])
    assert "REQUIREMENTS.md" in prompt
    assert "beans/" in prompt
    assert "no original source" in prompt.lower()


def test_local_lane_requires_model(tmp_path: Path) -> None:
    harvest = _make_harvest_dir(tmp_path)
    with pytest.raises(RebuildError, match="local lane requires model"):
        run_rebuild(harvest, tmp_path / "ws", lane=RebuildLane.LOCAL)


def test_build_task_md_has_frontmatter_and_brief() -> None:
    from repo_mirror_kit.harvester.rebuild.executor import build_rebuild_task_md

    md = build_rebuild_task_md(
        ["REQUIREMENTS.md", "beans", "openapi.yaml"],
        data_class="public",
        allowed_commands=["python3 -m pytest", "python3"],
        final_verify="python3 -m pytest",
    )
    assert md.startswith("---\n")
    assert "data_class: public" in md
    assert "  - python3 -m pytest" in md
    assert "final_verify: python3 -m pytest" in md
    assert "REQUIREMENTS.md" in md
    assert "Acceptance criteria" in md


def test_local_lane_success_parses_state(tmp_path: Path) -> None:
    harvest = _make_harvest_dir(tmp_path)
    workspace = tmp_path / "ws"

    def fake_forge_loop(argv, cwd, timeout):
        # argv == ["forge-loop", "run", <task_dir>, "--model", m, "--repo", ws]
        task_dir = Path(argv[2])
        (Path(argv[6]) / "app.py").write_text("built", encoding="utf-8")
        (task_dir / "state.yaml").write_text(
            "model: gemma4:26b\n"
            "repo: ws\n"
            "data_class: public\n"
            "phase: done\n"
            "retries_total: 2\n"
            "steps:\n"
            "- {id: 1, title: scaffold, detail: '', status: done, attempts: 1}\n"
            "- {id: 2, title: routes, detail: '', status: done, attempts: 2}\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    result = run_rebuild(
        harvest, workspace, lane=RebuildLane.LOCAL, model="gemma4:26b",
        data_class="public", runner=fake_forge_loop,
    )
    assert result.success is True
    assert result.lane == "local"
    assert result.retries == 2
    assert result.turns == 2
    assert result.cost_usd is None  # local — no cost
    # workspace was git-inited before forge-loop ran (baseline commit).
    assert (workspace / ".git").is_dir()
    # task.md was written outside the workspace.
    assert (tmp_path / "ws-task" / "task.md").is_file()


def test_local_lane_escalation_is_failure(tmp_path: Path) -> None:
    harvest = _make_harvest_dir(tmp_path)
    workspace = tmp_path / "ws"

    def fake_forge_loop(argv, cwd, timeout):
        task_dir = Path(argv[2])
        (task_dir / "state.yaml").write_text(
            "model: gemma4:26b\nrepo: ws\ndata_class: public\n"
            "phase: escalated\nretries_total: 3\nsteps: []\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")

    result = run_rebuild(
        harvest, workspace, lane=RebuildLane.LOCAL, model="gemma4:26b",
        runner=fake_forge_loop,
    )
    assert result.success is False
    assert "escalated" in result.error


def test_run_rebuild_success_parses_telemetry(tmp_path: Path) -> None:
    harvest = _make_harvest_dir(tmp_path)
    workspace = tmp_path / "ws"

    def fake_runner(argv, cwd, timeout):
        # Agent "built" a file, and emits claude JSON telemetry.
        (Path(cwd) / "main.py").write_text("print('hi')", encoding="utf-8")
        payload = (
            '{"type":"result","total_cost_usd":0.12,"num_turns":7,'
            '"usage":{"input_tokens":1000,"output_tokens":500}}'
        )
        return subprocess.CompletedProcess(argv, 0, stdout=payload, stderr="")

    result = run_rebuild(harvest, workspace, model="claude-opus-4-8", runner=fake_runner)
    assert isinstance(result, RebuildResult)
    assert result.success is True
    assert result.tokens_in == 1000
    assert result.tokens_out == 500
    assert result.cost_usd == 0.12
    assert result.turns == 7
    assert result.intervention_count == 0
    # git_init committed the result so it is re-harvestable.
    assert (workspace / ".git").is_dir()


def test_run_rebuild_nonzero_exit_is_failure(tmp_path: Path) -> None:
    harvest = _make_harvest_dir(tmp_path)

    def fake_runner(argv, cwd, timeout):
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="boom")

    result = run_rebuild(harvest, tmp_path / "ws", runner=fake_runner, git_init=False)
    assert result.success is False
    assert result.error == "boom"
    assert result.exit_code == 1


def test_run_rebuild_timeout_is_failure(tmp_path: Path) -> None:
    harvest = _make_harvest_dir(tmp_path)

    def fake_runner(argv, cwd, timeout):
        raise subprocess.TimeoutExpired(argv, timeout)

    result = run_rebuild(harvest, tmp_path / "ws", timeout=5, runner=fake_runner)
    assert result.success is False
    assert "timed out" in result.error
