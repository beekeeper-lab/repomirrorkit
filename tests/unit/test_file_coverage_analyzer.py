"""Unit tests for the file coverage analyzer."""

from __future__ import annotations

import textwrap
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.file_coverage import (
    analyze_uncovered_files,
    find_uncovered_files,
)
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    GeneralLogicSurface,
    RouteSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(path: str, category: str = "source") -> FileEntry:
    """Create a FileEntry for testing."""
    ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
    return FileEntry(path=path, size=100, extension=ext, hash="abc", category=category)


def _make_inventory(entries: list[FileEntry]) -> InventoryResult:
    return InventoryResult(
        files=entries,
        skipped=[],
        total_files=len(entries),
        total_size=len(entries) * 100,
        total_skipped=0,
    )


def _make_profile() -> StackProfile:
    return StackProfile(stacks={})


def _write_file(workdir: Path, rel_path: str, content: str) -> None:
    full = workdir / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(textwrap.dedent(content), encoding="utf-8")


# ---------------------------------------------------------------------------
# find_uncovered_files
# ---------------------------------------------------------------------------


class TestFindUncoveredFiles:
    """Tests for find_uncovered_files()."""

    def test_all_files_covered(self) -> None:
        entries = [_make_entry("src/app.py"), _make_entry("src/utils.py")]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="app",
                    source_refs=[SourceRef(file_path="src/app.py")],
                ),
            ],
            apis=[
                ApiSurface(
                    name="utils",
                    source_refs=[SourceRef(file_path="src/utils.py")],
                ),
            ],
        )

        result = find_uncovered_files(inventory, surfaces)
        assert result == []

    def test_uncovered_files_detected(self) -> None:
        entries = [
            _make_entry("src/app.py"),
            _make_entry("src/utils.py"),
            _make_entry("src/helpers.py"),
        ]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="app",
                    source_refs=[SourceRef(file_path="src/app.py")],
                ),
            ],
        )

        result = find_uncovered_files(inventory, surfaces)
        assert Path("src/helpers.py") in result
        assert Path("src/utils.py") in result
        assert Path("src/app.py") not in result

    def test_non_source_files_excluded(self) -> None:
        entries = [
            _make_entry("src/app.py", category="source"),
            _make_entry("README.md", category="documentation"),
            _make_entry("logo.png", category="asset"),
            _make_entry("config.yaml", category="config"),
        ]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection()

        result = find_uncovered_files(inventory, surfaces)
        # Only the source file should appear
        assert len(result) == 1
        assert result[0] == Path("src/app.py")

    def test_exclusion_patterns_applied(self) -> None:
        entries = [
            _make_entry("src/app.py"),
            _make_entry("src/__init__.py"),
            _make_entry("migrations/001_init.py"),
        ]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection()

        result = find_uncovered_files(inventory, surfaces)
        # __init__.py and migrations should be excluded by defaults
        paths = [str(p) for p in result]
        assert "src/app.py" in paths
        assert "src/__init__.py" not in paths
        assert "migrations/001_init.py" not in paths

    def test_custom_exclusion_patterns(self) -> None:
        entries = [
            _make_entry("src/app.py"),
            _make_entry("src/generated.py"),
        ]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection()

        result = find_uncovered_files(
            inventory, surfaces, exclusion_patterns=("**/generated.py",)
        )
        paths = [str(p) for p in result]
        assert "src/app.py" in paths
        assert "src/generated.py" not in paths

    def test_empty_inventory(self) -> None:
        inventory = _make_inventory([])
        surfaces = SurfaceCollection()
        result = find_uncovered_files(inventory, surfaces)
        assert result == []

    def test_empty_surfaces(self) -> None:
        entries = [_make_entry("src/main.py")]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection()

        result = find_uncovered_files(inventory, surfaces)
        assert len(result) == 1

    def test_results_sorted(self) -> None:
        entries = [
            _make_entry("z_module.py"),
            _make_entry("a_module.py"),
            _make_entry("m_module.py"),
        ]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection()

        result = find_uncovered_files(inventory, surfaces)
        assert result == sorted(result)

    def test_test_files_considered(self) -> None:
        """Test files (category=test) are also checked for coverage."""
        entries = [
            _make_entry("src/app.py"),
            _make_entry("tests/test_app.py", category="test"),
        ]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection()

        result = find_uncovered_files(inventory, surfaces)
        paths = [str(p) for p in result]
        assert "src/app.py" in paths
        assert "tests/test_app.py" in paths


# ---------------------------------------------------------------------------
# analyze_uncovered_files
# ---------------------------------------------------------------------------


