"""Config & environment variable analyzer.

Extracts configuration references — environment variables, feature flags,
and external service dependencies — from source files, dotenv files,
appsettings.json, and docker-compose.yml, producing ConfigSurface objects
with variable names, defaults, required flags, and usage locations.

Supports: Node.js/TS (process.env), Python (os.environ/os.getenv),
.NET (GetEnvironmentVariable, IConfiguration), dotenv files, and
appsettings.json.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import ConfigSurface, SourceRef
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_MAX_FILE_SIZE = 512_000  # Skip files larger than 512 KB
_MAX_FILES_TO_SCAN = 200  # Cap per category to bound runtime

# ---------------------------------------------------------------------------
# Feature flag and external service naming patterns
# ---------------------------------------------------------------------------

_FEATURE_FLAG_RE: re.Pattern[str] = re.compile(
    r"^(?:FEATURE_|FF_|ENABLE_|DISABLE_|TOGGLE_|FLAG_)"
    r"|_(?:ENABLED|DISABLED|FEATURE|FLAG)$",
)

_EXTERNAL_SERVICE_RE: re.Pattern[str] = re.compile(
    r"(?:DATABASE|DB|REDIS|MONGO|MYSQL|POSTGRES|RABBITMQ|KAFKA|ELASTIC"
    r"|MEMCACHED|SMTP|MAIL|S3|AWS|GCP|AZURE|SENTRY|STRIPE|TWILIO"
    r"|SENDGRID|DATADOG|NEWRELIC|ALGOLIA|FIREBASE)_(?:URL|URI|HOST"
    r"|ENDPOINT|DSN|CONNECTION|CONN)",
    re.IGNORECASE,
)

_EXTERNAL_KEY_RE: re.Pattern[str] = re.compile(
    r"(?:API_KEY|SECRET_KEY|ACCESS_KEY|AUTH_TOKEN|CLIENT_SECRET"
    r"|CLIENT_ID|PRIVATE_KEY|PUBLIC_KEY)$",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Node.js / TypeScript patterns
# ---------------------------------------------------------------------------

_JS_SOURCE_FILE_RE: re.Pattern[str] = re.compile(
    r"\.[jt]sx?$",
)

_PROCESS_ENV_DOT_RE: re.Pattern[str] = re.compile(
    r"process\.env\.([A-Z][A-Z0-9_]*)",
)

_PROCESS_ENV_BRACKET_RE: re.Pattern[str] = re.compile(
    r"""process\.env\[['"]([A-Z][A-Z0-9_]*)['"]\]""",
)

# Capture default: process.env.VAR || 'default' or process.env.VAR ?? 'default'
_JS_DEFAULT_RE: re.Pattern[str] = re.compile(
    r"process\.env\.([A-Z][A-Z0-9_]*)\s*(?:\|\||[?]{2})\s*['\"]([^'\"]*)['\"]",
)

_JS_DEFAULT_BRACKET_RE: re.Pattern[str] = re.compile(
    r"""process\.env\[['"]([A-Z][A-Z0-9_]*)['"]\]\s*(?:\|\||[?]{2})\s*['\"]([^'\"]*)['\"]""",
)

# ---------------------------------------------------------------------------
# Python patterns
# ---------------------------------------------------------------------------

_PY_SOURCE_FILE_RE: re.Pattern[str] = re.compile(
    r"\.py$",
)

_OS_ENVIRON_BRACKET_RE: re.Pattern[str] = re.compile(
    r"""os\.environ\[['"]([A-Za-z_][A-Za-z0-9_]*)['"]\]""",
)

_OS_GETENV_RE: re.Pattern[str] = re.compile(
    r"""os\.getenv\(\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]"""
    r"""(?:\s*,\s*['"]([^'"]*)['"]\s*)?\)""",
)

_OS_ENVIRON_GET_RE: re.Pattern[str] = re.compile(
    r"""os\.environ\.get\(\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]"""
    r"""(?:\s*,\s*['"]([^'"]*)['"]\s*)?\)""",
)

# ---------------------------------------------------------------------------
# .NET patterns
# ---------------------------------------------------------------------------

_DOTNET_SOURCE_FILE_RE: re.Pattern[str] = re.compile(
    r"\.cs$",
)

_DOTNET_GET_ENV_RE: re.Pattern[str] = re.compile(
    r"""Environment\.GetEnvironmentVariable\(\s*"([^"]+)"\s*\)""",
)

_DOTNET_ICONFIG_RE: re.Pattern[str] = re.compile(
    r"""IConfiguration\[['"]([^'"]+)['"]\]""",
)

_DOTNET_CONFIG_BRACKET_RE: re.Pattern[str] = re.compile(
    r"""(?:configuration|config|_config|_configuration)\[['"]([^'"]+)['"]\]""",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Dotenv file patterns
# ---------------------------------------------------------------------------

_DOTENV_FILE_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)\.env(?:\.[a-zA-Z0-9_.-]+)?$",
)

