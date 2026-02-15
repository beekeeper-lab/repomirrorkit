"""Unit tests for the route and page analyzer."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.routes import (
    _extract_dynamic_segments,
    _extract_nextjs_routes,
    _extract_react_router_routes,
    _extract_sveltekit_routes,
    _extract_vue_router_routes,
    _is_route_group,
    _line_number,
    _pages_parts_to_route,
    analyze_routes,
)
from repo_mirror_kit.harvester.analyzers.surfaces import RouteSurface
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory(paths: list[str]) -> InventoryResult:
    """Build an InventoryResult from a list of file paths."""
    files = [
        FileEntry(
            path=p,
            size=100,
            extension=_ext(p),
            hash="abc123",
            category="source",
        )
        for p in paths
    ]
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=100 * len(files),
        total_skipped=0,
    )


def _ext(path: str) -> str:
    """Extract file extension from a path."""
    dot = path.rfind(".")
    if dot == -1:
        return ""
    return path[dot:]


def _make_profile(stacks: dict[str, float]) -> StackProfile:
    """Build a StackProfile with given stacks."""
    return StackProfile(stacks=stacks, evidence={}, signals=[])


# ---------------------------------------------------------------------------
# Next.js pages/ router
# ---------------------------------------------------------------------------


class TestNextjsPagesRouter:
    """Tests for Next.js pages/ directory route extraction."""

    def test_basic_page_route(self) -> None:
        inventory = _make_inventory(["pages/about.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/about"
        assert routes[0].method == "GET"

    def test_index_page_is_root(self) -> None:
        inventory = _make_inventory(["pages/index.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/"

    def test_nested_page_route(self) -> None:
        inventory = _make_inventory(["pages/blog/post.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/blog/post"

    def test_dynamic_segment(self) -> None:
        inventory = _make_inventory(["pages/blog/[slug].tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/blog/[slug]"

    def test_catch_all_route(self) -> None:
        inventory = _make_inventory(["pages/docs/[...path].tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/docs/[...path]"

    def test_nested_index_page(self) -> None:
        inventory = _make_inventory(["pages/dashboard/index.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/dashboard"

    def test_src_pages_prefix(self) -> None:
        inventory = _make_inventory(["src/pages/about.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/about"

    def test_skips_special_pages(self) -> None:
        inventory = _make_inventory(
            [
                "pages/_app.tsx",
                "pages/_document.tsx",
                "pages/_error.tsx",
                "pages/about.tsx",
            ]
        )
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/about"

    def test_skips_api_routes(self) -> None:
        inventory = _make_inventory(
            [
                "pages/api/users.ts",
                "pages/about.tsx",
            ]
        )
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/about"

    def test_skips_non_js_files(self) -> None:
        inventory = _make_inventory(
            [
                "pages/about.tsx",
                "pages/styles.css",
                "pages/data.json",
            ]
        )
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/about"

    def test_multiple_extensions(self) -> None:
        inventory = _make_inventory(
            [
                "pages/home.js",
                "pages/about.jsx",
                "pages/contact.ts",
                "pages/faq.tsx",
            ]
        )
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 4
        paths = {r.path for r in routes}
        assert paths == {"/home", "/about", "/contact", "/faq"}

    def test_source_refs_populated(self) -> None:
        inventory = _make_inventory(["pages/about.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes[0].source_refs) == 1
        assert routes[0].source_refs[0].file_path == "pages/about.tsx"

    def test_component_refs_populated(self) -> None:
        inventory = _make_inventory(["pages/about.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert routes[0].component_refs == ["pages/about.tsx"]

    def test_route_name_format(self) -> None:
        inventory = _make_inventory(["pages/about.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert routes[0].name == "nextjs:/about"

    def test_surface_type(self) -> None:
        inventory = _make_inventory(["pages/about.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert routes[0].surface_type == "route"


# ---------------------------------------------------------------------------
# Next.js app/ router
# ---------------------------------------------------------------------------


class TestNextjsAppRouter:
    """Tests for Next.js app/ directory route extraction."""

    def test_root_page(self) -> None:
        inventory = _make_inventory(["app/page.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/"

    def test_nested_page(self) -> None:
        inventory = _make_inventory(["app/dashboard/page.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/dashboard"

    def test_deeply_nested_page(self) -> None:
        inventory = _make_inventory(["app/dashboard/settings/page.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/dashboard/settings"

    def test_dynamic_segment(self) -> None:
        inventory = _make_inventory(["app/blog/[slug]/page.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/blog/[slug]"

    def test_route_group_excluded(self) -> None:
        inventory = _make_inventory(["app/(auth)/login/page.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/login"

    def test_src_app_prefix(self) -> None:
        inventory = _make_inventory(["src/app/about/page.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/about"

    def test_skips_layout_files(self) -> None:
        inventory = _make_inventory(
            [
                "app/layout.tsx",
                "app/page.tsx",
            ]
        )
        routes = _extract_nextjs_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/"

    def test_skips_api_routes(self) -> None:
        inventory = _make_inventory(
            [
                "app/api/users/route.ts",
                "app/about/page.tsx",
            ]
        )
        routes = _extract_nextjs_routes(inventory)

        # api/users/route.ts is skipped, about/page.tsx is kept
        assert len(routes) == 1
        assert routes[0].path == "/about"

    def test_name_format(self) -> None:
        inventory = _make_inventory(["app/dashboard/page.tsx"])
        routes = _extract_nextjs_routes(inventory)

        assert routes[0].name == "nextjs:/dashboard"


# ---------------------------------------------------------------------------
# React Router
# ---------------------------------------------------------------------------


class TestReactRouter:
    """Tests for React Router configuration file parsing."""

    def test_jsx_route_elements(self, tmp_path: Path) -> None:
        routes_file = tmp_path / "src" / "routes.tsx"
        routes_file.parent.mkdir(parents=True)
        routes_file.write_text(
            """
            <Route path="/home" element={<Home />} />
            <Route path="/about" element={<About />} />
            <Route path="/users/:id" element={<UserProfile />} />
            """,
            encoding="utf-8",
        )
        inventory = _make_inventory(["src/routes.tsx"])
        routes = _extract_react_router_routes(inventory, tmp_path)

        assert len(routes) == 3
        paths = {r.path for r in routes}
        assert paths == {"/home", "/about", "/users/:id"}

    def test_route_source_refs(self, tmp_path: Path) -> None:
        routes_file = tmp_path / "src" / "routes.tsx"
        routes_file.parent.mkdir(parents=True)
        routes_file.write_text(
            '<Route path="/home" element={<Home />} />',
            encoding="utf-8",
        )
        inventory = _make_inventory(["src/routes.tsx"])
        routes = _extract_react_router_routes(inventory, tmp_path)

        assert len(routes) == 1
        assert routes[0].source_refs[0].file_path == "src/routes.tsx"
        assert routes[0].source_refs[0].start_line is not None

    def test_route_name_format(self, tmp_path: Path) -> None:
        routes_file = tmp_path / "src" / "routes.tsx"
        routes_file.parent.mkdir(parents=True)
        routes_file.write_text(
            '<Route path="/home" element={<Home />} />',
            encoding="utf-8",
        )
        inventory = _make_inventory(["src/routes.tsx"])
        routes = _extract_react_router_routes(inventory, tmp_path)

        assert routes[0].name == "react:/home"

    def test_object_style_routes(self, tmp_path: Path) -> None:
        routes_file = tmp_path / "src" / "router.ts"
        routes_file.parent.mkdir(parents=True)
        routes_file.write_text(
            """
            const routes = [
                { path: "/dashboard", element: Dashboard },
                { path: "/settings", element: Settings },
            ];
            """,
            encoding="utf-8",
        )
        inventory = _make_inventory(["src/router.ts"])
        routes = _extract_react_router_routes(inventory, tmp_path)

        assert len(routes) == 2
        paths = {r.path for r in routes}
        assert paths == {"/dashboard", "/settings"}

    def test_skips_non_route_files(self, tmp_path: Path) -> None:
        other_file = tmp_path / "src" / "utils.ts"
        other_file.parent.mkdir(parents=True)
        other_file.write_text('<Route path="/home" />', encoding="utf-8")

        inventory = _make_inventory(["src/utils.ts"])
        routes = _extract_react_router_routes(inventory, tmp_path)

        assert len(routes) == 0

    def test_no_workdir_returns_empty(self) -> None:
        inventory = _make_inventory(["src/routes.tsx"])
        routes = _extract_react_router_routes(inventory, None)

        assert routes == []

    def test_app_tsx_routes(self, tmp_path: Path) -> None:
        app_file = tmp_path / "src" / "App.tsx"
        app_file.parent.mkdir(parents=True)
        app_file.write_text(
            '<Route path="/login" element={<Login />} />',
            encoding="utf-8",
        )
        inventory = _make_inventory(["src/App.tsx"])
        routes = _extract_react_router_routes(inventory, tmp_path)

        assert len(routes) == 1
        assert routes[0].path == "/login"


# ---------------------------------------------------------------------------
# Vue Router
# ---------------------------------------------------------------------------


class TestVueRouter:
    """Tests for Vue Router configuration file parsing."""

    def test_basic_routes(self, tmp_path: Path) -> None:
        router_file = tmp_path / "src" / "router" / "index.ts"
        router_file.parent.mkdir(parents=True)
        router_file.write_text(
            """
            const routes = [
                { path: '/', component: Home },
                { path: '/about', component: About },
                { path: '/users/:id', component: UserProfile },
            ];
            """,
            encoding="utf-8",
        )
        inventory = _make_inventory(["src/router/index.ts"])
        routes = _extract_vue_router_routes(inventory, tmp_path)

        assert len(routes) == 3
        paths = {r.path for r in routes}
        assert paths == {"/", "/about", "/users/:id"}

    def test_route_name_format(self, tmp_path: Path) -> None:
        router_file = tmp_path / "router" / "index.js"
        router_file.parent.mkdir(parents=True)
        router_file.write_text(
            "{ path: '/home', component: Home }",
            encoding="utf-8",
        )
        inventory = _make_inventory(["router/index.js"])
        routes = _extract_vue_router_routes(inventory, tmp_path)

        assert routes[0].name == "vue:/home"

    def test_source_refs(self, tmp_path: Path) -> None:
        router_file = tmp_path / "src" / "router" / "index.ts"
        router_file.parent.mkdir(parents=True)
        router_file.write_text(
            "{ path: '/home', component: Home }",
            encoding="utf-8",
        )
        inventory = _make_inventory(["src/router/index.ts"])
        routes = _extract_vue_router_routes(inventory, tmp_path)

        assert routes[0].source_refs[0].file_path == "src/router/index.ts"
        assert routes[0].source_refs[0].start_line is not None

    def test_skips_non_route_paths(self, tmp_path: Path) -> None:
        # Non-path values should be skipped.
        router_file = tmp_path / "src" / "router" / "index.ts"
        router_file.parent.mkdir(parents=True)
        router_file.write_text(
            """
            import { path: 'vue-router' }
            { path: '/valid', component: Valid }
            """,
            encoding="utf-8",
        )
        inventory = _make_inventory(["src/router/index.ts"])
        routes = _extract_vue_router_routes(inventory, tmp_path)

        assert len(routes) == 1
        assert routes[0].path == "/valid"

    def test_no_workdir_returns_empty(self) -> None:
        inventory = _make_inventory(["src/router/index.ts"])
        routes = _extract_vue_router_routes(inventory, None)

        assert routes == []


# ---------------------------------------------------------------------------
# SvelteKit
# ---------------------------------------------------------------------------


class TestSvelteKit:
    """Tests for SvelteKit file-based route extraction."""

    def test_root_page(self) -> None:
        inventory = _make_inventory(["src/routes/+page.svelte"])
        routes = _extract_sveltekit_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/"

    def test_nested_route(self) -> None:
        inventory = _make_inventory(["src/routes/about/+page.svelte"])
        routes = _extract_sveltekit_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/about"

    def test_deeply_nested_route(self) -> None:
        inventory = _make_inventory(["src/routes/dashboard/settings/+page.svelte"])
        routes = _extract_sveltekit_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/dashboard/settings"

    def test_dynamic_segment(self) -> None:
        inventory = _make_inventory(["src/routes/blog/[slug]/+page.svelte"])
        routes = _extract_sveltekit_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/blog/[slug]"

    def test_route_group_excluded(self) -> None:
        inventory = _make_inventory(["src/routes/(app)/dashboard/+page.svelte"])
        routes = _extract_sveltekit_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/dashboard"

    def test_multiple_routes(self) -> None:
        inventory = _make_inventory(
            [
                "src/routes/+page.svelte",
                "src/routes/about/+page.svelte",
                "src/routes/blog/+page.svelte",
                "src/routes/blog/[slug]/+page.svelte",
            ]
        )
        routes = _extract_sveltekit_routes(inventory)

        assert len(routes) == 4
        paths = {r.path for r in routes}
        assert paths == {"/", "/about", "/blog", "/blog/[slug]"}

    def test_skips_non_page_files(self) -> None:
        inventory = _make_inventory(
            [
                "src/routes/+page.svelte",
                "src/routes/+layout.svelte",
                "src/routes/+error.svelte",
                "src/routes/+page.server.ts",
            ]
        )
        routes = _extract_sveltekit_routes(inventory)

        assert len(routes) == 1
        assert routes[0].path == "/"

    def test_skips_files_outside_routes_dir(self) -> None:
        inventory = _make_inventory(
            [
                "src/components/+page.svelte",
                "src/routes/+page.svelte",
            ]
        )
        routes = _extract_sveltekit_routes(inventory)

        assert len(routes) == 1

    def test_route_name_format(self) -> None:
        inventory = _make_inventory(["src/routes/about/+page.svelte"])
        routes = _extract_sveltekit_routes(inventory)

        assert routes[0].name == "sveltekit:/about"

    def test_source_refs_populated(self) -> None:
        inventory = _make_inventory(["src/routes/about/+page.svelte"])
        routes = _extract_sveltekit_routes(inventory)

        assert routes[0].source_refs[0].file_path == "src/routes/about/+page.svelte"


# ---------------------------------------------------------------------------
# Top-level analyze_routes
# ---------------------------------------------------------------------------


class TestAnalyzeRoutes:
    """Tests for the top-level analyze_routes orchestrator."""

    def test_nextjs_detection(self) -> None:
        inventory = _make_inventory(
            [
                "pages/index.tsx",
                "pages/about.tsx",
            ]
        )
        profile = _make_profile({"nextjs": 0.9})
        routes = analyze_routes(inventory, profile)

        assert len(routes) == 2
        paths = {r.path for r in routes}
        assert paths == {"/", "/about"}

    def test_sveltekit_detection(self) -> None:
        inventory = _make_inventory(
            [
                "src/routes/+page.svelte",
                "src/routes/about/+page.svelte",
            ]
        )
        profile = _make_profile({"sveltekit": 0.8, "svelte": 0.9})
        routes = analyze_routes(inventory, profile)

        assert len(routes) == 2

    def test_react_detection(self, tmp_path: Path) -> None:
        routes_file = tmp_path / "src" / "routes.tsx"
        routes_file.parent.mkdir(parents=True)
        routes_file.write_text(
            '<Route path="/home" element={<Home />} />',
            encoding="utf-8",
        )
        inventory = _make_inventory(["src/routes.tsx"])
        profile = _make_profile({"react": 0.8})
        routes = analyze_routes(inventory, profile, workdir=tmp_path)

        assert len(routes) == 1
        assert routes[0].path == "/home"

    def test_vue_detection(self, tmp_path: Path) -> None:
        router_file = tmp_path / "src" / "router" / "index.ts"
        router_file.parent.mkdir(parents=True)
        router_file.write_text(
            "{ path: '/dashboard', component: Dashboard }",
            encoding="utf-8",
        )
        inventory = _make_inventory(["src/router/index.ts"])
        profile = _make_profile({"vue": 0.8})
        routes = analyze_routes(inventory, profile, workdir=tmp_path)

        assert len(routes) == 1
        assert routes[0].path == "/dashboard"

    def test_empty_profile_returns_empty(self) -> None:
        inventory = _make_inventory(["pages/about.tsx"])
        profile = _make_profile({})
        routes = analyze_routes(inventory, profile)

        assert routes == []

    def test_react_skipped_when_nextjs_present(self, tmp_path: Path) -> None:
        """React Router extraction is skipped when Next.js is detected."""
        routes_file = tmp_path / "src" / "routes.tsx"
        routes_file.parent.mkdir(parents=True)
        routes_file.write_text(
            '<Route path="/home" element={<Home />} />',
            encoding="utf-8",
        )
        inventory = _make_inventory(
            [
                "pages/about.tsx",
                "src/routes.tsx",
            ]
        )
        profile = _make_profile({"nextjs": 0.9, "react": 0.8})
        routes = analyze_routes(inventory, profile, workdir=tmp_path)

        # Only Next.js routes, no React Router routes.
        assert len(routes) == 1
        assert routes[0].name.startswith("nextjs:")

    def test_all_routes_are_route_surfaces(self) -> None:
        inventory = _make_inventory(["pages/about.tsx"])
        profile = _make_profile({"nextjs": 0.9})
        routes = analyze_routes(inventory, profile)

        for route in routes:
            assert isinstance(route, RouteSurface)
            assert route.surface_type == "route"


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestDynamicSegments:
    """Tests for dynamic segment extraction."""

    def test_nextjs_bracket_syntax(self) -> None:
        segments = _extract_dynamic_segments("/blog/[slug]")
        assert segments == ["slug"]

    def test_nextjs_catch_all(self) -> None:
        segments = _extract_dynamic_segments("/docs/[...path]")
        assert segments == ["path"]

    def test_react_colon_syntax(self) -> None:
        segments = _extract_dynamic_segments("/users/:id")
        assert segments == ["id"]

    def test_generic_brace_syntax(self) -> None:
        segments = _extract_dynamic_segments("/items/{slug}")
        assert segments == ["slug"]

    def test_multiple_segments(self) -> None:
        segments = _extract_dynamic_segments("/users/:userId/posts/:postId")
        assert "userId" in segments
        assert "postId" in segments

    def test_no_dynamic_segments(self) -> None:
        segments = _extract_dynamic_segments("/about")
        assert segments == []


class TestPagesPartsToRoute:
    """Tests for Next.js pages path conversion."""

    def test_simple_page(self) -> None:
        assert _pages_parts_to_route(("about.tsx",), "about") == "/about"

    def test_index_page(self) -> None:
        assert _pages_parts_to_route(("index.tsx",), "index") == "/"

    def test_nested_page(self) -> None:
        result = _pages_parts_to_route(("blog", "post.tsx"), "post")
        assert result == "/blog/post"

    def test_nested_index(self) -> None:
        result = _pages_parts_to_route(("blog", "index.tsx"), "index")
        assert result == "/blog"


class TestIsRouteGroup:
    """Tests for route group detection."""

    def test_route_group(self) -> None:
        assert _is_route_group("(auth)") is True

    def test_not_route_group(self) -> None:
        assert _is_route_group("auth") is False

    def test_partial_parens_start(self) -> None:
        assert _is_route_group("(auth") is False

    def test_partial_parens_end(self) -> None:
        assert _is_route_group("auth)") is False


class TestLineNumber:
    """Tests for line number calculation."""

    def test_first_line(self) -> None:
        assert _line_number("hello\nworld", 0) == 1

    def test_second_line(self) -> None:
        assert _line_number("hello\nworld", 6) == 2

    def test_third_line(self) -> None:
        assert _line_number("a\nb\nc", 4) == 3
