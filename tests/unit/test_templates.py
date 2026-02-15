"""Unit tests for bean template rendering."""

from __future__ import annotations

import pytest

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    ComponentSurface,
    ConfigSurface,
    CrosscuttingSurface,
    ModelField,
    ModelSurface,
    RouteSurface,
    SourceRef,
    Surface,
)
from repo_mirror_kit.harvester.beans.templates import (
    render_api_bean,
    render_auth_bean,
    render_bean,
    render_component_bean,
    render_config_bean,
    render_crosscutting_bean,
    render_model_bean,
    render_route_bean,
)

# --- Fixtures ---


def _make_ref() -> SourceRef:
    return SourceRef(file_path="src/app.py", start_line=10, end_line=25)


def _make_route() -> RouteSurface:
    return RouteSurface(
        name="Home Page",
        path="/home",
        method="GET",
        component_refs=["HomeView", "Sidebar"],
        api_refs=["/api/data", "/api/user"],
        auth_requirements=["login_required"],
        source_refs=[_make_ref()],
    )


def _make_component() -> ComponentSurface:
    return ComponentSurface(
        name="Sidebar",
        props=["items", "collapsed"],
        outputs=["item_selected"],
        usage_locations=["main_window.py"],
        states=["expanded", "collapsed"],
        source_refs=[_make_ref()],
    )


def _make_api() -> ApiSurface:
    return ApiSurface(
        name="get_users",
        method="GET",
        path="/api/users",
        auth="bearer",
        request_schema={"page": "int"},
        response_schema={"users": "list"},
        side_effects=["audit_log"],
        source_refs=[_make_ref()],
    )


def _make_model() -> ModelSurface:
    return ModelSurface(
        name="User",
        entity_name="User",
        fields=[
            ModelField(name="id", field_type="int", constraints=["primary_key"]),
            ModelField(name="email", field_type="str", constraints=["unique"]),
        ],
        relationships=["has_many:Order"],
        persistence_refs=["users_table"],
        source_refs=[_make_ref()],
    )


def _make_auth() -> AuthSurface:
    return AuthSurface(
        name="admin_auth",
        roles=["admin", "superadmin"],
        permissions=["read", "write", "delete"],
        rules=["require_mfa"],
        protected_endpoints=["/api/admin"],
        source_refs=[_make_ref()],
    )


def _make_config() -> ConfigSurface:
    return ConfigSurface(
        name="DATABASE_URL",
        env_var_name="DATABASE_URL",
        default_value="sqlite:///db.sqlite3",
        required=True,
        usage_locations=["config.py", "db.py"],
        source_refs=[_make_ref()],
    )


def _make_crosscutting() -> CrosscuttingSurface:
    return CrosscuttingSurface(
        name="logging",
        concern_type="logging",
        description="Structured logging across all services",
        affected_files=["app.py", "api.py", "worker.py"],
        source_refs=[_make_ref()],
    )


# --- Frontmatter Tests ---


class TestFrontmatter:
    def test_frontmatter_contains_required_fields(self) -> None:
        result = render_route_bean(_make_route(), "BEAN-001")
        assert "---" in result
        assert "id: BEAN-001" in result
        assert "type: page" in result
        assert '"Home Page"' in result
        assert "source_refs:" in result
        assert "traceability:" in result
        assert "status: draft" in result

    def test_frontmatter_source_refs_serialized(self) -> None:
        result = render_route_bean(_make_route(), "BEAN-001")
        assert "src/app.py" in result
        assert "10" in result

    def test_frontmatter_status_always_draft(self) -> None:
        for renderer, surface in [
            (render_route_bean, _make_route()),
            (render_component_bean, _make_component()),
            (render_api_bean, _make_api()),
            (render_model_bean, _make_model()),
            (render_auth_bean, _make_auth()),
            (render_config_bean, _make_config()),
            (render_crosscutting_bean, _make_crosscutting()),
        ]:
            result = renderer(surface, "BEAN-999")
            assert "status: draft" in result


# --- Route Bean Tests (Spec 8.3: 8 sections) ---


