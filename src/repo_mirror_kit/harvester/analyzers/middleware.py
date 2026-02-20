"""Middleware and pipeline analyzer for web frameworks.

Discovers middleware registrations and pipeline configurations by scanning
source files for framework-specific patterns.  Produces ``MiddlewareSurface``
objects with middleware type, execution order hints, and scope information.

Supported frameworks:
- Express / Koa (app.use, router.use)
- Django (MIDDLEWARE setting)
- FastAPI (Depends, @app.middleware)
- Flask (@app.before_request, @app.after_request)
- ASP.NET (app.Use*, UseRouting, UseAuthentication, etc.)
- Python decorators used as middleware (@app.middleware)

Uses heuristic-based extraction (pattern matching, not full AST) per spec v1.
"""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import MiddlewareSurface, SourceRef
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# Extensions scanned for middleware patterns.
_JS_TS_EXTENSIONS: frozenset[str] = frozenset({".js", ".jsx", ".ts", ".tsx"})
_PY_EXTENSIONS: frozenset[str] = frozenset({".py"})
_ALL_EXTENSIONS: frozenset[str] = _JS_TS_EXTENSIONS | _PY_EXTENSIONS

_MAX_FILE_READ_BYTES: int = 512_000  # 500 KB limit for heuristic scanning.

# ---------------------------------------------------------------------------
# Express / Koa patterns
# ---------------------------------------------------------------------------

# app.use(middlewareName) or app.use('/path', middleware)
_EXPRESS_APP_USE_RE = re.compile(
    r"""(?:app|router|server)\.use\s*\(\s*(?:["']([^"']+)["']\s*,\s*)?(\w+)""",
)

# Koa-style: app.use(async (ctx, next) => { ... })
_KOA_INLINE_USE_RE = re.compile(
    r"""(?:app|router)\.use\s*\(\s*(?:async\s+)?\(""",
)

# ---------------------------------------------------------------------------
# Django patterns
# ---------------------------------------------------------------------------

# MIDDLEWARE = [ 'django.middleware.security.SecurityMiddleware', ... ]
_DJANGO_MIDDLEWARE_RE = re.compile(
    r"""MIDDLEWARE\s*=\s*\[([^\]]+)\]""",
    re.DOTALL,
)

# Individual middleware string entries.
_DJANGO_MW_ENTRY_RE = re.compile(
    r"""["']([^"']+)["']""",
)

# ---------------------------------------------------------------------------
# FastAPI / Starlette patterns
# ---------------------------------------------------------------------------

# Depends(some_dependency)
_FASTAPI_DEPENDS_RE = re.compile(
    r"""Depends\s*\(\s*(\w+)""",
)

# @app.middleware("http")
_FASTAPI_MIDDLEWARE_DECORATOR_RE = re.compile(
    r"""@\s*(?:app|router)\.middleware\s*\(\s*["'](\w+)["']\s*\)""",
)

# app.add_middleware(CORSMiddleware, ...)
_FASTAPI_ADD_MIDDLEWARE_RE = re.compile(
    r"""(?:app|router)\.add_middleware\s*\(\s*(\w+)""",
)

# ---------------------------------------------------------------------------
# Flask patterns
# ---------------------------------------------------------------------------

# @app.before_request, @app.after_request, @app.teardown_request
_FLASK_HOOK_RE = re.compile(
    r"""@\s*(?:app|blueprint|bp)\.(\w+_request)\s*""",
)

# ---------------------------------------------------------------------------
# ASP.NET patterns
# ---------------------------------------------------------------------------

# app.UseRouting(), app.UseAuthentication(), etc.
_ASPNET_USE_RE = re.compile(
    r"""(?:app|builder)\.Use(\w+)\s*\(""",
)

# ---------------------------------------------------------------------------
# Settings / config file patterns
# ---------------------------------------------------------------------------

_SETTINGS_FILENAMES: frozenset[str] = frozenset(
    {
        "settings.py",
        "config.py",
        "conf.py",
        "django_settings.py",
    }
)


def analyze_middleware(
    inventory: InventoryResult,
    profile: StackProfile,
    workdir: Path | None = None,
) -> list[MiddlewareSurface]:
    """Discover middleware registrations across the repository.

    Scans source files for Express/Koa ``app.use()``, Django ``MIDDLEWARE``
    settings, FastAPI ``Depends()`` and ``add_middleware()``, Flask request
    hooks, and ASP.NET ``Use*`` pipeline methods.

    Args:
        inventory: The scanned file inventory.
        profile: Detection results identifying which stacks are present.
        workdir: Repository working directory for reading file contents.

    Returns:
        A list of ``MiddlewareSurface`` objects, one per discovered
        middleware registration.
    """
    if workdir is None:
        logger.debug("middleware_skipped", reason="no_workdir")
        return []

    surfaces: list[MiddlewareSurface] = []

    for entry in inventory.files:
        if entry.extension not in _ALL_EXTENSIONS:
            continue

        content = _read_file_safe(workdir / entry.path)
        if content is None:
            continue

        if entry.extension in _JS_TS_EXTENSIONS:
            surfaces.extend(_scan_express_koa(content, entry.path))
            surfaces.extend(_scan_aspnet(content, entry.path))

        if entry.extension in _PY_EXTENSIONS:
            surfaces.extend(_scan_django(content, entry.path))
            surfaces.extend(_scan_fastapi(content, entry.path))
            surfaces.extend(_scan_flask(content, entry.path))

    logger.info("middleware_analysis_complete", total_surfaces=len(surfaces))
    return surfaces


# ---------------------------------------------------------------------------
# Framework-specific scanners
# ---------------------------------------------------------------------------


