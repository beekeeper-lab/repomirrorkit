"""Unit tests for the surface map report generator."""

from __future__ import annotations

import json
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    ComponentSurface,
    ConfigSurface,
    CrosscuttingSurface,
    ModelField,
    ModelSurface,
    RouteSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.reports.surface_map import (
    generate_surface_map_json,
    generate_surface_map_markdown,
    write_surface_map,
)


def _make_ref(path: str = "src/app.py") -> SourceRef:
    return SourceRef(file_path=path, start_line=1, end_line=10)


def _make_populated_collection() -> SurfaceCollection:
    """Build a SurfaceCollection with at least one surface of each type."""
    return SurfaceCollection(
        routes=[
            RouteSurface(
                name="home",
                path="/home",
                method="GET",
                source_refs=[_make_ref("src/pages/home.tsx")],
            ),
            RouteSurface(
                name="login",
                path="/login",
                method="POST",
                source_refs=[_make_ref("src/pages/login.tsx")],
            ),
        ],
        components=[
            ComponentSurface(
                name="Button",
                props=["label", "onClick", "disabled"],
                usage_locations=["src/pages/home.tsx", "src/pages/login.tsx"],
                source_refs=[_make_ref("src/components/Button.tsx")],
            ),
        ],
        apis=[
            ApiSurface(
                name="create_user",
                method="POST",
                path="/api/users",
                auth="bearer",
                source_refs=[_make_ref("src/api/users.py")],
            ),
            ApiSurface(
                name="list_users",
                method="GET",
                path="/api/users",
                source_refs=[_make_ref("src/api/users.py")],
            ),
        ],
        models=[
            ModelSurface(
                name="User",
                entity_name="User",
                fields=[
                    ModelField(name="id", field_type="int"),
                    ModelField(name="email", field_type="str"),
                    ModelField(name="name", field_type="str"),
                ],
                source_refs=[_make_ref("src/models/user.py")],
            ),
        ],
        auth=[
            AuthSurface(
                name="JWT Auth",
                roles=["admin", "user"],
                permissions=["read", "write"],
                protected_endpoints=["/api/users", "/api/admin"],
                source_refs=[_make_ref("src/auth/jwt.py")],
            ),
        ],
        config=[
            ConfigSurface(
                name="DATABASE_URL",
                env_var_name="DATABASE_URL",
                required=True,
                source_refs=[_make_ref("src/config.py")],
            ),
            ConfigSurface(
                name="DEBUG",
                env_var_name="DEBUG",
                required=False,
                default_value="false",
                source_refs=[_make_ref("src/config.py")],
            ),
        ],
        crosscutting=[
            CrosscuttingSurface(
                name="logging",
                concern_type="logging",
                description="Structured JSON logging via structlog",
                affected_files=["src/app.py", "src/api/users.py"],
                source_refs=[_make_ref("src/logging.py")],
            ),
        ],
    )


def _make_profile() -> StackProfile:
    return StackProfile(
        stacks={"react": 0.9, "fastapi": 0.8},
        evidence={
            "react": ["package.json"],
            "fastapi": ["requirements.txt"],
        },
    )


# ---------------------------------------------------------------------------
# Markdown generation tests
# ---------------------------------------------------------------------------


