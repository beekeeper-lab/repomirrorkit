"""Unit tests for bean writer — file generation, ordering, slugs, resume."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    ComponentSurface,
    ConfigSurface,
    CrosscuttingSurface,
    ModelSurface,
    RouteSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.beans.writer import WrittenBean, slugify, write_beans
from repo_mirror_kit.harvester.state import StateManager

# --- Slug generation tests ---


class TestSlugify:
    def test_basic_lowercase(self) -> None:
        assert slugify("Home Page") == "home-page"

    def test_preserves_numbers(self) -> None:
        assert slugify("Page 42") == "page-42"

    def test_strips_special_chars(self) -> None:
        assert slugify("get_users (v2)") == "get-users-v2"

    def test_collapses_consecutive_hyphens(self) -> None:
        assert slugify("foo---bar") == "foo-bar"

    def test_strips_leading_trailing_hyphens(self) -> None:
        assert slugify("--hello--") == "hello"

    def test_empty_string_returns_unnamed(self) -> None:
        assert slugify("") == "unnamed"

    def test_only_special_chars_returns_unnamed(self) -> None:
        assert slugify("!!!") == "unnamed"

    def test_unicode_stripped(self) -> None:
        assert slugify("café résumé") == "caf-r-sum"

    def test_single_word(self) -> None:
        assert slugify("Dashboard") == "dashboard"

    def test_already_slugified(self) -> None:
        assert slugify("my-component") == "my-component"

    def test_underscores_become_hyphens(self) -> None:
        assert slugify("get_all_users") == "get-all-users"

    def test_dots_become_hyphens(self) -> None:
        assert slugify("config.env") == "config-env"


# --- Helpers ---


def _make_ref() -> SourceRef:
    return SourceRef(file_path="src/app.py", start_line=1, end_line=10)


def _make_collection() -> SurfaceCollection:
    """Build a SurfaceCollection with one surface of each type."""
    return SurfaceCollection(
        routes=[
            RouteSurface(
                name="Home Page",
                path="/",
                method="GET",
                source_refs=[_make_ref()],
            ),
        ],
        components=[
            ComponentSurface(
                name="Sidebar",
                source_refs=[_make_ref()],
            ),
        ],
        apis=[
            ApiSurface(
                name="get_users",
                method="GET",
                path="/api/users",
                source_refs=[_make_ref()],
            ),
        ],
        models=[
            ModelSurface(
                name="User",
                source_refs=[_make_ref()],
            ),
        ],
        auth=[
            AuthSurface(
                name="admin_auth",
                source_refs=[_make_ref()],
            ),
        ],
        config=[
            ConfigSurface(
                name="DATABASE_URL",
                env_var_name="DATABASE_URL",
                source_refs=[_make_ref()],
            ),
        ],
        crosscutting=[
            CrosscuttingSurface(
                name="logging",
                concern_type="logging",
                source_refs=[_make_ref()],
            ),
        ],
    )


# --- Writer tests ---


class TestWriteBeans:
    def test_writes_all_bean_files(self, tmp_path: Path) -> None:
        collection = _make_collection()
        results = write_beans(collection, tmp_path)
        assert len(results) == 7
        for r in results:
            assert r.path.exists()

    def test_bean_numbering_sequential(self, tmp_path: Path) -> None:
        collection = _make_collection()
        results = write_beans(collection, tmp_path)
        numbers = [r.bean_number for r in results]
        assert numbers == [1, 2, 3, 4, 5, 6, 7]

    def test_bean_ids_formatted(self, tmp_path: Path) -> None:
        collection = _make_collection()
        results = write_beans(collection, tmp_path)
        ids = [r.bean_id for r in results]
        assert ids == [
            "BEAN-001",
            "BEAN-002",
            "BEAN-003",
            "BEAN-004",
            "BEAN-005",
            "BEAN-006",
            "BEAN-007",
        ]

    def test_ordering_routes_first_crosscutting_last(self, tmp_path: Path) -> None:
        collection = _make_collection()
        results = write_beans(collection, tmp_path)
        types = [r.surface_type for r in results]
        assert types == [
            "route",
            "component",
            "api",
            "model",
            "auth",
            "config",
            "crosscutting",
        ]

    def test_filenames_match_pattern(self, tmp_path: Path) -> None:
        collection = _make_collection()
        results = write_beans(collection, tmp_path)
        assert results[0].path.name == "BEAN-001-home-page.md"
        assert results[1].path.name == "BEAN-002-sidebar.md"
        assert results[2].path.name == "BEAN-003-get-users.md"

    def test_files_written_in_beans_dir(self, tmp_path: Path) -> None:
        collection = _make_collection()
        results = write_beans(collection, tmp_path)
        for r in results:
            assert r.path.parent == tmp_path / "beans"

    def test_bean_content_has_frontmatter(self, tmp_path: Path) -> None:
        collection = _make_collection()
        write_beans(collection, tmp_path)
        content = (tmp_path / "beans" / "BEAN-001-home-page.md").read_text(
            encoding="utf-8"
        )
        assert content.startswith("---")
        assert "id: BEAN-001" in content
        assert "status: draft" in content

    def test_bean_content_has_body_sections(self, tmp_path: Path) -> None:
        collection = _make_collection()
        write_beans(collection, tmp_path)
        content = (tmp_path / "beans" / "BEAN-001-home-page.md").read_text(
            encoding="utf-8"
        )
        assert "## Overview" in content
        assert "## Acceptance criteria" in content

    def test_empty_collection_produces_no_files(self, tmp_path: Path) -> None:
        collection = SurfaceCollection()
        results = write_beans(collection, tmp_path)
        assert results == []

    def test_creates_beans_directory(self, tmp_path: Path) -> None:
        output = tmp_path / "nested" / "output"
        collection = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="test", path="/test", method="GET", source_refs=[_make_ref()]
                ),
            ],
        )
        write_beans(collection, output)
        assert (output / "beans").is_dir()


# --- Resume/skip tests ---


class TestWriteBeansResume:
    def test_skips_already_written_beans(self, tmp_path: Path) -> None:
        state = StateManager(tmp_path, checkpoint_interval=10)
        state.initialize(["E"])
        # Simulate 3 beans already written
        state._state.bean_count = 3

        collection = _make_collection()
        results = write_beans(collection, tmp_path, state=state)

        skipped = [r for r in results if r.skipped]
        written = [r for r in results if not r.skipped]
        assert len(skipped) == 3
        assert len(written) == 4

    def test_skipped_beans_not_written_to_disk(self, tmp_path: Path) -> None:
        state = StateManager(tmp_path, checkpoint_interval=10)
        state.initialize(["E"])
        state._state.bean_count = 2

        collection = _make_collection()
        results = write_beans(collection, tmp_path, state=state)

        # Beans 1 and 2 should be skipped — no file written
        for r in results[:2]:
            assert r.skipped
            assert not r.path.exists()

        # Beans 3+ should be written
        for r in results[2:]:
            assert not r.skipped
            assert r.path.exists()

    def test_no_state_writes_all(self, tmp_path: Path) -> None:
        collection = _make_collection()
        results = write_beans(collection, tmp_path, state=None)
        assert all(not r.skipped for r in results)

    def test_never_overwrites_existing_files(self, tmp_path: Path) -> None:
        collection = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="Home",
                    path="/",
                    method="GET",
                    source_refs=[_make_ref()],
                ),
            ],
        )
        # Write once
        write_beans(collection, tmp_path)
        content1 = (tmp_path / "beans" / "BEAN-001-home.md").read_text(encoding="utf-8")

        # Write again with state showing bean already written
        state = StateManager(tmp_path, checkpoint_interval=10)
        state.initialize(["E"])
        state._state.bean_count = 1

        write_beans(collection, tmp_path, state=state)
        content2 = (tmp_path / "beans" / "BEAN-001-home.md").read_text(encoding="utf-8")
        assert content1 == content2


# --- Checkpoint tests ---


class TestWriteBeansCheckpoint:
    def test_checkpoints_at_interval(self, tmp_path: Path) -> None:
        state = StateManager(tmp_path, checkpoint_interval=3)
        state.initialize(["E"])

        collection = _make_collection()
        write_beans(collection, tmp_path, state=state)

        # After writing 7 beans, bean_count should be 7
        assert state.get_bean_count() == 7

    def test_checkpoint_interval_respected(self, tmp_path: Path) -> None:
        state = StateManager(tmp_path, checkpoint_interval=2)
        state.initialize(["E"])

        collection = SurfaceCollection(
            routes=[
                RouteSurface(
                    name=f"Route {i}",
                    path=f"/r{i}",
                    method="GET",
                    source_refs=[_make_ref()],
                )
                for i in range(5)
            ],
        )
        write_beans(collection, tmp_path, state=state)
        assert state.get_bean_count() == 5


# --- WrittenBean dataclass tests ---


class TestWrittenBean:
    def test_written_bean_fields(self) -> None:
        bean = WrittenBean(
            bean_number=1,
            bean_id="BEAN-001",
            slug="home-page",
            surface_type="route",
            title="Home Page",
            path=Path("/tmp/beans/BEAN-001-home-page.md"),
        )
        assert bean.bean_number == 1
        assert bean.bean_id == "BEAN-001"
        assert bean.slug == "home-page"
        assert bean.surface_type == "route"
        assert bean.title == "Home Page"
        assert not bean.skipped

    def test_written_bean_skipped(self) -> None:
        bean = WrittenBean(
            bean_number=1,
            bean_id="BEAN-001",
            slug="home-page",
            surface_type="route",
            title="Home Page",
            path=Path("/tmp/beans/BEAN-001-home-page.md"),
            skipped=True,
        )
        assert bean.skipped
