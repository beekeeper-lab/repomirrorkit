"""One-shot connectivity check for an LLM provider ("Test connection")."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass

from repo_mirror_kit.harvester.providers import PROVIDERS, find_key


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of :func:`probe_provider`. ``message`` never contains key values."""

    ok: bool
    message: str
    seconds: float = 0.0


def _scrub(text: str, secret: str | None) -> str:
    out = text.replace(secret, "[key]") if secret else text
    return out.strip().splitlines()[0][:240] if out.strip() else "no details"


def probe_provider(provider_id: str, model: str | None = None) -> ProbeResult:
    """Send a tiny request through the provider and report success or why not."""
    provider = PROVIDERS.get(provider_id)
    if provider is None:
        return ProbeResult(False, f"unknown provider {provider_id!r}")
    started = time.monotonic()

    if provider.kind == "cli":
        from repo_mirror_kit.harvester.llm.cli_backend import scrubbed_env

        claude = shutil.which("claude")
        if claude is None:
            return ProbeResult(False, "the `claude` CLI is not on PATH")
        try:
            proc = subprocess.run(  # noqa: S603 - fixed argv
                [
                    claude,
                    "-p",
                    "Reply with exactly: OK",
                    "--output-format",
                    "json",
                    "--no-session-persistence",
                    "--max-budget-usd",
                    "0.10",
                    "--allowedTools",
                    "Read",
                    *(["--model", model or provider.default_model]),
                ],
                capture_output=True,
                text=True,
                timeout=90,
                env=scrubbed_env(),
                check=False,
            )
        except FileNotFoundError:
            return ProbeResult(False, "the `claude` CLI is not on PATH")
        except subprocess.TimeoutExpired:
            return ProbeResult(False, "timed out after 90s (is Claude Code logged in?)")
        took = time.monotonic() - started
        if proc.returncode == 0 and '"is_error":false' in proc.stdout.replace(" ", ""):
            return ProbeResult(True, "Claude Code responded", took)
        return ProbeResult(False, _scrub(proc.stderr or proc.stdout, None), took)

    key, source = find_key(provider)
    if not key:
        names = " / ".join(provider.env_vars)
        return ProbeResult(False, f"no API key found ({names}); add one in Settings")
    try:
        from repo_mirror_kit.harvester.llm.client import LLMClient

        client = LLMClient(
            api_key=key,
            model=model or provider.default_model,
            base_url=provider.base_url,
        )
        client.complete("Reply with exactly: OK", "Say OK.", max_tokens=16)
    except Exception as exc:
        return ProbeResult(
            False,
            f"{type(exc).__name__}: {_scrub(str(exc), key)}",
            time.monotonic() - started,
        )
    return ProbeResult(
        True, f"responded (key from {source})", time.monotonic() - started
    )