class TestRouteBeanTemplate:
    def test_renders_with_sample_data(self) -> None:
        result = render_route_bean(_make_route(), "BEAN-001")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_has_eight_required_sections(self) -> None:
        result = render_route_bean(_make_route(), "BEAN-001")
        assert "## Overview" in result
        assert "## User stories" in result
        assert "## Functional requirements" in result
        assert "## UI elements" in result
        assert "## Data & API interactions" in result
        assert "## Validation & error states" in result
        assert "## Acceptance criteria" in result
        assert "## Open questions" in result

    def test_contains_route_path(self) -> None:
        result = render_route_bean(_make_route(), "BEAN-001")
        assert "/home" in result
        assert "GET" in result

    def test_contains_component_refs(self) -> None:
        result = render_route_bean(_make_route(), "BEAN-001")
        assert "HomeView" in result
        assert "Sidebar" in result

    def test_contains_api_refs(self) -> None:
        result = render_route_bean(_make_route(), "BEAN-001")
        assert "/api/data" in result
        assert "/api/user" in result

    def test_frontmatter_type_is_page(self) -> None:
        result = render_route_bean(_make_route(), "BEAN-001")
        assert "type: page" in result


# --- Component Bean Tests (Spec 8.4: 6 sections) ---


class TestComponentBeanTemplate:
    def test_renders_with_sample_data(self) -> None:
        result = render_component_bean(_make_component(), "BEAN-002")
        assert isinstance(result, str)

    def test_has_six_required_sections(self) -> None:
        result = render_component_bean(_make_component(), "BEAN-002")
        assert "## Purpose" in result
        assert "## Props/inputs contract" in result
        assert "## Outputs/events" in result
        assert "## States" in result
        assert "## Usage locations" in result
        assert "## Acceptance criteria" in result

    def test_contains_props(self) -> None:
        result = render_component_bean(_make_component(), "BEAN-002")
        assert "`items`" in result
        assert "`collapsed`" in result

    def test_contains_outputs(self) -> None:
        result = render_component_bean(_make_component(), "BEAN-002")
        assert "`item_selected`" in result

    def test_contains_states(self) -> None:
        result = render_component_bean(_make_component(), "BEAN-002")
        assert "expanded" in result
        assert "collapsed" in result

    def test_frontmatter_type_is_component(self) -> None:
        result = render_component_bean(_make_component(), "BEAN-002")
        assert "type: component" in result


# --- API Bean Tests (Spec 8.5: 8 sections) ---


class TestApiBeanTemplate:
    def test_renders_with_sample_data(self) -> None:
        result = render_api_bean(_make_api(), "BEAN-003")
        assert isinstance(result, str)

    def test_has_eight_required_sections(self) -> None:
        result = render_api_bean(_make_api(), "BEAN-003")
        assert "## Endpoints" in result
        assert "## Auth" in result
        assert "## Request schema" in result
        assert "## Response schema" in result
        assert "## Errors" in result
        assert "## Side effects" in result
        assert "## Acceptance criteria" in result
        assert "## Examples" in result

    def test_contains_endpoint_info(self) -> None:
        result = render_api_bean(_make_api(), "BEAN-003")
        assert "GET" in result
        assert "/api/users" in result

    def test_contains_auth(self) -> None:
        result = render_api_bean(_make_api(), "BEAN-003")
        assert "bearer" in result

    def test_contains_schemas(self) -> None:
        result = render_api_bean(_make_api(), "BEAN-003")
        assert '"page"' in result
        assert '"users"' in result

    def test_contains_side_effects(self) -> None:
        result = render_api_bean(_make_api(), "BEAN-003")
        assert "audit_log" in result

    def test_frontmatter_type_is_api(self) -> None:
        result = render_api_bean(_make_api(), "BEAN-003")
        assert "type: api" in result


# --- Model Bean Tests (Spec 8.6: 6 sections) ---


