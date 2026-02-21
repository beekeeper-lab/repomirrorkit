"""Bean template rendering for the harvester.

Renders Surface dataclass instances into well-formed markdown beans
with YAML frontmatter. Each bean type has a dedicated render function
producing the sections defined in the spec (8.3-8.9), upgraded with
behavioral requirements when LLM enrichment data is available.
"""

from __future__ import annotations

import json
from typing import Any

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    BuildDeploySurface,
    ComponentSurface,
    ConfigSurface,
    CrosscuttingSurface,
    DependencySurface,
    GeneralLogicSurface,
    IntegrationSurface,
    MiddlewareSurface,
    ModelSurface,
    RouteSurface,
    SourceRef,
    StateMgmtSurface,
    Surface,
    TestPatternSurface,
    UIFlowSurface,
)


def _render_frontmatter(
    bean_id: str,
    bean_type: str,
    title: str,
    source_refs: list[SourceRef],
    traceability: list[str] | None = None,
    enrichment: dict[str, Any] | None = None,
) -> str:
    """Render YAML frontmatter block for a bean.

    Args:
        bean_id: Unique bean identifier (e.g. "BEAN-001").
        bean_type: The bean type discriminator.
        title: Human-readable title.
        source_refs: Source code references.
        traceability: Optional traceability links.
        enrichment: Optional enrichment data for priority/dependencies.

    Returns:
        A YAML frontmatter string delimited by ``---``.
    """
    refs_list: list[dict[str, Any]] = []
    for ref in source_refs:
        entry: dict[str, Any] = {"file_path": ref.file_path}
        if ref.start_line is not None:
            entry["start_line"] = ref.start_line
        if ref.end_line is not None:
            entry["end_line"] = ref.end_line
        refs_list.append(entry)

    trace = traceability if traceability is not None else []
    priority = "unassessed"
    dependencies: list[str] = []
    if enrichment:
        priority = enrichment.get("priority", "unassessed")
        dependencies = enrichment.get("dependencies", [])

    lines = [
        "---",
        f"id: {bean_id}",
        f"type: {bean_type}",
        f"title: {json.dumps(title)}",
        f"source_refs: {json.dumps(refs_list)}",
        f"traceability: {json.dumps(trace)}",
        f"priority: {priority}",
        f"dependencies: {json.dumps(dependencies)}",
        "status: draft",
        "---",
    ]
    return "\n".join(lines)


def _bullet_list(items: list[str], empty_msg: str = "- (none)") -> str:
    """Render a markdown bullet list from items."""
    if not items:
        return empty_msg
    return "\n".join(f"- {item}" for item in items)


def _render_enrichment_sections(surface: Surface) -> str:
    """Render behavioral enrichment sections shared across all renderers.

    If enrichment data is available, renders Behavioral Description,
    Acceptance Criteria (Given/When/Then), and Data Flow sections.
    Otherwise renders structured TODO placeholders.

    Args:
        surface: Any Surface subclass with optional enrichment dict.

    Returns:
        Markdown string with enrichment sections.
    """
    enrichment = surface.enrichment
    lines: list[str] = []

    # Behavioral description
    lines.append("## Behavioral description")
    lines.append("")
    if enrichment and enrichment.get("behavioral_description"):
        lines.append(enrichment["behavioral_description"])
    else:
        lines.append(
            "TODO: Describe the expected behavior from a user/system perspective."
        )
    lines.append("")

    # Inferred intent
    if enrichment and enrichment.get("inferred_intent"):
        lines.append("## Inferred intent")
        lines.append("")
        lines.append(enrichment["inferred_intent"])
        lines.append("")

    # Given/When/Then acceptance criteria
    lines.append("## Acceptance criteria (Given/When/Then)")
    lines.append("")
    gwt_list = enrichment.get("given_when_then", []) if enrichment else []
    if gwt_list:
        for criterion in gwt_list:
            given = criterion.get("given", "")
            when = criterion.get("when", "")
            then = criterion.get("then", "")
            lines.append(f"- [ ] **Given** {given} **When** {when} **Then** {then}")
    else:
        lines.append("- [ ] TODO: Define Given/When/Then acceptance criteria.")
    lines.append("")

    # Data flow
    lines.append("## Data flow")
    lines.append("")
    if enrichment and enrichment.get("data_flow"):
        lines.append(enrichment["data_flow"])
    else:
        lines.append("TODO: Describe the data flow for this surface.")
    lines.append("")

    return "\n".join(lines)