_DOTENV_LINE_RE: re.Pattern[str] = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$",
)

# ---------------------------------------------------------------------------
# appsettings.json pattern
# ---------------------------------------------------------------------------

_APPSETTINGS_FILE_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)appsettings(?:\.[a-zA-Z0-9]+)?\.json$",
)

# ---------------------------------------------------------------------------
# docker-compose environment patterns
# ---------------------------------------------------------------------------

_DOCKER_COMPOSE_FILE_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)(?:docker-compose|compose)(?:\.[a-zA-Z0-9_.-]+)?\.ya?ml$",
)

_DOCKER_ENV_RE: re.Pattern[str] = re.compile(
    r"^\s*-?\s*([A-Z][A-Z0-9_]*)(?:=(.*))?$",
)


# ---------------------------------------------------------------------------
# Internal tracking
# ---------------------------------------------------------------------------


@dataclass
class _EnvVarInfo:
    """Accumulator for a single env var across multiple files."""

    default_value: str | None = None
    has_default: bool = False
    locations: list[str] = field(default_factory=list)
    source_refs: list[SourceRef] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _read_file_safe(path: Path) -> str | None:
    """Read a file's text content, returning None on failure.

    Args:
        path: Absolute path to the file.

    Returns:
        File content as string, or None if unreadable or too large.
    """
    try:
        if path.stat().st_size > _MAX_FILE_SIZE:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _matching_files(
    inventory: InventoryResult,
    pattern: re.Pattern[str],
) -> list[FileEntry]:
    """Return inventory files whose paths match the given regex.

    Args:
        inventory: The file inventory.
        pattern: Regex to match against file paths.

    Returns:
        Matching FileEntry objects, capped at _MAX_FILES_TO_SCAN.
    """
    matches = [f for f in inventory.files if pattern.search(f.path)]
    return matches[:_MAX_FILES_TO_SCAN]


def _classify_var(name: str) -> str:
    """Classify an env var by naming convention.

    Args:
        name: The environment variable name.

    Returns:
        One of 'feature_flag', 'external_service', or 'config'.
    """
    if _FEATURE_FLAG_RE.search(name):
        return "feature_flag"
    if _EXTERNAL_SERVICE_RE.search(name) or _EXTERNAL_KEY_RE.search(name):
        return "external_service"
    return "config"


def _consolidate(
    env_vars: dict[str, _EnvVarInfo],
) -> list[ConfigSurface]:
    """Convert accumulated env var info into deduplicated ConfigSurface list.

    Args:
        env_vars: Mapping of var name to accumulated info.

    Returns:
        Deduplicated list of ConfigSurface objects.
    """
    surfaces: list[ConfigSurface] = []
    for var_name, info in sorted(env_vars.items()):
        classification = _classify_var(var_name)
        surface_name = var_name
        if classification == "feature_flag":
            surface_name = f"flag:{var_name}"
        elif classification == "external_service":
            surface_name = f"service:{var_name}"

        surfaces.append(
            ConfigSurface(
                name=surface_name,
                env_var_name=var_name,
                default_value=info.default_value,
                required=not info.has_default,
                usage_locations=list(dict.fromkeys(info.locations)),
                source_refs=info.source_refs,
            )
        )
    return surfaces


