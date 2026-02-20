"""Route and page analyzer for frontend frameworks.

Discovers UI routes across detected frontend frameworks by examining file
structure and configuration files.  Produces ``RouteSurface`` objects with
path, associated components, and source references.

Supported frameworks:
- Next.js (pages/ and app/ routers)
- React Router (configuration file parsing)
- Vue Router (router/index.{js,ts} parsing)
- SvelteKit (src/routes/ file structure)

Uses heuristic-based extraction (pattern matching, not full AST) per spec v1.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import RouteSurface, SourceRef
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# Extensions used for route files across JS/TS frameworks.
_JS_TS_EXTENSIONS: frozenset[str] = frozenset({".js", ".jsx", ".ts", ".tsx"})

# Next.js roots: project root or src/ prefix.
_NEXTJS_ROOTS: tuple[str, ...] = ("", "src/")

# Next.js special pages that are not routes themselves.
_NEXTJS_SPECIAL_STEMS: frozenset[str] = frozenset(
    {"_app", "_document", "_error", "_middleware"}
)

# Next.js App Router convention files that define a page route.
_APP_ROUTER_PAGE_STEMS: frozenset[str] = frozenset({"page"})

# SvelteKit route file that defines a page.
_SVELTEKIT_PAGE_FILE: str = "+page.svelte"

# Regex patterns for dynamic route segments across frameworks.
_DYNAMIC_SEGMENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\[\.{3}(\w+)\]"),  # Next.js catch-all: [...slug]
    re.compile(r"\[(\w+)\]"),  # Next.js / SvelteKit: [id]
    re.compile(r":(\w+)"),  # React Router / Vue Router: :id
    re.compile(r"\{(\w+)\}"),  # Generic: {slug}
)

# React Router route definition patterns (heuristic).
_REACT_ROUTE_RE = re.compile(
    r"""<Route\s+[^>]*?path\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# React Router v6 object-style route definitions.
_REACT_ROUTE_OBJECT_RE = re.compile(
    r"""path\s*:\s*["']([^"']+)["']""",
)

# Vue Router route definition patterns (heuristic).
_VUE_ROUTE_RE = re.compile(
    r"""path\s*:\s*["']([^"']+)["']""",
)

# Files commonly containing React Router configuration.
_REACT_ROUTER_FILENAMES: frozenset[str] = frozenset(
    {
        "routes.js",
        "routes.ts",
        "routes.tsx",
        "routes.jsx",
        "router.js",
        "router.ts",
        "router.tsx",
        "router.jsx",
        "App.tsx",
        "App.jsx",
        "App.js",
    }
)

# Vue Router configuration file paths.
_VUE_ROUTER_PATHS: frozenset[str] = frozenset(
    {
        "router/index.js",
        "router/index.ts",
        "src/router/index.js",
        "src/router/index.ts",
    }
)

_MAX_FILE_READ_BYTES: int = 512_000  # 500 KB limit for heuristic scanning.


def analyze_routes(
    inventory: InventoryResult,
    profile: StackProfile,
    workdir: Path | None = None,
) -> list[RouteSurface]:
    """Discover UI routes across all detected frontend frameworks.

    Examines the ``StackProfile`` to determine which frameworks are present
    and applies the appropriate extraction strategy for each.

    Args:
        inventory: The scanned file inventory.
        profile: Detection results identifying which stacks are present.
        workdir: Repository working directory for reading file contents.
            Required for React Router and Vue Router config parsing.

    Returns:
        A list of ``RouteSurface`` objects, one per discovered route.
    """
    routes: list[RouteSurface] = []
    stacks = profile.stacks

    if "nextjs" in stacks:
        nextjs_routes = _extract_nextjs_routes(inventory)
        routes.extend(nextjs_routes)
        logger.info("routes_extracted", framework="nextjs", count=len(nextjs_routes))

    if "react" in stacks and "nextjs" not in stacks:
        react_routes = _extract_react_router_routes(inventory, workdir)
        routes.extend(react_routes)
        logger.info("routes_extracted", framework="react", count=len(react_routes))

    if "vue" in stacks:
        vue_routes = _extract_vue_router_routes(inventory, workdir)
        routes.extend(vue_routes)
        logger.info("routes_extracted", framework="vue", count=len(vue_routes))

    if "sveltekit" in stacks:
        svelte_routes = _extract_sveltekit_routes(inventory)
        routes.extend(svelte_routes)
        logger.info("routes_extracted", framework="sveltekit", count=len(svelte_routes))

    logger.info("route_analysis_complete", total_routes=len(routes))
    return routes


