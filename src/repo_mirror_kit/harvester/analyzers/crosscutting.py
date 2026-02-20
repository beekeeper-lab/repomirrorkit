"""Cross-cutting concerns analyzer.

Identifies logging, error handling, telemetry, background job, and
deployment patterns in a repository.  Produces ``CrosscuttingSurface``
objects categorized by concern type.

Concern categories:
- **logging**: Logger initialization, structured logging config, log levels.
- **error-handling**: Global error handlers, error boundaries, custom error classes.
- **telemetry**: Metrics libraries, tracing setup, health check endpoints.
- **jobs**: Queue definitions, cron configs, worker patterns.
- **deployment**: Dockerfile, docker-compose, Kubernetes manifests, CI/CD config.
"""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    CrosscuttingSurface,
    SourceRef,
)
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_MAX_FILE_SIZE = 512_000  # Skip files larger than 512 KB
_MAX_FILES_PER_CATEGORY = 300  # Cap per concern category to bound runtime

# ---------------------------------------------------------------------------
# Logging patterns
# ---------------------------------------------------------------------------

_LOGGING_FILE_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)(?:logger|logging|log)[./]"
    r"|\.(?:py|js|ts|jsx|tsx|cs|go|rb|java)$",
    re.IGNORECASE,
)

_LOGGING_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Python
    ("python:logging", re.compile(r"\bimport\s+logging\b")),
    ("python:structlog", re.compile(r"\bimport\s+structlog\b")),
    ("python:loguru", re.compile(r"\bfrom\s+loguru\s+import\b")),
    ("python:getLogger", re.compile(r"\blogging\.getLogger\s*\(")),
    # Node / JS / TS
    ("node:winston", re.compile(r"\b(?:require|import).*['\"]winston['\"]")),
    ("node:pino", re.compile(r"\b(?:require|import).*['\"]pino['\"]")),
    ("node:bunyan", re.compile(r"\b(?:require|import).*['\"]bunyan['\"]")),
    ("node:morgan", re.compile(r"\b(?:require|import).*['\"]morgan['\"]")),
    ("node:log4js", re.compile(r"\b(?:require|import).*['\"]log4js['\"]")),
    ("node:console", re.compile(r"\bconsole\.(?:log|warn|error|info|debug)\s*\(")),
    # .NET
    ("dotnet:ILogger", re.compile(r"\bILogger(?:<\w+>)?\b")),
    ("dotnet:Serilog", re.compile(r"\bSerilog\b")),
    ("dotnet:NLog", re.compile(r"\bNLog\b")),
    ("dotnet:Log4Net", re.compile(r"\blog4net\b", re.IGNORECASE)),
    # Go
    ("go:log", re.compile(r"\b(?:log|logrus|zap|zerolog)\.")),
    # Java
    ("java:slf4j", re.compile(r"\bLoggerFactory\.getLogger\s*\(")),
    ("java:log4j", re.compile(r"\bLog(?:Manager|4j)\b")),
]

# ---------------------------------------------------------------------------
# Error handling patterns
# ---------------------------------------------------------------------------

_ERROR_HANDLING_FILE_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)(?:error|exception|handler|middleware|boundary)"
    r"|\.(?:py|js|ts|jsx|tsx|cs|go|rb|java)$",
    re.IGNORECASE,
)

_ERROR_HANDLING_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # React error boundaries
    (
        "react:ErrorBoundary",
        re.compile(r"\bcomponentDidCatch\b|\bErrorBoundary\b"),
    ),
    # Express / Node global handlers
    (
        "express:errorMiddleware",
        re.compile(
            r"(?:app|router)\.use\s*\(\s*(?:function\s*)?\("
            r"\s*err\s*,\s*req\s*,\s*res\s*,\s*next\s*\)"
        ),
    ),
    (
        "node:uncaughtException",
        re.compile(
            r"process\.on\s*\(\s*['\"]"
            r"(?:uncaughtException|unhandledRejection)['\"]"
        ),
    ),
    # Python global handlers
    (
        "python:sys.excepthook",
        re.compile(r"\bsys\.excepthook\b"),
    ),
    (
        "python:custom_exception",
        re.compile(
            r"class\s+\w+(?:Error|Exception)\s*\(\s*(?:Exception|BaseException)\s*\)"
        ),
    ),
    (
        "python:error_handler",
        re.compile(r"@\w+\.(?:errorhandler|exception_handler)\s*\("),
    ),
    # .NET exception handling
    (
        "dotnet:ExceptionHandler",
        re.compile(r"\bUseExceptionHandler\b|\bExceptionFilterAttribute\b"),
    ),
    (
        "dotnet:GlobalExceptionFilter",
        re.compile(r"\bIExceptionFilter\b|\bExceptionFilter\b"),
    ),
    # NestJS
    (
        "nestjs:ExceptionFilter",
        re.compile(r"@Catch\s*\(|implements\s+ExceptionFilter"),
    ),
    # Generic custom error classes (JS/TS)
    (
        "js:customError",
        re.compile(r"class\s+\w+Error\s+extends\s+Error\b"),
    ),
]

