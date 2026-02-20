"""Unit tests for behavioral requirement sections in bean templates.

Tests that all 11 renderers produce behavioral sections (Behavioral description,
Acceptance criteria, Data flow) and that the 4 new renderers (state_mgmt,
middleware, integration, ui_flow) produce their type-specific sections.
"""

from __future__ import annotations

from typing import Any

import pytest

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    ComponentSurface,
    ConfigSurface,
    CrosscuttingSurface,
    IntegrationSurface,
    MiddlewareSurface,
    ModelField,
    ModelSurface,
    RouteSurface,
    SourceRef,
    StateMgmtSurface,
    Surface,
    UIFlowSurface,
)
from repo_mirror_kit.harvester.beans.templates import (
    render_api_bean,
    render_auth_bean,
    render_bean,
    render_component_bean,
    render_config_bean,
    render_crosscutting_bean,
    render_integration_bean,
    render_middleware_bean,
    render_model_bean,
    render_route_bean,
    render_state_mgmt_bean,
    render_ui_flow_bean,
)

# ---------------------------------------------------------------------------
# Shared enrichment data
# ---------------------------------------------------------------------------

_ENRICHMENT: dict[str, Any] = {
    "behavioral_description": "This route serves the main dashboard.",
    "inferred_intent": "Allows users to view aggregated metrics.",
    "given_when_then": [
        {
            "given": "a logged-in user",
            "when": "they visit /dashboard",
            "then": "they see the metrics overview",
        },
    ],
    "data_flow": "Data flows from metrics-service through the API gateway.",
    "priority": "high",
    "dependencies": ["auth-service", "metrics-db"],
}


def _ref() -> SourceRef:
    return SourceRef(file_path="src/app.py", start_line=1, end_line=20)


# ---------------------------------------------------------------------------
# Surface factories (with and without enrichment)
# ---------------------------------------------------------------------------


def _surfaces_with_enrichment() -> list[tuple[str, Surface, str]]:
    """Return (label, surface, bean_id) tuples WITH enrichment data."""
    e = _ENRICHMENT
    return [
        ("route", RouteSurface(name="dash", path="/dash", method="GET", source_refs=[_ref()], enrichment=dict(e)), "BEAN-001"),
        ("component", ComponentSurface(name="widget", props=["x"], source_refs=[_ref()], enrichment=dict(e)), "BEAN-002"),
        ("api", ApiSurface(name="get_data", method="GET", path="/api/data", source_refs=[_ref()], enrichment=dict(e)), "BEAN-003"),
        ("model", ModelSurface(name="User", fields=[ModelField(name="id", field_type="int")], source_refs=[_ref()], enrichment=dict(e)), "BEAN-004"),
        ("auth", AuthSurface(name="rbac", roles=["admin"], source_refs=[_ref()], enrichment=dict(e)), "BEAN-005"),
        ("config", ConfigSurface(name="DB_URL", env_var_name="DB_URL", source_refs=[_ref()], enrichment=dict(e)), "BEAN-006"),
        ("crosscutting", CrosscuttingSurface(name="logging", concern_type="logging", source_refs=[_ref()], enrichment=dict(e)), "BEAN-007"),
        ("state_mgmt", StateMgmtSurface(name="app_store", store_name="app", pattern="redux", actions=["inc"], selectors=["getCount"], source_refs=[_ref()], enrichment=dict(e)), "BEAN-008"),
        ("middleware", MiddlewareSurface(name="cors", middleware_type="http", applies_to=["/api/*"], transforms=["add CORS headers"], source_refs=[_ref()], enrichment=dict(e)), "BEAN-009"),
        ("integration", IntegrationSurface(name="payment_hook", integration_type="webhook", target_service="Stripe", protocol="HTTPS", data_exchanged=["payment_event"], source_refs=[_ref()], enrichment=dict(e)), "BEAN-010"),
        ("ui_flow", UIFlowSurface(name="onboarding", flow_type="wizard", entry_point="/signup", steps=["create account", "verify email"], exit_points=["/dashboard"], source_refs=[_ref()], enrichment=dict(e)), "BEAN-011"),
    ]


