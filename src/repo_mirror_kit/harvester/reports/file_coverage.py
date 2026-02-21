"""File coverage report generation.

Produces per-file coverage status (covered/uncovered/excluded), overall
file coverage percentage, uncovered file grouping by directory, and a
directory coverage heatmap. Outputs ``file-coverage.json`` and
``file-coverage.md`` to the reports directory.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.file_coverage import (
    _SOURCE_CATEGORIES,
    DEFAULT_EXCLUSION_PATTERNS,
    _matches_any_exclusion,
)
from repo_mirror_kit.harvester.analyzers.surfaces import SurfaceCollection
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# Default file coverage threshold
THRESHOLD_FILE_COVERAGE: float = 90.0


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileStatus:
    """Coverage status of a single file.

    Attributes:
        path: Repository-relative file path.
        status: One of 'covered', 'uncovered', or 'excluded'.
    """

    path: str
    status: str  # covered | uncovered | excluded


@dataclass(frozen=True)
class DirectoryCoverage:
    """Coverage summary for a single directory.

    Attributes:
        directory: Directory path.
        total: Total source files in this directory.
        covered: Number of covered files.
        uncovered: Number of uncovered files.
    """

    directory: str
    total: int
    covered: int
    uncovered: int

    @property
    def percentage(self) -> float:
        """Return coverage percentage, or 100.0 if total is zero."""
        if self.total == 0:
            return 100.0
        return (self.covered / self.total) * 100.0


@dataclass(frozen=True)
class FileCoverageGateResult:
    """Result of the file coverage gate evaluation.

    Attributes:
        threshold: Required file coverage percentage.
        actual: Actual file coverage percentage.
        passed: Whether the gate passed.
    """

    threshold: float
    actual: float
    passed: bool


@dataclass(frozen=True)
class FileCoverageReport:
    """Complete file coverage analysis result.

    Attributes:
        file_statuses: Per-file coverage status.
        total_source: Total source files considered.
        covered_count: Number of covered files.
        uncovered_count: Number of uncovered files.
        excluded_count: Number of excluded files.
        coverage_percentage: Overall file coverage percentage.
        directory_coverage: Per-directory coverage summaries.
        gate_result: File coverage gate evaluation.
    """

    file_statuses: list[FileStatus]
    total_source: int
    covered_count: int
    uncovered_count: int
    excluded_count: int
    coverage_percentage: float
    directory_coverage: list[DirectoryCoverage]
    gate_result: FileCoverageGateResult = field(
        default_factory=lambda: FileCoverageGateResult(
            threshold=THRESHOLD_FILE_COVERAGE, actual=100.0, passed=True
        )
    )


# ---------------------------------------------------------------------------
# Report computation
# ---------------------------------------------------------------------------


def compute_file_coverage(
    inventory: InventoryResult,
    surfaces: SurfaceCollection,
    exclusion_patterns: tuple[str, ...] = DEFAULT_EXCLUSION_PATTERNS,
    threshold: float = THRESHOLD_FILE_COVERAGE,
) -> FileCoverageReport:
    """Compute file coverage report from inventory and surfaces.

    Args:
        inventory: File inventory from Stage B.
        surfaces: Extracted surfaces (including general_logic).
        exclusion_patterns: Glob patterns for excluded files.
        threshold: Coverage gate threshold percentage.

    Returns:
        A FileCoverageReport with per-file and per-directory metrics.
    """
    # Collect all file paths referenced by any surface
    covered_files: set[str] = set()
    for surface in surfaces:
        for ref in surface.source_refs:
            covered_files.add(ref.file_path)

    file_statuses: list[FileStatus] = []
    covered_count = 0
    uncovered_count = 0
    excluded_count = 0

    # Track per-directory stats
    dir_covered: dict[str, int] = defaultdict(int)
    dir_total: dict[str, int] = defaultdict(int)
    dir_uncovered: dict[str, int] = defaultdict(int)

    for entry in inventory.files:
        # Non-source files are excluded
        if entry.category not in _SOURCE_CATEGORIES:
            file_statuses.append(FileStatus(path=entry.path, status="excluded"))
            excluded_count += 1
            continue

        # Exclusion pattern matches
        if _matches_any_exclusion(entry.path, exclusion_patterns):
            file_statuses.append(FileStatus(path=entry.path, status="excluded"))
            excluded_count += 1
            continue

        # Get directory for heatmap
        parts = PurePosixPath(entry.path).parts
        directory = str(PurePosixPath(*parts[:-1])) if len(parts) > 1 else "."

        dir_total[directory] += 1

        if entry.path in covered_files:
            file_statuses.append(FileStatus(path=entry.path, status="covered"))
            covered_count += 1
            dir_covered[directory] += 1
        else:
            file_statuses.append(FileStatus(path=entry.path, status="uncovered"))
            uncovered_count += 1
            dir_uncovered[directory] += 1

    total_source = covered_count + uncovered_count
    if total_source == 0:
        coverage_pct = 100.0
    else:
        coverage_pct = (covered_count / total_source) * 100.0

    # Build directory coverage list, sorted by coverage % ascending (worst first)
    directory_coverage: list[DirectoryCoverage] = []
    for d in sorted(dir_total.keys()):
        dc = DirectoryCoverage(
            directory=d,
            total=dir_total[d],
            covered=dir_covered.get(d, 0),
            uncovered=dir_uncovered.get(d, 0),
        )
        directory_coverage.append(dc)
    directory_coverage.sort(key=lambda dc: dc.percentage)

    gate = FileCoverageGateResult(
        threshold=threshold,
        actual=coverage_pct,
        passed=coverage_pct >= threshold,
    )

    return FileCoverageReport(
        file_statuses=file_statuses,
        total_source=total_source,
        covered_count=covered_count,
        uncovered_count=uncovered_count,
        excluded_count=excluded_count,
        coverage_percentage=coverage_pct,
        directory_coverage=directory_coverage,
        gate_result=gate,
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_file_coverage_json(report: FileCoverageReport) -> str:
    """Generate machine-readable file-coverage.json content.

    Args:
        report: The file coverage report.

    Returns:
        A JSON string with file coverage data.
    """
    data: dict[str, Any] = {
        "summary": {
            "total_source_files": report.total_source,
            "covered": report.covered_count,
            "uncovered": report.uncovered_count,
            "excluded": report.excluded_count,
            "coverage_percentage": round(report.coverage_percentage, 2),
        },
        "gate": {
            "name": "File Coverage",
            "threshold": report.gate_result.threshold,
            "actual": round(report.gate_result.actual, 2),
            "passed": report.gate_result.passed,
        },
        "uncovered_files": [
            fs.path for fs in report.file_statuses if fs.status == "uncovered"
        ],
        "directory_coverage": [
            {
                "directory": dc.directory,
                "total": dc.total,
                "covered": dc.covered,
                "uncovered": dc.uncovered,
                "percentage": round(dc.percentage, 2),
            }
            for dc in report.directory_coverage
        ],
    }
    return json.dumps(data, indent=2)


def generate_file_coverage_markdown(report: FileCoverageReport) -> str:
    """Generate human-readable file-coverage.md content.

    Args:
        report: The file coverage report.

    Returns:
        A Markdown string with file coverage summary.
    """
    lines: list[str] = [
        "# File Coverage Report",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total source files | {report.total_source} |",
        f"| Covered | {report.covered_count} |",
        f"| Uncovered | {report.uncovered_count} |",
        f"| Excluded | {report.excluded_count} |",
        f"| Coverage | {report.coverage_percentage:.1f}% |",
        "",
        "## File Coverage Gate",
        "",
        "| Threshold | Actual | Status |",
        "|-----------|--------|--------|",
        f"| {report.gate_result.threshold:.0f}% | {report.gate_result.actual:.1f}% | {'PASS' if report.gate_result.passed else 'FAIL'} |",
        "",
    ]

    # Uncovered files grouped by directory
    if report.uncovered_count > 0:
        lines.append("## Uncovered Files by Directory")
        lines.append("")

        # Group uncovered files by directory
        by_dir: dict[str, list[str]] = defaultdict(list)
        for fs in report.file_statuses:
            if fs.status == "uncovered":
                parts = PurePosixPath(fs.path).parts
                directory = str(PurePosixPath(*parts[:-1])) if len(parts) > 1 else "."
                by_dir[directory].append(fs.path)

        for directory in sorted(by_dir.keys()):
            lines.append(f"### `{directory}/`")
            lines.append("")
            for f in sorted(by_dir[directory]):
                lines.append(f"- `{f}`")
            lines.append("")

    # Directory heatmap
    if report.directory_coverage:
        lines.append("## Directory Coverage Heatmap")
        lines.append("")
        lines.append("| Directory | Total | Covered | Uncovered | Coverage % |")
        lines.append("|-----------|-------|---------|-----------|------------|")
        for dc in report.directory_coverage:
            lines.append(
                f"| `{dc.directory}/` | {dc.total} | {dc.covered} | {dc.uncovered} | {dc.percentage:.1f}% |"
            )
        lines.append("")

    return "\n".join(lines)


def write_file_coverage_reports(
    output_dir: Path,
    report: FileCoverageReport,
) -> tuple[Path, Path]:
    """Write file-coverage.json and file-coverage.md to reports directory.

    Args:
        output_dir: Root output directory.
        report: The file coverage report.

    Returns:
        A tuple of (json_path, md_path) for the written files.
    """
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = reports_dir / "file-coverage.json"
    md_path = reports_dir / "file-coverage.md"

    json_content = generate_file_coverage_json(report)
    json_path.write_text(json_content, encoding="utf-8")
    logger.info("file_coverage_report_written", path=str(json_path), format="json")

    md_content = generate_file_coverage_markdown(report)
    md_path.write_text(md_content, encoding="utf-8")
    logger.info("file_coverage_report_written", path=str(md_path), format="markdown")

    return json_path, md_path
