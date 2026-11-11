"""Tier-1 rebuild scoring: surface re-extraction diff (IMP-09 / WP-3.4).

Compares two harvest runs — the *original* project and an agentic *rebuild*
of it — by diffing their ``surfaces.json`` surface collections. For each
surface type it computes:

- **recall** — fraction of the original's surfaces that reappear in the
  rebuild ("did the rebuild reproduce what was there?").
- **precision** — fraction of the rebuild's surfaces that existed in the
  original ("did the rebuild avoid inventing surfaces?").

This is the cheapest signal in the recreation-fidelity ladder and reuses the
harvester's own extraction: harvest the rebuild the same way the original was
harvested, then compare. It reads the machine-readable ``surfaces.json``
emitted by :mod:`~repo_mirror_kit.harvester.reports.surface_map`. That
serialization is one-way (there is no ``SurfaceCollection`` loader in the
repo), so this module parses the JSON directly.

Surface identity within a category is, in order of preference:
``"<METHOD> <path>"`` (routes/apis), else ``path``, else the normalized
``name``. Identities are compared as sets, so duplicates collapse and
precision/recall stay within ``[0, 1]``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# The 16 surface categories, matching SurfaceCollection.to_dict() keys. Kept
# as an explicit tuple (not derived) so a scoring run over an old surfaces.json
# is stable even if the collection grows new categories later.
SURFACE_CATEGORIES: tuple[str, ...] = (
    "routes",
    "components",
    "apis",
    "models",
    "auth",
    "config",
    "crosscutting",
    "state_mgmt",
    "middleware",
    "integrations",
    "ui_flows",
    "build_deploy",
    "dependencies",
    "test_patterns",
    "seed_data",
    "screens",
    "general_logic",
)

SURFACES_FILENAME = "surfaces.json"


class ScoringError(Exception):
    """Raised when a surfaces.json file is missing or malformed."""


def _identity(surface: dict[str, Any]) -> str:
    """Derive a stable within-category identity for a surface dict.

    Prefers ``"<METHOD> <path>"`` (routes/apis carry both), falls back to
    ``path``, then the lowercased ``name``. Empty when the surface has none
    of these (should not happen — every Surface has a name).
    """
    method = str(surface.get("method", "")).strip()
    path = str(surface.get("path", "")).strip()
    if method and path:
        return f"{method.upper()} {path}"
    if path:
        return path
    return str(surface.get("name", "")).strip().lower()


def _identities(surfaces: list[Any]) -> set[str]:
    """Collect distinct, non-empty identities from a category's surface list."""
    result: set[str] = set()
    for surface in surfaces:
        if not isinstance(surface, dict):
            continue
        ident = _identity(surface)
        if ident:
            result.add(ident)
    return result


@dataclass(frozen=True)
class CategoryScore:
    """Precision/recall for a single surface category."""

    category: str
    original_count: int
    rebuilt_count: int
    matched: int
    missing: tuple[str, ...]  # identities in original, absent from rebuild
    extra: tuple[str, ...]  # identities in rebuild, absent from original

    @property
    def precision(self) -> float | None:
        """matched / rebuilt_count, or None when the rebuild has none."""
        if self.rebuilt_count == 0:
            return None
        return self.matched / self.rebuilt_count

    @property
    def recall(self) -> float | None:
        """matched / original_count, or None when the original has none."""
        if self.original_count == 0:
            return None
        return self.matched / self.original_count

    @property
    def f1(self) -> float | None:
        """Harmonic mean of precision and recall, or None if either is None."""
        p, r = self.precision, self.recall
        if p is None or r is None or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "original_count": self.original_count,
            "rebuilt_count": self.rebuilt_count,
            "matched": self.matched,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "missing": list(self.missing),
            "extra": list(self.extra),
        }


