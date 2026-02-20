"""Traceability graph builder (Stage D).

Builds link maps from extracted surfaces and emits human-readable
markdown tables documenting relationships between surface types:
routes to components, routes to APIs, APIs to models, env vars
to files, middleware to routes, state to components, and
integrations to APIs.
"""

from __future__ import annotations

import logging
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import SurfaceCollection

logger = logging.getLogger(__name__)

_TRACEABILITY_DIR = "traceability"


def build_traceability_maps(
    surfaces: SurfaceCollection,
    output_dir: Path,
) -> list[Path]:
    """Build all traceability maps and write them to output_dir/traceability/.

    Cross-references surfaces using field-level refs to produce
    markdown documents linking related surface types.

    Args:
        surfaces: The full collection of extracted surfaces.
        output_dir: Root output directory where traceability/ will be created.

    Returns:
        List of paths to the generated traceability files.
    """
    trace_dir = output_dir / _TRACEABILITY_DIR
    trace_dir.mkdir(parents=True, exist_ok=True)

    generators: list[tuple[str, str]] = [
        ("routes_to_components.md", _build_routes_to_components(surfaces)),
        ("routes_to_apis.md", _build_routes_to_apis(surfaces)),
        ("apis_to_models.md", _build_apis_to_models(surfaces)),
        ("envvars_to_files.md", _build_envvars_to_files(surfaces)),
        ("middleware_to_routes.md", _build_middleware_to_routes(surfaces)),
        ("state_to_components.md", _build_state_to_components(surfaces)),
        ("integrations_to_apis.md", _build_integrations_to_apis(surfaces)),
    ]

    written: list[Path] = []
    for filename, content in generators:
        path = trace_dir / filename
        path.write_text(content, encoding="utf-8")
        written.append(path)
        logger.info(
            "traceability_map_written",
            extra={"path": str(path)},
        )

    return written


def _build_routes_to_components(surfaces: SurfaceCollection) -> str:
    """Build a markdown table mapping routes to their component dependencies."""
    lines: list[str] = [
        "# Routes to Components",
        "",
        "Maps each route to the UI components it references.",
        "",
    ]

    if not surfaces.routes:
        lines.append("No routes found.")
        lines.append("")
        return "\n".join(lines)

    # Build a lookup: component name -> source files
    component_files: dict[str, list[str]] = {}
    for comp in surfaces.components:
        files = [ref.file_path for ref in comp.source_refs]
        component_files[comp.name] = files

    lines.append("| Route | Method | Components | Component Files |")
    lines.append("|-------|--------|------------|-----------------|")

    linked_routes: list[str] = []
    orphaned_routes: list[str] = []

    for route in surfaces.routes:
        route_label = f"`{route.method} {route.path}`"
        if route.component_refs:
            linked_routes.append(route.path)
            comp_names = ", ".join(f"`{c}`" for c in route.component_refs)
            comp_files_list: list[str] = []
            for ref in route.component_refs:
                comp_files_list.extend(component_files.get(ref, []))
            comp_files_str = ", ".join(f"`{f}`" for f in comp_files_list) or "\u2014"
            lines.append(
                f"| {route_label} | {route.method} | {comp_names} | {comp_files_str} |"
            )
        else:
            orphaned_routes.append(route.path)
            lines.append(f"| {route_label} | {route.method} | \u2014 | \u2014 |")

    lines.append("")

    # Orphaned components (not referenced by any route)
    referenced_components = set()
    for route in surfaces.routes:
        referenced_components.update(route.component_refs)

    orphaned_components = [
        c.name for c in surfaces.components if c.name not in referenced_components
    ]

    if orphaned_routes or orphaned_components:
        lines.append("## Orphaned Surfaces")
        lines.append("")
        if orphaned_routes:
            lines.append("**Routes with no component references:**")
            lines.append("")
            for r in orphaned_routes:
                lines.append(f"- `{r}`")
            lines.append("")
        if orphaned_components:
            lines.append("**Components not referenced by any route:**")
            lines.append("")
            for c in orphaned_components:
                lines.append(f"- `{c}`")
            lines.append("")

    return "\n".join(lines)