# ---------------------------------------------------------------------------
# Telemetry / Observability patterns
# ---------------------------------------------------------------------------

_TELEMETRY_FILE_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)(?:metrics|telemetry|tracing|monitoring|observability|health|instrument)"
    r"|\.(?:py|js|ts|jsx|tsx|cs|go|rb|java)$",
    re.IGNORECASE,
)

_TELEMETRY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # OpenTelemetry
    (
        "opentelemetry",
        re.compile(r"\b(?:opentelemetry|@opentelemetry|otel)\b", re.IGNORECASE),
    ),
    # Prometheus
    (
        "prometheus",
        re.compile(r"\b(?:prom-client|prometheus_client|PrometheusMetrics)\b"),
    ),
    # Datadog
    (
        "datadog",
        re.compile(r"\b(?:dd-trace|datadog|ddtrace)\b", re.IGNORECASE),
    ),
    # New Relic
    (
        "newrelic",
        re.compile(r"\b(?:newrelic|new_relic|@newrelic)\b", re.IGNORECASE),
    ),
    # Sentry
    (
        "sentry",
        re.compile(r"\b(?:@sentry|sentry_sdk|Sentry\.init|Sentry\.captureException)\b"),
    ),
    # Jaeger / Zipkin tracing
    (
        "distributed_tracing",
        re.compile(r"\b(?:jaeger|zipkin|opentracing)\b", re.IGNORECASE),
    ),
    # Health check endpoints
    (
        "health_check",
        re.compile(
            r"""(?:['\"/]health['\"/]|['\"/]healthz['\"/]"""
            r"""|['\"/]ready['\"/]|['\"/]readiness['\"/])""",
        ),
    ),
    # StatsD
    (
        "statsd",
        re.compile(r"\b(?:statsd|StatsD|hot-shots)\b", re.IGNORECASE),
    ),
    # .NET health checks
    (
        "dotnet:HealthChecks",
        re.compile(r"\bAddHealthChecks\b|\bMapHealthChecks\b"),
    ),
    # Application Insights
    (
        "appinsights",
        re.compile(r"\b(?:ApplicationInsights|appinsights|TelemetryClient)\b"),
    ),
]

# ---------------------------------------------------------------------------
# Background job patterns
# ---------------------------------------------------------------------------

_JOBS_FILE_RE: re.Pattern[str] = re.compile(
    r"(?:^|/)(?:jobs?|workers?|queues?|tasks?|cron|scheduler|background)"
    r"|\.(?:py|js|ts|jsx|tsx|cs|go|rb|java)$"
    r"|crontab"
    r"|Procfile$",
    re.IGNORECASE,
)

_JOBS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Node queues
    ("node:bull", re.compile(r"\b(?:require|import).*['\"](?:bull|bullmq)['\"]")),
    ("node:agenda", re.compile(r"\b(?:require|import).*['\"]agenda['\"]")),
    ("node:bee-queue", re.compile(r"\b(?:require|import).*['\"]bee-queue['\"]")),
    ("node:node-cron", re.compile(r"\b(?:require|import).*['\"]node-cron['\"]")),
    # Python workers
    (
        "python:celery",
        re.compile(r"\b(?:from\s+celery|import\s+celery|@app\.task|@shared_task)\b"),
    ),
    ("python:rq", re.compile(r"\bfrom\s+rq\s+import\b|\bQueue\s*\(")),
    (
        "python:apscheduler",
        re.compile(r"\b(?:APScheduler|BackgroundScheduler|AsyncIOScheduler)\b"),
    ),
    ("python:dramatiq", re.compile(r"\b(?:import\s+dramatiq|@dramatiq\.actor)\b")),
    ("python:huey", re.compile(r"\bfrom\s+huey\s+import\b")),
    # .NET background
    (
        "dotnet:BackgroundService",
        re.compile(r"\bBackgroundService\b|\bIHostedService\b"),
    ),
    ("dotnet:Hangfire", re.compile(r"\bHangfire\b")),
    ("dotnet:Quartz", re.compile(r"\bQuartz\b.*(?:IJob|IScheduler)")),
    # Ruby
    ("ruby:sidekiq", re.compile(r"\b(?:Sidekiq|include\s+Sidekiq::Worker)\b")),
    ("ruby:delayed_job", re.compile(r"\bDelayedJob\b|\bhandle_asynchronously\b")),
    # Go
    ("go:asynq", re.compile(r"\b(?:asynq)\.")),
    # Cron patterns
    ("cron", re.compile(r"\bcron(?:tab|job)?\b", re.IGNORECASE)),
    # Procfile workers
    ("procfile:worker", re.compile(r"^worker:", re.MULTILINE)),
]

