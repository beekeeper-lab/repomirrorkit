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
    """

    repo: str
    ref: str | None = None
    out: Path | None = None
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE_GLOBS
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    resume: bool = False
    fail_on_gaps: bool = True
    log_level: str = "info"

    def __post_init__(self) -> None:
        """Validate configuration values after initialization."""
        if not self.repo:
            raise ConfigValidationError("--repo is required and cannot be empty")
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
