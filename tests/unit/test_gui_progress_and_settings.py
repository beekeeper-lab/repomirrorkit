"""GUI: harvest worker never goes silent; settings dialog manages keys safely."""

from __future__ import annotations

import logging
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from repo_mirror_kit.harvester import providers as prov
from repo_mirror_kit.harvester.harvest_logging import (
    configure_logging,
    register_log_handler,
    unregister_log_handler,
)
from repo_mirror_kit.harvester.llm import probe as probe_mod
from repo_mirror_kit.workers.harvest_worker import HarvestWorker

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample-projects" / "python-flask"


@pytest.fixture
def cfg_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    for name in (
        "ANTHROPIC_API_KEY",
        "KIMI_API_KEY",
        "MOONSHOT_API_KEY",
        "DEEPSEEK_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    return tmp_path / "cfg"


def _git_repo(tmp_path: Path) -> Path:
    git = shutil.which("git") or "git"
    dst = tmp_path / "projects" / "demo"
    shutil.copytree(FIXTURE, dst)
    for cmd in (
        [git, "init", "-q"],
        [git, "add", "-A"],
        [git, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "i"],
    ):
        subprocess.run(cmd, cwd=dst, check=True, capture_output=True)  # noqa: S603
    return dst


def _run_worker(
    worker: HarvestWorker,
) -> tuple[list[tuple[bool, str]], list[str], list[str]]:
    done: list[tuple[bool, str]] = []
    events: list[str] = []
    logs: list[str] = []
    worker.harvest_finished.connect(lambda ok, msg: done.append((ok, msg)))
    worker.stage_changed.connect(events.append)
    worker.progress_updated.connect(events.append)
    worker.log_message.connect(logs.append)
    worker.run()  # synchronous: same code path as the thread body
    return done, events, logs


def test_relative_project_path_no_longer_kills_the_worker_silently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cfg_home: Path
) -> None:
    """The reported bug: GUI passes 'projects/<name>' (relative) → config error → no signal."""
    _git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    worker = HarvestWorker(Path("projects/demo"), Path("projects/demo/ai"))

    done, events, logs = _run_worker(worker)

    assert done and done[0][0] is True, done
    assert any("Stage A" in e for e in events) and any("Stage G" in e for e in events)
    assert any("pipeline_starting" in line for line in logs), (
        "structured logs must reach the panel"
    )
    assert any("LLM enrichment: off" in line for line in logs)


def test_any_failure_still_emits_finished_and_a_traceback(
    tmp_path: Path, cfg_home: Path
) -> None:
    worker = HarvestWorker(tmp_path / "does-not-exist", tmp_path / "out")
    done, _events, logs = _run_worker(worker)
    assert len(done) == 1 and done[0][0] is False
    assert any("Traceback" in line or "Error" in line for line in logs) or done[0][1]


def test_enabled_llm_without_key_degrades_visibly(
    tmp_path: Path, cfg_home: Path
) -> None:
    _git_repo(tmp_path)
    settings = prov.LlmSettings(enabled=True, provider="kimi")
    worker = HarvestWorker(tmp_path / "projects" / "demo", tmp_path / "out", settings)
    done, events, logs = _run_worker(worker)
    assert done[0][0] is True
    assert any("No API key for Kimi" in e for e in events)
    assert any("off (structural only)" in line for line in logs)