# ---------------------------------------------------------------------------
# Deployment patterns
# ---------------------------------------------------------------------------

_DEPLOYMENT_FILE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Docker
    ("docker:dockerfile", re.compile(r"(?:^|/)Dockerfile(?:\.\w+)?$")),
    ("docker:compose", re.compile(r"(?:^|/)(?:docker-)?compose(?:\.\w+)?\.ya?ml$")),
    ("docker:dockerignore", re.compile(r"(?:^|/)\.dockerignore$")),
    # Kubernetes
    (
        "k8s:manifest",
        re.compile(
            r"(?:^|/)(?:k8s|kubernetes|manifests?|deploy)/"
            r".*\.ya?ml$"
        ),
    ),
    (
        "k8s:helm",
        re.compile(r"(?:^|/)(?:Chart|values)\.ya?ml$|(?:^|/)templates/.*\.ya?ml$"),
    ),
    ("k8s:kustomize", re.compile(r"(?:^|/)kustomization\.ya?ml$")),
    # CI/CD
    ("ci:github-actions", re.compile(r"(?:^|/)\.github/workflows/.*\.ya?ml$")),
    ("ci:gitlab-ci", re.compile(r"(?:^|/)\.gitlab-ci\.ya?ml$")),
    ("ci:jenkins", re.compile(r"(?:^|/)Jenkinsfile$")),
    ("ci:circleci", re.compile(r"(?:^|/)\.circleci/config\.ya?ml$")),
    ("ci:azure-pipelines", re.compile(r"(?:^|/)azure-pipelines\.ya?ml$")),
    ("ci:travis", re.compile(r"(?:^|/)\.travis\.ya?ml$")),
    ("ci:bitbucket", re.compile(r"(?:^|/)bitbucket-pipelines\.ya?ml$")),
    # Terraform / IaC
    ("iac:terraform", re.compile(r"(?:^|/).*\.tf$")),
    ("iac:pulumi", re.compile(r"(?:^|/)Pulumi\.ya?ml$")),
    # Platform config
    ("platform:vercel", re.compile(r"(?:^|/)vercel\.json$")),
    ("platform:netlify", re.compile(r"(?:^|/)netlify\.toml$")),
    ("platform:heroku", re.compile(r"(?:^|/)Procfile$|(?:^|/)app\.json$")),
    ("platform:fly", re.compile(r"(?:^|/)fly\.toml$")),
    ("platform:render", re.compile(r"(?:^|/)render\.ya?ml$")),
]

# Content patterns for deployment files that need content inspection
_DEPLOYMENT_CONTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("k8s:deployment", re.compile(r"kind:\s*Deployment\b")),
    ("k8s:service", re.compile(r"kind:\s*Service\b")),
    ("k8s:ingress", re.compile(r"kind:\s*Ingress\b")),
    ("k8s:configmap", re.compile(r"kind:\s*ConfigMap\b")),
    ("k8s:secret", re.compile(r"kind:\s*Secret\b")),
    ("docker:multistage", re.compile(r"^FROM\s+.+\s+AS\s+", re.MULTILINE)),
]


# ---------------------------------------------------------------------------
# File reading helper
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


# ---------------------------------------------------------------------------
# Category extractors
# ---------------------------------------------------------------------------