def _build_routes_to_apis(surfaces: SurfaceCollection) -> str:
    """Build a markdown table mapping routes to the API calls they make."""
    lines: list[str] = [
        "# Routes to APIs",
        "",
        "Maps each route to the API endpoints it calls.",
        "",
    ]

    if not surfaces.routes:
        lines.append("No routes found.")
        lines.append("")
        return "\n".join(lines)

    # Build a lookup: api name -> ApiSurface
    api_lookup: dict[str, str] = {}
    for api in surfaces.apis:
        api_lookup[api.name] = f"{api.method} {api.path}"

    lines.append("| Route | Method | API Calls |")
    lines.append("|-------|--------|-----------|")

    orphaned_routes: list[str] = []

    for route in surfaces.routes:
        route_label = f"`{route.method} {route.path}`"
        if route.api_refs:
            api_labels: list[str] = []
            for ref in route.api_refs:
                detail = api_lookup.get(ref, ref)
                api_labels.append(f"`{detail}`")
            apis_str = ", ".join(api_labels)
            lines.append(f"| {route_label} | {route.method} | {apis_str} |")
        else:
            orphaned_routes.append(route.path)
            lines.append(f"| {route_label} | {route.method} | \u2014 |")

    lines.append("")

    # Orphaned APIs (not referenced by any route)
    referenced_apis = set()
    for route in surfaces.routes:
        referenced_apis.update(route.api_refs)

    orphaned_apis = [a.name for a in surfaces.apis if a.name not in referenced_apis]

    if orphaned_routes or orphaned_apis:
        lines.append("## Orphaned Surfaces")
        lines.append("")
        if orphaned_routes:
            lines.append("**Routes with no API references:**")
            lines.append("")
            for r in orphaned_routes:
                lines.append(f"- `{r}`")
            lines.append("")
        if orphaned_apis:
            lines.append("**APIs not referenced by any route:**")
            lines.append("")
            for a in orphaned_apis:
                lines.append(f"- `{a}`")
            lines.append("")

    return "\n".join(lines)


def _build_apis_to_models(surfaces: SurfaceCollection) -> str:
    """Build a markdown table mapping API endpoints to the models they access."""
    lines: list[str] = [
        "# APIs to Models",
        "",
        "Maps each API endpoint to the data models it accesses.",
        "",
    ]

    if not surfaces.apis:
        lines.append("No API endpoints found.")
        lines.append("")
        return "\n".join(lines)

    # Build a lookup: model name -> ModelSurface entity_name
    model_lookup: dict[str, str] = {}
    for model in surfaces.models:
        model_lookup[model.name] = model.entity_name or model.name

    lines.append("| API Endpoint | Method | Models Accessed |")
    lines.append("|-------------|--------|-----------------|")

    orphaned_apis: list[str] = []

    for api in surfaces.apis:
        api_label = f"`{api.method} {api.path}`"
        # side_effects often contain model references
        if api.side_effects:
            model_names: list[str] = []
            for effect in api.side_effects:
                display = model_lookup.get(effect, effect)
                model_names.append(f"`{display}`")
            models_str = ", ".join(model_names)
            lines.append(f"| {api_label} | {api.method} | {models_str} |")
        else:
            orphaned_apis.append(f"{api.method} {api.path}")
            lines.append(f"| {api_label} | {api.method} | \u2014 |")

    lines.append("")

    # Orphaned models (not referenced by any API)
    referenced_models = set()
    for api in surfaces.apis:
        referenced_models.update(api.side_effects)

    orphaned_models = [
        m.name for m in surfaces.models if m.name not in referenced_models
    ]

    if orphaned_apis or orphaned_models:
        lines.append("## Orphaned Surfaces")
        lines.append("")
        if orphaned_apis:
            lines.append("**APIs with no model references:**")
            lines.append("")
            for a in orphaned_apis:
                lines.append(f"- `{a}`")
            lines.append("")
        if orphaned_models:
            lines.append("**Models not referenced by any API:**")
            lines.append("")
            for m in orphaned_models:
                lines.append(f"- `{m}`")
            lines.append("")

    return "\n".join(lines)