# ---------------------------------------------------------------------------
# Next.js: pages/ router
# ---------------------------------------------------------------------------


def _extract_nextjs_routes(inventory: InventoryResult) -> list[RouteSurface]:
    """Extract routes from Next.js pages/ and app/ directory structures.

    Args:
        inventory: The scanned file inventory.

    Returns:
        A list of RouteSurface objects for discovered Next.js routes.
    """
    routes: list[RouteSurface] = []

    for entry in inventory.files:
        if entry.extension not in _JS_TS_EXTENSIONS:
            continue

        path_obj = PurePosixPath(entry.path)
        parts = path_obj.parts

        # Check pages/ router (root or src/)
        pages_route = _try_nextjs_pages_route(entry.path, parts)
        if pages_route is not None:
            routes.append(pages_route)
            continue

        # Check app/ router (root or src/)
        app_route = _try_nextjs_app_route(entry.path, parts)
        if app_route is not None:
            routes.append(app_route)

    return routes


def _try_nextjs_pages_route(
    file_path: str, parts: tuple[str, ...]
) -> RouteSurface | None:
    """Try to interpret a file as a Next.js pages/ route.

    Args:
        file_path: Repository-relative file path.
        parts: Tuple of path components.

    Returns:
        A RouteSurface if the file is a valid pages/ route, else None.
    """
    # Determine the pages-relative path segments.
    pages_parts: tuple[str, ...] | None = None

    if len(parts) >= 2 and parts[0] == "pages":
        pages_parts = parts[1:]
    elif len(parts) >= 3 and parts[0] == "src" and parts[1] == "pages":
        pages_parts = parts[2:]

    if pages_parts is None:
        return None

    # Skip api/ routes (handled by API analyzer).
    if pages_parts and pages_parts[0] == "api":
        logger.debug("route_skipped", path=file_path, reason="api_route")
        return None

    stem = PurePosixPath(file_path).stem

    # Skip special pages.
    if stem in _NEXTJS_SPECIAL_STEMS:
        logger.debug("route_skipped", path=file_path, reason="special_page")
        return None

    # Build the route path from the pages-relative segments.
    route_path = _pages_parts_to_route(pages_parts, stem)

    return RouteSurface(
        name=f"nextjs:{route_path}",
        path=route_path,
        method="GET",
        source_refs=[SourceRef(file_path=file_path)],
        component_refs=[file_path],
    )


def _pages_parts_to_route(pages_parts: tuple[str, ...], stem: str) -> str:
    """Convert pages-relative path parts to a URL route.

    ``pages/about.tsx`` → ``/about``
    ``pages/blog/[slug].tsx`` → ``/blog/[slug]``
    ``pages/index.tsx`` → ``/``

    Args:
        pages_parts: Path parts relative to the pages/ directory.
        stem: File stem (without extension).

    Returns:
        The URL route path.
    """
    # Build directory segments (everything except the filename).
    segments: list[str] = list(pages_parts[:-1])

    # Add the file stem unless it is "index".
    if stem != "index":
        segments.append(stem)

    if not segments:
        return "/"

    return "/" + "/".join(segments)


# ---------------------------------------------------------------------------
# Next.js: app/ router
# ---------------------------------------------------------------------------