def _record_var(
    env_vars: dict[str, _EnvVarInfo],
    var_name: str,
    file_path: str,
    line_num: int | None,
    default: str | None = None,
) -> None:
    """Record an env var reference, merging with existing entries.

    Args:
        env_vars: Accumulator dict.
        var_name: The env var name.
        file_path: File where the reference was found.
        line_num: Line number of the reference (or None).
        default: Default value if found.
    """
    if var_name not in env_vars:
        env_vars[var_name] = _EnvVarInfo()

    info = env_vars[var_name]
    if file_path not in info.locations:
        info.locations.append(file_path)
    info.source_refs.append(SourceRef(file_path=file_path, start_line=line_num))

    if default is not None:
        info.default_value = default
        info.has_default = True


# ---------------------------------------------------------------------------
# Node.js / TypeScript extraction
# ---------------------------------------------------------------------------


def _extract_js_config(
    inventory: InventoryResult,
    workdir: Path,
) -> dict[str, _EnvVarInfo]:
    """Extract process.env references from JS/TS files.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        Dict of env var name to accumulated info.
    """
    files = _matching_files(inventory, _JS_SOURCE_FILE_RE)
    if not files:
        return {}

    env_vars: dict[str, _EnvVarInfo] = {}

    for entry in files:
        path = workdir / entry.path
        content = _read_file_safe(path)
        if content is None:
            continue

        # Check for defaults first (process.env.VAR || 'val')
        defaults_found: set[str] = set()
        for m in _JS_DEFAULT_RE.finditer(content):
            var_name = m.group(1)
            default_val = m.group(2)
            line_num = content[: m.start()].count("\n") + 1
            _record_var(env_vars, var_name, entry.path, line_num, default_val)
            defaults_found.add(var_name)

        for m in _JS_DEFAULT_BRACKET_RE.finditer(content):
            var_name = m.group(1)
            default_val = m.group(2)
            line_num = content[: m.start()].count("\n") + 1
            _record_var(env_vars, var_name, entry.path, line_num, default_val)
            defaults_found.add(var_name)

        # Then plain references (without duplicating those with defaults)
        for m in _PROCESS_ENV_DOT_RE.finditer(content):
            var_name = m.group(1)
            if var_name not in defaults_found:
                line_num = content[: m.start()].count("\n") + 1
                _record_var(env_vars, var_name, entry.path, line_num)

        for m in _PROCESS_ENV_BRACKET_RE.finditer(content):
            var_name = m.group(1)
            if var_name not in defaults_found:
                line_num = content[: m.start()].count("\n") + 1
                _record_var(env_vars, var_name, entry.path, line_num)

    return env_vars


# ---------------------------------------------------------------------------
# Python extraction
# ---------------------------------------------------------------------------


def _extract_python_config(
    inventory: InventoryResult,
    workdir: Path,
) -> dict[str, _EnvVarInfo]:
    """Extract os.environ/os.getenv references from Python files.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        Dict of env var name to accumulated info.
    """
    files = _matching_files(inventory, _PY_SOURCE_FILE_RE)
    if not files:
        return {}

    env_vars: dict[str, _EnvVarInfo] = {}

    for entry in files:
        path = workdir / entry.path
        content = _read_file_safe(path)
        if content is None:
            continue

        # os.environ["VAR"] — no default, always required
        for m in _OS_ENVIRON_BRACKET_RE.finditer(content):
            var_name = m.group(1)
            line_num = content[: m.start()].count("\n") + 1
            _record_var(env_vars, var_name, entry.path, line_num)

        # os.getenv("VAR", "default") — may have default
        for m in _OS_GETENV_RE.finditer(content):
            var_name = m.group(1)
            default_val = m.group(2)  # None if no default arg
            line_num = content[: m.start()].count("\n") + 1
            _record_var(env_vars, var_name, entry.path, line_num, default_val)

        # os.environ.get("VAR", "default") — may have default
        for m in _OS_ENVIRON_GET_RE.finditer(content):
            var_name = m.group(1)
            default_val = m.group(2)
            line_num = content[: m.start()].count("\n") + 1
            _record_var(env_vars, var_name, entry.path, line_num, default_val)

    return env_vars


# ---------------------------------------------------------------------------
# .NET extraction
# ---------------------------------------------------------------------------


