"""Configuration loading and validation for the harvester."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
    """

    repo: str
    ref: str | None = None
    out: Path | None = None
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE_GLOBS
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES
    resume: bool = False
    fail_on_gaps: bool = True
    log_level: str = "info"
    llm_enabled: bool = DEFAULT_LLM_ENABLED
    llm_api_key: str | None = None
    llm_model: str = "claude-sonnet-4-6"

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
        if self.llm_enabled and not self.llm_api_key:
            # BEAN-056: --llm is default-on, so a missing API key must NOT
            # raise — it would break every default invocation. Emit a clear,
            # actionable warning to stderr and silently downgrade
            # llm_enabled to False so the run continues in structural-only
            # mode. Users who don't want the warning can pass --no-llm.
            import sys

            sys.stderr.write(
                "\n"
                "⚠ ANTHROPIC_API_KEY is not set — falling back to "
                "structural-only mode (no LLM enrichment).\n"
                "\n"
                "  Get a key: https://console.anthropic.com/settings/keys\n"
                "  Then run:  export ANTHROPIC_API_KEY=sk-ant-...\n"
                "\n"
                "  To suppress this warning, pass --no-llm.\n"
                "\n"
            )
            object.__setattr__(self, "llm_enabled", False)


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