def _surfaces_without_enrichment() -> list[tuple[str, Surface, str]]:
    """Return (label, surface, bean_id) tuples WITHOUT enrichment data."""
    return [
        ("route", RouteSurface(name="dash", path="/dash", method="GET", source_refs=[_ref()]), "BEAN-001"),
        ("component", ComponentSurface(name="widget", props=["x"], source_refs=[_ref()]), "BEAN-002"),
        ("api", ApiSurface(name="get_data", method="GET", path="/api/data", source_refs=[_ref()]), "BEAN-003"),
        ("model", ModelSurface(name="User", fields=[ModelField(name="id", field_type="int")], source_refs=[_ref()]), "BEAN-004"),
        ("auth", AuthSurface(name="rbac", roles=["admin"], source_refs=[_ref()]), "BEAN-005"),
        ("config", ConfigSurface(name="DB_URL", env_var_name="DB_URL", source_refs=[_ref()]), "BEAN-006"),
        ("crosscutting", CrosscuttingSurface(name="logging", concern_type="logging", source_refs=[_ref()]), "BEAN-007"),
        ("state_mgmt", StateMgmtSurface(name="app_store", store_name="app", pattern="redux", actions=["inc"], selectors=["getCount"], source_refs=[_ref()]), "BEAN-008"),
        ("middleware", MiddlewareSurface(name="cors", middleware_type="http", applies_to=["/api/*"], transforms=["add CORS headers"], source_refs=[_ref()]), "BEAN-009"),
        ("integration", IntegrationSurface(name="payment_hook", integration_type="webhook", target_service="Stripe", protocol="HTTPS", data_exchanged=["payment_event"], source_refs=[_ref()]), "BEAN-010"),
        ("ui_flow", UIFlowSurface(name="onboarding", flow_type="wizard", entry_point="/signup", steps=["create account", "verify email"], exit_points=["/dashboard"], source_refs=[_ref()]), "BEAN-011"),
    ]


# ---------------------------------------------------------------------------
# All 11 renderers produce behavioral sections
# ---------------------------------------------------------------------------


class TestBehavioralSectionsPresent:
    """Every renderer must emit the three shared behavioral sections."""

    @pytest.mark.parametrize(
        ("label", "surface", "bean_id"),
        _surfaces_with_enrichment(),
        ids=[t[0] for t in _surfaces_with_enrichment()],
    )
    def test_behavioral_description_section_present(
        self, label: str, surface: Surface, bean_id: str,
    ) -> None:
        result = render_bean(surface, bean_id)
        assert "## Behavioral description" in result

    @pytest.mark.parametrize(
        ("label", "surface", "bean_id"),
        _surfaces_with_enrichment(),
        ids=[t[0] for t in _surfaces_with_enrichment()],
    )
    def test_acceptance_criteria_section_present(
        self, label: str, surface: Surface, bean_id: str,
    ) -> None:
        result = render_bean(surface, bean_id)
        assert "## Acceptance criteria (Given/When/Then)" in result

    @pytest.mark.parametrize(
        ("label", "surface", "bean_id"),
        _surfaces_with_enrichment(),
        ids=[t[0] for t in _surfaces_with_enrichment()],
    )
    def test_data_flow_section_present(
        self, label: str, surface: Surface, bean_id: str,
    ) -> None:
        result = render_bean(surface, bean_id)
        assert "## Data flow" in result


# ---------------------------------------------------------------------------
# Enrichment content appears when enrichment data is provided
# ---------------------------------------------------------------------------


class TestEnrichmentContentPopulated:
    @pytest.mark.parametrize(
        ("label", "surface", "bean_id"),
        _surfaces_with_enrichment(),
        ids=[t[0] for t in _surfaces_with_enrichment()],
    )
    def test_behavioral_description_contains_enrichment(
        self, label: str, surface: Surface, bean_id: str,
    ) -> None:
        result = render_bean(surface, bean_id)
        assert "This route serves the main dashboard." in result

    @pytest.mark.parametrize(
        ("label", "surface", "bean_id"),
        _surfaces_with_enrichment(),
        ids=[t[0] for t in _surfaces_with_enrichment()],
    )
    def test_given_when_then_contains_enrichment(
        self, label: str, surface: Surface, bean_id: str,
    ) -> None:
        result = render_bean(surface, bean_id)
        assert "a logged-in user" in result
        assert "they visit /dashboard" in result
        assert "they see the metrics overview" in result

    @pytest.mark.parametrize(
        ("label", "surface", "bean_id"),
        _surfaces_with_enrichment(),
        ids=[t[0] for t in _surfaces_with_enrichment()],
    )
    def test_data_flow_contains_enrichment(
        self, label: str, surface: Surface, bean_id: str,
    ) -> None:
        result = render_bean(surface, bean_id)
        assert "Data flows from metrics-service through the API gateway." in result


# ---------------------------------------------------------------------------
# TODO placeholders when enrichment is absent
# ---------------------------------------------------------------------------