class TestMarkdownReport:
    def test_contains_title(self) -> None:
        md = generate_surface_map_markdown(SurfaceCollection())
        assert "# Surface Map Report" in md

    def test_all_seven_sections_present(self) -> None:
        md = generate_surface_map_markdown(SurfaceCollection())
        assert "## Summary" in md
        assert "## Routes / Pages" in md
        assert "## Components" in md
        assert "## API Endpoints" in md
        assert "## Models / Entities" in md
        assert "## Auth Patterns" in md
        assert "## Config / Environment Variables" in md
        assert "## Cross-cutting Concerns" in md

    def test_empty_sections_show_none_detected(self) -> None:
        md = generate_surface_map_markdown(SurfaceCollection())
        assert md.count("None detected.") == 7

    def test_summary_shows_stacks(self) -> None:
        surfaces = _make_populated_collection()
        profile = _make_profile()
        md = generate_surface_map_markdown(surfaces, profile)
        assert "fastapi" in md
        assert "react" in md

    def test_summary_shows_no_stacks_without_profile(self) -> None:
        md = generate_surface_map_markdown(SurfaceCollection())
        assert "**Detected stacks:** None" in md

    def test_summary_total_count(self) -> None:
        surfaces = _make_populated_collection()
        md = generate_surface_map_markdown(surfaces)
        assert f"**Total surfaces:** {len(surfaces)}" in md

    def test_summary_table_counts(self) -> None:
        surfaces = _make_populated_collection()
        md = generate_surface_map_markdown(surfaces)
        assert "| Routes / Pages | 2 |" in md
        assert "| Components | 1 |" in md
        assert "| API Endpoints | 2 |" in md
        assert "| Models / Entities | 1 |" in md
        assert "| Auth Patterns | 1 |" in md
        assert "| Config / Env Vars | 2 |" in md
        assert "| Cross-cutting Concerns | 1 |" in md

    def test_routes_listed_with_path_and_method(self) -> None:
        surfaces = _make_populated_collection()
        md = generate_surface_map_markdown(surfaces)
        assert "| home | `/home` | GET |" in md
        assert "| login | `/login` | POST |" in md

    def test_components_listed_with_usage_count(self) -> None:
        surfaces = _make_populated_collection()
        md = generate_surface_map_markdown(surfaces)
        # Button has 3 props and 2 usage locations
        assert "| Button | 3 | 2 |" in md

    def test_apis_listed_with_method_and_path(self) -> None:
        surfaces = _make_populated_collection()
        md = generate_surface_map_markdown(surfaces)
        assert "| create_user | POST | `/api/users` |" in md
        assert "| list_users | GET | `/api/users` |" in md

    def test_models_listed_with_field_count(self) -> None:
        surfaces = _make_populated_collection()
        md = generate_surface_map_markdown(surfaces)
        assert "| User | User | 3 |" in md

    def test_auth_shows_roles_and_permissions(self) -> None:
        surfaces = _make_populated_collection()
        md = generate_surface_map_markdown(surfaces)
        assert "### JWT Auth" in md
        assert "admin" in md
        assert "user" in md
        assert "read" in md
        assert "write" in md

    def test_config_shows_env_vars(self) -> None:
        surfaces = _make_populated_collection()
        md = generate_surface_map_markdown(surfaces)
        assert "| `DATABASE_URL` | Yes |" in md
        assert "| `DEBUG` | No | false |" in md

    def test_crosscutting_shows_concerns(self) -> None:
        surfaces = _make_populated_collection()
        md = generate_surface_map_markdown(surfaces)
        assert "**logging**" in md
        assert "Structured JSON logging via structlog" in md

    def test_route_default_method_is_get(self) -> None:
        surfaces = SurfaceCollection(
            routes=[RouteSurface(name="index", path="/")],
        )
        md = generate_surface_map_markdown(surfaces)
        assert "| index | `/` | GET |" in md


# ---------------------------------------------------------------------------
# JSON generation tests
# ---------------------------------------------------------------------------


