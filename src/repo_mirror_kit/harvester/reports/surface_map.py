"""Surface map report generator.

Produces a human-readable Markdown report and a machine-readable JSON file
from a ``SurfaceCollection`` and an optional ``StackProfile``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    ComponentSurface,
    ConfigSurface,
    CrosscuttingSurface,
    DependencySurface,
    IntegrationSurface,
    MiddlewareSurface,
    ModelSurface,
    RouteSurface,
    StateMgmtSurface,
    SurfaceCollection,
    UIFlowSurface,
)
from repo_mirror_kit.harvester.detectors.base import StackProfile

logger = structlog.get_logger()


def generate_surface_map_markdown(
    surfaces: SurfaceCollection,
    profile: StackProfile | None = None,
) -> str:
    """Generate a human-readable Markdown surface map report.

    Args:
        surfaces: The collection of all extracted surfaces.
        profile: Optional stack detection profile for the summary header.

    Returns:
        The complete Markdown report as a string.
    """
    sections: list[str] = []
    sections.append("# Surface Map Report\n")
    sections.append(_build_summary_section(surfaces, profile))
    sections.append(_build_routes_section(surfaces.routes))
    sections.append(_build_components_section(surfaces.components))
    sections.append(_build_apis_section(surfaces.apis))
    sections.append(_build_models_section(surfaces.models))
    sections.append(_build_auth_section(surfaces.auth))
    sections.append(_build_config_section(surfaces.config))
    sections.append(_build_crosscutting_section(surfaces.crosscutting))
    sections.append(_build_state_mgmt_section(surfaces.state_mgmt))
    sections.append(_build_middleware_section(surfaces.middleware))
    sections.append(_build_integrations_section(surfaces.integrations))
    sections.append(_build_ui_flows_section(surfaces.ui_flows))
    sections.append(_build_dependencies_section(surfaces.dependencies))
    return "\n".join(sections)


def generate_surface_map_json(
    surfaces: SurfaceCollection,
    profile: StackProfile | None = None,
) -> str:
    """Generate a machine-readable JSON surface map.

    Args:
        surfaces: The collection of all extracted surfaces.
        profile: Optional stack detection profile for metadata.

    Returns:
        A JSON string with all surfaces organized by type.
    """
    data: dict[str, Any] = {
        "summary": {
            "total_surfaces": len(surfaces),
            "detected_stacks": list(profile.stacks.keys()) if profile else [],
            "counts": {
                "routes": len(surfaces.routes),
                "components": len(surfaces.components),
                "apis": len(surfaces.apis),
                "models": len(surfaces.models),
                "auth": len(surfaces.auth),
                "config": len(surfaces.config),
                "crosscutting": len(surfaces.crosscutting),
                "state_mgmt": len(surfaces.state_mgmt),
                "middleware": len(surfaces.middleware),
                "integrations": len(surfaces.integrations),
                "ui_flows": len(surfaces.ui_flows),
            },
        },
        "surfaces": surfaces.to_dict(),
    }
    return json.dumps(data, indent=2)


def write_surface_map(
    output_dir: Path,
    surfaces: SurfaceCollection,
    profile: StackProfile | None = None,
) -> tuple[Path, Path]:
    """Write both surface map reports to the output directory.

    Args:
        output_dir: Directory to write reports into (created if missing).
        surfaces: The collection of all extracted surfaces.
        profile: Optional stack detection profile for the summary header.

    Returns:
        A tuple of (markdown_path, json_path) for the written files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    md_path = output_dir / "surface-map.md"
    json_path = output_dir / "surfaces.json"

    md_content = generate_surface_map_markdown(surfaces, profile)
    md_path.write_text(md_content, encoding="utf-8")
    logger.info("surface_map_written", path=str(md_path), format="markdown")

    json_content = generate_surface_map_json(surfaces, profile)
    json_path.write_text(json_content, encoding="utf-8")
    logger.info("surface_map_written", path=str(json_path), format="json")

    return md_path, json_path


# ---------------------------------------------------------------------------
# Internal section builders
# ---------------------------------------------------------------------------

_NONE_DETECTED = "None detected.\n"