class TestTodoPlaceholders:
    @pytest.mark.parametrize(
        ("label", "surface", "bean_id"),
        _surfaces_without_enrichment(),
        ids=[t[0] for t in _surfaces_without_enrichment()],
    )
    def test_behavioral_description_has_todo(
        self, label: str, surface: Surface, bean_id: str,
    ) -> None:
        result = render_bean(surface, bean_id)
        assert "TODO: Describe the expected behavior" in result

    @pytest.mark.parametrize(
        ("label", "surface", "bean_id"),
        _surfaces_without_enrichment(),
        ids=[t[0] for t in _surfaces_without_enrichment()],
    )
    def test_acceptance_criteria_has_todo(
        self, label: str, surface: Surface, bean_id: str,
    ) -> None:
        result = render_bean(surface, bean_id)
        assert "TODO: Define Given/When/Then acceptance criteria." in result

    @pytest.mark.parametrize(
        ("label", "surface", "bean_id"),
        _surfaces_without_enrichment(),
        ids=[t[0] for t in _surfaces_without_enrichment()],
    )
    def test_data_flow_has_todo(
        self, label: str, surface: Surface, bean_id: str,
    ) -> None:
        result = render_bean(surface, bean_id)
        assert "TODO: Describe the data flow for this surface." in result


# ---------------------------------------------------------------------------
# Frontmatter includes priority and dependencies fields
# ---------------------------------------------------------------------------


class TestFrontmatterEnrichmentFields:
    @pytest.mark.parametrize(
        ("label", "surface", "bean_id"),
        _surfaces_with_enrichment(),
        ids=[t[0] for t in _surfaces_with_enrichment()],
    )
    def test_frontmatter_has_priority(
        self, label: str, surface: Surface, bean_id: str,
    ) -> None:
        result = render_bean(surface, bean_id)
        assert "priority: high" in result

    @pytest.mark.parametrize(
        ("label", "surface", "bean_id"),
        _surfaces_with_enrichment(),
        ids=[t[0] for t in _surfaces_with_enrichment()],
    )
    def test_frontmatter_has_dependencies(
        self, label: str, surface: Surface, bean_id: str,
    ) -> None:
        result = render_bean(surface, bean_id)
        assert "auth-service" in result
        assert "metrics-db" in result

    @pytest.mark.parametrize(
        ("label", "surface", "bean_id"),
        _surfaces_without_enrichment(),
        ids=[t[0] for t in _surfaces_without_enrichment()],
    )
    def test_frontmatter_default_priority_when_no_enrichment(
        self, label: str, surface: Surface, bean_id: str,
    ) -> None:
        result = render_bean(surface, bean_id)
        assert "priority: unassessed" in result


# ---------------------------------------------------------------------------
# State Management bean type-specific sections
# ---------------------------------------------------------------------------


class TestStateMgmtBeanSections:
    def test_has_store_overview(self) -> None:
        surface = StateMgmtSurface(
            name="counter_store",
            store_name="counter",
            pattern="redux",
            source_refs=[_ref()],
        )
        result = render_state_mgmt_bean(surface, "BEAN-100")
        assert "## Store overview" in result
        assert "counter" in result
        assert "redux" in result

    def test_has_actions(self) -> None:
        surface = StateMgmtSurface(
            name="counter_store",
            actions=["increment", "decrement"],
            source_refs=[_ref()],
        )
        result = render_state_mgmt_bean(surface, "BEAN-100")
        assert "## Actions" in result
        assert "`increment`" in result
        assert "`decrement`" in result

    def test_has_selectors(self) -> None:
        surface = StateMgmtSurface(
            name="counter_store",
            selectors=["getCount", "isLoading"],
            source_refs=[_ref()],
        )
        result = render_state_mgmt_bean(surface, "BEAN-100")
        assert "## Selectors" in result
        assert "`getCount`" in result
        assert "`isLoading`" in result

    def test_frontmatter_type(self) -> None:
        surface = StateMgmtSurface(name="store", source_refs=[_ref()])
        result = render_state_mgmt_bean(surface, "BEAN-100")
        assert "type: state_mgmt" in result


# ---------------------------------------------------------------------------
# Middleware bean type-specific sections
# ---------------------------------------------------------------------------