class TestAnalyzeUncoveredFiles:
    """Tests for analyze_uncovered_files()."""

    def test_generates_surfaces(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/utils.py",
            '''\
            """Utility functions for the project."""

            def helper_one():
                pass

            def helper_two():
                pass

            class MyClass:
                pass
            ''',
        )

        uncovered = [Path("src/utils.py")]
        inventory = _make_inventory([_make_entry("src/utils.py")])
        profile = _make_profile()

        result = analyze_uncovered_files(uncovered, inventory, profile, tmp_path)

        assert len(result) == 1
        surface = result[0]
        assert isinstance(surface, GeneralLogicSurface)
        assert surface.file_path == "src/utils.py"
        assert surface.surface_type == "general_logic"
        assert surface.name == "src/utils.py"
        assert len(surface.source_refs) == 1
        assert surface.source_refs[0].file_path == "src/utils.py"

    def test_extracts_python_info(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/service.py",
            '''\
            """Service layer for business logic."""

            def process_order():
                pass

            def _internal_helper():
                pass

            class OrderService:
                pass
            ''',
        )

        uncovered = [Path("src/service.py")]
        inventory = _make_inventory([_make_entry("src/service.py")])
        profile = _make_profile()

        result = analyze_uncovered_files(uncovered, inventory, profile, tmp_path)
        surface = result[0]

        assert "Service layer" in surface.module_purpose
        assert "def process_order()" in surface.exports
        assert "class OrderService" in surface.exports
        # Private functions should not be in exports
        assert "def _internal_helper()" not in surface.exports

    def test_handles_unreadable_file(self, tmp_path: Path) -> None:
        uncovered = [Path("nonexistent/file.py")]
        inventory = _make_inventory([_make_entry("nonexistent/file.py")])
        profile = _make_profile()

        result = analyze_uncovered_files(uncovered, inventory, profile, tmp_path)
        assert len(result) == 1
        assert result[0].module_purpose == "Could not read file"

    def test_complexity_hint_simple(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/simple.py",
            '''\
            """Simple module."""
            def one():
                pass
            ''',
        )

        uncovered = [Path("src/simple.py")]
        inventory = _make_inventory([_make_entry("src/simple.py")])
        profile = _make_profile()

        result = analyze_uncovered_files(uncovered, inventory, profile, tmp_path)
        assert result[0].complexity_hint == "simple"

    def test_complexity_hint_complex(self, tmp_path: Path) -> None:
        funcs = "\n".join(f"def func_{i}():\n    pass\n" for i in range(12))
        _write_file(tmp_path, "src/big.py", f'"""Big module."""\n{funcs}')

        uncovered = [Path("src/big.py")]
        inventory = _make_inventory([_make_entry("src/big.py")])
        profile = _make_profile()

        result = analyze_uncovered_files(uncovered, inventory, profile, tmp_path)
        assert result[0].complexity_hint == "complex"

    def test_js_file_extraction(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/utils.js",
            """\
            // Utility functions
            export function formatDate(date) { return date; }
            export const MAX_ITEMS = 100;
            function internal() {}
            """,
        )

        uncovered = [Path("src/utils.js")]
        inventory = _make_inventory([_make_entry("src/utils.js")])
        profile = _make_profile()

        result = analyze_uncovered_files(uncovered, inventory, profile, tmp_path)
        surface = result[0]
        assert "formatDate" in surface.exports
        assert "MAX_ITEMS" in surface.exports

    def test_empty_uncovered_list(self, tmp_path: Path) -> None:
        inventory = _make_inventory([])
        profile = _make_profile()
        result = analyze_uncovered_files([], inventory, profile, tmp_path)
        assert result == []


# ---------------------------------------------------------------------------
# GeneralLogicSurface
# ---------------------------------------------------------------------------


class TestGeneralLogicSurface:
    """Tests for the GeneralLogicSurface dataclass."""

    def test_surface_type(self) -> None:
        surface = GeneralLogicSurface(name="test")
        assert surface.surface_type == "general_logic"

    def test_to_dict(self) -> None:
        surface = GeneralLogicSurface(
            name="src/app.py",
            source_refs=[SourceRef(file_path="src/app.py")],
            file_path="src/app.py",
            module_purpose="Main application",
            exports=["def main()"],
            complexity_hint="simple",
        )
        d = surface.to_dict()
        assert d["surface_type"] == "general_logic"
        assert d["file_path"] == "src/app.py"
        assert d["module_purpose"] == "Main application"
        assert d["exports"] == ["def main()"]
        assert d["complexity_hint"] == "simple"

    def test_in_surface_collection(self) -> None:
        surface = GeneralLogicSurface(name="test")
        collection = SurfaceCollection(general_logic=[surface])
        assert len(collection) == 1
        assert list(collection) == [surface]

    def test_collection_to_dict_includes_general_logic(self) -> None:
        surface = GeneralLogicSurface(name="test", file_path="test.py")
        collection = SurfaceCollection(general_logic=[surface])
        d = collection.to_dict()
        assert "general_logic" in d
        assert len(d["general_logic"]) == 1