def _build_summary_section(
    surfaces: SurfaceCollection,
    profile: StackProfile | None,
) -> str:
    """Build the top-level summary section."""
    lines: list[str] = ["## Summary\n"]

    if profile and profile.stacks:
        stacks_str = ", ".join(sorted(profile.stacks.keys()))
        lines.append(f"**Detected stacks:** {stacks_str}\n")
    else:
        lines.append("**Detected stacks:** None\n")

    lines.append(f"**Total surfaces:** {len(surfaces)}\n")
    lines.append("| Surface Type | Count |")
    lines.append("|---|---|")
    lines.append(f"| Routes / Pages | {len(surfaces.routes)} |")
    lines.append(f"| Components | {len(surfaces.components)} |")
    lines.append(f"| API Endpoints | {len(surfaces.apis)} |")
    lines.append(f"| Models / Entities | {len(surfaces.models)} |")
    lines.append(f"| Auth Patterns | {len(surfaces.auth)} |")
    lines.append(f"| Config / Env Vars | {len(surfaces.config)} |")
    lines.append(f"| Cross-cutting Concerns | {len(surfaces.crosscutting)} |")
    lines.append(f"| State Management | {len(surfaces.state_mgmt)} |")
    lines.append(f"| Middleware | {len(surfaces.middleware)} |")
    lines.append(f"| Integrations | {len(surfaces.integrations)} |")
    lines.append(f"| UI Flows | {len(surfaces.ui_flows)} |")
    lines.append(f"| Dependencies | {len(surfaces.dependencies)} |")
    lines.append("")
    return "\n".join(lines)


def _build_routes_section(routes: list[RouteSurface]) -> str:
    """Build the routes/pages section."""
    lines: list[str] = ["## Routes / Pages\n"]
    if not routes:
        lines.append(_NONE_DETECTED)
        return "\n".join(lines)

    lines.append("| Name | Path | Method |")
    lines.append("|---|---|---|")
    for route in routes:
        method = route.method or "GET"
        lines.append(f"| {route.name} | `{route.path}` | {method} |")
    lines.append("")
    return "\n".join(lines)


def _build_components_section(components: list[ComponentSurface]) -> str:
    """Build the shared components section."""
    lines: list[str] = ["## Components\n"]
    if not components:
        lines.append(_NONE_DETECTED)
        return "\n".join(lines)

    lines.append("| Name | Props | Usage Count |")
    lines.append("|---|---|---|")
    for comp in components:
        usage_count = len(comp.usage_locations)
        prop_count = len(comp.props)
        lines.append(f"| {comp.name} | {prop_count} | {usage_count} |")
    lines.append("")
    return "\n".join(lines)


def _build_apis_section(apis: list[ApiSurface]) -> str:
    """Build the API endpoints section."""
    lines: list[str] = ["## API Endpoints\n"]
    if not apis:
        lines.append(_NONE_DETECTED)
        return "\n".join(lines)

    lines.append("| Name | Method | Path |")
    lines.append("|---|---|---|")
    for api in apis:
        lines.append(f"| {api.name} | {api.method} | `{api.path}` |")
    lines.append("")
    return "\n".join(lines)


def _build_models_section(models: list[ModelSurface]) -> str:
    """Build the models/entities section."""
    lines: list[str] = ["## Models / Entities\n"]
    if not models:
        lines.append(_NONE_DETECTED)
        return "\n".join(lines)

    lines.append("| Name | Entity | Fields |")
    lines.append("|---|---|---|")
    for model in models:
        field_count = len(model.fields)
        entity = model.entity_name or model.name
        lines.append(f"| {model.name} | {entity} | {field_count} |")
    lines.append("")
    return "\n".join(lines)


def _build_auth_section(auth: list[AuthSurface]) -> str:
    """Build the auth patterns section."""
    lines: list[str] = ["## Auth Patterns\n"]
    if not auth:
        lines.append(_NONE_DETECTED)
        return "\n".join(lines)

    for item in auth:
        lines.append(f"### {item.name}\n")
        if item.roles:
            lines.append(f"- **Roles:** {', '.join(item.roles)}")
        if item.permissions:
            lines.append(f"- **Permissions:** {', '.join(item.permissions)}")
        if item.protected_endpoints:
            lines.append(f"- **Protected endpoints:** {len(item.protected_endpoints)}")
        lines.append("")
    return "\n".join(lines)