def render_route_bean(surface: RouteSurface, bean_id: str) -> str:
    """Render a Page/Route bean (spec 8.3).

    Args:
        surface: A RouteSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="page",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    body = f"""
# {surface.name}

## Overview

Route `{surface.path}` ({surface.method}).

{_render_enrichment_sections(surface)}
## User stories

- As a user, I can access `{surface.path}` to interact with the {surface.name} page.

## Functional requirements

- The route responds to {surface.method} requests at `{surface.path}`.
{_bullet_list([f"Requires auth: {req}" for req in surface.auth_requirements], "- No specific auth requirements identified.")}

## UI elements

{_bullet_list([f"Component: {c}" for c in surface.component_refs], "- No UI components identified.")}

## Data & API interactions

{_bullet_list([f"API: {api}" for api in surface.api_refs], "- No API interactions identified.")}

## Validation & error states

- TODO: Define validation rules and error states for this route.

## Structural acceptance criteria

- [ ] Route `{surface.path}` responds to {surface.method} requests.
- [ ] All referenced components render correctly.
- [ ] API interactions complete successfully.

## Open questions

- TODO: Identify open design questions for this route.
"""
    return fm + "\n" + body.lstrip("\n")


def render_component_bean(surface: ComponentSurface, bean_id: str) -> str:
    """Render a Component bean (spec 8.4).

    Args:
        surface: A ComponentSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="component",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    body = f"""
# {surface.name}

## Purpose

UI component: {surface.name}.

{_render_enrichment_sections(surface)}
## Props/inputs contract

{_bullet_list([f"`{p}`" for p in surface.props], "- No props defined.")}

## Outputs/events

{_bullet_list([f"`{o}`" for o in surface.outputs], "- No outputs defined.")}

## States

{_bullet_list(surface.states, "- No states defined.")}

## Usage locations

{_bullet_list(surface.usage_locations, "- No usage locations identified.")}

## Structural acceptance criteria

- [ ] Component renders in all defined states.
- [ ] All props are accepted and applied correctly.
- [ ] All outputs/events fire as expected.
"""
    return fm + "\n" + body.lstrip("\n")


def render_api_bean(surface: ApiSurface, bean_id: str) -> str:
    """Render an API bean (spec 8.5).

    Args:
        surface: An ApiSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="api",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    req_schema = (
        json.dumps(surface.request_schema, indent=2)
        if surface.request_schema
        else "(none)"
    )
    resp_schema = (
        json.dumps(surface.response_schema, indent=2)
        if surface.response_schema
        else "(none)"
    )

    body = f"""
# {surface.name}

## Endpoints

- `{surface.method} {surface.path}`

{_render_enrichment_sections(surface)}
## Auth

- {surface.auth if surface.auth else "No auth requirement specified."}

## Request schema

```json
{req_schema}
```

## Response schema

```json
{resp_schema}
```

## Errors

- TODO: Define error responses for this endpoint.

## Side effects

{_bullet_list(surface.side_effects, "- No side effects identified.")}

## Structural acceptance criteria

- [ ] Endpoint `{surface.method} {surface.path}` responds correctly.
- [ ] Auth requirements are enforced.
- [ ] Request validation rejects invalid input.
- [ ] Response matches documented schema.

## Examples

```
{surface.method} {surface.path}
```

