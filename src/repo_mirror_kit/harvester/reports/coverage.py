"""Coverage metrics computation, threshold evaluation, and report generation.

Implements Stage F of the harvester pipeline: computes coverage metrics
for each surface type (spec section 7.1), evaluates pass/fail thresholds
(spec section 7.2), and emits ``reports/coverage.json`` and
``reports/coverage.md``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import SurfaceCollection
from repo_mirror_kit.harvester.beans.writer import WrittenBean
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Threshold constants (spec section 7.2)
# ---------------------------------------------------------------------------

THRESHOLD_ROUTES: float = 95.0
THRESHOLD_APIS: float = 95.0
THRESHOLD_MODELS: float = 95.0
THRESHOLD_COMPONENTS: float = 85.0
THRESHOLD_ENV_VARS: float = 100.0
THRESHOLD_STATE_MGMT: float = 80.0
THRESHOLD_MIDDLEWARE: float = 80.0
THRESHOLD_INTEGRATIONS: float = 85.0
THRESHOLD_UI_FLOWS: float = 75.0
THRESHOLD_TEST_PATTERNS: float = 70.0


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricPair:
    """A total/covered pair for a single metric category.

    Attributes:
        total: Total count of items in this category.
        covered: Count of items with bean or documented.
    """

    total: int
    covered: int

    @property
    def percentage(self) -> float:
        """Return coverage percentage, or 100.0 if total is zero."""
        if self.total == 0:
            return 100.0
        return (self.covered / self.total) * 100.0


@dataclass(frozen=True)
class FileMetrics:
    """File-level metrics from inventory scan.

    Attributes:
        total: Total files discovered.
        scanned: Files that were scanned (not skipped).
        skipped: Files that were skipped.
    """

    total: int
    scanned: int
    skipped: int


@dataclass(frozen=True)
class CoverageMetrics:
    """All coverage metrics per spec section 7.1.

    Attributes:
        files: File-level counts.
        routes: Route coverage.
        shared_components: Component coverage.
        apis: API coverage.
        models: Model coverage.
        env_vars: Environment variable documentation coverage.
        auth_surfaces: Auth surface documentation coverage.
        state_mgmt: State management coverage.
        middleware: Middleware coverage.
        integrations: Integration coverage.
        ui_flows: UI flow coverage.
    """

    files: FileMetrics
    routes: MetricPair
    shared_components: MetricPair
    apis: MetricPair
    models: MetricPair
    env_vars: MetricPair
    auth_surfaces: MetricPair
    state_mgmt: MetricPair
    middleware: MetricPair
    integrations: MetricPair
    ui_flows: MetricPair
    test_patterns: MetricPair

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "files": asdict(self.files),
            "routes": {
                "total": self.routes.total,
                "with_page_bean": self.routes.covered,
            },
            "shared_components": {
                "total": self.shared_components.total,
                "with_bean": self.shared_components.covered,
            },
            "apis": {"total": self.apis.total, "with_bean": self.apis.covered},
            "models": {"total": self.models.total, "with_bean": self.models.covered},
            "env_vars": {
                "total": self.env_vars.total,
                "documented": self.env_vars.covered,
            },
            "auth_surfaces": {
                "total": self.auth_surfaces.total,
                "documented": self.auth_surfaces.covered,
            },
            "state_mgmt": {
                "total": self.state_mgmt.total,
                "with_bean": self.state_mgmt.covered,
            },
            "middleware": {
                "total": self.middleware.total,
                "with_bean": self.middleware.covered,
            },
            "integrations": {
                "total": self.integrations.total,
                "with_bean": self.integrations.covered,
            },
            "ui_flows": {
                "total": self.ui_flows.total,
                "with_bean": self.ui_flows.covered,
            },
            "test_patterns": {
                "total": self.test_patterns.total,
                "with_bean": self.test_patterns.covered,
            },
        }


@dataclass(frozen=True)
class GateResult:
    """Result of evaluating a single coverage gate.

    Attributes:
        name: Human-readable gate name.
        threshold: Required percentage.
        actual: Actual coverage percentage.
        passed: Whether the gate passed.
    """

    name: str
    threshold: float
    actual: float
    passed: bool


@dataclass(frozen=True)
class CoverageEvaluation:
    """Overall coverage evaluation result.

    Attributes:
        metrics: The computed coverage metrics.
        gates: Individual gate evaluation results.
        all_passed: True if all gates passed.
    """

    metrics: CoverageMetrics
    gates: list[GateResult]
    all_passed: bool = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "all_passed", all(g.passed for g in self.gates))


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------


def compute_metrics(
    surfaces: SurfaceCollection,
    beans: list[WrittenBean],
    inventory: InventoryResult,
) -> CoverageMetrics:
    """Compute coverage metrics from surfaces, beans, and inventory.

    Groups written beans by surface_type and counts how many surfaces
    of each type have a corresponding bean.

    Args:
        surfaces: Extracted surfaces from analyzers.
        beans: Written bean records from the bean writer.
        inventory: File inventory result for file-level metrics.

    Returns:
        A CoverageMetrics instance with all 11 metric categories.
    """
    bean_counts: dict[str, int] = {}
    for bean in beans:
        bean_counts[bean.surface_type] = bean_counts.get(bean.surface_type, 0) + 1

    return CoverageMetrics(
        files=FileMetrics(
            total=inventory.total_files + inventory.total_skipped,
            scanned=inventory.total_files,
            skipped=inventory.total_skipped,
        ),
        routes=MetricPair(
            total=len(surfaces.routes),
            covered=bean_counts.get("route", 0),
        ),
        shared_components=MetricPair(
            total=len(surfaces.components),
            covered=bean_counts.get("component", 0),
        ),
        apis=MetricPair(
            total=len(surfaces.apis),
            covered=bean_counts.get("api", 0),
        ),
        models=MetricPair(
            total=len(surfaces.models),
            covered=bean_counts.get("model", 0),
        ),
        env_vars=MetricPair(
            total=len(surfaces.config),
            covered=bean_counts.get("config", 0),
        ),
        auth_surfaces=MetricPair(
            total=len(surfaces.auth),
            covered=bean_counts.get("auth", 0),
        ),
        state_mgmt=MetricPair(
            total=len(surfaces.state_mgmt),
            covered=bean_counts.get("state_mgmt", 0),
        ),
        middleware=MetricPair(
            total=len(surfaces.middleware),
            covered=bean_counts.get("middleware", 0),
        ),
        integrations=MetricPair(
            total=len(surfaces.integrations),
            covered=bean_counts.get("integration", 0),
        ),
        ui_flows=MetricPair(
            total=len(surfaces.ui_flows),
            covered=bean_counts.get("ui_flow", 0),
        ),
        test_patterns=MetricPair(
            total=len(surfaces.test_patterns),
            covered=bean_counts.get("test_pattern", 0),
        ),
    )


# ---------------------------------------------------------------------------
# Threshold evaluation
# ---------------------------------------------------------------------------


def evaluate_thresholds(metrics: CoverageMetrics) -> CoverageEvaluation:
    """Evaluate coverage metrics against spec section 7.2 thresholds.

    Each gate passes if the actual percentage meets or exceeds the
    threshold, or if the total count is zero (vacuous pass).

    Args:
        metrics: Computed coverage metrics.

    Returns:
        A CoverageEvaluation with per-gate results and overall pass/fail.
    """
    gates = [
        _evaluate_gate("Routes", metrics.routes, THRESHOLD_ROUTES),
        _evaluate_gate("APIs", metrics.apis, THRESHOLD_APIS),
        _evaluate_gate("Models", metrics.models, THRESHOLD_MODELS),
        _evaluate_gate("Components", metrics.shared_components, THRESHOLD_COMPONENTS),
        _evaluate_gate("Env Vars", metrics.env_vars, THRESHOLD_ENV_VARS),
        _evaluate_gate("State Mgmt", metrics.state_mgmt, THRESHOLD_STATE_MGMT),
        _evaluate_gate("Middleware", metrics.middleware, THRESHOLD_MIDDLEWARE),
        _evaluate_gate("Integrations", metrics.integrations, THRESHOLD_INTEGRATIONS),
        _evaluate_gate("UI Flows", metrics.ui_flows, THRESHOLD_UI_FLOWS),
        _evaluate_gate("Test Patterns", metrics.test_patterns, THRESHOLD_TEST_PATTERNS),
    ]
    return CoverageEvaluation(metrics=metrics, gates=gates)


def _evaluate_gate(name: str, pair: MetricPair, threshold: float) -> GateResult:
    """Evaluate a single coverage gate."""
    actual = pair.percentage
    passed = actual >= threshold
    return GateResult(name=name, threshold=threshold, actual=actual, passed=passed)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_coverage_json(evaluation: CoverageEvaluation) -> str:
    """Generate machine-readable coverage.json content.

    Args:
        evaluation: The coverage evaluation result.

    Returns:
        A JSON string with metrics and gate results.
    """
    data: dict[str, Any] = {
        "metrics": evaluation.metrics.to_dict(),
        "gates": [
            {
                "name": g.name,
                "threshold": g.threshold,
                "actual": round(g.actual, 2),
                "passed": g.passed,
            }
            for g in evaluation.gates
        ],
        "all_passed": evaluation.all_passed,
    }
    return json.dumps(data, indent=2)


def generate_coverage_markdown(evaluation: CoverageEvaluation) -> str:
    """Generate human-readable coverage.md content.

    Args:
        evaluation: The coverage evaluation result.

    Returns:
        A Markdown string with coverage summary and gate results.
    """
    m = evaluation.metrics
    lines: list[str] = [
        "# Coverage Report",
        "",
        "## File Metrics",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Total files | {m.files.total} |",
        f"| Scanned | {m.files.scanned} |",
        f"| Skipped | {m.files.skipped} |",
        "",
        "## Surface Coverage",
        "",
        "| Surface Type | Total | Covered | Coverage % |",
        "|---|---|---|---|",
        f"| Routes | {m.routes.total} | {m.routes.covered} | {m.routes.percentage:.1f}% |",
        f"| Components | {m.shared_components.total} | {m.shared_components.covered} | {m.shared_components.percentage:.1f}% |",
        f"| APIs | {m.apis.total} | {m.apis.covered} | {m.apis.percentage:.1f}% |",
        f"| Models | {m.models.total} | {m.models.covered} | {m.models.percentage:.1f}% |",
        f"| Env Vars | {m.env_vars.total} | {m.env_vars.covered} | {m.env_vars.percentage:.1f}% |",
        f"| Auth Surfaces | {m.auth_surfaces.total} | {m.auth_surfaces.covered} | {m.auth_surfaces.percentage:.1f}% |",
        f"| State Mgmt | {m.state_mgmt.total} | {m.state_mgmt.covered} | {m.state_mgmt.percentage:.1f}% |",
        f"| Middleware | {m.middleware.total} | {m.middleware.covered} | {m.middleware.percentage:.1f}% |",
        f"| Integrations | {m.integrations.total} | {m.integrations.covered} | {m.integrations.percentage:.1f}% |",
        f"| UI Flows | {m.ui_flows.total} | {m.ui_flows.covered} | {m.ui_flows.percentage:.1f}% |",
        f"| Test Patterns | {m.test_patterns.total} | {m.test_patterns.covered} | {m.test_patterns.percentage:.1f}% |",
        "",
        "## Coverage Gates",
        "",
        "| Gate | Threshold | Actual | Status |",
        "|------|-----------|--------|--------|",
    ]

    for gate in evaluation.gates:
        status = "PASS" if gate.passed else "FAIL"
        lines.append(
            f"| {gate.name} | {gate.threshold:.0f}% | {gate.actual:.1f}% | {status} |"
        )

    lines.append("")
    overall = "ALL GATES PASSED" if evaluation.all_passed else "GATES FAILED"
    lines.append(f"**Overall: {overall}**")
    lines.append("")

    return "\n".join(lines)


def write_coverage_reports(
    output_dir: Path,
    evaluation: CoverageEvaluation,
) -> tuple[Path, Path]:
    """Write coverage.json and coverage.md to the reports directory.

    Args:
        output_dir: Root output directory (reports/ subdirectory is created).
        evaluation: The coverage evaluation result.

    Returns:
        A tuple of (json_path, md_path) for the written files.
    """
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = reports_dir / "coverage.json"
    md_path = reports_dir / "coverage.md"

    json_content = generate_coverage_json(evaluation)
    json_path.write_text(json_content, encoding="utf-8")
    logger.info("coverage_report_written", path=str(json_path), format="json")

    md_content = generate_coverage_markdown(evaluation)
    md_path.write_text(md_content, encoding="utf-8")
    logger.info("coverage_report_written", path=str(md_path), format="markdown")

    return json_path, md_path
