"""Tests for repo_mirror_kit.harvester.inventory."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.inventory import (
    FileEntry,
    InventoryResult,
    SkippedFile,
    _categorize_file,
    _compute_hash,
    _is_binary,
    _matches_any_glob,
    _split_patterns,
    scan,
    write_report,
)


def _make_config(**overrides: object) -> HarvestConfig:
    """Create a HarvestConfig with sensible defaults for testing."""
    defaults: dict[str, object] = {
        "repo": "https://example.com/repo.git",
        "max_file_bytes": 1_000_000,
    }
    defaults.update(overrides)
    return HarvestConfig(**defaults)  # type: ignore[arg-type]


def _md5(content: bytes) -> str:
    """Compute MD5 hex digest for expected value comparison."""
    return hashlib.md5(content).hexdigest()  # noqa: S324


# ---------------------------------------------------------------------------
# _split_patterns
# ---------------------------------------------------------------------------


class TestSplitPatterns:
    def test_simple_names_separated_from_globs(self) -> None:
        simple, globs = _split_patterns(("node_modules", ".git", "**/*.min.*", "*.log"))
        assert simple == frozenset({"node_modules", ".git"})
        assert globs == ("**/*.min.*", "*.log")

    def test_empty_patterns(self) -> None:
        simple, globs = _split_patterns(())
        assert simple == frozenset()
        assert globs == ()

    def test_all_simple(self) -> None:
        simple, globs = _split_patterns(("build", "dist"))
        assert simple == frozenset({"build", "dist"})
        assert globs == ()

    def test_all_globs(self) -> None:
        simple, globs = _split_patterns(("**/*.py", "src/*.js"))
        assert simple == frozenset()
        assert set(globs) == {"**/*.py", "src/*.js"}

    def test_question_mark_is_glob(self) -> None:
        simple, globs = _split_patterns(("file?.txt",))
        assert simple == frozenset()
        assert globs == ("file?.txt",)

    def test_bracket_is_glob(self) -> None:
        simple, globs = _split_patterns(("[abc].py",))
        assert simple == frozenset()
        assert globs == ("[abc].py",)


# ---------------------------------------------------------------------------
# _matches_any_glob
# ---------------------------------------------------------------------------


class TestMatchesAnyGlob:
    def test_star_matches_extension(self) -> None:
        assert _matches_any_glob("src/main.py", ("*.py",))

    def test_doublestar_matches_nested(self) -> None:
        assert _matches_any_glob("lib/vendor/jquery.min.js", ("**/*.min.*",))

    def test_no_match(self) -> None:
        assert not _matches_any_glob("src/main.py", ("*.js",))

    def test_empty_patterns_no_match(self) -> None:
        assert not _matches_any_glob("anything.py", ())


# ---------------------------------------------------------------------------
# _is_binary
# ---------------------------------------------------------------------------


class TestIsBinary:
    def test_text_file_not_binary(self, tmp_path: Path) -> None:
        f = tmp_path / "hello.txt"
        f.write_text("Hello, world!\n")
        assert not _is_binary(f)

    def test_file_with_null_bytes_is_binary(self, tmp_path: Path) -> None:
        f = tmp_path / "binary.bin"
        f.write_bytes(b"some\x00binary\x00data")
        assert _is_binary(f)

    def test_empty_file_not_binary(self, tmp_path: Path) -> None:
        f = tmp_path / "empty"
        f.write_bytes(b"")
        assert not _is_binary(f)

    def test_nonexistent_file_not_binary(self, tmp_path: Path) -> None:
        f = tmp_path / "does_not_exist"
        assert not _is_binary(f)


# ---------------------------------------------------------------------------
# _compute_hash
# ---------------------------------------------------------------------------


class TestComputeHash:
    def test_known_content(self, tmp_path: Path) -> None:
        content = b"Hello, world!\n"
        f = tmp_path / "hello.txt"
        f.write_bytes(content)
        assert _compute_hash(f) == _md5(content)

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty"
        f.write_bytes(b"")
        assert _compute_hash(f) == _md5(b"")

    def test_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "missing"
        assert _compute_hash(f) == ""


# ---------------------------------------------------------------------------
# _categorize_file
# ---------------------------------------------------------------------------


class TestCategorizeFile:
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("src/main.py", "source"),
            ("lib/utils.js", "source"),
            ("app.ts", "source"),
            ("script.sh", "source"),
        ],
    )
    def test_source_files(self, path: str, expected: str) -> None:
        assert _categorize_file(path) == expected

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("config.yaml", "config"),
            ("settings.json", "config"),
            ("pyproject.toml", "config"),
            (".env", "config"),
            ("app.ini", "config"),
        ],
    )
    def test_config_by_extension(self, path: str, expected: str) -> None:
        assert _categorize_file(path) == expected

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("Dockerfile", "config"),
            ("Makefile", "config"),
            (".gitignore", "config"),
            (".editorconfig", "config"),
        ],
    )
    def test_config_by_filename(self, path: str, expected: str) -> None:
        assert _categorize_file(path) == expected

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("tests/test_main.py", "test"),
            ("spec/something_spec.js", "test"),
            ("__tests__/Button.test.js", "test"),
            ("test_utils.py", "test"),
        ],
    )
    def test_test_files(self, path: str, expected: str) -> None:
        assert _categorize_file(path) == expected

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("README.md", "documentation"),
            ("docs/guide.rst", "documentation"),
            ("CHANGELOG.txt", "documentation"),
        ],
    )
    def test_documentation_files(self, path: str, expected: str) -> None:
        assert _categorize_file(path) == expected

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("logo.png", "asset"),
            ("fonts/sans.woff2", "asset"),
            ("archive.zip", "asset"),
            ("photo.jpg", "asset"),
        ],
    )
    def test_asset_files(self, path: str, expected: str) -> None:
        assert _categorize_file(path) == expected

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("migrations/001_create_users.py", "migration"),
            ("alembic/versions/abc123.py", "migration"),
        ],
    )
    def test_migration_files(self, path: str, expected: str) -> None:
        assert _categorize_file(path) == expected

    def test_unknown_extension_defaults_to_source(self) -> None:
        assert _categorize_file("something.xyz") == "source"

    def test_migration_takes_priority_over_test(self) -> None:
        assert _categorize_file("tests/migrations/001.py") == "migration"


# ---------------------------------------------------------------------------
# scan — basic functionality
# ---------------------------------------------------------------------------


class TestScanBasic:
    def test_scans_text_files(self, tmp_path: Path) -> None:
        (tmp_path / "hello.py").write_text("print('hello')\n")
        (tmp_path / "readme.md").write_text("# Readme\n")
        config = _make_config(exclude=())
        result = scan(tmp_path, config)
        assert result.total_files == 2
        paths = [f.path for f in result.files]
        assert "hello.py" in paths
        assert "readme.md" in paths

    def test_file_entry_fields(self, tmp_path: Path) -> None:
        content = "x = 1\n"
        (tmp_path / "main.py").write_text(content)
        config = _make_config(exclude=())
        result = scan(tmp_path, config)
        assert result.total_files == 1
        entry = result.files[0]
        assert entry.path == "main.py"
        assert entry.size == len(content.encode())
        assert entry.extension == ".py"
        assert entry.hash == _md5(content.encode())
        assert entry.category == "source"

    def test_nested_directory_scanning(self, tmp_path: Path) -> None:
        sub = tmp_path / "src" / "pkg"
        sub.mkdir(parents=True)
        (sub / "mod.py").write_text("pass\n")
        config = _make_config(exclude=())
        result = scan(tmp_path, config)
        assert result.total_files == 1
        assert result.files[0].path == "src/pkg/mod.py"

    def test_empty_directory(self, tmp_path: Path) -> None:
        config = _make_config(exclude=())
        result = scan(tmp_path, config)
        assert result.total_files == 0
        assert result.total_size == 0
        assert result.files == []

    def test_total_size_sums_correctly(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("aaa")
        (tmp_path / "b.txt").write_text("bb")
        config = _make_config(exclude=())
        result = scan(tmp_path, config)
        assert result.total_size == 5


# ---------------------------------------------------------------------------
# scan — exclude filtering
# ---------------------------------------------------------------------------


class TestScanExcludeFiltering:
    def test_default_excludes_filter_node_modules(self, tmp_path: Path) -> None:
        nm = tmp_path / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("module.exports = {}")
        (tmp_path / "app.js").write_text("console.log('hi')")
        config = _make_config()
        result = scan(tmp_path, config)
        paths = [f.path for f in result.files]
        assert "app.js" in paths
        assert not any("node_modules" in p for p in paths)

    def test_default_excludes_filter_git_dir(self, tmp_path: Path) -> None:
        git_dir = tmp_path / ".git" / "objects"
        git_dir.mkdir(parents=True)
        (git_dir / "abc123").write_text("blob data")
        (tmp_path / "main.py").write_text("pass")
        config = _make_config()
        result = scan(tmp_path, config)
        assert result.total_files == 1
        assert result.files[0].path == "main.py"

    def test_default_excludes_filter_venv(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "site.py").write_text("pass")
        (tmp_path / "app.py").write_text("pass")
        config = _make_config()
        result = scan(tmp_path, config)
        assert result.total_files == 1

    def test_glob_exclude_min_files(self, tmp_path: Path) -> None:
        (tmp_path / "lib").mkdir()
        (tmp_path / "lib" / "jquery.min.js").write_text("minified")
        (tmp_path / "app.js").write_text("normal")
        config = _make_config()
        result = scan(tmp_path, config)
        paths = [f.path for f in result.files]
        assert "app.js" in paths
        assert "lib/jquery.min.js" not in paths

    def test_custom_exclude_adds_to_defaults(self, tmp_path: Path) -> None:
        (tmp_path / "keep.py").write_text("pass")
        logs = tmp_path / "logs"
        logs.mkdir()
        (logs / "app.log").write_text("log entry")
        config = _make_config(
            exclude=(
                "node_modules",
                ".git",
                ".venv",
                "dist",
                "build",
                "coverage",
                "**/*.min.*",
                "logs",
            )
        )
        result = scan(tmp_path, config)
        paths = [f.path for f in result.files]
        assert "keep.py" in paths
        assert not any("logs" in p for p in paths)

    def test_excluded_dirs_recorded_in_skipped(self, tmp_path: Path) -> None:
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "pkg.js").write_text("x")
        config = _make_config()
        result = scan(tmp_path, config)
        skip_paths = [s.path for s in result.skipped]
        assert "node_modules" in skip_paths

    def test_excluded_files_recorded_in_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "app.min.js").write_text("minified")
        config = _make_config()
        result = scan(tmp_path, config)
        skip_paths = [s.path for s in result.skipped]
        assert "app.min.js" in skip_paths
        skip_entry = next(s for s in result.skipped if s.path == "app.min.js")
        assert skip_entry.reason == "excluded"


# ---------------------------------------------------------------------------
# scan — include filtering
# ---------------------------------------------------------------------------


class TestScanIncludeFiltering:
    def test_include_restricts_to_matched_files(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("pass")
        (tmp_path / "style.css").write_text("body {}")
        (tmp_path / "app.js").write_text("x")
        config = _make_config(include=("*.py",), exclude=())
        result = scan(tmp_path, config)
        assert result.total_files == 1
        assert result.files[0].path == "main.py"

    def test_empty_include_includes_all(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("pass")
        (tmp_path / "b.js").write_text("x")
        config = _make_config(include=(), exclude=())
        result = scan(tmp_path, config)
        assert result.total_files == 2

    def test_include_with_doublestar(self, tmp_path: Path) -> None:
        sub = tmp_path / "src"
        sub.mkdir()
        (sub / "mod.py").write_text("pass")
        (tmp_path / "README.md").write_text("# Hi")
        config = _make_config(include=("src/**",), exclude=())
        result = scan(tmp_path, config)
        assert result.total_files == 1
        assert result.files[0].path == "src/mod.py"


# ---------------------------------------------------------------------------
# scan — size filtering
# ---------------------------------------------------------------------------


class TestScanSizeFiltering:
    def test_files_exceeding_max_bytes_skipped(self, tmp_path: Path) -> None:
        small = tmp_path / "small.txt"
        small.write_text("hi")
        big = tmp_path / "big.txt"
        big.write_bytes(b"x" * 500)
        config = _make_config(max_file_bytes=100, exclude=())
        result = scan(tmp_path, config)
        assert result.total_files == 1
        assert result.files[0].path == "small.txt"

    def test_too_large_recorded_with_reason(self, tmp_path: Path) -> None:
        big = tmp_path / "huge.dat"
        big.write_bytes(b"x" * 200)
        config = _make_config(max_file_bytes=100, exclude=())
        result = scan(tmp_path, config)
        skip = next(s for s in result.skipped if s.path == "huge.dat")
        assert skip.reason == "too_large"
        assert skip.size == 200

    def test_exact_max_bytes_included(self, tmp_path: Path) -> None:
        f = tmp_path / "exact.txt"
        f.write_bytes(b"x" * 100)
        config = _make_config(max_file_bytes=100, exclude=())
        result = scan(tmp_path, config)
        assert result.total_files == 1


# ---------------------------------------------------------------------------
# scan — binary detection
# ---------------------------------------------------------------------------


class TestScanBinaryDetection:
    def test_binary_files_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "script.py").write_text("pass")
        (tmp_path / "image.dat").write_bytes(b"\x89PNG\x00\x00")
        config = _make_config(exclude=())
        result = scan(tmp_path, config)
        assert result.total_files == 1
        assert result.files[0].path == "script.py"

    def test_binary_recorded_with_reason(self, tmp_path: Path) -> None:
        (tmp_path / "blob.bin").write_bytes(b"\x00\x01\x02")
        config = _make_config(exclude=())
        result = scan(tmp_path, config)
        skip = next(s for s in result.skipped if s.path == "blob.bin")
        assert skip.reason == "binary"
        assert skip.size == 3


# ---------------------------------------------------------------------------
# scan — deterministic ordering
# ---------------------------------------------------------------------------


class TestScanDeterministicOrder:
    def test_files_sorted_by_path(self, tmp_path: Path) -> None:
        (tmp_path / "z.py").write_text("pass")
        (tmp_path / "a.py").write_text("pass")
        sub = tmp_path / "m"
        sub.mkdir()
        (sub / "b.py").write_text("pass")
        config = _make_config(exclude=())
        result = scan(tmp_path, config)
        paths = [f.path for f in result.files]
        assert paths == sorted(paths)

    def test_consistent_across_runs(self, tmp_path: Path) -> None:
        for name in ("c.py", "a.py", "b.py"):
            (tmp_path / name).write_text(f"# {name}\n")
        config = _make_config(exclude=())
        r1 = scan(tmp_path, config)
        r2 = scan(tmp_path, config)
        assert [f.path for f in r1.files] == [f.path for f in r2.files]


# ---------------------------------------------------------------------------
# write_report
# ---------------------------------------------------------------------------


class TestWriteReport:
    def test_creates_inventory_json(self, tmp_path: Path) -> None:
        result = InventoryResult(
            files=[
                FileEntry(
                    path="main.py",
                    size=10,
                    extension=".py",
                    hash="abc123",
                    category="source",
                )
            ],
            skipped=[SkippedFile(path="node_modules", reason="excluded")],
            total_files=1,
            total_size=10,
            total_skipped=1,
        )
        report_path = write_report(tmp_path, result)
        assert report_path.exists()
        assert report_path.name == "inventory.json"
        assert report_path.parent.name == "reports"

    def test_json_content_structure(self, tmp_path: Path) -> None:
        result = InventoryResult(
            files=[
                FileEntry(
                    path="app.py",
                    size=20,
                    extension=".py",
                    hash="def456",
                    category="source",
                )
            ],
            skipped=[SkippedFile(path="big.dat", reason="too_large", size=9999)],
            total_files=1,
            total_size=20,
            total_skipped=1,
        )
        report_path = write_report(tmp_path, result)
        data = json.loads(report_path.read_text(encoding="utf-8"))

        assert len(data["files"]) == 1
        assert data["files"][0]["path"] == "app.py"
        assert data["files"][0]["hash"] == "def456"

        assert len(data["skipped"]) == 1
        assert data["skipped"][0]["reason"] == "too_large"
        assert data["skipped"][0]["size"] == 9999

        assert data["summary"]["total_files"] == 1
        assert data["summary"]["total_size"] == 20

    def test_skipped_without_size_omits_field(self, tmp_path: Path) -> None:
        result = InventoryResult(
            files=[],
            skipped=[SkippedFile(path=".git", reason="excluded")],
            total_files=0,
            total_size=0,
            total_skipped=1,
        )
        report_path = write_report(tmp_path, result)
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert "size" not in data["skipped"][0]

    def test_creates_reports_directory(self, tmp_path: Path) -> None:
        out = tmp_path / "output"
        result = InventoryResult(
            files=[], skipped=[], total_files=0, total_size=0, total_skipped=0
        )
        report_path = write_report(out, result)
        assert (out / "reports").is_dir()
        assert report_path.exists()


# ---------------------------------------------------------------------------
# Integration: scan + write_report
# ---------------------------------------------------------------------------


class TestScanIntegration:
    def test_full_pipeline(self, tmp_path: Path) -> None:
        """Scan a mock repo and write the report."""
        workdir = tmp_path / "repo"
        workdir.mkdir()
        (workdir / "src").mkdir()
        (workdir / "src" / "main.py").write_text("print('hello')\n")
        (workdir / "README.md").write_text("# Project\n")
        (workdir / "config.yaml").write_text("key: value\n")
        tests_dir = workdir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_main.py").write_text("def test_it(): pass\n")

        # Also create some files that should be excluded
        nm = workdir / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("exports = {}")
        git_dir = workdir / ".git" / "objects"
        git_dir.mkdir(parents=True)
        (git_dir / "pack").write_text("binary")

        config = _make_config()
        result = scan(workdir, config)

        # Verify included files
        paths = [f.path for f in result.files]
        assert "src/main.py" in paths
        assert "README.md" in paths
        assert "config.yaml" in paths
        assert "tests/test_main.py" in paths
        assert result.total_files == 4

        # Verify categories
        file_map = {f.path: f for f in result.files}
        assert file_map["src/main.py"].category == "source"
        assert file_map["README.md"].category == "documentation"
        assert file_map["config.yaml"].category == "config"
        assert file_map["tests/test_main.py"].category == "test"

        # Verify excluded dirs are in skipped
        skip_paths = [s.path for s in result.skipped]
        assert ".git" in skip_paths
        assert "node_modules" in skip_paths

        # Verify deterministic order
        assert paths == sorted(paths)

        # Write report and verify
        out_dir = tmp_path / "output"
        report_path = write_report(out_dir, result)
        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["summary"]["total_files"] == 4

    def test_with_state_checkpoint(self, tmp_path: Path) -> None:
        """Verify inventory works alongside StateManager."""
        from repo_mirror_kit.harvester.state import StateManager

        workdir = tmp_path / "repo"
        workdir.mkdir()
        (workdir / "app.py").write_text("pass\n")

        out_dir = tmp_path / "output"
        config = _make_config(exclude=())

        # Run scan
        result = scan(workdir, config)
        assert result.total_files == 1

        # Write report
        write_report(out_dir, result)

        # Checkpoint state
        mgr = StateManager(out_dir)
        mgr.initialize(["A", "B", "C"])
        mgr.complete_stage("B")
        assert mgr.is_stage_done("B")
