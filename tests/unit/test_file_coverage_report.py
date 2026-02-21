"""Unit tests for the file coverage report generation."""

from __future__ import annotations

import json
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    GeneralLogicSurface,
    RouteSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult
from repo_mirror_kit.harvester.reports.file_coverage import (
    THRESHOLD_FILE_COVERAGE,
    compute_file_coverage,
    generate_file_coverage_json,
    generate_file_coverage_markdown,
    write_file_coverage_reports,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(path: str, category: str = "source") -> FileEntry:
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


# ---------------------------------------------------------------------------
# compute_file_coverage
# ---------------------------------------------------------------------------


class TestComputeFileCoverage:
    """Tests for compute_file_coverage()."""

    def test_all_covered(self) -> None:
        entries = [_make_entry("src/app.py"), _make_entry("src/utils.py")]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="app",
                    source_refs=[
                        SourceRef(file_path="src/app.py"),
                        SourceRef(file_path="src/utils.py"),
                    ],
                ),
            ],
        )

        report = compute_file_coverage(inventory, surfaces)
        assert report.total_source == 2
        assert report.covered_count == 2
        assert report.uncovered_count == 0
        assert report.coverage_percentage == 100.0
        assert report.gate_result.passed is True

    def test_some_uncovered(self) -> None:
        entries = [
            _make_entry("src/app.py"),
            _make_entry("src/utils.py"),
            _make_entry("src/orphan.py"),
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

        report = compute_file_coverage(inventory, surfaces)
        assert report.total_source == 3
        assert report.covered_count == 1
        assert report.uncovered_count == 2

    def test_non_source_excluded(self) -> None:
        entries = [
            _make_entry("src/app.py"),
            _make_entry("README.md", category="documentation"),
            _make_entry("logo.png", category="asset"),
        ]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection()

        report = compute_file_coverage(inventory, surfaces)
        assert report.total_source == 1
        assert report.excluded_count == 2

    def test_gate_fails_below_threshold(self) -> None:
        # 1 covered out of 20 = 5% (well below 90%)
        entries = [_make_entry(f"src/file_{i}.py") for i in range(20)]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="one",
                    source_refs=[SourceRef(file_path="src/file_0.py")],
                ),
            ],
        )

        report = compute_file_coverage(inventory, surfaces)
        assert report.gate_result.passed is False
        assert report.gate_result.threshold == THRESHOLD_FILE_COVERAGE

    def test_custom_threshold(self) -> None:
        entries = [_make_entry("src/a.py"), _make_entry("src/b.py")]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="a",
                    source_refs=[SourceRef(file_path="src/a.py")],
                ),
            ],
        )

        # 50% coverage, threshold 40% — should pass
        report = compute_file_coverage(inventory, surfaces, threshold=40.0)
        assert report.gate_result.passed is True

    def test_directory_coverage(self) -> None:
        entries = [
            _make_entry("src/app.py"),
            _make_entry("src/utils.py"),
            _make_entry("lib/helper.py"),
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

        report = compute_file_coverage(inventory, surfaces)
        dirs = {dc.directory: dc for dc in report.directory_coverage}
        assert "src" in dirs
        assert "lib" in dirs
        assert dirs["src"].total == 2
        assert dirs["src"].covered == 1
        assert dirs["lib"].total == 1
        assert dirs["lib"].uncovered == 1

    def test_empty_inventory(self) -> None:
        inventory = _make_inventory([])
        surfaces = SurfaceCollection()

        report = compute_file_coverage(inventory, surfaces)
        assert report.total_source == 0
        assert report.coverage_percentage == 100.0
        assert report.gate_result.passed is True

    def test_general_logic_surfaces_count_as_covered(self) -> None:
        entries = [_make_entry("src/app.py"), _make_entry("src/orphan.py")]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="app",
                    source_refs=[SourceRef(file_path="src/app.py")],
                ),
            ],
            general_logic=[
                GeneralLogicSurface(
                    name="orphan",
                    source_refs=[SourceRef(file_path="src/orphan.py")],
                    file_path="src/orphan.py",
                ),
            ],
        )

        report = compute_file_coverage(inventory, surfaces)
        assert report.covered_count == 2
        assert report.uncovered_count == 0


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------


class TestFileCoverageJson:
    """Tests for generate_file_coverage_json()."""

    def test_valid_json(self) -> None:
        entries = [_make_entry("src/app.py"), _make_entry("src/orphan.py")]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="app",
                    source_refs=[SourceRef(file_path="src/app.py")],
                ),
            ],
        )

        report = compute_file_coverage(inventory, surfaces)
        raw = generate_file_coverage_json(report)
        data = json.loads(raw)

        assert data["summary"]["total_source_files"] == 2
        assert data["summary"]["covered"] == 1
        assert data["summary"]["uncovered"] == 1
        assert "gate" in data
        assert data["gate"]["name"] == "File Coverage"
        assert "src/orphan.py" in data["uncovered_files"]
        assert len(data["directory_coverage"]) > 0

    def test_empty_report_json(self) -> None:
        inventory = _make_inventory([])
        surfaces = SurfaceCollection()
        report = compute_file_coverage(inventory, surfaces)
        raw = generate_file_coverage_json(report)
        data = json.loads(raw)
        assert data["summary"]["total_source_files"] == 0
        assert data["uncovered_files"] == []


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


class TestFileCoverageMarkdown:
    """Tests for generate_file_coverage_markdown()."""

    def test_contains_summary(self) -> None:
        entries = [_make_entry("src/app.py")]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection()
        report = compute_file_coverage(inventory, surfaces)

        md = generate_file_coverage_markdown(report)
        assert "# File Coverage Report" in md
        assert "Total source files" in md
        assert "File Coverage Gate" in md

    def test_uncovered_section_present(self) -> None:
        entries = [_make_entry("src/app.py"), _make_entry("lib/util.py")]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection()
        report = compute_file_coverage(inventory, surfaces)

        md = generate_file_coverage_markdown(report)
        assert "Uncovered Files by Directory" in md
        assert "`src/app.py`" in md

    def test_no_uncovered_section_when_all_covered(self) -> None:
        entries = [_make_entry("src/app.py")]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection(
            routes=[
                RouteSurface(
                    name="app",
                    source_refs=[SourceRef(file_path="src/app.py")],
                ),
            ],
        )
        report = compute_file_coverage(inventory, surfaces)

        md = generate_file_coverage_markdown(report)
        assert "Uncovered Files by Directory" not in md


# ---------------------------------------------------------------------------
# Write reports to disk
# ---------------------------------------------------------------------------


class TestWriteFileCoverageReports:
    """Tests for write_file_coverage_reports()."""

    def test_writes_both_files(self, tmp_path: Path) -> None:
        entries = [_make_entry("src/app.py")]
        inventory = _make_inventory(entries)
        surfaces = SurfaceCollection()
        report = compute_file_coverage(inventory, surfaces)

        json_path, md_path = write_file_coverage_reports(tmp_path, report)

        assert json_path.exists()
        assert md_path.exists()
        assert json_path.name == "file-coverage.json"
        assert md_path.name == "file-coverage.md"

        # Verify JSON is parseable
        data = json.loads(json_path.read_text())
        assert "summary" in data

        # Verify MD has content
        md = md_path.read_text()
        assert "# File Coverage Report" in md
