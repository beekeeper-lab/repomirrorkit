"""Unit tests for the traceability graph builder (Stage D)."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    ComponentSurface,
    ConfigSurface,
    ModelSurface,
    RouteSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.reports.traceability import build_traceability_maps

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_surfaces() -> SurfaceCollection:
    """Return an empty SurfaceCollection."""
    return SurfaceCollection()


def _sample_surfaces() -> SurfaceCollection:
    """Return a SurfaceCollection with linked surfaces for testing."""
    return SurfaceCollection(
        routes=[
            RouteSurface(
                name="home",
                path="/",
                method="GET",
                component_refs=["Header", "HomePage"],
                api_refs=["fetchPosts"],
                source_refs=[SourceRef(file_path="src/routes.tsx", start_line=5)],
            ),
            RouteSurface(
                name="profile",
                path="/profile",
                method="GET",
                component_refs=["Header", "ProfileCard"],
                api_refs=["getUser"],
                source_refs=[SourceRef(file_path="src/routes.tsx", start_line=10)],
            ),
            RouteSurface(
                name="settings",
                path="/settings",
                method="GET",
                component_refs=[],
                api_refs=[],
                source_refs=[SourceRef(file_path="src/routes.tsx", start_line=15)],
            ),
        ],
        components=[
            ComponentSurface(
                name="Header",
                props=["title"],
                usage_locations=["src/pages/Home.tsx", "src/pages/Profile.tsx"],
                source_refs=[SourceRef(file_path="src/components/Header.tsx")],
            ),
            ComponentSurface(
                name="HomePage",
                props=[],
                usage_locations=["src/pages/Home.tsx"],
                source_refs=[SourceRef(file_path="src/pages/Home.tsx")],
            ),
            ComponentSurface(
                name="ProfileCard",
                props=["user"],
                usage_locations=["src/pages/Profile.tsx"],
                source_refs=[SourceRef(file_path="src/components/ProfileCard.tsx")],
            ),
            ComponentSurface(
                name="Footer",
                props=[],
                usage_locations=[],
                source_refs=[SourceRef(file_path="src/components/Footer.tsx")],
            ),
        ],
        apis=[
            ApiSurface(
                name="fetchPosts",
                method="GET",
                path="/api/posts",
                side_effects=["Post"],
                source_refs=[SourceRef(file_path="src/api/posts.ts")],
            ),
            ApiSurface(
                name="getUser",
                method="GET",
                path="/api/users/:id",
                side_effects=["User"],
                source_refs=[SourceRef(file_path="src/api/users.ts")],
            ),
            ApiSurface(
                name="healthCheck",
                method="GET",
                path="/api/health",
                side_effects=[],
                source_refs=[SourceRef(file_path="src/api/health.ts")],
            ),
        ],
        models=[
            ModelSurface(
                name="Post",
                entity_name="Post",
                fields=[],
                relationships=["User"],
                source_refs=[SourceRef(file_path="src/models/Post.ts")],
            ),
            ModelSurface(
                name="User",
                entity_name="User",
                fields=[],
                relationships=[],
                source_refs=[SourceRef(file_path="src/models/User.ts")],
            ),
            ModelSurface(
                name="AuditLog",
                entity_name="AuditLog",
                fields=[],
                relationships=[],
                source_refs=[SourceRef(file_path="src/models/AuditLog.ts")],
            ),
        ],
        config=[
            ConfigSurface(
                name="env:PORT",
                env_var_name="PORT",
                default_value="3000",
                required=False,
                usage_locations=["src/server.ts", "docker-compose.yml"],
                source_refs=[SourceRef(file_path=".env")],
            ),
            ConfigSurface(
                name="env:DATABASE_URL",
                env_var_name="DATABASE_URL",
                default_value=None,
                required=True,
                usage_locations=["src/db.ts"],
                source_refs=[SourceRef(file_path="src/config.ts")],
            ),
            ConfigSurface(
                name="env:ORPHAN_VAR",
                env_var_name="ORPHAN_VAR",
                default_value=None,
                required=False,
                usage_locations=[],
                source_refs=[],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Test: build_traceability_maps creates all 4 files
# ---------------------------------------------------------------------------


class TestBuildTraceabilityMaps:
    """Top-level orchestration function."""

    def test_creates_traceability_directory(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        assert (tmp_path / "traceability").is_dir()

    def test_returns_four_file_paths(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        result = build_traceability_maps(surfaces, tmp_path)
        assert len(result) == 4
        for path in result:
            assert path.exists()

    def test_file_names(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        result = build_traceability_maps(surfaces, tmp_path)
        names = {p.name for p in result}
        assert names == {
            "routes_to_components.md",
            "routes_to_apis.md",
            "apis_to_models.md",
            "envvars_to_files.md",
        }

    def test_empty_surfaces_produces_files(self, tmp_path: Path) -> None:
        surfaces = _empty_surfaces()
        result = build_traceability_maps(surfaces, tmp_path)
        assert len(result) == 4
        for path in result:
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert len(content) > 0

    def test_idempotent(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        result = build_traceability_maps(surfaces, tmp_path)
        assert len(result) == 4


# ---------------------------------------------------------------------------
# Test: routes_to_components.md
# ---------------------------------------------------------------------------


class TestRoutesToComponents:
    """Verify routes_to_components.md content."""

    def test_header_present(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "routes_to_components.md").read_text(
            encoding="utf-8"
        )
        assert "# Routes to Components" in content

    def test_table_headers(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "routes_to_components.md").read_text(
            encoding="utf-8"
        )
        assert "| Route |" in content
        assert "| Method |" in content or "Method" in content

    def test_linked_routes_listed(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "routes_to_components.md").read_text(
            encoding="utf-8"
        )
        assert "`GET /`" in content
        assert "`Header`" in content
        assert "`HomePage`" in content

    def test_orphaned_route_marked(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "routes_to_components.md").read_text(
            encoding="utf-8"
        )
        assert "Orphaned" in content
        assert "`/settings`" in content

    def test_orphaned_component_listed(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "routes_to_components.md").read_text(
            encoding="utf-8"
        )
        assert "`Footer`" in content

    def test_empty_routes(self, tmp_path: Path) -> None:
        surfaces = _empty_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "routes_to_components.md").read_text(
            encoding="utf-8"
        )
        assert "No routes found" in content


# ---------------------------------------------------------------------------
# Test: routes_to_apis.md
# ---------------------------------------------------------------------------


class TestRoutesToApis:
    """Verify routes_to_apis.md content."""

    def test_linked_route_shows_api(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "routes_to_apis.md").read_text(
            encoding="utf-8"
        )
        assert "`GET /`" in content
        assert "fetchPosts" in content or "/api/posts" in content

    def test_orphaned_route_no_api_refs(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "routes_to_apis.md").read_text(
            encoding="utf-8"
        )
        assert "Orphaned" in content
        assert "`/settings`" in content

    def test_orphaned_api_listed(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "routes_to_apis.md").read_text(
            encoding="utf-8"
        )
        assert "`healthCheck`" in content

    def test_empty_routes(self, tmp_path: Path) -> None:
        surfaces = _empty_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "routes_to_apis.md").read_text(
            encoding="utf-8"
        )
        assert "No routes found" in content


# ---------------------------------------------------------------------------
# Test: apis_to_models.md
# ---------------------------------------------------------------------------


class TestApisToModels:
    """Verify apis_to_models.md content."""

    def test_linked_api_shows_models(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "apis_to_models.md").read_text(
            encoding="utf-8"
        )
        assert "`GET /api/posts`" in content
        assert "`Post`" in content

    def test_orphaned_api_no_models(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "apis_to_models.md").read_text(
            encoding="utf-8"
        )
        assert "Orphaned" in content
        assert "healthCheck" in content or "/api/health" in content

    def test_orphaned_model_listed(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "apis_to_models.md").read_text(
            encoding="utf-8"
        )
        assert "`AuditLog`" in content

    def test_empty_apis(self, tmp_path: Path) -> None:
        surfaces = _empty_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "apis_to_models.md").read_text(
            encoding="utf-8"
        )
        assert "No API endpoints found" in content


# ---------------------------------------------------------------------------
# Test: envvars_to_files.md
# ---------------------------------------------------------------------------


class TestEnvvarsToFiles:
    """Verify envvars_to_files.md content."""

    def test_env_var_with_files(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "envvars_to_files.md").read_text(
            encoding="utf-8"
        )
        assert "`PORT`" in content
        assert "`src/server.ts`" in content

    def test_required_flag(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "envvars_to_files.md").read_text(
            encoding="utf-8"
        )
        # DATABASE_URL is required
        lines = content.split("\n")
        db_line = [ln for ln in lines if "DATABASE_URL" in ln]
        assert len(db_line) >= 1
        assert "Yes" in db_line[0]

    def test_default_value_shown(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "envvars_to_files.md").read_text(
            encoding="utf-8"
        )
        assert "`3000`" in content

    def test_orphaned_var_noted(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "envvars_to_files.md").read_text(
            encoding="utf-8"
        )
        assert "Orphaned" in content
        assert "`ORPHAN_VAR`" in content

    def test_empty_config(self, tmp_path: Path) -> None:
        surfaces = _empty_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        content = (tmp_path / "traceability" / "envvars_to_files.md").read_text(
            encoding="utf-8"
        )
        assert "No environment variables found" in content


# ---------------------------------------------------------------------------
# Test: markdown table format
# ---------------------------------------------------------------------------


class TestMarkdownFormat:
    """Verify maps are formatted as proper markdown tables."""

    def test_table_separator_row(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        for filename in [
            "routes_to_components.md",
            "routes_to_apis.md",
            "apis_to_models.md",
            "envvars_to_files.md",
        ]:
            content = (tmp_path / "traceability" / filename).read_text(encoding="utf-8")
            # Markdown tables have |---| separator rows
            assert "|---" in content

    def test_all_files_have_headers(self, tmp_path: Path) -> None:
        surfaces = _sample_surfaces()
        build_traceability_maps(surfaces, tmp_path)
        for filename in [
            "routes_to_components.md",
            "routes_to_apis.md",
            "apis_to_models.md",
            "envvars_to_files.md",
        ]:
            content = (tmp_path / "traceability" / filename).read_text(encoding="utf-8")
            assert content.startswith("#")


# ---------------------------------------------------------------------------
# Test: graph building with various surface combinations
# ---------------------------------------------------------------------------


class TestGraphBuildingEdgeCases:
    """Edge cases in graph building logic."""

    def test_route_refs_unknown_component(self, tmp_path: Path) -> None:
        """Route references a component that doesn't exist in surfaces."""
        surfaces = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="home",
                    path="/",
                    method="GET",
                    component_refs=["NonExistent"],
                    source_refs=[SourceRef(file_path="src/routes.tsx")],
                ),
            ],
        )
        result = build_traceability_maps(surfaces, tmp_path)
        assert len(result) == 4
        content = (tmp_path / "traceability" / "routes_to_components.md").read_text(
            encoding="utf-8"
        )
        assert "`NonExistent`" in content

    def test_route_refs_unknown_api(self, tmp_path: Path) -> None:
        """Route references an API that doesn't exist in surfaces."""
        surfaces = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="home",
                    path="/",
                    method="GET",
                    api_refs=["missingApi"],
                    source_refs=[SourceRef(file_path="src/routes.tsx")],
                ),
            ],
        )
        result = build_traceability_maps(surfaces, tmp_path)
        assert len(result) == 4
        content = (tmp_path / "traceability" / "routes_to_apis.md").read_text(
            encoding="utf-8"
        )
        assert "missingApi" in content

    def test_api_refs_unknown_model(self, tmp_path: Path) -> None:
        """API references a model that doesn't exist in surfaces."""
        surfaces = SurfaceCollection(
            apis=[
                ApiSurface(
                    name="getItems",
                    method="GET",
                    path="/api/items",
                    side_effects=["UnknownModel"],
                    source_refs=[SourceRef(file_path="src/api/items.ts")],
                ),
            ],
        )
        result = build_traceability_maps(surfaces, tmp_path)
        assert len(result) == 4
        content = (tmp_path / "traceability" / "apis_to_models.md").read_text(
            encoding="utf-8"
        )
        assert "UnknownModel" in content

    def test_only_config_surfaces(self, tmp_path: Path) -> None:
        """Only config surfaces, no routes/apis/models."""
        surfaces = SurfaceCollection(
            config=[
                ConfigSurface(
                    name="env:API_KEY",
                    env_var_name="API_KEY",
                    default_value="test",
                    required=False,
                    usage_locations=["src/app.ts"],
                    source_refs=[SourceRef(file_path=".env")],
                ),
            ],
        )
        result = build_traceability_maps(surfaces, tmp_path)
        assert len(result) == 4
        content = (tmp_path / "traceability" / "envvars_to_files.md").read_text(
            encoding="utf-8"
        )
        assert "`API_KEY`" in content
        assert "`src/app.ts`" in content
