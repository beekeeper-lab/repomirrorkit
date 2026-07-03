"""Fidelity (recreation-readiness) metrics and gates (BEAN-076).

The existence gates in :mod:`coverage` verify that every surface produced a
bean — pipeline plumbing. They cannot fail on shallow analysis. Fidelity
metrics measure *depth*: could a rebuild agent actually work from this
output?

- **API request contracts** — API surfaces whose request schema was
  determined (populated fields, or an explicitly-empty field list, which
  is a real answer). ``{"unknown": true}`` markers and empty dicts do
  not count.
- **API response contracts** — response fields extracted, or at least a
  declared response type name.
- **Model fields** — model surfaces with a non-empty field list.
- **Model relationships** — models carrying structured relationship
  details (BEAN-055). Only applicable when the repo has 2+ models.
- **Screen field mappings** — placeholder until ``ScreenSurface`` lands
  (BEAN-064); reported as N/A so the gap stays visible.
- **Placeholder-free beans** — written beans containing no ``TODO:``
  placeholder text. Informational by default (threshold 0): structural-only
  runs legitimately contain placeholders until enrichment fills them.

A category with zero applicable items is reported as **N/A** — visibly
distinct from 100%, never a silent vacuous pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers import SurfaceCollection

logger = structlog.get_logger()

# Default thresholds (percentages). Chosen so the checked-in fixtures pass
# with LLM enrichment off; raise deliberately as extraction deepens.
DEFAULT_FIDELITY_THRESHOLDS: dict[str, float] = {
    "api_request_contracts": 60.0,
    "api_response_contracts": 60.0,
    "model_fields": 80.0,
    "model_relationships": 50.0,
    "screen_field_mappings": 60.0,
    "placeholder_free_beans": 0.0,
}


@dataclass(frozen=True)
class FidelityMetric:
    """A single recreation-readiness measurement.

    Attributes:
        name: Metric key (matches DEFAULT_FIDELITY_THRESHOLDS).
        covered: Items meeting the depth bar.
        total: Applicable items (0 → metric is N/A).
        threshold: Required percentage for the gate.
    """

    name: str
    covered: int
    total: int
    threshold: float

    @property
    def applicable(self) -> bool:
        """Whether any items exist to measure."""
        return self.total > 0

    @property
    def percentage(self) -> float:
        """Covered percentage (0.0 when not applicable)."""
        if self.total == 0:
            return 0.0
        return round(100.0 * self.covered / self.total, 1)

    @property
    def passed(self) -> bool:
        """Gate outcome; N/A metrics pass but are reported distinctly."""
        if not self.applicable:
            return True
        return self.percentage >= self.threshold

    def to_dict(self) -> dict[str, object]:
        """Serialize for coverage.json."""
        return {
            "name": self.name,
            "covered": self.covered,
            "total": self.total,
            "percentage": self.percentage,
            "threshold": self.threshold,
            "applicable": self.applicable,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class FidelityEvaluation:
    """All fidelity metrics plus the combined gate outcome."""

    metrics: list[FidelityMetric]
    all_passed: bool = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "all_passed", all(m.passed for m in self.metrics))

    def to_dict(self) -> dict[str, object]:
        """Serialize for coverage.json."""
        return {
            "all_passed": self.all_passed,
            "metrics": [m.to_dict() for m in self.metrics],
        }


def _request_contract_determined(schema: dict[str, object]) -> bool:
    """Whether a request schema represents a determined contract."""
    return "fields" in schema


def _response_contract_determined(schema: dict[str, object]) -> bool:
    """Whether a response schema represents a determined contract."""
    fields = schema.get("fields")
    if isinstance(fields, list) and fields:
        return True
    return "type" in schema


def compute_fidelity(
    surfaces: SurfaceCollection,
    beans_dir: Path | None = None,
    thresholds: dict[str, float] | None = None,
) -> FidelityEvaluation:
    """Compute recreation-readiness metrics over surfaces and written beans.

    Args:
        surfaces: All extracted surfaces.
        beans_dir: Directory of written bean markdown files (optional; the
            placeholder metric is N/A without it).
        thresholds: Threshold overrides; defaults apply per metric.

    Returns:
        A FidelityEvaluation with per-metric results and overall outcome.
    """
    limits = {**DEFAULT_FIDELITY_THRESHOLDS, **(thresholds or {})}

    apis = surfaces.apis
    models = surfaces.models

    request_covered = sum(
        1 for s in apis if _request_contract_determined(s.request_schema)
    )
    response_covered = sum(
        1 for s in apis if _response_contract_determined(s.response_schema)
    )
    model_fields_covered = sum(1 for m in models if m.fields)
    relationship_covered = sum(1 for m in models if m.relationship_details)
    relationship_total = len(models) if len(models) >= 2 else 0

    placeholder_total = 0
    placeholder_free = 0
    if beans_dir is not None and beans_dir.is_dir():
        for bean_path in sorted(beans_dir.glob("BEAN-*.md")):
            placeholder_total += 1
            try:
                if "TODO:" not in bean_path.read_text(encoding="utf-8"):
                    placeholder_free += 1
            except OSError:
                continue

    metrics = [
        FidelityMetric(
            name="api_request_contracts",
            covered=request_covered,
            total=len(apis),
            threshold=limits["api_request_contracts"],
        ),
        FidelityMetric(
            name="api_response_contracts",
            covered=response_covered,
            total=len(apis),
            threshold=limits["api_response_contracts"],
        ),
        FidelityMetric(
            name="model_fields",
            covered=model_fields_covered,
            total=len(models),
            threshold=limits["model_fields"],
        ),
        FidelityMetric(
            name="model_relationships",
            covered=relationship_covered,
            total=relationship_total,
            threshold=limits["model_relationships"],
        ),
        FidelityMetric(
            name="screen_field_mappings",
            covered=0,
            total=0,  # ScreenSurface lands with BEAN-064
            threshold=limits["screen_field_mappings"],
        ),
        FidelityMetric(
            name="placeholder_free_beans",
            covered=placeholder_free,
            total=placeholder_total,
            threshold=limits["placeholder_free_beans"],
        ),
    ]

    evaluation = FidelityEvaluation(metrics=metrics)
    logger.info(
        "fidelity_computed",
        all_passed=evaluation.all_passed,
        metrics={
            m.name: (f"{m.percentage}%" if m.applicable else "n/a") for m in metrics
        },
    )
    return evaluation


_METRIC_LABELS: dict[str, str] = {
    "api_request_contracts": "API request contracts determined",
    "api_response_contracts": "API response contracts determined",
    "model_fields": "Models with extracted fields",
    "model_relationships": "Models with structured relationships",
    "screen_field_mappings": "Screen fields mapped to models",
    "placeholder_free_beans": "Beans free of TODO placeholders",
}


def render_fidelity_markdown(evaluation: FidelityEvaluation) -> str:
    """Render the fidelity section appended to coverage.md."""
    lines = [
        "",
        "## Fidelity (recreation-readiness)",
        "",
        "Depth metrics: could a rebuild agent work from this output?",
        "N/A means no applicable items were found — visibly distinct from",
        "a 100% pass.",
        "",
        "| Metric | Covered | Total | % | Threshold | Status |",
        "|--------|---------|-------|---|-----------|--------|",
    ]
    for metric in evaluation.metrics:
        label = _METRIC_LABELS.get(metric.name, metric.name)
        if not metric.applicable:
            lines.append(f"| {label} | - | - | N/A | {metric.threshold}% | N/A |")
            continue
        status = "PASS" if metric.passed else "FAIL"
        lines.append(
            f"| {label} | {metric.covered} | {metric.total} "
            f"| {metric.percentage}% | {metric.threshold}% | {status} |"
        )
    overall = "PASS" if evaluation.all_passed else "FAIL"
    lines.extend(["", f"**Fidelity gates: {overall}**", ""])
    return "\n".join(lines)