def _try_nextjs_app_route(
    file_path: str, parts: tuple[str, ...]
) -> RouteSurface | None:
    """Try to interpret a file as a Next.js app/ router page.

    Only files named ``page.{js,jsx,ts,tsx}`` define routes in the app
    router.

    Args:
        file_path: Repository-relative file path.
        parts: Tuple of path components.

    Returns:
        A RouteSurface if the file is a valid app/ page route, else None.
    """
    stem = PurePosixPath(file_path).stem
    if stem not in _APP_ROUTER_PAGE_STEMS:
        return None

    # Determine app-relative path segments.
    app_parts: tuple[str, ...] | None = None

    if len(parts) >= 2 and parts[0] == "app":
        app_parts = parts[1:]
    elif len(parts) >= 3 and parts[0] == "src" and parts[1] == "app":
        app_parts = parts[2:]

    if app_parts is None:
        return None

    # Skip api/ routes.
    if app_parts and app_parts[0] == "api":
        logger.debug("route_skipped", path=file_path, reason="api_route")
        return None

    # Build route from directory segments (exclude the filename itself).
    dir_segments = list(app_parts[:-1])

    # Filter out route groups (parenthesized segments like (auth)).
    dir_segments = [s for s in dir_segments if not _is_route_group(s)]

    if not dir_segments:
        route_path = "/"
    else:
        route_path = "/" + "/".join(dir_segments)

    return RouteSurface(
        name=f"nextjs:{route_path}",
        path=route_path,
        method="GET",
        source_refs=[SourceRef(file_path=file_path)],
        component_refs=[file_path],
    )


def _is_route_group(segment: str) -> bool:
    """Check if a directory segment is a Next.js route group.

    Route groups are wrapped in parentheses, e.g. ``(auth)``, and do
    not contribute to the URL path.

    Args:
        segment: A single path segment.

    Returns:
        True if the segment is a route group.
    """
    return segment.startswith("(") and segment.endswith(")")


# ---------------------------------------------------------------------------
# React Router
# ---------------------------------------------------------------------------


def _extract_react_router_routes(
    inventory: InventoryResult,
    workdir: Path | None,
) -> list[RouteSurface]:
    """Extract routes from React Router configuration files.

    Scans files with common React Router naming patterns for ``<Route>``
    JSX elements and object-style route definitions.

    Args:
        inventory: The scanned file inventory.
        workdir: Repository working directory for reading file contents.

    Returns:
        A list of RouteSurface objects for discovered React routes.
    """
    if workdir is None:
        logger.debug("route_extraction_skipped", reason="no_workdir", framework="react")
        return []

    routes: list[RouteSurface] = []

    for entry in inventory.files:
        if entry.extension not in _JS_TS_EXTENSIONS:
            continue

        filename = PurePosixPath(entry.path).name
        if filename not in _REACT_ROUTER_FILENAMES:
            continue

        content = _read_file_safe(workdir / entry.path)
        if content is None:
            continue

        # Look for <Route path="..." /> patterns.
        for match in _REACT_ROUTE_RE.finditer(content):
            route_path = match.group(1)
            routes.append(
                RouteSurface(
                    name=f"react:{route_path}",
                    path=route_path,
                    method="GET",
                    source_refs=[
                        SourceRef(
                            file_path=entry.path,
                            start_line=_line_number(content, match.start()),
                        )
                    ],
                    component_refs=[entry.path],
                )
            )

        # Look for object-style route definitions { path: "/..." }.
        # Only if no JSX routes were found in this file to avoid duplicates.
        if not any(r.source_refs[0].file_path == entry.path for r in routes):
            for match in _REACT_ROUTE_OBJECT_RE.finditer(content):
                route_path = match.group(1)
                # Skip paths that look like non-route config (e.g. "react").
                if not route_path.startswith("/"):
                    continue
                routes.append(
                    RouteSurface(
                        name=f"react:{route_path}",
                        path=route_path,
                        method="GET",
                        source_refs=[
                            SourceRef(
                                file_path=entry.path,
                                start_line=_line_number(content, match.start()),
                            )
                        ],
                        component_refs=[entry.path],
                    )
                )

    return routes


# ---------------------------------------------------------------------------
# Vue Router
# ---------------------------------------------------------------------------


