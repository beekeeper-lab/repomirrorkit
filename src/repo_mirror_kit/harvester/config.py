"""Configuration loading and validation for the harvester."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from repo_mirror_kit.harvester.providers import is_local_endpoint

DEFAULT_EXCLUDE_GLOBS: tuple[str, ...] = (
    "node_modules",
    "dist",
    "build",
    ".git",
    ".venv",
    "coverage",
    "**/*.min.*",
)

DEFAULT_MAX_FILE_BYTES: int = 1_000_000

# Default cap on the total on-disk size of a cloned working copy (excluding
# ``.git``). 500 MiB is generous for typical repositories but bounded enough
# to prevent runaway behavior from pathological or malicious inputs.
DEFAULT_MAX_TOTAL_BYTES: int = 500 * 1024 * 1024

# BEAN-059: single source of truth for the LLM-enrichment default, shared by
# HarvestConfig and the CLI so programmatic and CLI runs behave identically.
DEFAULT_LLM_ENABLED: bool = True

VALID_LOG_LEVELS: frozenset[str] = frozenset({"debug", "info", "warn", "error"})


DEFAULT_LLM_MODEL = "claude-sonnet-5-5"

VALID_STAGES: tuple[str, ...] = ("A", "B", "C", "C2", "C3", "D", "E", "F", "G")


class ConfigValidationError(Exception):
    """Raised when harvest configuration fails validation."""


@dataclass(frozen=True)
class HarvestConfig:
    """Holds all parsed configuration for a harvest run.

    Args:
        repo: Repository URL to clone and analyze.
        ref: Git ref (branch, tag, or commit SHA) to check out.
        out: Output directory for reports and artifacts.
        include: Glob patterns to include (restricts scanning to matched files).
        exclude: Glob patterns to exclude (added to default excludes).
        max_file_bytes: Maximum file size to process in bytes.
        resume: Whether to resume from a previous incomplete run.
        fail_on_gaps: Whether to fail with exit code 2 if coverage gaps are found.
        log_level: Logging level (debug, info, warn, error).
        llm_enabled: Whether to enable LLM enrichment of surfaces. Defaults
            to on; when ``llm_api_key`` is missing the run downgrades to
            structural-only output with a warning (BEAN-056).
        llm_api_key: Anthropic API key for LLM enrichment. Sourced from the
            ``ANTHROPIC_API_KEY`` environment variable only — there is no CLI
            flag for it, so the key cannot leak into shell history or argv.
        llm_model: Claude model to use for LLM enrichment.
        llm_base_url: Optional base URL override for the Anthropic SDK, used
            to target a local Anthropic-API-compatible endpoint such as
            Ollama. When set, a missing ``llm_api_key`` no longer triggers
            the no-API-key warning/fallback below.
        mirror: Mirror mode (BEAN-080): the output directory must be a
            self-contained requirements package. Requires LLM enrichment and
            an API key (validation fails fast without them), defaults
            ``fail_on_fidelity`` to on, and enables Stage H cleanup.
        keep_source: Skip Stage H cleanup even in mirror mode, preserving
            the cloned working copy. Always wins over ``cleanup``/``mirror``.
        cleanup: Whether Stage H removes ``<out>/repo/`` (including its
            ``.git``) after a fully successful run. ``None`` (the default)
            resolves to ``mirror``; ``__post_init__`` replaces it with a
            concrete bool.
    """

    repo: str
    ref: str | None = None
    out: Path | None = None
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE_GLOBS
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES
    resume: bool = False
    # BEAN-060: force re-run from this stage onward (implies resume).
    from_stage: str | None = None
    fail_on_gaps: bool = True
    # BEAN-076: exit non-zero when fidelity (recreation-readiness) gates
    # fail. ``None`` resolves to ``mirror`` in ``__post_init__`` — off by
    # default while extraction depth is still growing, on in mirror mode.
    fail_on_fidelity: bool | None = None
    log_level: str = "info"
    llm_enabled: bool = DEFAULT_LLM_ENABLED
    # repr=False: a config must never print its key (logs, tracebacks, debuggers).
    llm_api_key: str | None = field(default=None, repr=False)
    llm_model: str = DEFAULT_LLM_MODEL
    llm_base_url: str | None = None
    # BEAN-068: agentic enrichment (read/grep/list tools over the clone).
    llm_agentic: bool = True
    llm_max_turns: int = 8
    llm_budget_usd: float = 5.0
    # "api" (Anthropic SDK; needs a key or local endpoint) or "claude-cli"
    # (headless `claude -p` on the operator's Claude Code login — no API key).
    llm_backend: str = "api"
    llm_concurrency: int = 1
    # Provider id from harvester.providers (anthropic | kimi | deepseek | claude-cli).
    # Fills in endpoint, key lookup and default model when those are not given.
    llm_provider: str | None = None
    # BEAN-080: mirror mode + Stage H cleanup. See SPEC-MIRROR-MODE.md.
    mirror: bool = False
    keep_source: bool = False
    cleanup: bool | None = None

    def _apply_provider(self) -> None:
        _provider_defaults(self)

    def _key_hint(self) -> str:
        return _key_hint_for(self)

    def __post_init__(self) -> None:
        """Validate configuration values after initialization."""
        # Import locally to avoid a top-level circular import: git_ops also
        # ships clone exceptions used elsewhere by config consumers.
        from repo_mirror_kit.harvester.git_ops import (
            GitCloneError,
            validate_clone_url,
        )

        if not self.repo:
            raise ConfigValidationError("--repo is required and cannot be empty")
        try:
            validate_clone_url(self.repo)
        except GitCloneError as exc:
            raise ConfigValidationError(str(exc)) from exc
        if self.llm_max_turns < 1:
            raise ConfigValidationError("--llm-max-turns must be >= 1")
        self._apply_provider()
        if self.llm_backend not in ("api", "claude-cli"):
            raise ConfigValidationError(
                f"Invalid --llm-backend '{self.llm_backend}'. Must be 'api' or 'claude-cli'."
            )
        if not 1 <= self.llm_concurrency <= 8:
            raise ConfigValidationError("--llm-concurrency must be between 1 and 8")
        if self.llm_budget_usd < 0:
            raise ConfigValidationError("--llm-budget-usd must be >= 0")
        if self.from_stage is not None and self.from_stage not in VALID_STAGES:
            raise ConfigValidationError(
                f"Invalid --from-stage '{self.from_stage}'. "
                f"Must be one of: {', '.join(VALID_STAGES)}"
            )
        normalized_level = self.log_level.lower()
        if normalized_level not in VALID_LOG_LEVELS:
            raise ConfigValidationError(
                f"Invalid --log-level '{self.log_level}'. "
                f"Must be one of: {', '.join(sorted(VALID_LOG_LEVELS))}"
            )
        if normalized_level != self.log_level:
            object.__setattr__(self, "log_level", normalized_level)
        if self.max_file_bytes <= 0:
            raise ConfigValidationError(
                f"--max-file-bytes must be positive, got {self.max_file_bytes}"
            )
        if self.max_total_bytes <= 0:
            raise ConfigValidationError(
                f"--max-total-bytes must be positive, got {self.max_total_bytes}"
            )
        # BEAN-080: mirror mode is strict — structural-only output cannot
        # reach mirror grade, so a missing key/CLI/package fails fast (exit 3
        # at the CLI) instead of the BEAN-056 warn-and-degrade below.
        if self.mirror:
            if not self.llm_enabled:
                raise ConfigValidationError(
                    "--mirror requires LLM enrichment; remove --no-llm."
                )
            if self.llm_backend == "claude-cli":
                import shutil

                if shutil.which("claude") is None:
                    raise ConfigValidationError(
                        "--mirror with --llm-backend claude-cli requires the "
                        "`claude` CLI on PATH."
                    )
            else:
                if not self.llm_api_key and not is_local_endpoint(self.llm_base_url):
                    raise ConfigValidationError(
                        "--mirror requires ANTHROPIC_API_KEY to be set (or "
                        "--llm-backend claude-cli / --llm-base-url).\n"
                        "  Get a key: https://console.anthropic.com/settings/keys\n"
                        "  Then run:  export ANTHROPIC_API_KEY=sk-ant-..."
                    )
                from repo_mirror_kit.harvester.llm.client import HAS_ANTHROPIC

                if not HAS_ANTHROPIC:
                    raise ConfigValidationError(
                        "--mirror requires the 'anthropic' package. "
                        "Install it with: uv add anthropic"
                    )
        # Resolve cleanup: explicit --cleanup wins over the mirror default;
        # --keep-source always wins over both.
        effective_cleanup = self.cleanup if self.cleanup is not None else self.mirror
        if self.keep_source:
            effective_cleanup = False
        object.__setattr__(self, "cleanup", effective_cleanup)
        # Resolve fail_on_fidelity: unset → on in mirror mode, off otherwise.
        if self.fail_on_fidelity is None:
            object.__setattr__(self, "fail_on_fidelity", self.mirror)
        if self.llm_enabled and self.llm_backend == "claude-cli":
            import shutil
            import sys

            if shutil.which("claude") is None:
                sys.stderr.write(
                    "\n⚠ --llm-backend claude-cli needs the `claude` CLI on PATH — "
                    "falling back to structural-only mode.\n\n"
                )
                object.__setattr__(self, "llm_enabled", False)
        elif (
            self.llm_enabled
            and not self.llm_api_key
            and not is_local_endpoint(self.llm_base_url)
        ):
            # BEAN-056: --llm is default-on, so a missing API key must NOT
            # raise — it would break every default invocation. Emit a clear,
            # actionable warning to stderr and silently downgrade
            # llm_enabled to False so the run continues in structural-only
            # mode. Users who don't want the warning can pass --no-llm.
            # Exception: when llm_base_url points at a local endpoint (e.g.
            # Ollama), no real API key is required, so skip this fallback.
            import sys

            sys.stderr.write(
                "\n"
                f"⚠ No API key found for {self._key_hint()} — falling back to "
                "structural-only mode (no LLM enrichment).\n"
                "\n"
                "  Get a key: https://console.anthropic.com/settings/keys\n"
                "  Then run:  export ANTHROPIC_API_KEY=sk-ant-...\n"
                "\n"
                "  To suppress this warning, pass --no-llm.\n"
                "\n"
            )
            object.__setattr__(self, "llm_enabled", False)


def _key_hint_for(config: HarvestConfig) -> str:
    from repo_mirror_kit.harvester.providers import PROVIDERS, env_file_path

    provider = PROVIDERS.get(config.llm_provider or "anthropic")
    names = " / ".join(provider.env_vars) if provider else "ANTHROPIC_API_KEY"
    return f"{names} (set it in your environment or in {env_file_path()})"


def _provider_defaults(config: HarvestConfig) -> None:
    """Resolve ``llm_provider`` into backend / endpoint / key / model."""
    from repo_mirror_kit.harvester.providers import PROVIDERS, find_key

    if config.llm_provider is None:
        return
    provider = PROVIDERS.get(config.llm_provider)
    if provider is None:
        raise ConfigValidationError(
            f"Invalid --llm-provider '{config.llm_provider}'. "
            f"Must be one of: {', '.join(PROVIDERS)}"
        )
    if provider.kind == "cli":
        object.__setattr__(config, "llm_backend", "claude-cli")
    else:
        if config.llm_base_url is None and provider.base_url:
            object.__setattr__(config, "llm_base_url", provider.base_url)
        if not config.llm_api_key:
            value, _source = find_key(provider)
            if value:
                object.__setattr__(config, "llm_api_key", value)
    if config.llm_model == DEFAULT_LLM_MODEL and provider.default_model:
        object.__setattr__(config, "llm_model", provider.default_model)


def parse_glob_patterns(value: str) -> tuple[str, ...]:
    """Parse a comma-separated string of glob patterns into a tuple.

    Args:
        value: Comma-separated glob pattern string.

    Returns:
        Tuple of trimmed, non-empty glob patterns.
    """
    return tuple(p.strip() for p in value.split(",") if p.strip())


def merge_exclude_globs(user_excludes: str | None) -> tuple[str, ...]:
    """Merge user-provided exclude patterns with defaults.

    Args:
        user_excludes: Comma-separated user exclude patterns, or None.

    Returns:
        Tuple combining default excludes with any user-provided excludes.
    """
    if not user_excludes:
        return DEFAULT_EXCLUDE_GLOBS
    user_patterns = parse_glob_patterns(user_excludes)
    return DEFAULT_EXCLUDE_GLOBS + user_patterns