def _extract_dotnet_config(
    inventory: InventoryResult,
    workdir: Path,
) -> dict[str, _EnvVarInfo]:
    """Extract environment and configuration references from .NET files.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        Dict of env var name to accumulated info.
    """
    files = _matching_files(inventory, _DOTNET_SOURCE_FILE_RE)
    if not files:
        return {}

    env_vars: dict[str, _EnvVarInfo] = {}

    for entry in files:
        path = workdir / entry.path
        content = _read_file_safe(path)
        if content is None:
            continue

        # Environment.GetEnvironmentVariable("VAR")
        for m in _DOTNET_GET_ENV_RE.finditer(content):
            var_name = m.group(1)
            line_num = content[: m.start()].count("\n") + 1
            _record_var(env_vars, var_name, entry.path, line_num)

        # IConfiguration["section:key"] or config["key"]
        for m in _DOTNET_ICONFIG_RE.finditer(content):
            key = m.group(1)
            line_num = content[: m.start()].count("\n") + 1
            _record_var(env_vars, key, entry.path, line_num)

        for m in _DOTNET_CONFIG_BRACKET_RE.finditer(content):
            key = m.group(1)
            line_num = content[: m.start()].count("\n") + 1
            _record_var(env_vars, key, entry.path, line_num)

    return env_vars


# ---------------------------------------------------------------------------
# Dotenv file extraction
# ---------------------------------------------------------------------------


def _extract_dotenv(
    inventory: InventoryResult,
    workdir: Path,
) -> dict[str, _EnvVarInfo]:
    """Extract env vars from .env files.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        Dict of env var name to accumulated info.
    """
    files = _matching_files(inventory, _DOTENV_FILE_RE)
    if not files:
        return {}

    env_vars: dict[str, _EnvVarInfo] = {}

    for entry in files:
        path = workdir / entry.path
        content = _read_file_safe(path)
        if content is None:
            continue

        is_example = ".env.example" in entry.path or ".env.sample" in entry.path

        for i, line in enumerate(content.splitlines(), start=1):
            # Skip comments and empty lines
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            m = _DOTENV_LINE_RE.match(line)
            if m:
                var_name = m.group(1)
                raw_value = m.group(2).strip()

                # Strip surrounding quotes
                if len(raw_value) >= 2 and raw_value[0] in ('"', "'"):
                    if raw_value[-1] == raw_value[0]:
                        raw_value = raw_value[1:-1]

                # Example files: value is a placeholder, not a real default
                if is_example:
                    default = None
                else:
                    default = raw_value if raw_value else None

                _record_var(env_vars, var_name, entry.path, i, default)

    return env_vars


# ---------------------------------------------------------------------------
# appsettings.json extraction
# ---------------------------------------------------------------------------


def _flatten_json(
    data: dict[str, object],
    prefix: str = "",
) -> list[tuple[str, str | None]]:
    """Flatten nested JSON into colon-separated keys.

    Args:
        data: JSON dict to flatten.
        prefix: Current key prefix.

    Returns:
        List of (key, value_or_none) tuples.
    """
    items: list[tuple[str, str | None]] = []
    for key, value in data.items():
        full_key = f"{prefix}:{key}" if prefix else key
        if isinstance(value, dict):
            items.extend(_flatten_json(value, full_key))
        else:
            str_val = str(value) if value is not None else None
            items.append((full_key, str_val))
    return items


def _extract_appsettings(
    inventory: InventoryResult,
    workdir: Path,
) -> dict[str, _EnvVarInfo]:
    """Extract configuration keys from appsettings.json files.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        Dict of config key to accumulated info.
    """
    files = _matching_files(inventory, _APPSETTINGS_FILE_RE)
    if not files:
        return {}

    env_vars: dict[str, _EnvVarInfo] = {}

    for entry in files:
        path = workdir / entry.path
        content = _read_file_safe(path)
        if content is None:
            continue

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            logger.warning("appsettings_parse_error", file=entry.path)
            continue

        if not isinstance(data, dict):
            continue

        for key, value in _flatten_json(data):
            _record_var(env_vars, key, entry.path, None, value)

    return env_vars


# ---------------------------------------------------------------------------
# docker-compose environment extraction
# ---------------------------------------------------------------------------


