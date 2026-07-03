"""Tests for fidelity (recreation-readiness) gates (BEAN-076)."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    ModelField,
    ModelRelationship,
    ModelSurface,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.reports.fidelity import (
    compute_fidelity,
    render_fidelity_markdown,
)


def _api(request_schema: dict | None, response_schema: dict | None) -> ApiSurface:
    return ApiSurface(
        name="GET /x",
        method="GET",
        path="/x",
        request_schema=request_schema or {},
        response_schema=response_schema or {},
    )


def _metric(evaluation, name: str):
    return next(m for m in evaluation.metrics if m.name == name)


class TestApiContractMetrics:
    def test_populated_and_explicit_empty_count_as_determined(self) -> None:
        surfaces = SurfaceCollection(
            apis=[
                _api(
                    {"fields": [{"name": "a"}], "confidence": "inferred"},
                    {"fields": [{"name": "b"}], "confidence": "inferred"},
                ),
                _api({"fields": [], "confidence": "inferred"}, {"unknown": True}),
            ]
        )
        evaluation = compute_fidelity(surfaces)
        assert _metric(evaluation, "api_request_contracts").percentage == 100.0
        assert _metric(evaluation, "api_response_contracts").percentage == 50.0

    def test_unknown_markers_do_not_count(self) -> None:
        surfaces = SurfaceCollection(apis=[_api({"unknown": True}, {"unknown": True})])
        evaluation = compute_fidelity(surfaces)
        request = _metric(evaluation, "api_request_contracts")
        assert request.covered == 0
        assert request.passed is False

    def test_type_only_response_counts(self) -> None:
        surfaces = SurfaceCollection(apis=[_api({"fields": []}, {"type": "OrderOut"})])
        evaluation = compute_fidelity(surfaces)
        assert _metric(evaluation, "api_response_contracts").covered == 1


class TestNAHandling:
    def test_empty_categories_are_na_not_pass(self) -> None:
        evaluation = compute_fidelity(SurfaceCollection())
        for name in ("api_request_contracts", "model_fields"):
            metric = _metric(evaluation, name)
            assert metric.applicable is False
            assert metric.passed is True  # N/A never blocks
        markdown = render_fidelity_markdown(evaluation)
        assert "N/A" in markdown
        assert "| 100.0% |" not in markdown  # N/A is not rendered as a rate

    def test_single_model_relationships_na(self) -> None:
        surfaces = SurfaceCollection(
            models=[ModelSurface(name="User", entity_name="User")]
        )
        evaluation = compute_fidelity(surfaces)
        assert _metric(evaluation, "model_relationships").applicable is False


class TestModelAndPlaceholderMetrics:
    def test_model_fields_and_relationships(self) -> None:
        surfaces = SurfaceCollection(
            models=[
                ModelSurface(
                    name="User",
                    entity_name="User",
                    fields=[ModelField(name="id", field_type="int")],
                    relationship_details=[
                        ModelRelationship(
                            source_model="User",
                            target_model="Post",
                            kind="one_to_many",
                        )
                    ],
                ),
                ModelSurface(name="Post", entity_name="Post"),
            ]
        )
        evaluation = compute_fidelity(surfaces)
        assert _metric(evaluation, "model_fields").percentage == 50.0
        relationships = _metric(evaluation, "model_relationships")
        assert relationships.total == 2
        assert relationships.covered == 1

    def test_placeholder_scan(self, tmp_path: Path) -> None:
        beans = tmp_path / "beans"
        beans.mkdir()
        (beans / "BEAN-001-clean.md").write_text("# Clean bean\n")
        (beans / "BEAN-002-todo.md").write_text("TODO: Describe behavior\n")
        evaluation = compute_fidelity(SurfaceCollection(), beans_dir=beans)
        metric = _metric(evaluation, "placeholder_free_beans")
        assert metric.total == 2
        assert metric.covered == 1


class TestThresholds:
    def test_threshold_override_flips_outcome(self) -> None:
        surfaces = SurfaceCollection(apis=[_api({"unknown": True}, {"unknown": True})])
        default = compute_fidelity(surfaces)
        assert default.all_passed is False
        relaxed = compute_fidelity(
            surfaces,
            thresholds={
                "api_request_contracts": 0.0,
                "api_response_contracts": 0.0,
            },
        )
        assert relaxed.all_passed is True

    def test_markdown_shows_pass_fail(self) -> None:
        surfaces = SurfaceCollection(
            apis=[
                _api(
                    {"fields": [{"name": "a"}]},
                    {"fields": [{"name": "b"}]},
                )
            ]
        )
        markdown = render_fidelity_markdown(compute_fidelity(surfaces))
        assert "PASS" in markdown
        assert "## Fidelity (recreation-readiness)" in markdown