def _extract_logging(
    inventory: InventoryResult,
    workdir: Path,
) -> list[CrosscuttingSurface]:
    """Extract logging infrastructure patterns.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        CrosscuttingSurface objects for detected logging patterns.
    """
    found_patterns: dict[str, list[str]] = {}  # pattern_name -> [file_paths]

    files_scanned = 0
    for entry in inventory.files:
        if files_scanned >= _MAX_FILES_PER_CATEGORY:
            break
        if not _LOGGING_FILE_RE.search(entry.path):
            continue

        content = _read_file_safe(workdir / entry.path)
        if content is None:
            continue

        files_scanned += 1

        for pattern_name, pattern_re in _LOGGING_PATTERNS:
            if pattern_re.search(content):
                if pattern_name not in found_patterns:
                    found_patterns[pattern_name] = []
                if entry.path not in found_patterns[pattern_name]:
                    found_patterns[pattern_name].append(entry.path)

    if not found_patterns:
        return []

    # Aggregate into a single surface per logging library/framework
    all_affected: list[str] = []
    descriptions: list[str] = []
    refs: list[SourceRef] = []
    for pattern_name, file_paths in sorted(found_patterns.items()):
        descriptions.append(pattern_name)
        for fp in file_paths:
            if fp not in all_affected:
                all_affected.append(fp)
                refs.append(SourceRef(file_path=fp))

    return [
        CrosscuttingSurface(
            name="logging",
            concern_type="logging",
            description=", ".join(descriptions),
            affected_files=all_affected,
            source_refs=refs,
        )
    ]


def _extract_error_handling(
    inventory: InventoryResult,
    workdir: Path,
) -> list[CrosscuttingSurface]:
    """Extract error handling patterns.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        CrosscuttingSurface objects for detected error handling patterns.
    """
    found_patterns: dict[str, list[str]] = {}

    files_scanned = 0
    for entry in inventory.files:
        if files_scanned >= _MAX_FILES_PER_CATEGORY:
            break
        if not _ERROR_HANDLING_FILE_RE.search(entry.path):
            continue

        content = _read_file_safe(workdir / entry.path)
        if content is None:
            continue

        files_scanned += 1

        for pattern_name, pattern_re in _ERROR_HANDLING_PATTERNS:
            if pattern_re.search(content):
                if pattern_name not in found_patterns:
                    found_patterns[pattern_name] = []
                if entry.path not in found_patterns[pattern_name]:
                    found_patterns[pattern_name].append(entry.path)

    if not found_patterns:
        return []

    all_affected: list[str] = []
    descriptions: list[str] = []
    refs: list[SourceRef] = []
    for pattern_name, file_paths in sorted(found_patterns.items()):
        descriptions.append(pattern_name)
        for fp in file_paths:
            if fp not in all_affected:
                all_affected.append(fp)
                refs.append(SourceRef(file_path=fp))

    return [
        CrosscuttingSurface(
            name="error_handling",
            concern_type="error-handling",
            description=", ".join(descriptions),
            affected_files=all_affected,
            source_refs=refs,
        )
    ]


def _extract_telemetry(
    inventory: InventoryResult,
    workdir: Path,
) -> list[CrosscuttingSurface]:
    """Extract observability and telemetry patterns.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        CrosscuttingSurface objects for detected telemetry patterns.
    """
    found_patterns: dict[str, list[str]] = {}

    files_scanned = 0
    for entry in inventory.files:
        if files_scanned >= _MAX_FILES_PER_CATEGORY:
            break
        if not _TELEMETRY_FILE_RE.search(entry.path):
            continue

        content = _read_file_safe(workdir / entry.path)
        if content is None:
            continue

        files_scanned += 1

        for pattern_name, pattern_re in _TELEMETRY_PATTERNS:
            if pattern_re.search(content):
                if pattern_name not in found_patterns:
                    found_patterns[pattern_name] = []
                if entry.path not in found_patterns[pattern_name]:
                    found_patterns[pattern_name].append(entry.path)

    if not found_patterns:
        return []

    all_affected: list[str] = []
    descriptions: list[str] = []
    refs: list[SourceRef] = []
    for pattern_name, file_paths in sorted(found_patterns.items()):
        descriptions.append(pattern_name)
        for fp in file_paths:
            if fp not in all_affected:
                all_affected.append(fp)
                refs.append(SourceRef(file_path=fp))

    return [
        CrosscuttingSurface(
            name="telemetry",
            concern_type="telemetry",
            description=", ".join(descriptions),
            affected_files=all_affected,
            source_refs=refs,
        )
    ]