class TestModelBeanTemplate:
    def test_renders_with_sample_data(self) -> None:
        result = render_model_bean(_make_model(), "BEAN-004")
        assert isinstance(result, str)

    def test_has_six_required_sections(self) -> None:
        result = render_model_bean(_make_model(), "BEAN-004")
        assert "## Entity description" in result
        assert "## Fields" in result
        assert "## Relationships" in result
        assert "## Persistence" in result
        assert "## Validation rules" in result
        assert "## Acceptance criteria" in result

    def test_contains_fields(self) -> None:
        result = render_model_bean(_make_model(), "BEAN-004")
        assert "`id`" in result
        assert "int" in result
        assert "`email`" in result
        assert "str" in result

    def test_contains_constraints(self) -> None:
        result = render_model_bean(_make_model(), "BEAN-004")
        assert "primary_key" in result
        assert "unique" in result

    def test_contains_relationships(self) -> None:
        result = render_model_bean(_make_model(), "BEAN-004")
        assert "has_many:Order" in result

    def test_contains_persistence(self) -> None:
        result = render_model_bean(_make_model(), "BEAN-004")
        assert "users_table" in result

    def test_frontmatter_type_is_model(self) -> None:
        result = render_model_bean(_make_model(), "BEAN-004")
        assert "type: model" in result


# --- Auth Bean Tests (Spec 8.7: 4 sections) ---


class TestAuthBeanTemplate:
    def test_renders_with_sample_data(self) -> None:
        result = render_auth_bean(_make_auth(), "BEAN-005")
        assert isinstance(result, str)

    def test_has_four_required_sections(self) -> None:
        result = render_auth_bean(_make_auth(), "BEAN-005")
        assert "## Roles/permissions/rules" in result
        assert "## Protected routes/endpoints map" in result
        assert "## Token/session assumptions" in result
        assert "## Acceptance criteria" in result

    def test_contains_roles(self) -> None:
        result = render_auth_bean(_make_auth(), "BEAN-005")
        assert "admin" in result
        assert "superadmin" in result

    def test_contains_permissions(self) -> None:
        result = render_auth_bean(_make_auth(), "BEAN-005")
        assert "read" in result
        assert "write" in result
        assert "delete" in result

    def test_contains_rules(self) -> None:
        result = render_auth_bean(_make_auth(), "BEAN-005")
        assert "require_mfa" in result

    def test_contains_protected_endpoints(self) -> None:
        result = render_auth_bean(_make_auth(), "BEAN-005")
        assert "/api/admin" in result

    def test_frontmatter_type_is_auth(self) -> None:
        result = render_auth_bean(_make_auth(), "BEAN-005")
        assert "type: auth" in result


# --- Config Bean Tests (Spec 8.8: 4 sections) ---


class TestConfigBeanTemplate:
    def test_renders_with_sample_data(self) -> None:
        result = render_config_bean(_make_config(), "BEAN-006")
        assert isinstance(result, str)

    def test_has_four_required_sections(self) -> None:
        result = render_config_bean(_make_config(), "BEAN-006")
        assert "## Env vars + defaults" in result
        assert "## Feature flags" in result
        assert "## Required external services" in result
        assert "## Acceptance criteria" in result

    def test_contains_env_var(self) -> None:
        result = render_config_bean(_make_config(), "BEAN-006")
        assert "DATABASE_URL" in result

    def test_contains_default_value(self) -> None:
        result = render_config_bean(_make_config(), "BEAN-006")
        assert "sqlite:///db.sqlite3" in result

    def test_contains_required_flag(self) -> None:
        result = render_config_bean(_make_config(), "BEAN-006")
        assert "Yes" in result

    def test_contains_usage_locations(self) -> None:
        result = render_config_bean(_make_config(), "BEAN-006")
        assert "config.py" in result
        assert "db.py" in result

    def test_frontmatter_type_is_config(self) -> None:
        result = render_config_bean(_make_config(), "BEAN-006")
        assert "type: config" in result

    def test_optional_config_no_required_criterion(self) -> None:
        config = ConfigSurface(
            name="DEBUG",
            env_var_name="DEBUG",
            default_value="false",
            required=False,
        )
        result = render_config_bean(config, "BEAN-099")
        assert "No" in result


# --- Crosscutting Bean Tests (Spec 8.9) ---