def _extract_vue_router_routes(
    inventory: InventoryResult,
    workdir: Path | None,
) -> list[RouteSurface]:
    """Extract routes from Vue Router configuration files.

    Scans ``router/index.{js,ts}`` for route path definitions.

    Args:
        inventory: The scanned file inventory.
        workdir: Repository working directory for reading file contents.

    Returns:
        A list of RouteSurface objects for discovered Vue routes.
    """
    if workdir is None:
        logger.debug("route_extraction_skipped", reason="no_workdir", framework="vue")
        return []

    routes: list[RouteSurface] = []

    for entry in inventory.files:
        if entry.path not in _VUE_ROUTER_PATHS:
            continue

        content = _read_file_safe(workdir / entry.path)
        if content is None:
            continue

        for match in _VUE_ROUTE_RE.finditer(content):
            route_path = match.group(1)
            # Skip paths that don't look like routes.
            if not route_path.startswith("/"):
                continue
            routes.append(
                RouteSurface(
                    name=f"vue:{route_path}",
                    path=route_path,
                    method="GET",
                    source_refs=[
                        SourceRef(
                            file_path=entry.path,
                            start_line=_line_number(content, match.start()),
                        )
                    ],
                    component_refs=[entry.path],
                )
            )

    return routes


# ---------------------------------------------------------------------------
# SvelteKit
# ---------------------------------------------------------------------------


def _extract_sveltekit_routes(
    inventory: InventoryResult,
) -> list[RouteSurface]:
    """Extract routes from SvelteKit src/routes/ directory structure.

    SvelteKit uses ``+page.svelte`` files within the ``src/routes/``
    directory to define routes.

    Args:
        inventory: The scanned file inventory.

    Returns:
        A list of RouteSurface objects for discovered SvelteKit routes.
    """
    routes: list[RouteSurface] = []

    for entry in inventory.files:
        filename = PurePosixPath(entry.path).name
        if filename != _SVELTEKIT_PAGE_FILE:
            continue

        parts = PurePosixPath(entry.path).parts

        # Find the "routes" directory in the path.
        route_parts = _sveltekit_route_parts(parts)
        if route_parts is None:
            logger.debug("route_skipped", path=entry.path, reason="not_in_routes_dir")
            continue

        # Build route from directory segments (exclude the filename).
        # Filter out SvelteKit group segments (parenthesized).
        dir_segments = [s for s in route_parts if not _is_route_group(s)]

        if not dir_segments:
            route_path = "/"
        else:
            route_path = "/" + "/".join(dir_segments)

        routes.append(
            RouteSurface(
                name=f"sveltekit:{route_path}",
                path=route_path,
                method="GET",
                source_refs=[SourceRef(file_path=entry.path)],
                component_refs=[entry.path],
            )
        )

    return routes


def _sveltekit_route_parts(parts: tuple[str, ...]) -> list[str] | None:
    """Extract the route-relative directory segments from a SvelteKit path.

    Looks for a ``routes`` directory in the path and returns the segments
    between ``routes/`` and the filename.

    Args:
        parts: Tuple of path components.

    Returns:
        The directory segments relative to ``routes/``, or None if the
        path is not under a ``routes/`` directory.
    """
    try:
        routes_idx = list(parts).index("routes")
    except ValueError:
        return None

    # Everything between routes/ and the filename.
    return list(parts[routes_idx + 1 : -1])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_dynamic_segments(route_path: str) -> list[str]:
    """Extract dynamic segment names from a route path.

    Recognizes Next.js ``[id]``, ``[...slug]``, React Router ``:id``,
    and generic ``{slug}`` patterns.

    Args:
        route_path: The URL route path.

    Returns:
        A list of dynamic segment parameter names.
    """
    segments: list[str] = []
    for pattern in _DYNAMIC_SEGMENT_PATTERNS:
        for match in pattern.finditer(route_path):
            name = match.group(1)
            if name not in segments:
                segments.append(name)
    return segments


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
                "route_file_too_large",
                path=str(file_path),
                size=len(content),
            )
            return None
        return content
    except OSError:
        logger.debug("route_file_read_failed", path=str(file_path))
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