class TestMiddlewareBeanSections:
    def test_has_middleware_overview(self) -> None:
        surface = MiddlewareSurface(
            name="cors_middleware",
            middleware_type="http",
            execution_order=1,
            source_refs=[_ref()],
        )
        result = render_middleware_bean(surface, "BEAN-101")
        assert "## Middleware overview" in result
        assert "http" in result

    def test_has_applies_to(self) -> None:
        surface = MiddlewareSurface(
            name="cors_middleware",
            applies_to=["/api/*", "/webhook/*"],
            source_refs=[_ref()],
        )
        result = render_middleware_bean(surface, "BEAN-101")
        assert "## Applies to" in result
        assert "/api/*" in result
        assert "/webhook/*" in result

    def test_has_transforms(self) -> None:
        surface = MiddlewareSurface(
            name="cors_middleware",
            transforms=["add CORS headers", "validate origin"],
            source_refs=[_ref()],
        )
        result = render_middleware_bean(surface, "BEAN-101")
        assert "## Transforms" in result
        assert "add CORS headers" in result
        assert "validate origin" in result

    def test_frontmatter_type(self) -> None:
        surface = MiddlewareSurface(name="mw", source_refs=[_ref()])
        result = render_middleware_bean(surface, "BEAN-101")
        assert "type: middleware" in result


# ---------------------------------------------------------------------------
# Integration bean type-specific sections
# ---------------------------------------------------------------------------


class TestIntegrationBeanSections:
    def test_has_integration_overview(self) -> None:
        surface = IntegrationSurface(
            name="stripe_hook",
            integration_type="webhook",
            target_service="Stripe",
            protocol="HTTPS",
            source_refs=[_ref()],
        )
        result = render_integration_bean(surface, "BEAN-102")
        assert "## Integration overview" in result
        assert "webhook" in result
        assert "Stripe" in result
        assert "HTTPS" in result

    def test_has_data_exchanged(self) -> None:
        surface = IntegrationSurface(
            name="stripe_hook",
            data_exchanged=["payment_event", "refund_event"],
            source_refs=[_ref()],
        )
        result = render_integration_bean(surface, "BEAN-102")
        assert "## Data exchanged" in result
        assert "payment_event" in result
        assert "refund_event" in result

    def test_frontmatter_type(self) -> None:
        surface = IntegrationSurface(name="integ", source_refs=[_ref()])
        result = render_integration_bean(surface, "BEAN-102")
        assert "type: integration" in result


# ---------------------------------------------------------------------------
# UI Flow bean type-specific sections
# ---------------------------------------------------------------------------


class TestUIFlowBeanSections:
    def test_has_flow_overview(self) -> None:
        surface = UIFlowSurface(
            name="onboarding",
            flow_type="wizard",
            entry_point="/signup",
            source_refs=[_ref()],
        )
        result = render_ui_flow_bean(surface, "BEAN-103")
        assert "## Flow overview" in result
        assert "wizard" in result
        assert "/signup" in result

    def test_has_steps(self) -> None:
        surface = UIFlowSurface(
            name="onboarding",
            steps=["create account", "verify email", "set profile"],
            source_refs=[_ref()],
        )
        result = render_ui_flow_bean(surface, "BEAN-103")
        assert "## Steps" in result
        assert "create account" in result
        assert "verify email" in result
        assert "set profile" in result

    def test_has_exit_points(self) -> None:
        surface = UIFlowSurface(
            name="onboarding",
            exit_points=["/dashboard", "/logout"],
            source_refs=[_ref()],
        )
        result = render_ui_flow_bean(surface, "BEAN-103")
        assert "## Exit points" in result
        assert "/dashboard" in result
        assert "/logout" in result

    def test_frontmatter_type(self) -> None:
        surface = UIFlowSurface(name="flow", source_refs=[_ref()])
        result = render_ui_flow_bean(surface, "BEAN-103")
        assert "type: ui_flow" in result


# ---------------------------------------------------------------------------
# render_bean dispatch works for the 4 new types
# ---------------------------------------------------------------------------


class TestRenderBeanDispatchNewTypes:
    def test_dispatch_state_mgmt(self) -> None:
        surface = StateMgmtSurface(name="store", source_refs=[_ref()])
        result = render_bean(surface, "BEAN-200")
        assert "type: state_mgmt" in result
        assert "## Store overview" in result

    def test_dispatch_middleware(self) -> None:
        surface = MiddlewareSurface(name="mw", source_refs=[_ref()])
        result = render_bean(surface, "BEAN-201")
        assert "type: middleware" in result
        assert "## Middleware overview" in result

    def test_dispatch_integration(self) -> None:
        surface = IntegrationSurface(name="integ", source_refs=[_ref()])
        result = render_bean(surface, "BEAN-202")
        assert "type: integration" in result
        assert "## Integration overview" in result

    def test_dispatch_ui_flow(self) -> None:
        surface = UIFlowSurface(name="flow", source_refs=[_ref()])
        result = render_bean(surface, "BEAN-203")
        assert "type: ui_flow" in result
        assert "## Flow overview" in result
