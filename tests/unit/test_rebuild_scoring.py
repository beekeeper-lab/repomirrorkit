"""Unit tests for tier-1 rebuild scoring (surface re-extraction diff)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_mirror_kit.harvester.rebuild.scoring import (
    ScoringError,
    diff_harvest_dirs,
    load_surfaces,
    score_surfaces,
    write_score_reports,
)


def _surfaces(**by_category: list[dict]) -> dict[str, list]:
    """Build a category→surfaces mapping for scoring."""
    return dict(by_category)


def _write_surfaces_json(path: Path, surfaces: dict[str, list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"summary": {}, "surfaces": surfaces}), encoding="utf-8")


ROUTES = [
    {
        "name": "list_users",
        "surface_type": "route",
        "method": "GET",
        "path": "/api/users",
    },
    {
        "name": "create_user",
        "surface_type": "route",
        "method": "POST",
        "path": "/api/users",
    },
]
MODELS = [{"name": "User", "surface_type": "model"}]


def test_identical_surfaces_score_perfect() -> None:
    original = _surfaces(routes=list(ROUTES), models=list(MODELS))
    report = score_surfaces(original, original)
    assert report.overall_recall == 1.0
    assert report.overall_precision == 1.0
    assert report.overall_f1 == 1.0
    assert report.total_matched == report.total_original == 3


def test_missing_surface_lowers_recall() -> None:
    original = _surfaces(routes=list(ROUTES), models=list(MODELS))
    # Rebuild dropped one route.
    rebuilt = _surfaces(routes=[ROUTES[0]], models=list(MODELS))
    report = score_surfaces(original, rebuilt)
    assert report.overall_recall == pytest.approx(2 / 3)
    # Everything the rebuild produced was correct → precision 1.0.
    assert report.overall_precision == 1.0
    routes_score = next(c for c in report.categories if c.category == "routes")
    assert routes_score.missing == ("POST /api/users",)
    assert routes_score.recall == 0.5


def test_extra_surface_lowers_precision() -> None:
    original = _surfaces(routes=[ROUTES[0]])
    # Rebuild invented an extra endpoint.
    rebuilt = _surfaces(
        routes=[
            ROUTES[0],
            {
                "name": "delete_user",
                "surface_type": "route",
                "method": "DELETE",
                "path": "/api/users/{id}",
            },
        ]
    )
    report = score_surfaces(original, rebuilt)
    assert report.overall_recall == 1.0
    assert report.overall_precision == 0.5
    routes_score = next(c for c in report.categories if c.category == "routes")
    assert routes_score.extra == ("DELETE /api/users/{id}",)


def test_empty_category_yields_none_not_crash() -> None:
    report = score_surfaces(_surfaces(), _surfaces())
    assert report.overall_recall is None
    assert report.overall_precision is None
    assert report.overall_f1 is None
    routes_score = next(c for c in report.categories if c.category == "routes")
    assert routes_score.precision is None
    assert routes_score.recall is None


def test_identity_prefers_method_path_then_name() -> None:
    # Same name, different method+path → treated as distinct surfaces.
    original = _surfaces(
        apis=[
            {"name": "users", "surface_type": "api", "method": "GET", "path": "/u"},
            {"name": "users", "surface_type": "api", "method": "POST", "path": "/u"},
        ]
    )
    rebuilt = _surfaces(
        apis=[{"name": "users", "surface_type": "api", "method": "GET", "path": "/u"}]
    )
    report = score_surfaces(original, rebuilt)
    apis = next(c for c in report.categories if c.category == "apis")
    assert apis.original_count == 2
    assert apis.matched == 1
    assert apis.recall == 0.5


def test_name_only_identity_is_case_insensitive() -> None:
    original = _surfaces(models=[{"name": "User", "surface_type": "model"}])
    rebuilt = _surfaces(models=[{"name": "user", "surface_type": "model"}])
    report = score_surfaces(original, rebuilt)
    assert report.overall_recall == 1.0


def test_duplicate_identities_collapse() -> None:
    original = _surfaces(models=[{"name": "User"}, {"name": "User"}])
    report = score_surfaces(original, _surfaces(models=[{"name": "User"}]))
    models = next(c for c in report.categories if c.category == "models")
    assert models.original_count == 1  # deduped
    assert models.recall == 1.0


def test_diff_harvest_dirs_reads_surfaces_json(tmp_path: Path) -> None:
    orig_dir = tmp_path / "orig"
    rebuilt_dir = tmp_path / "rebuilt"
    _write_surfaces_json(orig_dir / "surfaces.json", _surfaces(routes=list(ROUTES)))
    _write_surfaces_json(rebuilt_dir / "surfaces.json", _surfaces(routes=[ROUTES[0]]))
    report = diff_harvest_dirs(orig_dir, rebuilt_dir)
    assert report.overall_recall == 0.5


def test_load_surfaces_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ScoringError):
        load_surfaces(tmp_path / "nope.json")


def test_load_surfaces_accepts_bare_surfaces_object(tmp_path: Path) -> None:
    # A file that is itself the surfaces object (no wrapping "surfaces" key).
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"routes": list(ROUTES)}), encoding="utf-8")
    loaded = load_surfaces(path)
    assert len(loaded["routes"]) == 2


def test_write_score_reports_emits_both_formats(tmp_path: Path) -> None:
    report = score_surfaces(
        _surfaces(routes=list(ROUTES)), _surfaces(routes=list(ROUTES))
    )
    json_path, md_path = write_score_reports(tmp_path, report)
    assert json_path.is_file() and md_path.is_file()
    data = json.loads(json_path.read_text())
    assert data["summary"]["overall_recall"] == 1.0
    assert "surface re-extraction diff" in md_path.read_text()