- TODO: Add example request/response payloads.
"""
    return fm + "\n" + body.lstrip("\n")


def render_model_bean(surface: ModelSurface, bean_id: str) -> str:
    """Render a Model bean (spec 8.6).

    Args:
        surface: A ModelSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="model",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    field_lines: list[str] = []
    for f in surface.fields:
        constraints = f", constraints: {f.constraints}" if f.constraints else ""
        field_lines.append(f"- `{f.name}`: {f.field_type}{constraints}")

    body = f"""
# {surface.name}

## Entity description

Model entity: {surface.entity_name if surface.entity_name else surface.name}.

{_render_enrichment_sections(surface)}
## Fields

{chr(10).join(field_lines) if field_lines else "- No fields defined."}

## Relationships

{_bullet_list(surface.relationships, "- No relationships defined.")}

## Persistence

{_bullet_list(surface.persistence_refs, "- No persistence references identified.")}

## Validation rules

- TODO: Define validation rules for this model.

## Structural acceptance criteria

- [ ] All fields are persisted correctly.
- [ ] Relationships are maintained on create/update/delete.
- [ ] Validation rules reject invalid data.
"""
    return fm + "\n" + body.lstrip("\n")


def render_auth_bean(surface: AuthSurface, bean_id: str) -> str:
    """Render an Auth bean (spec 8.7).

    Args:
        surface: An AuthSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="auth",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    body = f"""
# {surface.name}

{_render_enrichment_sections(surface)}
## Roles/permissions/rules

### Roles

{_bullet_list(surface.roles, "- No roles defined.")}

### Permissions

{_bullet_list(surface.permissions, "- No permissions defined.")}

### Rules

{_bullet_list(surface.rules, "- No rules defined.")}

## Protected routes/endpoints map

{_bullet_list(surface.protected_endpoints, "- No protected endpoints identified.")}

## Token/session assumptions

- TODO: Define token/session handling assumptions.

## Structural acceptance criteria

- [ ] Roles are enforced at all protected endpoints.
- [ ] Permissions are checked correctly.
- [ ] Unauthorized access returns appropriate error responses.
"""
    return fm + "\n" + body.lstrip("\n")


def render_config_bean(surface: ConfigSurface, bean_id: str) -> str:
    """Render a Config bean (spec 8.8).

    Args:
        surface: A ConfigSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="config",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    default_display = (
        f"`{surface.default_value}`" if surface.default_value is not None else "(none)"
    )
    required_display = "Yes" if surface.required else "No"

    body = f"""
# {surface.name}

{_render_enrichment_sections(surface)}
## Env vars + defaults

| Variable | Default | Required |
|----------|---------|----------|
| `{surface.env_var_name}` | {default_display} | {required_display} |

Usage locations:
{_bullet_list(surface.usage_locations, "- No usage locations identified.")}

## Feature flags

- TODO: Identify any feature flags related to this configuration.

## Required external services

- TODO: Identify external services that depend on this configuration.

## Structural acceptance criteria

- [ ] Application starts with default value when env var is not set.
- [ ] Application reads the env var correctly when set.
{"- [ ] Application fails to start when required env var is missing." if surface.required else ""}
"""
    return fm + "\n" + body.lstrip("\n")


def render_crosscutting_bean(surface: CrosscuttingSurface, bean_id: str) -> str:
    """Render a Crosscutting bean (spec 8.9).

    Args:
        surface: A CrosscuttingSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="crosscutting",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    body = f"""
# {surface.name}

## Concern type

{surface.concern_type if surface.concern_type else "Unspecified"}

## Description

{surface.description if surface.description else "TODO: Describe this cross-cutting concern."}

{_render_enrichment_sections(surface)}
## Affected files

{_bullet_list(surface.affected_files, "- No affected files identified.")}

## Structural acceptance criteria

- [ ] Cross-cutting concern is applied consistently across all affected files.
- [ ] No regressions introduced in affected components.
"""
    return fm + "\n" + body.lstrip("\n")


def render_state_mgmt_bean(surface: StateMgmtSurface, bean_id: str) -> str:
    """Render a State Management bean.

    Args:
        surface: A StateMgmtSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="state_mgmt",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    body = f"""
# {surface.name}

## Store overview

- **Store name:** {surface.store_name or surface.name}
- **Pattern:** {surface.pattern or "unidentified"}

{_render_enrichment_sections(surface)}
## Actions

{_bullet_list([f"`{a}`" for a in surface.actions], "- No actions identified.")}

## Selectors

{_bullet_list([f"`{s}`" for s in surface.selectors], "- No selectors identified.")}

## Structural acceptance criteria

- [ ] Store initializes with correct default state.
- [ ] All actions produce expected state transitions.
- [ ] Selectors return correct derived state.
"""
    return fm + "\n" + body.lstrip("\n")


