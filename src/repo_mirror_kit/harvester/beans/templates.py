"""Bean template rendering for the harvester.

Renders Surface dataclass instances into well-formed markdown beans
with YAML frontmatter. Each bean type has a dedicated render function
producing the sections defined in the spec (8.3-8.9).
"""

from __future__ import annotations

import json
from typing import Any

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    ComponentSurface,
    ConfigSurface,
    CrosscuttingSurface,
    ModelSurface,
    RouteSurface,
    SourceRef,
    Surface,
)


def _render_frontmatter(
    bean_id: str,
    bean_type: str,
    title: str,
    source_refs: list[SourceRef],
    traceability: list[str] | None = None,
) -> str:
    """Render YAML frontmatter block for a bean.

    Args:
        bean_id: Unique bean identifier (e.g. "BEAN-001").
        bean_type: The bean type discriminator.
        title: Human-readable title.
        source_refs: Source code references.
        traceability: Optional traceability links.

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

    lines = [
        "---",
        f"id: {bean_id}",
        f"type: {bean_type}",
        f"title: {json.dumps(title)}",
        f"source_refs: {json.dumps(refs_list)}",
        f"traceability: {json.dumps(trace)}",
        "status: draft",
        "---",
    ]
    return "\n".join(lines)


def _bullet_list(items: list[str], empty_msg: str = "- (none)") -> str:
    """Render a markdown bullet list from items."""
    if not items:
        return empty_msg
    return "\n".join(f"- {item}" for item in items)


def render_route_bean(surface: RouteSurface, bean_id: str) -> str:
    """Render a Page/Route bean (spec 8.3).

    Produces 8 required sections: Overview, User stories, Functional
    requirements, UI elements, Data & API interactions, Validation &
    error states, Acceptance criteria, Open questions.

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
    )

    body = f"""
# {surface.name}

## Overview

Route `{surface.path}` ({surface.method}).

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

## Acceptance criteria

- [ ] Route `{surface.path}` responds to {surface.method} requests.
- [ ] All referenced components render correctly.
- [ ] API interactions complete successfully.

## Open questions

- TODO: Identify open design questions for this route.
"""
    return fm + "\n" + body.lstrip("\n")


def render_component_bean(surface: ComponentSurface, bean_id: str) -> str:
    """Render a Component bean (spec 8.4).

    Produces 6 required sections: Purpose, Props/inputs contract,
    Outputs/events, States, Usage locations, Acceptance criteria.

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
    )

    body = f"""
# {surface.name}

## Purpose

UI component: {surface.name}.

## Props/inputs contract

{_bullet_list([f"`{p}`" for p in surface.props], "- No props defined.")}

## Outputs/events

{_bullet_list([f"`{o}`" for o in surface.outputs], "- No outputs defined.")}

## States

{_bullet_list(surface.states, "- No states defined.")}

## Usage locations

{_bullet_list(surface.usage_locations, "- No usage locations identified.")}

## Acceptance criteria

- [ ] Component renders in all defined states.
- [ ] All props are accepted and applied correctly.
- [ ] All outputs/events fire as expected.
"""
    return fm + "\n" + body.lstrip("\n")


def render_api_bean(surface: ApiSurface, bean_id: str) -> str:
    """Render an API bean (spec 8.5).

    Produces 8 required sections: Endpoints, Auth, Request schema,
    Response schema, Errors, Side effects, Acceptance criteria, Examples.

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

## Acceptance criteria

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

    Produces 6 required sections: Entity description, Fields,
    Relationships, Persistence, Validation rules, Acceptance criteria.

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
    )

    field_lines: list[str] = []
    for f in surface.fields:
        constraints = f", constraints: {f.constraints}" if f.constraints else ""
        field_lines.append(f"- `{f.name}`: {f.field_type}{constraints}")

    body = f"""
# {surface.name}

## Entity description

Model entity: {surface.entity_name if surface.entity_name else surface.name}.

## Fields

{chr(10).join(field_lines) if field_lines else "- No fields defined."}

## Relationships

{_bullet_list(surface.relationships, "- No relationships defined.")}

## Persistence

{_bullet_list(surface.persistence_refs, "- No persistence references identified.")}

## Validation rules

- TODO: Define validation rules for this model.

## Acceptance criteria

- [ ] All fields are persisted correctly.
- [ ] Relationships are maintained on create/update/delete.
- [ ] Validation rules reject invalid data.
"""
    return fm + "\n" + body.lstrip("\n")


def render_auth_bean(surface: AuthSurface, bean_id: str) -> str:
    """Render an Auth bean (spec 8.7).

    Produces 4 required sections: Roles/permissions/rules, Protected
    routes/endpoints map, Token/session assumptions, Acceptance criteria.

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
    )

    body = f"""
# {surface.name}

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

## Acceptance criteria

- [ ] Roles are enforced at all protected endpoints.
- [ ] Permissions are checked correctly.
- [ ] Unauthorized access returns appropriate error responses.
"""
    return fm + "\n" + body.lstrip("\n")


def render_config_bean(surface: ConfigSurface, bean_id: str) -> str:
    """Render a Config bean (spec 8.8).

    Produces 4 required sections: Env vars + defaults, Feature flags,
    Required external services, Acceptance criteria.

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
    )

    default_display = (
        f"`{surface.default_value}`" if surface.default_value is not None else "(none)"
    )
    required_display = "Yes" if surface.required else "No"

    body = f"""
# {surface.name}

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

## Acceptance criteria

- [ ] Application starts with default value when env var is not set.
- [ ] Application reads the env var correctly when set.
{"- [ ] Application fails to start when required env var is missing." if surface.required else ""}
"""
    return fm + "\n" + body.lstrip("\n")


def render_crosscutting_bean(surface: CrosscuttingSurface, bean_id: str) -> str:
    """Render a Crosscutting bean (spec 8.9).

    Produces concern-specific sections based on the concern_type.

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
    )

    body = f"""
# {surface.name}

## Concern type

{surface.concern_type if surface.concern_type else "Unspecified"}

## Description

{surface.description if surface.description else "TODO: Describe this cross-cutting concern."}

## Affected files

{_bullet_list(surface.affected_files, "- No affected files identified.")}

## Acceptance criteria

- [ ] Cross-cutting concern is applied consistently across all affected files.
- [ ] No regressions introduced in affected components.
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
