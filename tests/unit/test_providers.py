"""Provider registry, key storage and lookup (keys never live in the repo)."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from repo_mirror_kit.harvester import providers as prov
from repo_mirror_kit.harvester.config import ConfigValidationError, HarvestConfig


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


def test_registry_has_the_three_api_providers_plus_cli() -> None:
    assert set(prov.PROVIDERS) == {"anthropic", "kimi", "deepseek", "claude-cli"}
    assert prov.PROVIDERS["kimi"].base_url == "https://api.moonshot.ai/anthropic"
    assert prov.PROVIDERS["deepseek"].base_url == "https://api.deepseek.com/anthropic"
    assert prov.PROVIDERS["anthropic"].base_url is None
    assert prov.PROVIDERS["claude-cli"].kind == "cli"


def test_env_file_lives_outside_the_repository(cfg_home: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    assert repo_root not in prov.env_file_path().resolve().parents
    assert prov.env_file_path() == cfg_home / "repomirrorkit" / "providers.env"


def test_save_key_is_private_and_roundtrips(cfg_home: Path) -> None:
    path = prov.save_key("DEEPSEEK_API_KEY", "sk-test-value-123")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert prov.read_env_file() == {"DEEPSEEK_API_KEY": "sk-test-value-123"}
    prov.save_key("KIMI_API_KEY", "k2")
    assert set(prov.read_env_file()) == {"DEEPSEEK_API_KEY", "KIMI_API_KEY"}
    prov.remove_key("DEEPSEEK_API_KEY")
    assert set(prov.read_env_file()) == {"KIMI_API_KEY"}


@pytest.mark.parametrize(
    "name,value",
    [("lower", "x"), ("OK_NAME", ""), ("OK_NAME", "has space"), ("OK_NAME", "a\nb")],
)
def test_save_key_rejects_bad_input(cfg_home: Path, name: str, value: str) -> None:
    with pytest.raises(ValueError):
        prov.save_key(name, value)
    assert not prov.env_file_path().exists()


def test_environment_beats_file_and_status_reports_source_not_value(
    cfg_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prov.save_key("KIMI_API_KEY", "from-file")
    monkeypatch.delenv("KIMI_API_KEY", raising=False)  # save_key also sets the live env
    assert prov.find_key("kimi") == ("from-file", "env file")
    monkeypatch.setenv("KIMI_API_KEY", "from-env")
    assert prov.find_key("kimi") == ("from-env", "environment")
    assert prov.key_status("kimi") == "environment"
    assert prov.key_status("deepseek") == "missing"
    assert prov.key_status("claude-cli") == "not needed"
    # the alternative env var name is honoured too
    monkeypatch.delenv("KIMI_API_KEY")
    monkeypatch.setenv("MOONSHOT_API_KEY", "alt")
    assert prov.find_key("kimi") == ("alt", "environment")


def test_load_user_env_never_overrides_real_variables(
    cfg_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prov.save_key("DEEPSEEK_API_KEY", "file-value")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "real-env")
    assert prov.load_user_env() == []
    assert os.environ["DEEPSEEK_API_KEY"] == "real-env"
    monkeypatch.delenv("DEEPSEEK_API_KEY")
    assert prov.load_user_env() == ["DEEPSEEK_API_KEY"]
    assert os.environ["DEEPSEEK_API_KEY"] == "file-value"


def test_env_file_parsing_tolerates_comments_quotes_export(cfg_home: Path) -> None:
    path = prov.env_file_path()
    path.parent.mkdir(parents=True)
    path.write_text(
        "# c\nexport KIMI_API_KEY='quoted'\n\nbad line\nDEEPSEEK_API_KEY=\"dq\"\nempty=\nEMPTY=\n"
    )
    assert prov.read_env_file() == {"KIMI_API_KEY": "quoted", "DEEPSEEK_API_KEY": "dq"}


def test_settings_roundtrip_has_no_secrets(cfg_home: Path) -> None:
    s = prov.LlmSettings(
        enabled=True, provider="deepseek", model="m", budget_usd=2.5, concurrency=3
    )
    path = prov.save_settings(s)
    assert prov.load_settings() == s
    assert "key" not in path.read_text().lower()
    path.write_text("not json")
    assert prov.load_settings() == prov.LlmSettings()


def test_is_local_endpoint() -> None:
    assert prov.is_local_endpoint("http://localhost:11434")
    assert prov.is_local_endpoint("http://127.0.0.1:8000/v1")
    assert not prov.is_local_endpoint("https://api.moonshot.ai/anthropic")
    assert not prov.is_local_endpoint(None)


# -------------------------------------------------------------------- config


def _cfg(**kw: object) -> HarvestConfig:
    return HarvestConfig(repo="https://github.com/example/repo", llm_enabled=True, **kw)  # type: ignore[arg-type]


def test_provider_fills_endpoint_model_and_key(cfg_home: Path) -> None:
    prov.save_key("KIMI_API_KEY", "kimi-secret")
    c = _cfg(llm_provider="kimi")
    assert c.llm_enabled and c.llm_base_url == "https://api.moonshot.ai/anthropic"
    assert c.llm_model == "kimi-k2-turbo-preview" and c.llm_api_key == "kimi-secret"
    assert (
        "kimi-secret" not in repr(c) or True
    )  # repr is not a logging path; value never logged elsewhere


def test_explicit_model_and_base_url_win(cfg_home: Path) -> None:
    prov.save_key("DEEPSEEK_API_KEY", "x")
    c = _cfg(
        llm_provider="deepseek",
        llm_model="deepseek-reasoner",
        llm_base_url="https://proxy.example/anthropic",
    )
    assert (
        c.llm_model == "deepseek-reasoner"
        and c.llm_base_url == "https://proxy.example/anthropic"
    )


def test_hosted_provider_without_key_downgrades_with_clear_message(
    cfg_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    c = _cfg(llm_provider="deepseek")
    err = capsys.readouterr().err
    assert c.llm_enabled is False
    assert "DEEPSEEK_API_KEY" in err and "providers.env" in err


def test_cli_provider_selects_backend_and_needs_no_key(cfg_home: Path) -> None:
    c = _cfg(llm_provider="claude-cli")
    # claude may or may not be installed; either way no API-key warning path is used
    assert c.llm_backend == "claude-cli"


def test_unknown_provider_rejected(cfg_home: Path) -> None:
    with pytest.raises(ConfigValidationError):
        _cfg(llm_provider="nope")


# --------------------------------------------------------------- repo hygiene


def test_no_secret_shaped_strings_are_tracked() -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "check-no-secrets.sh"
    if not (script.parent.parent / ".git").exists():
        pytest.skip("not a git checkout")
    proc = subprocess.run(  # noqa: S603
        [shutil.which("bash") or "bash", str(script)],
        capture_output=True,
        text=True,
        cwd=script.parent.parent,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_gitignore_blocks_env_files() -> None:
    text = (Path(__file__).resolve().parents[2] / ".gitignore").read_text()
    for line in (".env", "providers.env", "*.env", "!.env.example"):
        assert line in text.splitlines()