def render_middleware_bean(surface: MiddlewareSurface, bean_id: str) -> str:
    """Render a Middleware bean.

    Args:
        surface: A MiddlewareSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="middleware",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    order_str = (
        str(surface.execution_order)
        if surface.execution_order is not None
        else "unspecified"
    )

    body = f"""
# {surface.name}

## Middleware overview

- **Type:** {surface.middleware_type or "unidentified"}
- **Execution order:** {order_str}

{_render_enrichment_sections(surface)}
## Applies to

{_bullet_list(surface.applies_to, "- All routes/endpoints (default).")}

## Transforms

{_bullet_list(surface.transforms, "- No transforms identified.")}

## Structural acceptance criteria

- [ ] Middleware executes in the correct order in the pipeline.
- [ ] Middleware applies only to intended routes/endpoints.
- [ ] Request/response transformations are correct.
"""
    return fm + "\n" + body.lstrip("\n")


def render_integration_bean(surface: IntegrationSurface, bean_id: str) -> str:
    """Render an Integration bean.

    Args:
        surface: An IntegrationSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="integration",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    body = f"""
# {surface.name}

## Integration overview

- **Type:** {surface.integration_type or "unidentified"}
- **Target service:** {surface.target_service or "unknown"}
- **Protocol:** {surface.protocol or "unspecified"}

{_render_enrichment_sections(surface)}
## Data exchanged

{_bullet_list(surface.data_exchanged, "- No data exchange patterns identified.")}

## Structural acceptance criteria

- [ ] Integration connects to the target service successfully.
- [ ] Data is exchanged in the correct format.
- [ ] Error handling covers connection failures and timeouts.
- [ ] Retry/backoff strategy is implemented where appropriate.
"""
    return fm + "\n" + body.lstrip("\n")


def render_ui_flow_bean(surface: UIFlowSurface, bean_id: str) -> str:
    """Render a UI Flow bean.

    Args:
        surface: A UIFlowSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="ui_flow",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    body = f"""
# {surface.name}

## Flow overview

- **Flow type:** {surface.flow_type or "unidentified"}
- **Entry point:** {surface.entry_point or "unspecified"}

{_render_enrichment_sections(surface)}
## Steps

{_bullet_list([f"Step: {s}" for s in surface.steps], "- No steps identified.")}

## Exit points

{_bullet_list(surface.exit_points, "- No exit points identified.")}

## Structural acceptance criteria

- [ ] Flow starts from the defined entry point.
- [ ] All steps are reachable and navigable.
- [ ] All exit points lead to valid destinations.
- [ ] Back navigation works correctly through the flow.
"""
    return fm + "\n" + body.lstrip("\n")


def render_build_deploy_bean(surface: BuildDeploySurface, bean_id: str) -> str:
    """Render a Build/Deploy bean.

    Args:
        surface: A BuildDeploySurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="build_deploy",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    body = f"""
# {surface.name}

## Build/deploy overview

- **Config type:** {surface.config_type or "unidentified"}
- **Tool:** {surface.tool or "unknown"}

{_render_enrichment_sections(surface)}
## Stages

{_bullet_list(surface.stages, "- No stages identified.")}

## Targets

{_bullet_list(surface.targets, "- No targets identified.")}

## Structural acceptance criteria

- [ ] Configuration file is valid and parseable.
- [ ] All referenced stages/targets are reachable.
- [ ] Build/deploy pipeline executes successfully.
"""
    return fm + "\n" + body.lstrip("\n")


def render_dependency_bean(surface: DependencySurface, bean_id: str) -> str:
    """Render a Dependency bean.

    Args:
        surface: A DependencySurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="dependency",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    direct_str = "Direct" if surface.is_direct else "Transitive"
    lock_str = (
        ", ".join(surface.lock_files) if surface.lock_files else "(none detected)"
    )

    body = f"""
# {surface.name}