class TestJsonReport:
    def test_valid_json(self) -> None:
        result = generate_surface_map_json(SurfaceCollection())
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_summary_present(self) -> None:
        result = generate_surface_map_json(SurfaceCollection())
        parsed = json.loads(result)
        assert "summary" in parsed
        assert "total_surfaces" in parsed["summary"]
        assert "counts" in parsed["summary"]

    def test_surfaces_present(self) -> None:
        result = generate_surface_map_json(SurfaceCollection())
        parsed = json.loads(result)
        assert "surfaces" in parsed
        assert "routes" in parsed["surfaces"]
        assert "components" in parsed["surfaces"]
        assert "apis" in parsed["surfaces"]
        assert "models" in parsed["surfaces"]
        assert "auth" in parsed["surfaces"]
        assert "config" in parsed["surfaces"]
        assert "crosscutting" in parsed["surfaces"]

    def test_empty_collection_counts_zero(self) -> None:
        result = generate_surface_map_json(SurfaceCollection())
        parsed = json.loads(result)
        assert parsed["summary"]["total_surfaces"] == 0
        for count in parsed["summary"]["counts"].values():
            assert count == 0

    def test_populated_collection_counts(self) -> None:
        surfaces = _make_populated_collection()
        result = generate_surface_map_json(surfaces)
        parsed = json.loads(result)
        assert parsed["summary"]["total_surfaces"] == len(surfaces)
        assert parsed["summary"]["counts"]["routes"] == 2
        assert parsed["summary"]["counts"]["components"] == 1
        assert parsed["summary"]["counts"]["apis"] == 2
        assert parsed["summary"]["counts"]["models"] == 1
        assert parsed["summary"]["counts"]["auth"] == 1
        assert parsed["summary"]["counts"]["config"] == 2
        assert parsed["summary"]["counts"]["crosscutting"] == 1

    def test_detected_stacks_included(self) -> None:
        profile = _make_profile()
        result = generate_surface_map_json(SurfaceCollection(), profile)
        parsed = json.loads(result)
        assert set(parsed["summary"]["detected_stacks"]) == {"react", "fastapi"}

    def test_detected_stacks_empty_without_profile(self) -> None:
        result = generate_surface_map_json(SurfaceCollection())
        parsed = json.loads(result)
        assert parsed["summary"]["detected_stacks"] == []

    def test_surfaces_contain_full_data(self) -> None:
        surfaces = _make_populated_collection()
        result = generate_surface_map_json(surfaces)
        parsed = json.loads(result)
        route = parsed["surfaces"]["routes"][0]
        assert route["name"] == "home"
        assert route["path"] == "/home"
        api = parsed["surfaces"]["apis"][0]
        assert api["method"] == "POST"
        assert api["path"] == "/api/users"


# ---------------------------------------------------------------------------
# File-writing tests
# ---------------------------------------------------------------------------


class TestWriteSurfaceMap:
    def test_writes_both_files(self, tmp_path: Path) -> None:
        surfaces = _make_populated_collection()
        profile = _make_profile()
        md_path, json_path = write_surface_map(tmp_path, surfaces, profile)

        assert md_path.exists()
        assert json_path.exists()
        assert md_path.name == "surface-map.md"
        assert json_path.name == "surfaces.json"

    def test_creates_output_dir(self, tmp_path: Path) -> None:
        out = tmp_path / "reports" / "nested"
        surfaces = SurfaceCollection()
        write_surface_map(out, surfaces)
        assert out.exists()

    def test_markdown_file_content(self, tmp_path: Path) -> None:
        surfaces = _make_populated_collection()
        md_path, _ = write_surface_map(tmp_path, surfaces)
        content = md_path.read_text(encoding="utf-8")
        assert "# Surface Map Report" in content
        assert "## Routes / Pages" in content

    def test_json_file_is_valid(self, tmp_path: Path) -> None:
        surfaces = _make_populated_collection()
        _, json_path = write_surface_map(tmp_path, surfaces)
        parsed = json.loads(json_path.read_text(encoding="utf-8"))
        assert parsed["summary"]["total_surfaces"] == len(surfaces)

    def test_empty_collection_writes_none_detected(self, tmp_path: Path) -> None:
        surfaces = SurfaceCollection()
        md_path, _ = write_surface_map(tmp_path, surfaces)
        content = md_path.read_text(encoding="utf-8")
        assert content.count("None detected.") == 7
