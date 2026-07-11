"""Tests for bean confidence/gaps frontmatter and rendering (BEAN-070)."""

from __future__ import annotations

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    RouteSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.beans.templates import (
    derive_confidence_and_gaps,
    render_bean,
)
from repo_mirror_kit.harvester.generator.requirements_md import (
    _render_gaps_rollup,
)


def _api(request_schema: dict, response_schema: dict) -> ApiSurface:
    return ApiSurface(
        name="POST /x",
        method="POST",
        path="/x",
        request_schema=request_schema,
        response_schema=response_schema,
        source_refs=[SourceRef(file_path="app.py", start_line=1)],
    )


class TestDerivation:
    def test_declared_beats_inferred(self) -> None:
        surface = _api(
            {"fields": [], "confidence": "declared"},
            {"fields": [{"name": "id"}], "confidence": "inferred"},
        )
        confidence, gaps = derive_confidence_and_gaps(surface)
        assert confidence == "declared"
        # Contracts are determined, so no contract-level gaps. (Behavioral
        # gaps still fire without enrichment — BEAN-081.)
        assert not any("contract could not be inferred" in g for g in gaps)

    def test_unknown_markers_become_gaps(self) -> None:
        surface = _api({"unknown": True}, {"unknown": True})
        confidence, gaps = derive_confidence_and_gaps(surface)
        assert confidence == "structural"
        assert any("Request contract" in g for g in gaps)
        assert any("Response contract" in g for g in gaps)

    def test_enrichment_gaps_appended(self) -> None:
        surface = _api({"unknown": True}, {"fields": [{"name": "id"}]})
        surface.enrichment["gaps"] = ["Error responses undetermined."]
        _, gaps = derive_confidence_and_gaps(surface)
        assert "Error responses undetermined." in gaps

    def test_llm_confidence_for_enriched_non_api(self) -> None:
        route = RouteSurface(name="/home", path="/home", method="GET")
        route.enrichment["behavioral_description"] = "Shows the home page."
        confidence, _ = derive_confidence_and_gaps(route)
        assert confidence == "llm"


class TestRendering:
    def test_frontmatter_carries_confidence_and_gaps(self) -> None:
        surface = _api(
            {"unknown": True}, {"fields": [{"name": "id"}], "confidence": "inferred"}
        )
        bean = render_bean(surface, "BEAN-001")
        frontmatter = bean.split("---")[1]
        assert "confidence: inferred" in frontmatter
        assert "Request contract could not be inferred" in frontmatter

    def test_gaps_section_rendered_when_gaps_exist(self) -> None:
        surface = _api({"unknown": True}, {"unknown": True})
        bean = render_bean(surface, "BEAN-001")
        assert "## Gaps & unknowns" in bean
        assert "resolve" in bean

    def test_no_gaps_section_when_clean(self) -> None:
        # BEAN-081: "clean" now requires behavioral enrichment + error
        # contract too, not just determined request/response schemas.
        surface = _api(
            {"fields": [{"name": "a"}], "confidence": "declared"},
            {"fields": [{"name": "b"}], "confidence": "declared"},
        )
        surface.enrichment.update(
            {
                "behavioral_description": "Creates a widget.",
                "given_when_then": [{"given": "g", "when": "w", "then": "t"}],
                "data_flow": "request -> service -> db",
                "error_contract": [{"condition": "invalid", "status": 400}],
            }
        )
        bean = render_bean(surface, "BEAN-001")
        assert "## Gaps & unknowns" not in bean
        assert "confidence: declared" in bean

    def test_non_api_beans_default_structural(self) -> None:
        route = RouteSurface(
            name="/home",
            path="/home",
            method="GET",
            source_refs=[SourceRef(file_path="a.tsx", start_line=1)],
        )
        bean = render_bean(route, "BEAN-002")
        assert "confidence: structural" in bean
        # BEAN-081: an unenriched route declares its unknowns as gaps
        # (never TODO), so the frontmatter gaps list is non-empty.
        assert "gaps: []" not in bean
        assert "TODO:" not in bean
        assert "## Gaps & unknowns" in bean


class TestRequirementsRollup:
    def test_rollup_counts_gaps(self) -> None:
        surfaces = SurfaceCollection(
            apis=[
                _api({"unknown": True}, {"unknown": True}),
                _api({"fields": []}, {"fields": [{"name": "id"}]}),
            ]
        )
        rollup = _render_gaps_rollup(surfaces)
        # BEAN-081: both surfaces now carry behavioral/data-flow gaps in
        # addition to any contract gaps, so both are affected.
        assert "across 2 surface(s)" in rollup

    def test_rollup_clean_message(self) -> None:
        rollup = _render_gaps_rollup(SurfaceCollection())
        assert "No unresolved extraction gaps" in rollup