## Package overview

- **Version constraint:** `{surface.version_constraint or "(any)"}`
- **Purpose:** {surface.purpose or "unclassified"}
- **Manifest file:** `{surface.manifest_file}`
- **Dependency type:** {direct_str}

{_render_enrichment_sections(surface)}
## Lock files

- {lock_str}

## Structural acceptance criteria

- [ ] Package `{surface.name}` is declared in the manifest with the correct version constraint.
- [ ] Package is classified as {surface.purpose or "runtime"} dependency.
- [ ] Lock file pins the exact resolved version.
"""
    return fm + "\n" + body.lstrip("\n")


def render_test_pattern_bean(surface: TestPatternSurface, bean_id: str) -> str:
    """Render a Test Pattern bean.

    Args:
        surface: A TestPatternSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="test_pattern",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    subject_display = (
        f"`{surface.subject_file}`" if surface.subject_file else "(unmapped)"
    )

    body = f"""
# {surface.name}

## Test overview

- **Framework:** {surface.framework or "unknown"}
- **Test type:** {surface.test_type or "unit"}
- **Test file:** `{surface.test_file}`
- **Subject file:** {subject_display}
- **Test count:** {surface.test_count}

{_render_enrichment_sections(surface)}
## Test names

{_bullet_list([f"`{n}`" for n in surface.test_names], "- No test names extracted.")}

## Structural acceptance criteria

- [ ] All tests in `{surface.test_file}` pass.
- [ ] Test file correctly tests the functionality in {subject_display}.
- [ ] Test count matches expected: {surface.test_count} tests.
"""
    return fm + "\n" + body.lstrip("\n")


def render_general_logic_bean(surface: GeneralLogicSurface, bean_id: str) -> str:
    """Render a General Logic bean for uncovered source files.

    Args:
        surface: A GeneralLogicSurface instance.
        bean_id: Unique bean identifier.

    Returns:
        Complete markdown string with frontmatter and body.
    """
    fm = _render_frontmatter(
        bean_id=bean_id,
        bean_type="general_logic",
        title=surface.name,
        source_refs=surface.source_refs,
        enrichment=surface.enrichment,
    )

    body = f"""
# {surface.name}

## Module overview

- **File:** `{surface.file_path}`
- **Purpose:** {surface.module_purpose or "TODO: Describe the purpose of this module."}
- **Complexity:** {surface.complexity_hint or "unassessed"}

{_render_enrichment_sections(surface)}
## Public API / Exports

{_bullet_list([f"`{e}`" for e in surface.exports], "- No public exports identified.")}

## Structural acceptance criteria

- [ ] Module behavior is documented.
- [ ] All public API contracts are covered by requirements.
- [ ] Integration points with other modules are identified.
"""
    return fm + "\n" + body.lstrip("\n")


_RENDERERS: dict[str, Any] = {
    "route": render_route_bean,
    "component": render_component_bean,
    "api": render_api_bean,
    "model": render_model_bean,
    "auth": render_auth_bean,
    "config": render_config_bean,
    "crosscutting": render_crosscutting_bean,
    "state_mgmt": render_state_mgmt_bean,
    "middleware": render_middleware_bean,
    "integration": render_integration_bean,
    "ui_flow": render_ui_flow_bean,
    "build_deploy": render_build_deploy_bean,
    "dependency": render_dependency_bean,
    "test_pattern": render_test_pattern_bean,
    "general_logic": render_general_logic_bean,
}


def render_bean(surface: Surface, bean_id: str) -> str:
    """Render a bean from a Surface instance.

    Dispatches to the appropriate renderer based on ``surface.surface_type``.

    Args:
        surface: Any Surface subclass instance.
        bean_id: Unique bean identifier (e.g. "BEAN-001").

    Returns:
        Complete markdown string with YAML frontmatter and body.

    Raises:
        ValueError: If the surface type has no registered renderer.
    """
    renderer = _RENDERERS.get(surface.surface_type)
    if renderer is None:
        msg = f"No renderer for surface type: {surface.surface_type!r}"
        raise ValueError(msg)
    result: str = renderer(surface, bean_id)
    return result
