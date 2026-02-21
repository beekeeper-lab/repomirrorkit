"""Unit tests for bean indexer — index generation and templates directory."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.beans.indexer import (
    generate_index,
    generate_templates_dir,
)
from repo_mirror_kit.harvester.beans.writer import WrittenBean

# --- Helpers ---


def _make_beans() -> list[WrittenBean]:
    """Build a sample list of WrittenBean records."""
    return [
        WrittenBean(
            bean_number=1,
            bean_id="BEAN-001",
            slug="home-page",
            surface_type="route",
            title="Home Page",
            path=Path("/tmp/beans/BEAN-001-home-page.md"),
        ),
        WrittenBean(
            bean_number=2,
            bean_id="BEAN-002",
            slug="sidebar",
            surface_type="component",
            title="Sidebar",
            path=Path("/tmp/beans/BEAN-002-sidebar.md"),
        ),
        WrittenBean(
            bean_number=3,
            bean_id="BEAN-003",
            slug="get-users",
            surface_type="api",
            title="get_users",
            path=Path("/tmp/beans/BEAN-003-get-users.md"),
        ),
    ]


# --- Index generation tests ---


class TestGenerateIndex:
    def test_creates_index_file(self, tmp_path: Path) -> None:
        beans = _make_beans()
        index_path = generate_index(beans, tmp_path)
        assert index_path.exists()
        assert index_path.name == "_index.md"

    def test_index_in_beans_directory(self, tmp_path: Path) -> None:
        beans = _make_beans()
        index_path = generate_index(beans, tmp_path)
        assert index_path.parent == tmp_path / "beans"

    def test_index_contains_header(self, tmp_path: Path) -> None:
        beans = _make_beans()
        generate_index(beans, tmp_path)
        content = (tmp_path / "beans" / "_index.md").read_text(encoding="utf-8")
        assert "# Bean Index" in content

    def test_index_contains_total_count(self, tmp_path: Path) -> None:
        beans = _make_beans()
        generate_index(beans, tmp_path)
        content = (tmp_path / "beans" / "_index.md").read_text(encoding="utf-8")
        assert "Total beans: 3" in content

    def test_index_contains_table_header(self, tmp_path: Path) -> None:
        beans = _make_beans()
        generate_index(beans, tmp_path)
        content = (tmp_path / "beans" / "_index.md").read_text(encoding="utf-8")
        assert "| ID | Title | Type | Status |" in content

    def test_index_lists_all_beans(self, tmp_path: Path) -> None:
        beans = _make_beans()
        generate_index(beans, tmp_path)
        content = (tmp_path / "beans" / "_index.md").read_text(encoding="utf-8")
        assert "| BEAN-001 | Home Page | route | draft |" in content
        assert "| BEAN-002 | Sidebar | component | draft |" in content
        assert "| BEAN-003 | get_users | api | draft |" in content

    def test_index_preserves_order(self, tmp_path: Path) -> None:
        beans = _make_beans()
        generate_index(beans, tmp_path)
        content = (tmp_path / "beans" / "_index.md").read_text(encoding="utf-8")
        pos_001 = content.index("BEAN-001")
        pos_002 = content.index("BEAN-002")
        pos_003 = content.index("BEAN-003")
        assert pos_001 < pos_002 < pos_003

    def test_empty_beans_list(self, tmp_path: Path) -> None:
        index_path = generate_index([], tmp_path)
        assert index_path.exists()
        content = index_path.read_text(encoding="utf-8")
        assert "Total beans: 0" in content
        assert "| ID | Title | Type | Status |" in content

    def test_creates_beans_dir_if_missing(self, tmp_path: Path) -> None:
        output = tmp_path / "nested" / "dir"
        beans = _make_beans()
        generate_index(beans, output)
        assert (output / "beans" / "_index.md").exists()


# --- Templates directory tests ---


class TestGenerateTemplatesDir:
    def test_creates_templates_directory(self, tmp_path: Path) -> None:
        templates_dir = generate_templates_dir(tmp_path)
        assert templates_dir.exists()
        assert templates_dir.is_dir()

    def test_templates_dir_location(self, tmp_path: Path) -> None:
        templates_dir = generate_templates_dir(tmp_path)
        assert templates_dir == tmp_path / "beans" / "_templates"

    def test_creates_all_template_files(self, tmp_path: Path) -> None:
        generate_templates_dir(tmp_path)
        templates_dir = tmp_path / "beans" / "_templates"
        expected_files = {
            "route.md",
            "component.md",
            "api.md",
            "model.md",
            "auth.md",
            "config.md",
            "crosscutting.md",
            "state_mgmt.md",
            "middleware.md",
            "integration.md",
            "ui_flow.md",
            "build_deploy.md",
            "dependency.md",
            "test_pattern.md",
            "general_logic.md",
        }
        actual_files = {f.name for f in templates_dir.iterdir()}
        assert actual_files == expected_files

    def test_template_files_have_content(self, tmp_path: Path) -> None:
        generate_templates_dir(tmp_path)
        templates_dir = tmp_path / "beans" / "_templates"
        for f in templates_dir.iterdir():
            content = f.read_text(encoding="utf-8")
            assert len(content) > 0
            assert content.startswith("#")

    def test_template_files_contain_spec_references(self, tmp_path: Path) -> None:
        generate_templates_dir(tmp_path)
        templates_dir = tmp_path / "beans" / "_templates"
        route_content = (templates_dir / "route.md").read_text(encoding="utf-8")
        assert "spec 8.3" in route_content
        api_content = (templates_dir / "api.md").read_text(encoding="utf-8")
        assert "spec 8.5" in api_content

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        output = tmp_path / "deep" / "nested"
        generate_templates_dir(output)
        assert (output / "beans" / "_templates").is_dir()

    def test_idempotent(self, tmp_path: Path) -> None:
        generate_templates_dir(tmp_path)
        generate_templates_dir(tmp_path)
        templates_dir = tmp_path / "beans" / "_templates"
        assert len(list(templates_dir.iterdir())) == 15
