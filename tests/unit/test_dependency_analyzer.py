"""Unit tests for the dependency & package analyzer."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.dependencies import analyze_dependencies
from repo_mirror_kit.harvester.analyzers.surfaces import DependencySurface, SourceRef
from repo_mirror_kit.harvester.beans.templates import render_bean
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
            extension="." + p.rsplit(".", 1)[-1] if "." in p else "",
            hash="abc123",
            category="source",
        )
        for p in paths
    ]
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=len(files) * 100,
        total_skipped=0,
    )


def _make_profile(stacks: dict[str, float] | None = None) -> StackProfile:
    """Build a StackProfile with the given stacks."""
    stacks = stacks or {}
    return StackProfile(
        stacks=stacks,
        evidence={name: [] for name in stacks},
        signals=[],
    )


def _write_file(workdir: Path, rel_path: str, content: str) -> None:
    """Write a file under workdir with the given content."""
    full = workdir / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(textwrap.dedent(content), encoding="utf-8")


def _find_by_name(
    surfaces: list[DependencySurface], name: str
) -> DependencySurface | None:
    """Find a surface by package name."""
    for s in surfaces:
        if s.name == name:
            return s
    return None


# ---------------------------------------------------------------------------
# Empty / no-op
# ---------------------------------------------------------------------------


class TestEmptyInventory:
    def test_empty_inventory_returns_empty(self, tmp_path: Path) -> None:
        inventory = _make_inventory([])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)
        assert result == []


# ---------------------------------------------------------------------------
# JavaScript / TypeScript: package.json
# ---------------------------------------------------------------------------


class TestJavaScriptDependencies:
    def test_extracts_all_dependency_groups(self, tmp_path: Path) -> None:
        pkg = {
            "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
            "devDependencies": {"jest": "^29.0.0"},
            "peerDependencies": {"react": ">=16.0.0"},
        }
        _write_file(tmp_path, "package.json", json.dumps(pkg))
        inventory = _make_inventory(["package.json"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        react = _find_by_name(result, "react")
        assert react is not None
        assert react.version_constraint == "^18.2.0"
        assert react.purpose == "runtime"
        assert react.manifest_file == "package.json"
        assert react.is_direct is True

        jest = _find_by_name(result, "jest")
        assert jest is not None
        assert jest.purpose == "dev"

        # peerDependencies
        peer_react = [s for s in result if s.name == "react" and s.purpose == "peer"]
        assert len(peer_react) == 1
        assert peer_react[0].version_constraint == ">=16.0.0"

    def test_invalid_json_skipped(self, tmp_path: Path) -> None:
        _write_file(tmp_path, "package.json", "not valid json {")
        inventory = _make_inventory(["package.json"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)
        assert result == []

    def test_nested_package_json(self, tmp_path: Path) -> None:
        pkg = {"dependencies": {"express": "^4.18.0"}}
        _write_file(tmp_path, "packages/api/package.json", json.dumps(pkg))
        inventory = _make_inventory(["packages/api/package.json"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)
        assert len(result) == 1
        assert result[0].name == "express"
        assert result[0].manifest_file == "packages/api/package.json"


# ---------------------------------------------------------------------------
# Python: pyproject.toml
# ---------------------------------------------------------------------------


class TestPythonDependencies:
    def test_pyproject_toml_project_dependencies(self, tmp_path: Path) -> None:
        content = """\
            [project]
            dependencies = [
                "click>=8.0",
                "structlog>=23.1.0",
            ]
        """
        _write_file(tmp_path, "pyproject.toml", content)
        inventory = _make_inventory(["pyproject.toml"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        click = _find_by_name(result, "click")
        assert click is not None
        assert click.version_constraint == ">=8.0"
        assert click.purpose == "runtime"

    def test_pyproject_toml_optional_dependencies(self, tmp_path: Path) -> None:
        content = """\
            [project.optional-dependencies]
            dev = ["pytest>=7.0", "ruff>=0.1.0"]
            test = ["coverage>=7.0"]
        """
        _write_file(tmp_path, "pyproject.toml", content)
        inventory = _make_inventory(["pyproject.toml"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        pytest_dep = _find_by_name(result, "pytest")
        assert pytest_dep is not None
        assert pytest_dep.purpose == "dev"

        coverage_dep = _find_by_name(result, "coverage")
        assert coverage_dep is not None
        assert coverage_dep.purpose == "test"

    def test_pyproject_toml_build_system(self, tmp_path: Path) -> None:
        content = """\
            [build-system]
            requires = ["hatchling>=1.18"]
        """
        _write_file(tmp_path, "pyproject.toml", content)
        inventory = _make_inventory(["pyproject.toml"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        hatch = _find_by_name(result, "hatchling")
        assert hatch is not None
        assert hatch.purpose == "build"

    def test_requirements_txt(self, tmp_path: Path) -> None:
        content = """\
            # Core requirements
            flask==2.3.3
            sqlalchemy>=2.0
        """
        _write_file(tmp_path, "requirements.txt", content)
        inventory = _make_inventory(["requirements.txt"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        flask = _find_by_name(result, "flask")
        assert flask is not None
        assert flask.version_constraint == "==2.3.3"
        assert flask.purpose == "runtime"

    def test_requirements_dev_txt_classified_as_dev(self, tmp_path: Path) -> None:
        content = """\
            pytest>=7.0
        """
        _write_file(tmp_path, "requirements-dev.txt", content)
        inventory = _make_inventory(["requirements-dev.txt"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        assert len(result) == 1
        assert result[0].purpose == "dev"

    def test_requirements_txt_skips_comments_and_flags(self, tmp_path: Path) -> None:
        content = """\
            # A comment
            -r base.txt
            flask==2.3.3
        """
        _write_file(tmp_path, "requirements.txt", content)
        inventory = _make_inventory(["requirements.txt"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)
        assert len(result) == 1
        assert result[0].name == "flask"

    def test_pipfile(self, tmp_path: Path) -> None:
        content = """\
            [packages]
            django = ">=4.0"

            [dev-packages]
            pytest = "*"
        """
        _write_file(tmp_path, "Pipfile", content)
        inventory = _make_inventory(["Pipfile"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        django = _find_by_name(result, "django")
        assert django is not None
        assert django.purpose == "runtime"

        pytest_dep = _find_by_name(result, "pytest")
        assert pytest_dep is not None
        assert pytest_dep.purpose == "dev"
        assert pytest_dep.version_constraint == ""  # "*" normalized to ""


# ---------------------------------------------------------------------------
# Go: go.mod
# ---------------------------------------------------------------------------


class TestGoDependencies:
    def test_go_mod_require_block(self, tmp_path: Path) -> None:
        content = """\
            module example.com/app

            go 1.21

            require (
            \tgithub.com/gin-gonic/gin v1.9.1
            \tgithub.com/stretchr/testify v1.8.4 // indirect
            )
        """
        _write_file(tmp_path, "go.mod", content)
        inventory = _make_inventory(["go.mod"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        gin = _find_by_name(result, "github.com/gin-gonic/gin")
        assert gin is not None
        assert gin.version_constraint == "v1.9.1"
        assert gin.is_direct is True

        testify = _find_by_name(result, "github.com/stretchr/testify")
        assert testify is not None
        assert testify.is_direct is False

    def test_go_mod_single_require(self, tmp_path: Path) -> None:
        content = """\
            module example.com/app

            go 1.21

            require github.com/pkg/errors v0.9.1
        """
        _write_file(tmp_path, "go.mod", content)
        inventory = _make_inventory(["go.mod"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)
        assert len(result) == 1
        assert result[0].name == "github.com/pkg/errors"


# ---------------------------------------------------------------------------
# .NET: *.csproj
# ---------------------------------------------------------------------------


class TestDotNetDependencies:
    def test_csproj_package_references(self, tmp_path: Path) -> None:
        content = """\
            <Project Sdk="Microsoft.NET.Sdk.Web">
              <ItemGroup>
                <PackageReference Include="Microsoft.AspNetCore.OpenApi" Version="8.0.0" />
                <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
              </ItemGroup>
            </Project>
        """
        _write_file(tmp_path, "MyApp.csproj", content)
        inventory = _make_inventory(["MyApp.csproj"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        assert len(result) == 2
        openapi = _find_by_name(result, "Microsoft.AspNetCore.OpenApi")
        assert openapi is not None
        assert openapi.version_constraint == "8.0.0"
        assert openapi.purpose == "runtime"


# ---------------------------------------------------------------------------
# Ruby: Gemfile
# ---------------------------------------------------------------------------


class TestRubyDependencies:
    def test_gemfile_basic(self, tmp_path: Path) -> None:
        content = """\
            source 'https://rubygems.org'

            gem 'rails', '~> 7.0'
            gem 'pg'

            group :development, :test do
              gem 'rspec-rails'
            end
        """
        _write_file(tmp_path, "Gemfile", content)
        inventory = _make_inventory(["Gemfile"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        rails = _find_by_name(result, "rails")
        assert rails is not None
        assert rails.version_constraint == "~> 7.0"
        assert rails.purpose == "runtime"

        pg = _find_by_name(result, "pg")
        assert pg is not None


# ---------------------------------------------------------------------------
# Rust: Cargo.toml
# ---------------------------------------------------------------------------


class TestRustDependencies:
    def test_cargo_toml(self, tmp_path: Path) -> None:
        content = """\
            [package]
            name = "myapp"
            version = "0.1.0"

            [dependencies]
            serde = { version = "1.0", features = ["derive"] }
            tokio = "1.33"

            [dev-dependencies]
            criterion = "0.5"

            [build-dependencies]
            cc = "1.0"
        """
        _write_file(tmp_path, "Cargo.toml", content)
        inventory = _make_inventory(["Cargo.toml"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        serde = _find_by_name(result, "serde")
        assert serde is not None
        assert serde.version_constraint == "1.0"
        assert serde.purpose == "runtime"

        tokio = _find_by_name(result, "tokio")
        assert tokio is not None
        assert tokio.version_constraint == "1.33"

        criterion = _find_by_name(result, "criterion")
        assert criterion is not None
        assert criterion.purpose == "dev"

        cc = _find_by_name(result, "cc")
        assert cc is not None
        assert cc.purpose == "build"


# ---------------------------------------------------------------------------
# Lock file detection
# ---------------------------------------------------------------------------


class TestLockFileDetection:
    def test_lock_files_attached_to_surfaces(self, tmp_path: Path) -> None:
        pkg = {"dependencies": {"express": "^4.18.0"}}
        _write_file(tmp_path, "package.json", json.dumps(pkg))
        _write_file(tmp_path, "package-lock.json", "{}")
        inventory = _make_inventory(["package.json", "package-lock.json"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        assert len(result) == 1
        assert "package-lock.json" in result[0].lock_files

    def test_multiple_lock_files(self, tmp_path: Path) -> None:
        content = """\
            [project]
            dependencies = ["click>=8.0"]
        """
        _write_file(tmp_path, "pyproject.toml", content)
        _write_file(tmp_path, "uv.lock", "")
        _write_file(tmp_path, "poetry.lock", "")
        inventory = _make_inventory(["pyproject.toml", "uv.lock", "poetry.lock"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        assert len(result) == 1
        assert "uv.lock" in result[0].lock_files
        assert "poetry.lock" in result[0].lock_files

    def test_no_lock_files_empty_list(self, tmp_path: Path) -> None:
        pkg = {"dependencies": {"express": "^4.18.0"}}
        _write_file(tmp_path, "package.json", json.dumps(pkg))
        inventory = _make_inventory(["package.json"])
        result = analyze_dependencies(inventory, _make_profile(), tmp_path)

        assert len(result) == 1
        assert result[0].lock_files == []


# ---------------------------------------------------------------------------
# DependencySurface dataclass
# ---------------------------------------------------------------------------


class TestDependencySurface:
    def test_surface_type_set(self) -> None:
        s = DependencySurface(name="express")
        assert s.surface_type == "dependency"

    def test_to_dict(self) -> None:
        s = DependencySurface(
            name="express",
            version_constraint="^4.18.0",
            purpose="runtime",
            manifest_file="package.json",
            is_direct=True,
            lock_files=["package-lock.json"],
            source_refs=[SourceRef(file_path="package.json")],
        )
        d = s.to_dict()
        assert d["name"] == "express"
        assert d["version_constraint"] == "^4.18.0"
        assert d["purpose"] == "runtime"
        assert d["manifest_file"] == "package.json"
        assert d["is_direct"] is True
        assert d["lock_files"] == ["package-lock.json"]


# ---------------------------------------------------------------------------
# Bean template rendering
# ---------------------------------------------------------------------------


class TestDependencyBeanTemplate:
    def test_render_dependency_bean(self) -> None:
        s = DependencySurface(
            name="express",
            version_constraint="^4.18.0",
            purpose="runtime",
            manifest_file="package.json",
            is_direct=True,
            lock_files=["package-lock.json"],
            source_refs=[SourceRef(file_path="package.json")],
        )
        result = render_bean(s, "BEAN-100")
        assert "BEAN-100" in result
        assert "express" in result
        assert "^4.18.0" in result
        assert "runtime" in result
        assert "package.json" in result
        assert "Direct" in result
        assert "package-lock.json" in result
        assert "---" in result  # frontmatter

    def test_render_transitive_dependency(self) -> None:
        s = DependencySurface(
            name="debug",
            version_constraint="^4.3.0",
            purpose="runtime",
            manifest_file="package.json",
            is_direct=False,
            source_refs=[SourceRef(file_path="package.json")],
        )
        result = render_bean(s, "BEAN-101")
        assert "Transitive" in result


# ---------------------------------------------------------------------------
# SurfaceCollection integration
# ---------------------------------------------------------------------------


class TestSurfaceCollectionDependencies:
    def test_dependencies_in_collection(self) -> None:
        from repo_mirror_kit.harvester.analyzers.surfaces import SurfaceCollection

        dep = DependencySurface(name="express", purpose="runtime")
        collection = SurfaceCollection(dependencies=[dep])
        assert len(collection) == 1
        assert list(collection) == [dep]

        d = collection.to_dict()
        assert "dependencies" in d
        assert len(d["dependencies"]) == 1
