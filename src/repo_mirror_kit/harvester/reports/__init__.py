"""Report generators for harvested repository data."""

from __future__ import annotations

from repo_mirror_kit.harvester.reports.coverage import (
    CoverageEvaluation,
    CoverageMetrics,
    compute_metrics,
    evaluate_thresholds,
    write_coverage_reports,
)
from repo_mirror_kit.harvester.reports.file_coverage import (
    FileCoverageReport,
    compute_file_coverage,
    write_file_coverage_reports,
)
from repo_mirror_kit.harvester.reports.gaps import (
    GapReport,
    run_all_gap_queries,
    write_gaps_report,
)
from repo_mirror_kit.harvester.reports.surface_map import (
    generate_surface_map_json,
    generate_surface_map_markdown,
    write_surface_map,
)
from repo_mirror_kit.harvester.reports.traceability import build_traceability_maps

__all__ = [
    "CoverageEvaluation",
    "CoverageMetrics",
    "FileCoverageReport",
    "GapReport",
    "build_traceability_maps",
    "compute_file_coverage",
    "compute_metrics",
    "evaluate_thresholds",
    "generate_surface_map_json",
    "generate_surface_map_markdown",
    "run_all_gap_queries",
    "write_coverage_reports",
    "write_file_coverage_reports",
    "write_gaps_report",
    "write_surface_map",
]