def _extract_jobs(
    inventory: InventoryResult,
    workdir: Path,
) -> list[CrosscuttingSurface]:
    """Extract background job and worker patterns.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        CrosscuttingSurface objects for detected job/worker patterns.
    """
    found_patterns: dict[str, list[str]] = {}

    files_scanned = 0
    for entry in inventory.files:
        if files_scanned >= _MAX_FILES_PER_CATEGORY:
            break
        if not _JOBS_FILE_RE.search(entry.path):
            continue

        content = _read_file_safe(workdir / entry.path)
        if content is None:
            continue

        files_scanned += 1

        for pattern_name, pattern_re in _JOBS_PATTERNS:
            if pattern_re.search(content):
                if pattern_name not in found_patterns:
                    found_patterns[pattern_name] = []
                if entry.path not in found_patterns[pattern_name]:
                    found_patterns[pattern_name].append(entry.path)

    if not found_patterns:
        return []

    all_affected: list[str] = []
    descriptions: list[str] = []
    refs: list[SourceRef] = []
    for pattern_name, file_paths in sorted(found_patterns.items()):
        descriptions.append(pattern_name)
        for fp in file_paths:
            if fp not in all_affected:
                all_affected.append(fp)
                refs.append(SourceRef(file_path=fp))

    return [
        CrosscuttingSurface(
            name="background_jobs",
            concern_type="jobs",
            description=", ".join(descriptions),
            affected_files=all_affected,
            source_refs=refs,
        )
    ]


def _extract_deployment(
    inventory: InventoryResult,
    workdir: Path,
) -> list[CrosscuttingSurface]:
    """Extract deployment configuration patterns.

    Args:
        inventory: The file inventory.
        workdir: Repository root.

    Returns:
        CrosscuttingSurface objects for detected deployment patterns.
    """
    found_patterns: dict[str, list[str]] = {}

    # First pass: match by file path patterns
    for entry in inventory.files:
        for pattern_name, pattern_re in _DEPLOYMENT_FILE_PATTERNS:
            if pattern_re.search(entry.path):
                if pattern_name not in found_patterns:
                    found_patterns[pattern_name] = []
                if entry.path not in found_patterns[pattern_name]:
                    found_patterns[pattern_name].append(entry.path)

    # Second pass: inspect content for k8s resource types and Docker features
    yaml_files = [e for e in inventory.files if e.path.endswith((".yml", ".yaml"))]
    dockerfile_files = [e for e in inventory.files if "Dockerfile" in e.path]
    content_files = yaml_files + dockerfile_files

    for entry in content_files[:_MAX_FILES_PER_CATEGORY]:
        content = _read_file_safe(workdir / entry.path)
        if content is None:
            continue

        for pattern_name, pattern_re in _DEPLOYMENT_CONTENT_PATTERNS:
            if pattern_re.search(content):
                if pattern_name not in found_patterns:
                    found_patterns[pattern_name] = []
                if entry.path not in found_patterns[pattern_name]:
                    found_patterns[pattern_name].append(entry.path)

    if not found_patterns:
        return []

    all_affected: list[str] = []
    descriptions: list[str] = []
    refs: list[SourceRef] = []
    for pattern_name, file_paths in sorted(found_patterns.items()):
        descriptions.append(pattern_name)
        for fp in file_paths:
            if fp not in all_affected:
                all_affected.append(fp)
                refs.append(SourceRef(file_path=fp))

    return [
        CrosscuttingSurface(
            name="deployment",
            concern_type="deployment",
            description=", ".join(descriptions),
            affected_files=all_affected,
            source_refs=refs,
        )
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_crosscutting(
    inventory: InventoryResult,
    workdir: Path,
) -> list[CrosscuttingSurface]:
    """Analyze repository files for cross-cutting concern patterns.

    Scans the file inventory for logging, error handling, telemetry,
    background job, and deployment patterns.  Each detected category
    produces one ``CrosscuttingSurface`` object.

    Args:
        inventory: The scanned file inventory.
        workdir: Root directory of the repository checkout.

    Returns:
        A list of CrosscuttingSurface objects for all detected concerns.
    """
    surfaces: list[CrosscuttingSurface] = []

    extractors = [
        ("logging", _extract_logging),
        ("error-handling", _extract_error_handling),
        ("telemetry", _extract_telemetry),
        ("jobs", _extract_jobs),
        ("deployment", _extract_deployment),
    ]

    for category, extractor in extractors:
        logger.info("crosscutting_analysis_starting", category=category)
        results = extractor(inventory, workdir)
        surfaces.extend(results)
        logger.info(
            "crosscutting_analysis_complete",
            category=category,
            surfaces_found=len(results),
        )

    logger.info("crosscutting_analysis_total", total_surfaces=len(surfaces))
    return surfaces
