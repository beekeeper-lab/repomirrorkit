"""LLM provider registry, key lookup and user-level key storage.

Providers (all but ``claude-cli`` speak the Anthropic Messages API, so one
client serves them; Kimi and DeepSeek publish Anthropic-compatible endpoints):

========== ===================================== ==================================
id         endpoint                              key variable(s)
========== ===================================== ==================================
anthropic  Anthropic API                         ``ANTHROPIC_API_KEY``
kimi       Moonshot AI (Kimi) /anthropic         ``KIMI_API_KEY``, ``MOONSHOT_API_KEY``
deepseek   DeepSeek /anthropic                   ``DEEPSEEK_API_KEY``
claude-cli headless ``claude -p`` (subscription) none — uses your Claude Code login
========== ===================================== ==================================

Where keys live — **never in the repository**:

1. the process environment (preferred; set it in your shell profile), or
2. a per-user env file ``~/.config/repomirrorkit/providers.env`` (honours
   ``XDG_CONFIG_HOME``), created with mode ``0600`` in a ``0700`` directory.
   The GUI settings screen can write it, or you can edit it by hand.

Environment variables win over the file. Values are never logged or returned
by the status helpers (only *where* a key was found).
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

APP_DIR_NAME = "repomirrorkit"
ENV_FILE_NAME = "providers.env"
SETTINGS_FILE_NAME = "settings.json"

_KEY_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


@dataclass(frozen=True)
class Provider:
    """One selectable LLM backend."""

    id: str
    label: str
    kind: str  # "api" | "cli"
    base_url: str | None = None
    env_vars: tuple[str, ...] = ()
    default_model: str = ""
    key_help_url: str = ""
    note: str = ""


PROVIDERS: dict[str, Provider] = {
    "anthropic": Provider(
        id="anthropic",
        label="Anthropic (Claude API)",
        kind="api",
        base_url=None,
        env_vars=("ANTHROPIC_API_KEY",),
        default_model="claude-sonnet-5-5",
        key_help_url="https://console.anthropic.com/settings/keys",
    ),
    "kimi": Provider(
        id="kimi",
        label="Kimi (Moonshot AI)",
        kind="api",
        base_url="https://api.moonshot.ai/anthropic",
        env_vars=("KIMI_API_KEY", "MOONSHOT_API_KEY"),
        default_model="kimi-k2-turbo-preview",
        key_help_url="https://platform.moonshot.ai/console/api-keys",
        note="Anthropic-compatible endpoint. Model name is editable.",
    ),
    "deepseek": Provider(
        id="deepseek",
        label="DeepSeek",
        kind="api",
        base_url="https://api.deepseek.com/anthropic",
        env_vars=("DEEPSEEK_API_KEY",),
        default_model="deepseek-chat",
        key_help_url="https://platform.deepseek.com/api_keys",
        note="Anthropic-compatible endpoint. Model name is editable.",
    ),
    "claude-cli": Provider(
        id="claude-cli",
        label="Claude Code login (subscription, no API key)",
        kind="cli",
        default_model="sonnet",
        note="Runs headless `claude -p` on this machine with your Claude Code login.",
    ),
}

DEFAULT_PROVIDER = "anthropic"


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def user_config_dir() -> Path:
    """Per-user config directory (outside any repository)."""
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_DIR_NAME


def env_file_path() -> Path:
    """Path of the per-user provider key file."""
    return user_config_dir() / ENV_FILE_NAME


def settings_file_path() -> Path:
    """Path of the (non-secret) GUI settings file."""
    return user_config_dir() / SETTINGS_FILE_NAME


# ---------------------------------------------------------------------------
# Env file (keys)
# ---------------------------------------------------------------------------


def read_env_file(path: Path | None = None) -> dict[str, str]:
    """Parse ``KEY=VALUE`` lines (``#`` comments, optional quotes)."""
    target = path or env_file_path()
    out: dict[str, str] = {}
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return out
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if _KEY_NAME_RE.match(key) and value:
            out[key] = value
    return out


def load_user_env() -> list[str]:
    """Load the env file into ``os.environ`` without overriding real variables.

    Returns:
        Names (not values) that were set from the file.
    """
    loaded: list[str] = []
    for key, value in read_env_file().items():
        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


def _write_env_file(values: dict[str, str]) -> Path:
    path = env_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    body = (
        "# RepoMirrorKit provider keys. Per-user file — never commit it.\n"
        "# Real environment variables take precedence over this file.\n"
        + "".join(f"{k}={v}\n" for k, v in sorted(values.items()))
    )
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent), prefix=".providers-", suffix=".tmp"
    )
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path