class TestCrosscuttingBeanTemplate:
    def test_renders_with_sample_data(self) -> None:
        result = render_crosscutting_bean(_make_crosscutting(), "BEAN-007")
        assert isinstance(result, str)

    def test_has_concern_specific_sections(self) -> None:
        result = render_crosscutting_bean(_make_crosscutting(), "BEAN-007")
        assert "## Concern type" in result
        assert "## Description" in result
        assert "## Affected files" in result
        assert "## Acceptance criteria" in result

    def test_contains_concern_type(self) -> None:
        result = render_crosscutting_bean(_make_crosscutting(), "BEAN-007")
        assert "logging" in result

    def test_contains_description(self) -> None:
        result = render_crosscutting_bean(_make_crosscutting(), "BEAN-007")
        assert "Structured logging across all services" in result

    def test_contains_affected_files(self) -> None:
        result = render_crosscutting_bean(_make_crosscutting(), "BEAN-007")
        assert "app.py" in result
        assert "api.py" in result
        assert "worker.py" in result

    def test_frontmatter_type_is_crosscutting(self) -> None:
        result = render_crosscutting_bean(_make_crosscutting(), "BEAN-007")
        assert "type: crosscutting" in result


# --- Dispatch Tests ---


class TestRenderBeanDispatch:
    def test_dispatch_route(self) -> None:
        result = render_bean(_make_route(), "BEAN-001")
        assert "type: page" in result
        assert "## Overview" in result

    def test_dispatch_component(self) -> None:
        result = render_bean(_make_component(), "BEAN-002")
        assert "type: component" in result
        assert "## Purpose" in result

    def test_dispatch_api(self) -> None:
        result = render_bean(_make_api(), "BEAN-003")
        assert "type: api" in result
        assert "## Endpoints" in result

    def test_dispatch_model(self) -> None:
        result = render_bean(_make_model(), "BEAN-004")
        assert "type: model" in result
        assert "## Entity description" in result

    def test_dispatch_auth(self) -> None:
        result = render_bean(_make_auth(), "BEAN-005")
        assert "type: auth" in result
        assert "## Roles/permissions/rules" in result

    def test_dispatch_config(self) -> None:
        result = render_bean(_make_config(), "BEAN-006")
        assert "type: config" in result
        assert "## Env vars + defaults" in result

    def test_dispatch_crosscutting(self) -> None:
        result = render_bean(_make_crosscutting(), "BEAN-007")
        assert "type: crosscutting" in result
        assert "## Concern type" in result

    def test_dispatch_unknown_type_raises(self) -> None:
        surface = Surface(name="unknown", surface_type="widget")
        with pytest.raises(ValueError, match="No renderer for surface type"):
            render_bean(surface, "BEAN-999")


# --- Empty/Minimal Data Tests ---


class TestMinimalSurfaces:
    def test_route_minimal(self) -> None:
        route = RouteSurface(name="minimal", path="/", method="GET")
        result = render_route_bean(route, "BEAN-100")
        assert "## Overview" in result
        assert "status: draft" in result

    def test_component_minimal(self) -> None:
        comp = ComponentSurface(name="minimal")
        result = render_component_bean(comp, "BEAN-101")
        assert "## Purpose" in result
        assert "No props defined" in result

    def test_api_minimal(self) -> None:
        api = ApiSurface(name="minimal", method="POST", path="/api/test")
        result = render_api_bean(api, "BEAN-102")
        assert "## Endpoints" in result
        assert "No auth requirement" in result

    def test_model_minimal(self) -> None:
        model = ModelSurface(name="minimal")
        result = render_model_bean(model, "BEAN-103")
        assert "## Entity description" in result
        assert "No fields defined" in result

    def test_auth_minimal(self) -> None:
        auth = AuthSurface(name="minimal")
        result = render_auth_bean(auth, "BEAN-104")
        assert "## Roles/permissions/rules" in result
        assert "No roles defined" in result

    def test_config_minimal(self) -> None:
        config = ConfigSurface(name="minimal", env_var_name="MINIMAL")
        result = render_config_bean(config, "BEAN-105")
        assert "## Env vars + defaults" in result

    def test_crosscutting_minimal(self) -> None:
        cc = CrosscuttingSurface(name="minimal")
        result = render_crosscutting_bean(cc, "BEAN-106")
        assert "## Concern type" in result
        assert "Unspecified" in result