@dataclass(frozen=True)
class ScoreReport:
    """Full tier-1 surface-diff score for one rebuild."""

    categories: tuple[CategoryScore, ...]

    @property
    def total_original(self) -> int:
        return sum(c.original_count for c in self.categories)

    @property
    def total_rebuilt(self) -> int:
        return sum(c.rebuilt_count for c in self.categories)

    @property
    def total_matched(self) -> int:
        return sum(c.matched for c in self.categories)

    @property
    def overall_precision(self) -> float | None:
        """Micro-averaged precision across all categories."""
        if self.total_rebuilt == 0:
            return None
        return self.total_matched / self.total_rebuilt

    @property
    def overall_recall(self) -> float | None:
        """Micro-averaged recall across all categories."""
        if self.total_original == 0:
            return None
        return self.total_matched / self.total_original

    @property
    def overall_f1(self) -> float | None:
        p, r = self.overall_precision, self.overall_recall
        if p is None or r is None or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "total_original": self.total_original,
                "total_rebuilt": self.total_rebuilt,
                "total_matched": self.total_matched,
                "overall_precision": self.overall_precision,
                "overall_recall": self.overall_recall,
                "overall_f1": self.overall_f1,
            },
            "categories": [
                c.to_dict()
                for c in self.categories
                if c.original_count or c.rebuilt_count
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        """Human-readable score table, non-empty categories only."""

        def pct(value: float | None) -> str:
            return "n/a" if value is None else f"{value * 100:.1f}%"

        lines = [
            "# Rebuild score — tier-1 surface re-extraction diff",
            "",
            "How much of the original's extracted surface the rebuild reproduced "
            "(recall) and how much of the rebuild's surface was in the original "
            "(precision). Structural signal only — not behavioral parity.",
            "",
            "## Overall",
            "",
            f"- **Recall:** {pct(self.overall_recall)} "
            f"({self.total_matched}/{self.total_original} original surfaces reproduced)",
            f"- **Precision:** {pct(self.overall_precision)} "
            f"({self.total_matched}/{self.total_rebuilt} rebuild surfaces matched)",
            f"- **F1:** {pct(self.overall_f1)}",
            "",
            "## By surface type",
            "",
            "| Surface | Original | Rebuilt | Matched | Precision | Recall | F1 |",
            "|---|--:|--:|--:|--:|--:|--:|",
        ]
        for c in self.categories:
            if not (c.original_count or c.rebuilt_count):
                continue
            lines.append(
                f"| {c.category} | {c.original_count} | {c.rebuilt_count} | "
                f"{c.matched} | {pct(c.precision)} | {pct(c.recall)} | {pct(c.f1)} |"
            )
        lines.append("")

        missing_lines = [
            f"- `{c.category}`: {', '.join(c.missing)}"
            for c in self.categories
            if c.missing
        ]
        if missing_lines:
            lines.extend(["## Missing from rebuild", ""])
            lines.extend(missing_lines)
            lines.append("")
        return "\n".join(lines)


def load_surfaces(surfaces_json_path: Path) -> dict[str, list[Any]]:
    """Load the ``surfaces`` block from a ``surfaces.json`` file.

    Returns a mapping of category name → list of surface dicts. Categories
    absent from the file are returned as empty lists.

    Raises:
        ScoringError: if the file is missing or not valid surfaces JSON.
    """
    if not surfaces_json_path.is_file():
        raise ScoringError(f"surfaces file not found: {surfaces_json_path}")
    try:
        data = json.loads(surfaces_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScoringError(f"cannot read {surfaces_json_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ScoringError(f"malformed surfaces file: {surfaces_json_path}")

    surfaces = data.get("surfaces", data)
    if not isinstance(surfaces, dict):
        raise ScoringError(f"no 'surfaces' object in {surfaces_json_path}")

    result: dict[str, list[Any]] = {}
    for category in SURFACE_CATEGORIES:
        value = surfaces.get(category, [])
        result[category] = value if isinstance(value, list) else []
    return result


def score_surfaces(
    original: dict[str, list[Any]],
    rebuilt: dict[str, list[Any]],
) -> ScoreReport:
    """Score a rebuilt surface map against the original.

    Args:
        original: category → surface dicts, from the source harvest.
        rebuilt: category → surface dicts, from re-harvesting the rebuild.

    Returns:
        A :class:`ScoreReport` with per-category and overall precision/recall.
    """
    categories: list[CategoryScore] = []
    for category in SURFACE_CATEGORIES:
        orig_ids = _identities(original.get(category, []))
        rebuilt_ids = _identities(rebuilt.get(category, []))
        matched = orig_ids & rebuilt_ids
        categories.append(
            CategoryScore(
                category=category,
                original_count=len(orig_ids),
                rebuilt_count=len(rebuilt_ids),
                matched=len(matched),
                missing=tuple(sorted(orig_ids - rebuilt_ids)),
                extra=tuple(sorted(rebuilt_ids - orig_ids)),
            )
        )
    return ScoreReport(categories=tuple(categories))


def diff_harvest_dirs(original_dir: Path, rebuilt_dir: Path) -> ScoreReport:
    """Score two harvest output directories by their ``surfaces.json`` files.

    Each directory is a harvest ``--out`` root containing ``surfaces.json``.
    """
    original = load_surfaces(original_dir / SURFACES_FILENAME)
    rebuilt = load_surfaces(rebuilt_dir / SURFACES_FILENAME)
    return score_surfaces(original, rebuilt)


def write_score_reports(output_dir: Path, report: ScoreReport) -> tuple[Path, Path]:
    """Write ``rebuild-score.{json,md}`` into ``output_dir``.

    Returns the (json_path, markdown_path) tuple.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "rebuild-score.json"
    md_path = output_dir / "rebuild-score.md"
    json_path.write_text(report.to_json(), encoding="utf-8")
    md_path.write_text(report.to_markdown(), encoding="utf-8")
    return json_path, md_path
