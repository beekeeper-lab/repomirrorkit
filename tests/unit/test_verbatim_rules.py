"""Tests for verbatim-rule tables + zero-TODO placeholder policy (BEAN-081)."""

from __future__ import annotations

import re

import pytest

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    ModelField,
    ModelSurface,
    RouteSurface,
    SourceRef,
)
from repo_mirror_kit.harvester.beans.templates import (
    derive_confidence_and_gaps,
    render_bean,
)


def _ref() -> SourceRef:
    return SourceRef(file_path="src/app.py", start_line=1, end_line=20)


def _all_surface_samples() -> list[tuple[str, object]]:
    """One instance of each renderer-backed surface, WITHOUT enrichment."""
    return [
        (
            "route",
            RouteSurface(name="r", path="/r", method="GET", source_refs=[_ref()]),
        ),
        (
            "api",
            ApiSurface(name="a", method="POST", path="/a", source_refs=[_ref()]),
        ),
        (
            "model",
            ModelSurface(
                name="M",
                fields=[ModelField(name="id", field_type="int")],
                source_refs=[_ref()],
            ),
        ),
        ("auth", AuthSurface(name="rbac", roles=["admin"], source_refs=[_ref()])),
    ]


class TestNoTodoPlaceholder:
    """Core BEAN-081 guarantee: rendered beans never contain a TODO literal."""

    @pytest.mark.parametrize(
        ("label", "surface"),
        _all_surface_samples(),
        ids=[s[0] for s in _all_surface_samples()],
    )
    def test_unenriched_bean_has_no_todo(self, label: str, surface: object) -> None:
        bean = render_bean(surface, "BEAN-001")  # type: ignore[arg-type]
        assert "TODO:" not in bean

    @pytest.mark.parametrize(
        ("label", "surface"),
        _all_surface_samples(),
        ids=[s[0] for s in _all_surface_samples()],
    )
    def test_unenriched_bean_declares_gaps(self, label: str, surface: object) -> None:
        # Absence must be declared, not silent.
        bean = render_bean(surface, "BEAN-001")  # type: ignore[arg-type]
        assert "## Gaps & unknowns" in bean
        assert "_Not determined by the harvest" in bean


class TestExactRulesTable:
    """`enrichment["exact_rules"]` renders a verbatim validation table (BEAN-082 feeds this)."""

    def test_model_validation_table_renders_exact_values(self) -> None:
        model = ModelSurface(
            name="User",
            fields=[ModelField(name="email", field_type="str")],
            source_refs=[_ref()],
        )
        model.enrichment["exact_rules"] = [
            {
                "field": "email",
                "rule": "regex",
                "value": r"^[^@]+@[^@]+$",
                "error_message": "Invalid email address",
                "confidence": "declared",
            }
        ]
        bean = render_bean(model, "BEAN-001")
        assert "| Field | Rule | Value / pattern | Error message | Confidence |" in bean
        assert "`^[^@]+@[^@]+$`" in bean  # exact pattern, verbatim
        assert "Invalid email address" in bean
        assert "declared" in bean
        # A determined validation table means no model-validation gap.
        _, gaps = derive_confidence_and_gaps(model)
        assert not any("Validation rules for this model" in g for g in gaps)

    def test_no_source_code_block_in_validation_table(self) -> None:
        model = ModelSurface(
            name="User",
            fields=[ModelField(name="age", field_type="int")],
            source_refs=[_ref()],
        )
        model.enrichment["exact_rules"] = [
            {"field": "age", "rule": "min", "value": "18", "confidence": "inferred"}
        ]
        bean = render_bean(model, "BEAN-001")
        assert "```python" not in bean
        assert "def " not in bean

    def test_pipe_in_value_is_escaped(self) -> None:
        # A regex with alternation (|) must not break the markdown table row.
        model = ModelSurface(
            name="User",
            fields=[ModelField(name="role", field_type="str")],
            source_refs=[_ref()],
        )
        model.enrichment["exact_rules"] = [
            {
                "field": "role",
                "rule": "enum",
                "value": "admin|editor|viewer",
                "confidence": "declared",
            }
        ]
        bean = render_bean(model, "BEAN-001")
        assert r"admin\|editor\|viewer" in bean
        # The row keeps exactly 5 columns: count only UNESCAPED pipes (the
        # real column separators), so the alternation pipes don't inject cols.
        table_rows = [ln for ln in bean.splitlines() if ln.startswith("| `role`")]
        assert table_rows
        for row in table_rows:
            unescaped_pipes = len(re.findall(r"(?<!\\)\|", row))
            assert unescaped_pipes == 6, row

    def test_none_and_newline_cells_are_safe(self) -> None:
        model = ModelSurface(
            name="User",
            fields=[ModelField(name="bio", field_type="str")],
            source_refs=[_ref()],
        )
        model.enrichment["exact_rules"] = [
            {
                "field": "bio",
                "rule": "max_length",
                "value": "500",
                "error_message": "Too long.\nShorten it.",
                "confidence": None,
            }
        ]
        bean = render_bean(model, "BEAN-001")
        # Newline collapsed to a space; no row split.
        assert "Too long. Shorten it." in bean


class TestRouteGapSplit:
    """BEAN-081 hardening: each empty route section has its own declared gap."""

    def test_route_declares_both_gaps_when_empty(self) -> None:
        route = RouteSurface(name="r", path="/r", method="GET", source_refs=[_ref()])
        _, gaps = derive_confidence_and_gaps(route)
        assert any("Validation rules for this route" in g for g in gaps)
        assert any("Error states for this route" in g for g in gaps)

    def test_route_partial_data_leaves_only_the_missing_gap(self) -> None:
        route = RouteSurface(name="r", path="/r", method="GET", source_refs=[_ref()])
        route.enrichment["exact_rules"] = [
            {"field": "q", "rule": "required", "value": "true"}
        ]
        _, gaps = derive_confidence_and_gaps(route)
        assert not any("Validation rules for this route" in g for g in gaps)
        assert any("Error states for this route" in g for g in gaps)


class TestBehavioralSignalEdge:
    def test_empty_signals_dict_still_declares_gap(self) -> None:
        route = RouteSurface(name="r", path="/r", method="GET", source_refs=[_ref()])
        route.enrichment["behavioral_signals"] = {"docstring": "", "test_names": []}
        _, gaps = derive_confidence_and_gaps(route)
        assert any("Behavioral description was not extracted" in g for g in gaps)


class TestErrorContractTable:
    """`enrichment["error_contract"]` renders a verbatim error table."""

    def test_api_error_table_renders(self) -> None:
        api = ApiSurface(name="a", method="POST", path="/a", source_refs=[_ref()])
        api.enrichment["error_contract"] = [
            {
                "condition": "missing name",
                "status": 400,
                "response": "name is required",
                "confidence": "inferred",
            }
        ]
        bean = render_bean(api, "BEAN-001")
        assert "| Condition | Status | Response | Confidence |" in bean
        assert "`400`" in bean
        assert "name is required" in bean
        _, gaps = derive_confidence_and_gaps(api)
        assert not any("Error responses for this endpoint" in g for g in gaps)


class TestTokenSession:
    def test_auth_token_session_renders_when_present(self) -> None:
        auth = AuthSurface(name="rbac", roles=["admin"], source_refs=[_ref()])
        # A human-readable description of the auth scheme, not a credential.
        session_desc = "JWT in Authorization header, 24h expiry."
        auth.enrichment["token_session"] = session_desc
        bean = render_bean(auth, "BEAN-001")
        assert "JWT in Authorization header, 24h expiry." in bean
        assert "TODO:" not in bean