def test_log_handler_survives_configure_logging_and_has_no_ansi() -> None:
    captured: list[str] = []

    class H(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(self.format(record))

    handler = H()
    register_log_handler(handler)
    try:
        configure_logging("info")  # the pipeline does this at the start of every run
        import structlog

        structlog.get_logger("t").info("hello_event", detail="x")
    finally:
        unregister_log_handler(handler)
    assert any("hello_event" in line for line in captured)
    assert not any("\x1b[" in line for line in captured)
    structlog.get_logger("t").info("after_unregister")
    assert not any("after_unregister" in line for line in captured)


# ---------------------------------------------------------------------- probe


def test_probe_reports_missing_key_and_scrubs_errors(
    cfg_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert not probe_mod.probe_provider("deepseek").ok
    assert "DEEPSEEK_API_KEY" in probe_mod.probe_provider("deepseek").message
    prov.save_key("DEEPSEEK_API_KEY", "sk-very-secret-key-value")

    class Boom:
        def __init__(self, **kw: object) -> None:
            pass

        def complete(self, *a: object, **k: object) -> str:
            raise RuntimeError("401 bad key sk-very-secret-key-value")

    monkeypatch.setattr("repo_mirror_kit.harvester.llm.client.LLMClient", Boom)
    result = probe_mod.probe_provider("deepseek")
    assert not result.ok and "sk-very-secret-key-value" not in result.message
    assert "[key]" in result.message

    class Fine(Boom):
        def complete(self, *a: object, **k: object) -> str:
            return "OK"

    monkeypatch.setattr("repo_mirror_kit.harvester.llm.client.LLMClient", Fine)
    assert probe_mod.probe_provider("deepseek").ok


# ------------------------------------------------------------ settings dialog


def test_settings_dialog_saves_key_privately_and_never_displays_it(
    qtbot,
    cfg_home: Path,  # type: ignore[no-untyped-def]
) -> None:
    from repo_mirror_kit.views.settings_dialog import SettingsDialog

    dialog = SettingsDialog(prov.LlmSettings())
    qtbot.addWidget(dialog)
    dialog._provider.setCurrentIndex(dialog._provider.findData("deepseek"))
    assert "not set" in dialog._key_status.text()

    dialog._key_input.setText("sk-secret-deepseek-value")
    dialog._save_key.click()

    path = prov.env_file_path()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert prov.read_env_file() == {"DEEPSEEK_API_KEY": "sk-secret-deepseek-value"}
    assert dialog._key_input.text() == "", "the key field is cleared after saving"
    shown = " ".join(
        w.text() for w in (dialog._key_status, dialog._where, dialog._test_result)
    )
    assert "sk-secret-deepseek-value" not in shown
    assert (
        "env file" in dialog._key_status.text()
        or "environment" in dialog._key_status.text()
    )
    assert str(path) in dialog._where.text() or str(path) in dialog._key_status.text()

    dialog._remove_key.setEnabled(True)
    os.environ.pop("DEEPSEEK_API_KEY", None)
    dialog._remove_key.click()
    assert prov.read_env_file() == {}


def test_settings_dialog_rejects_bad_key_and_persists_choices(
    qtbot,
    cfg_home: Path,  # type: ignore[no-untyped-def]
) -> None:
    from repo_mirror_kit.views.settings_dialog import SettingsDialog

    dialog = SettingsDialog(prov.LlmSettings())
    qtbot.addWidget(dialog)
    dialog._provider.setCurrentIndex(dialog._provider.findData("kimi"))
    dialog._key_input.setText("has a space")
    dialog._save_key.click()
    assert (
        "Not saved" in dialog._test_result.text() and not prov.env_file_path().exists()
    )

    dialog._enabled.setChecked(True)
    dialog._model.setText("kimi-k2-0905-preview")
    dialog._budget.setValue(1.5)
    dialog._buttons.accepted.emit()
    saved = prov.load_settings()
    assert (saved.enabled, saved.provider, saved.model, saved.budget_usd) == (
        True,
        "kimi",
        "kimi-k2-0905-preview",
        1.5,
    )


def test_claude_cli_hides_key_section(qtbot, cfg_home: Path) -> None:  # type: ignore[no-untyped-def]
    from repo_mirror_kit.views.settings_dialog import SettingsDialog

    dialog = SettingsDialog(prov.LlmSettings())
    qtbot.addWidget(dialog)
    dialog.show()
    dialog._provider.setCurrentIndex(dialog._provider.findData("claude-cli"))
    assert not dialog._key_box.isVisible() and dialog._concurrency.isEnabled()
    dialog._provider.setCurrentIndex(dialog._provider.findData("anthropic"))
    assert dialog._key_box.isVisible() and not dialog._concurrency.isEnabled()


def test_each_harvest_gets_a_fresh_output_folder(tmp_path: Path) -> None:
    from repo_mirror_kit.views.main_window import next_output_dir

    project = tmp_path / "projects" / "demo"
    project.mkdir(parents=True)
    first = next_output_dir(project)
    assert first == project / "ai"
    first.mkdir()
    (first / "repo").mkdir()
    second = next_output_dir(project)
    assert second == project / "ai-2" and (first / "repo").exists()  # nothing deleted
    second.mkdir()
    assert next_output_dir(project) == project / "ai-3"