def _scan_express_koa(content: str, file_path: str) -> list[MiddlewareSurface]:
    """Scan JS/TS content for Express or Koa middleware registrations.

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``MiddlewareSurface`` objects for discovered middleware.
    """
    surfaces: list[MiddlewareSurface] = []
    order = 0

    for match in _EXPRESS_APP_USE_RE.finditer(content):
        route_path = match.group(1) or "*"
        mw_name = match.group(2)
        order += 1
        surfaces.append(
            MiddlewareSurface(
                name=f"express:{mw_name}",
                middleware_type="express",
                execution_order=order,
                applies_to=[route_path],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # Detect inline Koa-style middleware that wasn't caught above.
    for match in _KOA_INLINE_USE_RE.finditer(content):
        # Skip if already matched by Express pattern at same offset.
        already_matched = any(
            s.source_refs
            and s.source_refs[0].start_line
            == _line_number(content, match.start())
            for s in surfaces
        )
        if already_matched:
            continue
        order += 1
        surfaces.append(
            MiddlewareSurface(
                name=f"koa:inline:{file_path}:{order}",
                middleware_type="koa",
                execution_order=order,
                applies_to=["*"],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    return surfaces


def _scan_django(content: str, file_path: str) -> list[MiddlewareSurface]:
    """Scan Python content for Django MIDDLEWARE settings.

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``MiddlewareSurface`` objects for discovered middleware.
    """
    surfaces: list[MiddlewareSurface] = []

    for block_match in _DJANGO_MIDDLEWARE_RE.finditer(content):
        block = block_match.group(1)
        order = 0
        for entry_match in _DJANGO_MW_ENTRY_RE.finditer(block):
            mw_dotpath = entry_match.group(1)
            mw_short_name = mw_dotpath.rsplit(".", maxsplit=1)[-1]
            order += 1
            surfaces.append(
                MiddlewareSurface(
                    name=f"django:{mw_short_name}",
                    middleware_type="django",
                    execution_order=order,
                    applies_to=["*"],
                    transforms=[mw_dotpath],
                    source_refs=[
                        SourceRef(
                            file_path=file_path,
                            start_line=_line_number(
                                content,
                                block_match.start() + entry_match.start(),
                            ),
                        )
                    ],
                )
            )

    return surfaces


def _scan_fastapi(content: str, file_path: str) -> list[MiddlewareSurface]:
    """Scan Python content for FastAPI/Starlette middleware patterns.

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``MiddlewareSurface`` objects for discovered middleware.
    """
    surfaces: list[MiddlewareSurface] = []

    # Depends() — dependency injection as middleware
    for match in _FASTAPI_DEPENDS_RE.finditer(content):
        dep_name = match.group(1)
        surfaces.append(
            MiddlewareSurface(
                name=f"fastapi:depends:{dep_name}",
                middleware_type="fastapi_depends",
                applies_to=["*"],
                transforms=[dep_name],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # @app.middleware("http")
    for match in _FASTAPI_MIDDLEWARE_DECORATOR_RE.finditer(content):
        protocol = match.group(1)
        surfaces.append(
            MiddlewareSurface(
                name=f"fastapi:middleware:{protocol}:{file_path}",
                middleware_type="fastapi_decorator",
                applies_to=["*"],
                transforms=[protocol],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # app.add_middleware(CORSMiddleware, ...)
    for match in _FASTAPI_ADD_MIDDLEWARE_RE.finditer(content):
        mw_name = match.group(1)
        surfaces.append(
            MiddlewareSurface(
                name=f"fastapi:{mw_name}",
                middleware_type="fastapi_class",
                applies_to=["*"],
                transforms=[mw_name],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    return surfaces


def _scan_flask(content: str, file_path: str) -> list[MiddlewareSurface]:
    """Scan Python content for Flask request hook decorators.

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``MiddlewareSurface`` objects for discovered middleware.
    """
    surfaces: list[MiddlewareSurface] = []

    for match in _FLASK_HOOK_RE.finditer(content):
        hook_type = match.group(1)
        surfaces.append(
            MiddlewareSurface(
                name=f"flask:{hook_type}:{file_path}",
                middleware_type="flask_hook",
                applies_to=["*"],
                transforms=[hook_type],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    return surfaces


def _scan_aspnet(content: str, file_path: str) -> list[MiddlewareSurface]:
    """Scan content for ASP.NET middleware pipeline Use* patterns.

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``MiddlewareSurface`` objects for discovered middleware.
    """
    surfaces: list[MiddlewareSurface] = []
    order = 0

    for match in _ASPNET_USE_RE.finditer(content):
        mw_name = match.group(1)
        order += 1
        surfaces.append(
            MiddlewareSurface(
                name=f"aspnet:Use{mw_name}",
                middleware_type="aspnet",
                execution_order=order,
                applies_to=["*"],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    return surfaces


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_file_safe(file_path: Path) -> str | None:
    """Read a file's text content safely, returning None on failure.

    Args:
        file_path: Absolute path to the file to read.

    Returns:
        The file content as a string, or None if reading failed.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        if len(content) > _MAX_FILE_READ_BYTES:
            logger.debug(
                "middleware_file_too_large",
                path=str(file_path),
                size=len(content),
            )
            return None
        return content
    except OSError:
        logger.debug("middleware_file_read_failed", path=str(file_path))
        return None


def _line_number(content: str, char_offset: int) -> int:
    """Calculate the 1-based line number for a character offset.

    Args:
        content: The full file content.
        char_offset: Zero-based character position.

    Returns:
        The 1-based line number.
    """
    return content[:char_offset].count("\n") + 1