def _build_config_section(config: list[ConfigSurface]) -> str:
    """Build the config/env vars section."""
    lines: list[str] = ["## Config / Environment Variables\n"]
    if not config:
        lines.append(_NONE_DETECTED)
        return "\n".join(lines)

    lines.append("| Variable | Required | Default |")
    lines.append("|---|---|---|")
    for cfg in config:
        var_name = cfg.env_var_name or cfg.name
        required = "Yes" if cfg.required else "No"
        default = cfg.default_value if cfg.default_value is not None else "\u2014"
        lines.append(f"| `{var_name}` | {required} | {default} |")
    lines.append("")
    return "\n".join(lines)


def _build_crosscutting_section(
    crosscutting: list[CrosscuttingSurface],
) -> str:
    """Build the cross-cutting concerns section."""
    lines: list[str] = ["## Cross-cutting Concerns\n"]
    if not crosscutting:
        lines.append(_NONE_DETECTED)
        return "\n".join(lines)

    for item in crosscutting:
        concern = item.concern_type or item.name
        lines.append(f"- **{concern}**: {item.description}")
        if item.affected_files:
            lines.append(f"  - Affected files: {len(item.affected_files)}")
    lines.append("")
    return "\n".join(lines)


def _build_state_mgmt_section(state_mgmt: list[StateMgmtSurface]) -> str:
    """Build the state management section."""
    lines: list[str] = ["## State Management\n"]
    if not state_mgmt:
        lines.append(_NONE_DETECTED)
        return "\n".join(lines)

    lines.append("| Name | Store | Pattern | Actions | Selectors |")
    lines.append("|---|---|---|---|---|")
    for sm in state_mgmt:
        store = sm.store_name or sm.name
        lines.append(
            f"| {sm.name} | {store} | {sm.pattern} | {len(sm.actions)} | {len(sm.selectors)} |"
        )
    lines.append("")
    return "\n".join(lines)


def _build_middleware_section(middleware: list[MiddlewareSurface]) -> str:
    """Build the middleware section."""
    lines: list[str] = ["## Middleware\n"]
    if not middleware:
        lines.append(_NONE_DETECTED)
        return "\n".join(lines)

    lines.append("| Name | Type | Order | Applies To |")
    lines.append("|---|---|---|---|")
    for mw in middleware:
        order = str(mw.execution_order) if mw.execution_order is not None else "\u2014"
        applies = ", ".join(mw.applies_to) if mw.applies_to else "all"
        lines.append(f"| {mw.name} | {mw.middleware_type} | {order} | {applies} |")
    lines.append("")
    return "\n".join(lines)


def _build_integrations_section(integrations: list[IntegrationSurface]) -> str:
    """Build the integrations section."""
    lines: list[str] = ["## Integrations\n"]
    if not integrations:
        lines.append(_NONE_DETECTED)
        return "\n".join(lines)

    lines.append("| Name | Type | Target | Protocol |")
    lines.append("|---|---|---|---|")
    for integ in integrations:
        lines.append(
            f"| {integ.name} | {integ.integration_type} | {integ.target_service} | {integ.protocol} |"
        )
    lines.append("")
    return "\n".join(lines)


def _build_ui_flows_section(ui_flows: list[UIFlowSurface]) -> str:
    """Build the UI flows section."""
    lines: list[str] = ["## UI Flows\n"]
    if not ui_flows:
        lines.append(_NONE_DETECTED)
        return "\n".join(lines)

    lines.append("| Name | Type | Steps | Entry Point |")
    lines.append("|---|---|---|---|")
    for flow in ui_flows:
        lines.append(
            f"| {flow.name} | {flow.flow_type} | {len(flow.steps)} | {flow.entry_point} |"
        )
    lines.append("")
    return "\n".join(lines)


def _build_dependencies_section(dependencies: list[DependencySurface]) -> str:
    """Build the dependencies section."""
    lines: list[str] = ["## Dependencies\n"]
    if not dependencies:
        lines.append(_NONE_DETECTED)
        return "\n".join(lines)

    lines.append("| Name | Version | Purpose | Manifest | Direct |")
    lines.append("|---|---|---|---|---|")
    for dep in dependencies:
        direct = "Yes" if dep.is_direct else "No"
        lines.append(
            f"| {dep.name} | {dep.version_constraint or '(any)'} | {dep.purpose} | {dep.manifest_file} | {direct} |"
        )
    lines.append("")
    return "\n".join(lines)