def save_key(env_var: str, value: str) -> Path:
    """Store *value* under *env_var* in the env file (mode 0600).

    Raises:
        ValueError: for an invalid variable name, or a value with whitespace
            or control characters (keys never contain them).
    """
    if not _KEY_NAME_RE.match(env_var):
        raise ValueError(f"invalid environment variable name: {env_var!r}")
    value = value.strip()
    if not value or re.search(r"[\s\x00-\x1f]", value):
        raise ValueError("a key must be non-empty and contain no whitespace")
    values = read_env_file()
    values[env_var] = value
    path = _write_env_file(values)
    os.environ[env_var] = value  # effective immediately for this process
    return path


def remove_key(env_var: str) -> None:
    """Remove *env_var* from the env file (the live environment is untouched)."""
    values = read_env_file()
    if values.pop(env_var, None) is not None:
        _write_env_file(values)


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


def find_key(provider: Provider | str) -> tuple[str | None, str]:
    """Find a provider's API key.

    Returns:
        ``(value, source)`` where source is ``"environment"``, ``"env file"``
        or ``"missing"``. API-key-less providers return ``(None, "not needed")``.
    """
    prov = PROVIDERS[provider] if isinstance(provider, str) else provider
    if prov.kind != "api":
        return None, "not needed"
    for name in prov.env_vars:
        if os.environ.get(name):
            return os.environ[name], "environment"
    file_values = read_env_file()
    for name in prov.env_vars:
        if file_values.get(name):
            return file_values[name], "env file"
    return None, "missing"


def key_status(provider: Provider | str) -> str:
    """Where the key lives (``environment`` / ``env file`` / ``missing`` / ``not needed``)."""
    return find_key(provider)[1]


def is_local_endpoint(base_url: str | None) -> bool:
    """True for localhost endpoints (no per-token cost, no real key)."""
    if not base_url:
        return False
    host = urlparse(base_url).hostname or ""
    return host in ("localhost", "127.0.0.1", "::1") or host.endswith(".local")


# ---------------------------------------------------------------------------
# Non-secret GUI settings
# ---------------------------------------------------------------------------


@dataclass
class LlmSettings:
    """What the GUI remembers between runs. Contains no secrets."""

    enabled: bool = False
    provider: str = DEFAULT_PROVIDER
    model: str = ""
    budget_usd: float = 5.0
    concurrency: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "model": self.model,
            "budget_usd": self.budget_usd,
            "concurrency": self.concurrency,
        }


def load_settings() -> LlmSettings:
    """Load saved settings (defaults when absent or unreadable)."""
    try:
        data = json.loads(settings_file_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return LlmSettings()
    if not isinstance(data, dict):
        return LlmSettings()
    base = LlmSettings()
    provider = str(data.get("provider", base.provider))
    return LlmSettings(
        enabled=bool(data.get("enabled", base.enabled)),
        provider=provider if provider in PROVIDERS else base.provider,
        model=str(data.get("model", base.model)),
        budget_usd=float(data.get("budget_usd", base.budget_usd)),
        concurrency=max(1, min(8, int(data.get("concurrency", base.concurrency)))),
    )


def save_settings(settings: LlmSettings) -> Path:
    """Persist non-secret settings."""
    path = settings_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings.to_dict(), indent=2) + "\n", encoding="utf-8")
    return path