def _build_envvars_to_files(surfaces: SurfaceCollection) -> str:
    """Build a markdown table mapping env vars to the files that reference them."""
    lines: list[str] = [
        "# Environment Variables to Files",
        "",
        "Maps each environment variable to the files that reference it.",
        "",
    ]

    if not surfaces.config:
        lines.append("No environment variables found.")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Environment Variable | Required | Default | Files |")
    lines.append("|---------------------|----------|---------|-------|")

    orphaned_vars: list[str] = []

    for cfg in surfaces.config:
        var_name = f"`{cfg.env_var_name}`"
        required = "Yes" if cfg.required else "No"
        default = f"`{cfg.default_value}`" if cfg.default_value else "\u2014"

        # Combine usage_locations and source_refs for file list
        files: set[str] = set()
        for loc in cfg.usage_locations:
            files.add(loc)
        for ref in cfg.source_refs:
            files.add(ref.file_path)

        if files:
            files_str = ", ".join(f"`{f}`" for f in sorted(files))
        else:
            orphaned_vars.append(cfg.env_var_name)
            files_str = "\u2014"

        lines.append(f"| {var_name} | {required} | {default} | {files_str} |")

    lines.append("")

    if orphaned_vars:
        lines.append("## Orphaned Surfaces")
        lines.append("")
        lines.append("**Environment variables with no file references:**")
        lines.append("")
        for v in orphaned_vars:
            lines.append(f"- `{v}`")
        lines.append("")

    return "\n".join(lines)


def _build_middleware_to_routes(surfaces: SurfaceCollection) -> str:
    """Build a markdown table mapping middleware to the routes they apply to."""
    lines: list[str] = [
        "# Middleware to Routes",
        "",
        "Maps each middleware to the routes/endpoints it applies to.",
        "",
    ]

    if not surfaces.middleware:
        lines.append("No middleware found.")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Middleware | Type | Applies To |")
    lines.append("|-----------|------|------------|")

    for mw in surfaces.middleware:
        applies = ", ".join(f"`{a}`" for a in mw.applies_to) if mw.applies_to else "all routes"
        lines.append(f"| {mw.name} | {mw.middleware_type} | {applies} |")

    lines.append("")
    return "\n".join(lines)


def _build_state_to_components(surfaces: SurfaceCollection) -> str:
    """Build a markdown table mapping state stores to components that use them."""
    lines: list[str] = [
        "# State Management to Components",
        "",
        "Maps each state store to the components that consume its state.",
        "",
    ]

    if not surfaces.state_mgmt:
        lines.append("No state management surfaces found.")
        lines.append("")
        return "\n".join(lines)

    # Build component lookup by source file
    file_to_components: dict[str, list[str]] = {}
    for comp in surfaces.components:
        for ref in comp.source_refs:
            if ref.file_path not in file_to_components:
                file_to_components[ref.file_path] = []
            file_to_components[ref.file_path].append(comp.name)

    lines.append("| Store | Pattern | Source File | Nearby Components |")
    lines.append("|-------|---------|-------------|-------------------|")

    for sm in surfaces.state_mgmt:
        store = sm.store_name or sm.name
        nearby: list[str] = []
        for ref in sm.source_refs:
            nearby.extend(file_to_components.get(ref.file_path, []))
        components_str = ", ".join(f"`{c}`" for c in nearby) if nearby else "\u2014"
        source_file = sm.source_refs[0].file_path if sm.source_refs else "\u2014"
        lines.append(f"| {store} | {sm.pattern} | `{source_file}` | {components_str} |")

    lines.append("")
    return "\n".join(lines)


def _build_integrations_to_apis(surfaces: SurfaceCollection) -> str:
    """Build a markdown table mapping integrations to related API endpoints."""
    lines: list[str] = [
        "# Integrations to APIs",
        "",
        "Maps each external integration to related internal API endpoints.",
        "",
    ]

    if not surfaces.integrations:
        lines.append("No integrations found.")
        lines.append("")
        return "\n".join(lines)

    # Build API lookup by source file
    file_to_apis: dict[str, list[str]] = {}
    for api in surfaces.apis:
        for ref in api.source_refs:
            if ref.file_path not in file_to_apis:
                file_to_apis[ref.file_path] = []
            file_to_apis[ref.file_path].append(f"{api.method} {api.path}")

    lines.append("| Integration | Type | Target | Related APIs |")
    lines.append("|-------------|------|--------|--------------|")

    for integ in surfaces.integrations:
        related: list[str] = []
        for ref in integ.source_refs:
            related.extend(file_to_apis.get(ref.file_path, []))
        apis_str = ", ".join(f"`{a}`" for a in related) if related else "\u2014"
        lines.append(
            f"| {integ.name} | {integ.integration_type} | {integ.target_service} | {apis_str} |"
        )

    lines.append("")
    return "\n".join(lines)
