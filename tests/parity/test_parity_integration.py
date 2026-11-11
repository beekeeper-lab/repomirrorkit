"""End-to-end parity tests against the runnable fixture apps (BEAN-077/078).

Boots real Flask and Express apps. Skipped when their toolchains are missing.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.parity.goldens import capture, load_script, replay
from repo_mirror_kit.harvester.parity.score import score_rebuild
from repo_mirror_kit.harvester.parity.server import AppProcess
from repo_mirror_kit.harvester.pipeline import HarvestPipeline

pytestmark = pytest.mark.parity

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample-projects"
GOLDENS = Path(__file__).parent.parent / "fixtures" / "goldens"
AUTH = {"X-API-Key": "demo-key"}
ENV = {"API_KEY": "demo-key", "PYTHON": sys.executable}

needs_flask = pytest.mark.skipif(
    subprocess.run(
        [sys.executable, "-c", "import flask, flask_sqlalchemy"], capture_output=True
    ).returncode
    != 0,
    reason="flask / flask-sqlalchemy not installed",
)
needs_node = pytest.mark.skipif(
    shutil.which("node") is None or shutil.which("npm") is None,
    reason="node/npm not available",
)


def _copy(name: str, tmp_path: Path) -> Path:
    dst = tmp_path / name
    shutil.copytree(
        FIXTURES / name,
        dst,
        ignore=shutil.ignore_patterns("node_modules", "__pycache__"),
    )
    return dst


def _golden(name: str) -> dict:
    return json.loads((GOLDENS / f"{name}.golden.json").read_text())


def _replay(app_dir: Path, golden: dict):
    with AppProcess(app_dir, "bash start.sh", ENV) as app:
        return replay(app.base_url, golden)


@needs_flask
def test_flask_original_matches_its_golden_and_capture_is_deterministic(
    tmp_path: Path,
) -> None:
    app = _copy("parity-flask", tmp_path)
    script = load_script(GOLDENS / "shop.script.json")
    runs = []
    for _ in range(2):
        with AppProcess(app, "bash start.sh", ENV) as srv:
            runs.append(capture(srv.base_url, script, AUTH, "parity-flask"))
    assert runs[0] == runs[1], "capture must be deterministic across runs"
    assert runs[0] == _golden("parity-flask"), (
        "checked-in golden drifted from the fixture app"
    )
    assert _replay(app, runs[0]).pass_rate == 1.0


@needs_flask
@needs_node
def test_cross_stack_equivalence_flask_golden_vs_express_app(tmp_path: Path) -> None:
    """Different framework, same behaviour → the harness scores 100% (layout-agnostic)."""
    express = _copy("parity-express", tmp_path)
    result = _replay(express, _golden("parity-flask"))
    assert result.pass_rate == 1.0 and result.strict_rate == 1.0, result.to_dict()[
        "failures"
    ]


@needs_flask
def test_deliberately_broken_rebuild_scores_measurably_lower(tmp_path: Path) -> None:
    """The metric discriminates: crippled behaviour scores far below the original."""
    broken = _copy("parity-flask", tmp_path)
    app_py = broken / "app.py"
    text = app_py.read_text()
    # 1) no auth, 2) no workflow guard, 3) wrong validation.
    text = text.replace(
        'return request.headers.get("X-API-Key") == API_KEY', "return True"
    )
    text = text.replace("if order.status not in allowed:", "if False:")
    text = text.replace("len(customer.strip()) < 2", "len(customer.strip()) < 0")
    app_py.write_text(text)
    good = _replay(
        _copy_again("parity-flask", tmp_path), _golden("parity-flask")
    ).pass_rate
    bad = _replay(broken, _golden("parity-flask")).pass_rate
    assert good == 1.0 and bad is not None and bad < 0.6


def _copy_again(name: str, tmp_path: Path) -> Path:
    dst = tmp_path / f"{name}-pristine"
    shutil.copytree(
        FIXTURES / name,
        dst,
        ignore=shutil.ignore_patterns("node_modules", "__pycache__"),
    )
    return dst


@needs_flask
@needs_node
def test_full_score_with_gherkin_calibration_and_schema(tmp_path: Path) -> None:
    """Harvest the Flask original; score the Express app against it (cross-stack)."""
    original = tmp_path / "orig"
    shutil.copytree(
        FIXTURES / "parity-flask",
        original,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    git = shutil.which("git") or "git"
    subprocess.run([git, "init", "-q"], cwd=original, check=True)
    subprocess.run([git, "add", "-A"], cwd=original, check=True)
    subprocess.run(
        [git, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "i"],
        cwd=original,
        check=True,
    )
    harvest = tmp_path / "harvest"
    assert (
        HarvestPipeline()
        .run(
            HarvestConfig(
                repo=str(original),
                out=harvest,
                llm_enabled=False,
                fail_on_gaps=False,
                log_level="warn",
            )
        )
        .success
    )
    express = _copy("parity-express", tmp_path)
    (tmp_path / "empty-harvest").mkdir()

    report = score_rebuild(
        golden=_golden("parity-flask"),
        original_harvest=harvest,
        rebuild_dir=express,
        rebuild_harvest=tmp_path / "empty-harvest",  # the express app has no DB design
        auth_headers=AUTH,
        env=ENV,
        original_dir=_copy_again("parity-flask", tmp_path),
    )
    data = report.to_dict()
    assert data["families"]["golden_replay"]["score"] == 1.0
    gh = data["families"]["gherkin"]
    assert gh["bound"] >= 5 and gh["relative_to_original"] == 1.0, gh
    # The rebuild has no DB design → schema is N/A (storage is a free choice).
    assert data["families"]["schema"]["score"] is None
    assert any("Schema family N/A" in n for n in data["notes"])
    assert data["overall"] == 1.0 and data["passed"]
