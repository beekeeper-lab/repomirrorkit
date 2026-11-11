"""Fidelity gates run as a regression suite over every fixture (task 7.5).

``harvest --fail-on-fidelity`` exits 4 when recreation-readiness depth drops
below the thresholds in ``reports/fidelity.py``. This module (a) asserts every
checked-in fixture passes it, and (b) proves the gate can actually turn red by
sabotaging an extractor.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import CliRunner

from repo_mirror_kit.harvester.cli import EXIT_FIDELITY_FAILED, EXIT_SUCCESS, main

FIXTURES = sorted(
    p.name
    for p in (Path(__file__).parent.parent / "fixtures" / "sample-projects").iterdir()
    if p.is_dir()
)


def _harvest(repo: Path, out: Path) -> int:
    result = CliRunner().invoke(
        main,
        [
            "harvest",
            "--repo",
            str(repo),
            "--out",
            str(out),
            "--no-llm",
            "--no-fail-on-gaps",
            "--fail-on-fidelity",
            "--log-level",
            "error",
        ],
    )
    return result.exit_code


@pytest.mark.integration
@pytest.mark.parametrize("fixture", FIXTURES)
def test_every_fixture_passes_the_fidelity_gate(
    local_git_repo: Callable[[str], Path], tmp_path: Path, fixture: str
) -> None:
    assert _harvest(local_git_repo(fixture), tmp_path / "out") == EXIT_SUCCESS


@pytest.mark.integration
def test_gate_turns_red_when_an_extractor_regresses(
    local_git_repo: Callable[[str], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deliberately break JS contract extraction: ts-next must fail the gate."""
    monkeypatch.setattr(
        "repo_mirror_kit.harvester.pipeline.populate_js_api_contracts",
        lambda *a, **k: 0,
    )
    code = _harvest(local_git_repo("ts-next"), tmp_path / "out")
    assert code == EXIT_FIDELITY_FAILED