def _extract_docker_compose_env(
    inventory: InventoryResult,
    workdir: Path,
) -> dict[str, _EnvVarInfo]:
    """Extract env vars from docker-compose environment sections.

    Uses simple line-based parsing to find environment variable definitions.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        Dict of env var name to accumulated info.
    """
    files = _matching_files(inventory, _DOCKER_COMPOSE_FILE_RE)
    if not files:
        return {}

    env_vars: dict[str, _EnvVarInfo] = {}

    for entry in files:
        path = workdir / entry.path
        content = _read_file_safe(path)
        if content is None:
            continue

        in_environment = False
        for i, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()

            # Detect environment: section
            if stripped == "environment:" or stripped.startswith("environment:"):
                in_environment = True
                continue

            # Exit environment section on next top-level key
            if (
                in_environment
                and stripped
                and not stripped.startswith("-")
                and ":" in stripped
            ):
                indent = len(line) - len(line.lstrip())
                if indent <= 4 and not stripped.startswith("-"):
                    in_environment = False
                    continue

            if in_environment:
                m = _DOCKER_ENV_RE.match(stripped)
                if m:
                    var_name = m.group(1)
                    raw_value = m.group(2)
                    default = raw_value.strip() if raw_value else None
                    _record_var(env_vars, var_name, entry.path, i, default)

    return env_vars


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_config(
    inventory: InventoryResult,
    profile: StackProfile,
    workdir: Path,
) -> list[ConfigSurface]:
    """Extract config and env var patterns from a repository.

    Examines files matching detected frameworks and common config file formats,
    then consolidates results into deduplicated ConfigSurface objects.

    Args:
        inventory: The scanned file inventory.
        profile: Stack detection profile indicating which frameworks are present.
        workdir: Root directory of the repository checkout.

    Returns:
        A list of ConfigSurface objects found in the repository.
    """
    detected = set(profile.stacks.keys())
    all_vars: dict[str, _EnvVarInfo] = {}

    # Framework-specific extractors — only run for detected stacks
    _framework_extractors: list[
        tuple[set[str], Callable[[InventoryResult, Path], dict[str, _EnvVarInfo]]]
    ] = [
        (
            {"express", "fastify", "nextjs", "nestjs", "react", "vue", "svelte"},
            _extract_js_config,
        ),
        ({"fastapi", "flask"}, _extract_python_config),
        ({"aspnet", "dotnet-minimal-api"}, _extract_dotnet_config),
    ]

    for stack_names, extractor in _framework_extractors:
        if detected & stack_names:
            framework = next(iter(detected & stack_names))
            logger.info("config_analysis_starting", framework=framework)
            results = extractor(inventory, workdir)
            _merge_vars(all_vars, results)
            logger.info(
                "config_analysis_complete",
                framework=framework,
                vars_found=len(results),
            )

    # Framework-agnostic extractors — always run
    _agnostic_extractors: list[
        tuple[str, Callable[[InventoryResult, Path], dict[str, _EnvVarInfo]]]
    ] = [
        ("dotenv", _extract_dotenv),
        ("appsettings", _extract_appsettings),
        ("docker-compose", _extract_docker_compose_env),
    ]

    for source_name, extractor in _agnostic_extractors:
        logger.info("config_analysis_starting", source=source_name)
        results = extractor(inventory, workdir)
        _merge_vars(all_vars, results)
        logger.info(
            "config_analysis_complete",
            source=source_name,
            vars_found=len(results),
        )

    surfaces = _consolidate(all_vars)
    logger.info("config_analysis_total", total_surfaces=len(surfaces))
    return surfaces


def _merge_vars(
    target: dict[str, _EnvVarInfo],
    source: dict[str, _EnvVarInfo],
) -> None:
    """Merge source env var info into target, consolidating duplicates.

    Args:
        target: The accumulator dict to merge into.
        source: New entries to merge.
    """
    for var_name, info in source.items():
        if var_name not in target:
            target[var_name] = info
        else:
            existing = target[var_name]
            for loc in info.locations:
                if loc not in existing.locations:
                    existing.locations.append(loc)
            existing.source_refs.extend(info.source_refs)
            if info.has_default and not existing.has_default:
                existing.default_value = info.default_value
                existing.has_default = True
