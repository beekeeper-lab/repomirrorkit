"""API endpoint analyzer.

Discovers backend API endpoints across detected frameworks by reading
source files and applying regex-based heuristic extraction.  Produces
``ApiSurface`` objects with HTTP method, path, auth hints, and
request/response type hints.

Supported frameworks:
- Express (``app.get()``, ``router.post()``)
- Fastify (``fastify.get()``, route registration)
- NestJS (``@Get()``, ``@Post()``, ``@Controller('path')``)
- FastAPI (``@app.get()``, ``@router.post()``)
- Flask (``@app.route()``, ``@blueprint.route()``)
- .NET minimal API (``app.MapGet()``, ``app.MapPost()``)
- .NET controllers (``[HttpGet]``, ``[HttpPost]``, ``[Route]``)
- Next.js API routes (``pages/api/`` or ``app/api/`` with exported HTTP methods)
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface, SourceRef
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Framework-to-stack-name mapping
# ---------------------------------------------------------------------------

_EXPRESS_STACKS: frozenset[str] = frozenset({"express"})
_FASTIFY_STACKS: frozenset[str] = frozenset({"fastify"})
_NESTJS_STACKS: frozenset[str] = frozenset({"nestjs"})
_FASTAPI_STACKS: frozenset[str] = frozenset({"fastapi"})
_FLASK_STACKS: frozenset[str] = frozenset({"flask"})
_DOTNET_STACKS: frozenset[str] = frozenset({"aspnet", "dotnet-minimal-api"})
_NEXTJS_STACKS: frozenset[str] = frozenset({"nextjs"})

# ---------------------------------------------------------------------------
# File extension filters
# ---------------------------------------------------------------------------

_JS_TS_EXTENSIONS: frozenset[str] = frozenset({".js", ".ts", ".jsx", ".tsx"})
_PYTHON_EXTENSIONS: frozenset[str] = frozenset({".py"})
_CSHARP_EXTENSIONS: frozenset[str] = frozenset({".cs"})

# ---------------------------------------------------------------------------
# HTTP method constants
# ---------------------------------------------------------------------------

_HTTP_METHODS: frozenset[str] = frozenset(
    {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
)

# ---------------------------------------------------------------------------
# Express / Fastify patterns
# ---------------------------------------------------------------------------

# Matches: app.get('/path', ...), router.post("/path", ...)
# Also handles fastify.get('/path', ...)
_EXPRESS_ROUTE_RE: re.Pattern[str] = re.compile(
    r"""
    (?:app|router|server|fastify)
    \.(?P<method>get|post|put|delete|patch|head|options)
    \s*\(\s*
    (?P<quote>['"`])(?P<path>[^'"`]+)(?P=quote)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Express/Fastify auth middleware hints
_EXPRESS_AUTH_RE: re.Pattern[str] = re.compile(
    r"""
    (?:authenticate|isAuth|requireAuth|ensureAuth|passport\.authenticate
       |verifyToken|authMiddleware|requireLogin|isAuthenticated|auth)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# NestJS patterns
# ---------------------------------------------------------------------------

# Controller decorator: @Controller('path') or @Controller()
_NESTJS_CONTROLLER_RE: re.Pattern[str] = re.compile(
    r"@Controller\(\s*(?:['\"](?P<prefix>[^'\"]*)['\"])?\s*\)"
)

# HTTP method decorators: @Get('path'), @Post(), etc.
_NESTJS_METHOD_RE: re.Pattern[str] = re.compile(
    r"""
    @(?P<method>Get|Post|Put|Delete|Patch|Head|Options)
    \(\s*(?:['\"](?P<path>[^'\"]*)['\"])?\s*\)
    """,
    re.VERBOSE,
)

# NestJS auth guards: @UseGuards(AuthGuard), @UseGuards(JwtAuthGuard)
_NESTJS_AUTH_RE: re.Pattern[str] = re.compile(
    r"@UseGuards\s*\([^)]*(?:Auth|Jwt|Role)[^)]*\)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# FastAPI patterns
# ---------------------------------------------------------------------------

# Matches: @app.get("/path"), @router.post("/path", ...)
_FASTAPI_ROUTE_RE: re.Pattern[str] = re.compile(
    r"""
    @\s*(?:\w+)
    \.(?P<method>get|post|put|delete|patch|head|options)
    \s*\(\s*
    (?P<quote>['"])(?P<path>[^'"]+)(?P=quote)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# FastAPI dependency-based auth hints
_FASTAPI_AUTH_RE: re.Pattern[str] = re.compile(
    r"""
    (?:Depends\s*\(\s*(?:get_current_user|require_auth|verify_token|auth)
       |OAuth2PasswordBearer|HTTPBearer|Security\s*\()
    """,
    re.VERBOSE | re.IGNORECASE,
)

# FastAPI response_model or return type hints
_FASTAPI_RESPONSE_RE: re.Pattern[str] = re.compile(
    r"response_model\s*=\s*(?P<model>\w+)"
)

# ---------------------------------------------------------------------------
# Flask patterns
# ---------------------------------------------------------------------------

# Matches: @app.route('/path'), @blueprint.route('/path', methods=['GET'])
_FLASK_ROUTE_RE: re.Pattern[str] = re.compile(
    r"""
    @\s*(?:\w+)
    \.route\s*\(\s*
    (?P<quote>['"])(?P<path>[^'"]+)(?P=quote)
    (?:\s*,\s*methods\s*=\s*\[(?P<methods>[^\]]+)\])?
    """,
    re.VERBOSE,
)

# Flask auth decorators
_FLASK_AUTH_RE: re.Pattern[str] = re.compile(
    r"@(?:login_required|auth_required|jwt_required|requires_auth)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# .NET minimal API patterns
# ---------------------------------------------------------------------------

# Matches: app.MapGet("/path", ...), app.MapPost("/path", ...)
_DOTNET_MINIMAL_RE: re.Pattern[str] = re.compile(
    r"""
    \.Map(?P<method>Get|Post|Put|Delete|Patch)
    \s*\(\s*
    (?P<quote>["'])(?P<path>[^"']+)(?P=quote)
    """,
    re.VERBOSE,
)

# .NET RequireAuthorization()
_DOTNET_AUTH_RE: re.Pattern[str] = re.compile(
    r"(?:RequireAuthorization|\.Authorize|Authorize\])",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# .NET controller patterns
# ---------------------------------------------------------------------------

# Controller class: [Route("api/[controller]")] or [Route("path")]
_DOTNET_ROUTE_ATTR_RE: re.Pattern[str] = re.compile(
    r'\[Route\(\s*"(?P<prefix>[^"]+)"\s*\)\]'
)

# HTTP method attributes: [HttpGet], [HttpGet("path")], [HttpPost("{id}")]
_DOTNET_HTTP_METHOD_RE: re.Pattern[str] = re.compile(
    r"""
    \[Http(?P<method>Get|Post|Put|Delete|Patch|Head|Options)
    (?:\(\s*"(?P<path>[^"]*)"\s*\))?\]
    """,
    re.VERBOSE,
)

# Controller class name to extract base name
_DOTNET_CONTROLLER_CLASS_RE: re.Pattern[str] = re.compile(
    r"class\s+(?P<name>\w+)Controller\b"
)

# ---------------------------------------------------------------------------
# Next.js API route patterns
# ---------------------------------------------------------------------------

# Exported HTTP method functions in Next.js App Router API routes
_NEXTJS_EXPORT_RE: re.Pattern[str] = re.compile(
    r"""
    export\s+(?:async\s+)?function\s+(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)
    """,
    re.VERBOSE,
)

# Default export in pages/api/ (handles all methods, defaults to handler)
_NEXTJS_DEFAULT_EXPORT_RE: re.Pattern[str] = re.compile(r"export\s+default\b")


# ---------------------------------------------------------------------------
# File reading helper
# ---------------------------------------------------------------------------


def _read_file_safe(path: Path) -> str:
    """Read a file's text content, returning empty string on failure.

    Args:
        path: Absolute path to the file.

    Returns:
        The file content as a string, or empty string on read error.
    """
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Individual framework extractors
# ---------------------------------------------------------------------------


def _extract_express_endpoints(
    workdir: Path,
    inventory: InventoryResult,
) -> list[ApiSurface]:
    """Extract API endpoints from Express/Fastify route definitions.

    Args:
        workdir: Repository root directory.
        inventory: File inventory to scan.

    Returns:
        List of discovered API surfaces.
    """
    surfaces: list[ApiSurface] = []

    for entry in inventory.files:
        ext = PurePosixPath(entry.path).suffix
        if ext not in _JS_TS_EXTENSIONS:
            continue

        content = _read_file_safe(workdir / entry.path)
        if not content:
            continue

        has_auth = bool(_EXPRESS_AUTH_RE.search(content))

        for match in _EXPRESS_ROUTE_RE.finditer(content):
            method = match.group("method").upper()
            path = match.group("path")
            line_num = content[: match.start()].count("\n") + 1

            surfaces.append(
                ApiSurface(
                    name=f"{method} {path}",
                    method=method,
                    path=path,
                    auth="required" if has_auth else "",
                    source_refs=[
                        SourceRef(
                            file_path=entry.path,
                            start_line=line_num,
                        )
                    ],
                )
            )

    return surfaces


def _extract_nestjs_endpoints(
    workdir: Path,
    inventory: InventoryResult,
) -> list[ApiSurface]:
    """Extract API endpoints from NestJS controller decorators.

    Args:
        workdir: Repository root directory.
        inventory: File inventory to scan.

    Returns:
        List of discovered API surfaces.
    """
    surfaces: list[ApiSurface] = []

    for entry in inventory.files:
        if not entry.path.endswith(".ts"):
            continue
        if ".controller." not in entry.path and "controller" not in entry.path.lower():
            continue

        content = _read_file_safe(workdir / entry.path)
        if not content:
            continue

        # Extract controller prefix
        prefix = ""
        ctrl_match = _NESTJS_CONTROLLER_RE.search(content)
        if ctrl_match and ctrl_match.group("prefix"):
            prefix = ctrl_match.group("prefix").strip("/")

        has_auth = bool(_NESTJS_AUTH_RE.search(content))

        for match in _NESTJS_METHOD_RE.finditer(content):
            method = match.group("method").upper()
            sub_path = match.group("path") or ""
            full_path = "/" + "/".join(p for p in [prefix, sub_path.strip("/")] if p)
            line_num = content[: match.start()].count("\n") + 1

            surfaces.append(
                ApiSurface(
                    name=f"{method} {full_path}",
                    method=method,
                    path=full_path,
                    auth="required" if has_auth else "",
                    source_refs=[
                        SourceRef(
                            file_path=entry.path,
                            start_line=line_num,
                        )
                    ],
                )
            )

    return surfaces


def _extract_fastapi_endpoints(
    workdir: Path,
    inventory: InventoryResult,
) -> list[ApiSurface]:
    """Extract API endpoints from FastAPI route decorators.

    Args:
        workdir: Repository root directory.
        inventory: File inventory to scan.

    Returns:
        List of discovered API surfaces.
    """
    surfaces: list[ApiSurface] = []

    for entry in inventory.files:
        ext = PurePosixPath(entry.path).suffix
        if ext not in _PYTHON_EXTENSIONS:
            continue

        content = _read_file_safe(workdir / entry.path)
        if not content:
            continue

        has_auth = bool(_FASTAPI_AUTH_RE.search(content))

        # Extract response model hints
        response_models: dict[int, str] = {}
        for rm_match in _FASTAPI_RESPONSE_RE.finditer(content):
            line = content[: rm_match.start()].count("\n") + 1
            response_models[line] = rm_match.group("model")

        for match in _FASTAPI_ROUTE_RE.finditer(content):
            method = match.group("method").upper()
            path = match.group("path")
            line_num = content[: match.start()].count("\n") + 1

            response_schema: dict[str, Any] = {}
            # Check for response_model on the same or next few lines
            for check_line in range(line_num, line_num + 3):
                if check_line in response_models:
                    response_schema = {"type": response_models[check_line]}
                    break

            surfaces.append(
                ApiSurface(
                    name=f"{method} {path}",
                    method=method,
                    path=path,
                    auth="required" if has_auth else "",
                    response_schema=response_schema,
                    source_refs=[
                        SourceRef(
                            file_path=entry.path,
                            start_line=line_num,
                        )
                    ],
                )
            )

    return surfaces


def _extract_flask_endpoints(
    workdir: Path,
    inventory: InventoryResult,
) -> list[ApiSurface]:
    """Extract API endpoints from Flask route decorators.

    Args:
        workdir: Repository root directory.
        inventory: File inventory to scan.

    Returns:
        List of discovered API surfaces.
    """
    surfaces: list[ApiSurface] = []

    for entry in inventory.files:
        ext = PurePosixPath(entry.path).suffix
        if ext not in _PYTHON_EXTENSIONS:
            continue

        content = _read_file_safe(workdir / entry.path)
        if not content:
            continue

        has_auth = bool(_FLASK_AUTH_RE.search(content))

        for match in _FLASK_ROUTE_RE.finditer(content):
            path = match.group("path")
            methods_str = match.group("methods")
            line_num = content[: match.start()].count("\n") + 1

            if methods_str:
                # Parse methods list: 'GET', 'POST' etc.
                methods = [
                    m.strip().strip("'\"").upper()
                    for m in methods_str.split(",")
                    if m.strip().strip("'\"").upper() in _HTTP_METHODS
                ]
            else:
                methods = ["GET"]

            for method in methods:
                surfaces.append(
                    ApiSurface(
                        name=f"{method} {path}",
                        method=method,
                        path=path,
                        auth="required" if has_auth else "",
                        source_refs=[
                            SourceRef(
                                file_path=entry.path,
                                start_line=line_num,
                            )
                        ],
                    )
                )

    return surfaces


def _extract_dotnet_minimal_endpoints(
    workdir: Path,
    inventory: InventoryResult,
) -> list[ApiSurface]:
    """Extract API endpoints from .NET minimal API ``MapGet``/``MapPost`` calls.

    Args:
        workdir: Repository root directory.
        inventory: File inventory to scan.

    Returns:
        List of discovered API surfaces.
    """
    surfaces: list[ApiSurface] = []

    for entry in inventory.files:
        ext = PurePosixPath(entry.path).suffix
        if ext not in _CSHARP_EXTENSIONS:
            continue

        content = _read_file_safe(workdir / entry.path)
        if not content:
            continue

        has_auth = bool(_DOTNET_AUTH_RE.search(content))

        for match in _DOTNET_MINIMAL_RE.finditer(content):
            method = match.group("method").upper()
            path = match.group("path")
            line_num = content[: match.start()].count("\n") + 1

            surfaces.append(
                ApiSurface(
                    name=f"{method} {path}",
                    method=method,
                    path=path,
                    auth="required" if has_auth else "",
                    source_refs=[
                        SourceRef(
                            file_path=entry.path,
                            start_line=line_num,
                        )
                    ],
                )
            )

    return surfaces


def _extract_dotnet_controller_endpoints(
    workdir: Path,
    inventory: InventoryResult,
) -> list[ApiSurface]:
    """Extract API endpoints from .NET controller attributes.

    Args:
        workdir: Repository root directory.
        inventory: File inventory to scan.

    Returns:
        List of discovered API surfaces.
    """
    surfaces: list[ApiSurface] = []

    for entry in inventory.files:
        ext = PurePosixPath(entry.path).suffix
        if ext not in _CSHARP_EXTENSIONS:
            continue
        if "controller" not in entry.path.lower():
            continue

        content = _read_file_safe(workdir / entry.path)
        if not content:
            continue

        # Extract route prefix from [Route("...")] attribute
        prefix = ""
        route_match = _DOTNET_ROUTE_ATTR_RE.search(content)
        if route_match:
            prefix = route_match.group("prefix")

        # Resolve [controller] placeholder from class name
        class_match = _DOTNET_CONTROLLER_CLASS_RE.search(content)
        if class_match:
            controller_name = class_match.group("name").lower()
            prefix = prefix.replace("[controller]", controller_name)

        has_auth = bool(_DOTNET_AUTH_RE.search(content))

        for match in _DOTNET_HTTP_METHOD_RE.finditer(content):
            method = match.group("method").upper()
            sub_path = match.group("path") or ""
            full_path = "/" + "/".join(
                p for p in [prefix.strip("/"), sub_path.strip("/")] if p
            )
            line_num = content[: match.start()].count("\n") + 1

            surfaces.append(
                ApiSurface(
                    name=f"{method} {full_path}",
                    method=method,
                    path=full_path,
                    auth="required" if has_auth else "",
                    source_refs=[
                        SourceRef(
                            file_path=entry.path,
                            start_line=line_num,
                        )
                    ],
                )
            )

    return surfaces


def _extract_nextjs_api_endpoints(
    workdir: Path,
    inventory: InventoryResult,
) -> list[ApiSurface]:
    """Extract API endpoints from Next.js API route files.

    Handles both Pages Router (``pages/api/``) and App Router (``app/api/``)
    conventions.

    Args:
        workdir: Repository root directory.
        inventory: File inventory to scan.

    Returns:
        List of discovered API surfaces.
    """
    surfaces: list[ApiSurface] = []

    for entry in inventory.files:
        parts = PurePosixPath(entry.path).parts
        ext = PurePosixPath(entry.path).suffix
        if ext not in _JS_TS_EXTENSIONS:
            continue

        # Determine if this is an API route file
        api_path = _resolve_nextjs_api_path(parts)
        if api_path is None:
            continue

        content = _read_file_safe(workdir / entry.path)
        if not content:
            continue

        # App Router: exported named HTTP method functions
        found_named = False
        for match in _NEXTJS_EXPORT_RE.finditer(content):
            method = match.group("method").upper()
            line_num = content[: match.start()].count("\n") + 1
            surfaces.append(
                ApiSurface(
                    name=f"{method} {api_path}",
                    method=method,
                    path=api_path,
                    source_refs=[
                        SourceRef(
                            file_path=entry.path,
                            start_line=line_num,
                        )
                    ],
                )
            )
            found_named = True

        # Pages Router: default export handler (all methods)
        if not found_named and _NEXTJS_DEFAULT_EXPORT_RE.search(content):
            surfaces.append(
                ApiSurface(
                    name=f"ALL {api_path}",
                    method="ALL",
                    path=api_path,
                    source_refs=[
                        SourceRef(file_path=entry.path),
                    ],
                )
            )

    return surfaces


def _resolve_nextjs_api_path(parts: tuple[str, ...]) -> str | None:
    """Convert a Next.js API route file path to an API path.

    Handles ``pages/api/``, ``app/api/``, and ``src/`` prefixed variants.

    Args:
        parts: Path components from PurePosixPath.parts.

    Returns:
        The API path string, or None if not an API route file.
    """
    # Strip optional src/ prefix
    if parts and parts[0] == "src":
        parts = parts[1:]

    if len(parts) < 3:
        return None

    root = parts[0]
    if root not in ("pages", "app"):
        return None
    if parts[1] != "api":
        return None

    # Build path from remaining segments, strip extension from last segment
    segments = list(parts[2:])
    last = PurePosixPath(segments[-1]).stem
    # Skip Next.js special files
    if last in ("route", "index"):
        segments = segments[:-1]
    else:
        segments[-1] = last

    # Convert dynamic segments: [id] -> :id, [...slug] -> :slug
    cleaned: list[str] = []
    for seg in segments:
        if seg.startswith("[") and seg.endswith("]"):
            param = seg[1:-1]
            if param.startswith("..."):
                param = param[3:]
            cleaned.append(f":{param}")
        else:
            cleaned.append(seg)

    return "/api/" + "/".join(cleaned) if cleaned else "/api"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_api_endpoints(
    workdir: Path,
    inventory: InventoryResult,
    profile: StackProfile,
) -> list[ApiSurface]:
    """Analyze repository files and extract API endpoint definitions.

    Only runs extraction strategies for frameworks detected in the
    ``StackProfile``. Each strategy reads relevant source files and
    uses regex-based heuristic parsing to discover endpoints.

    Args:
        workdir: Root of the cloned repository.
        inventory: The file inventory to analyze.
        profile: Detection results indicating which frameworks are present.

    Returns:
        A list of ``ApiSurface`` objects for all discovered endpoints.
    """
    detected_stacks = frozenset(profile.stacks.keys())
    surfaces: list[ApiSurface] = []

    # Express endpoints
    if detected_stacks & _EXPRESS_STACKS:
        found = _extract_express_endpoints(workdir, inventory)
        logger.info("api_analysis_express", endpoints_found=len(found))
        surfaces.extend(found)

    # Fastify endpoints (uses same pattern as Express)
    if detected_stacks & _FASTIFY_STACKS:
        found = _extract_express_endpoints(workdir, inventory)
        logger.info("api_analysis_fastify", endpoints_found=len(found))
        # Avoid duplicates if Express was also detected
        if not (detected_stacks & _EXPRESS_STACKS):
            surfaces.extend(found)

    # NestJS endpoints
    if detected_stacks & _NESTJS_STACKS:
        found = _extract_nestjs_endpoints(workdir, inventory)
        logger.info("api_analysis_nestjs", endpoints_found=len(found))
        surfaces.extend(found)

    # FastAPI endpoints
    if detected_stacks & _FASTAPI_STACKS:
        found = _extract_fastapi_endpoints(workdir, inventory)
        logger.info("api_analysis_fastapi", endpoints_found=len(found))
        surfaces.extend(found)

    # Flask endpoints
    if detected_stacks & _FLASK_STACKS:
        found = _extract_flask_endpoints(workdir, inventory)
        logger.info("api_analysis_flask", endpoints_found=len(found))
        surfaces.extend(found)

    # .NET minimal API
    if "dotnet-minimal-api" in detected_stacks:
        found = _extract_dotnet_minimal_endpoints(workdir, inventory)
        logger.info("api_analysis_dotnet_minimal", endpoints_found=len(found))
        surfaces.extend(found)

    # .NET controllers
    if "aspnet" in detected_stacks:
        found = _extract_dotnet_controller_endpoints(workdir, inventory)
        logger.info("api_analysis_aspnet", endpoints_found=len(found))
        surfaces.extend(found)

    # Next.js API routes
    if detected_stacks & _NEXTJS_STACKS:
        found = _extract_nextjs_api_endpoints(workdir, inventory)
        logger.info("api_analysis_nextjs", endpoints_found=len(found))
        surfaces.extend(found)

    logger.info(
        "api_analysis_complete",
        total_endpoints=len(surfaces),
        frameworks_analyzed=[
            s
            for s in detected_stacks
            if s
            in (
                _EXPRESS_STACKS
                | _FASTIFY_STACKS
                | _NESTJS_STACKS
                | _FASTAPI_STACKS
                | _FLASK_STACKS
                | _DOTNET_STACKS
                | _NEXTJS_STACKS
            )
        ],
    )

    return surfaces
