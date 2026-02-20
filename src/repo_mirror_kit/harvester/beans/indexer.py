"""Bean index generator for the harvester pipeline (Stage E).

Produces ``beans/_index.md`` — a master summary table listing every
generated bean — and populates ``beans/_templates/`` with the template
text files referenced by the spec.
"""

from __future__ import annotations

import logging
from pathlib import Path

from repo_mirror_kit.harvester.beans.templates import (
    render_api_bean,
    render_auth_bean,
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
from repo_mirror_kit.harvester.beans.writer import WrittenBean

logger = logging.getLogger(__name__)

# Template descriptions keyed by surface type.
_TEMPLATE_DESCRIPTIONS: dict[str, str] = {
    "route": "Page/Route bean template (spec 8.3)",
    "component": "Component bean template (spec 8.4)",
    "api": "API bean template (spec 8.5)",
    "model": "Model bean template (spec 8.6)",
    "auth": "Auth bean template (spec 8.7)",
    "config": "Config bean template (spec 8.8)",
    "crosscutting": "Crosscutting bean template (spec 8.9)",
    "state_mgmt": "State Management bean template",
    "middleware": "Middleware bean template",
    "integration": "Integration bean template",
    "ui_flow": "UI Flow bean template",
}

# Map surface type to its render function's docstring for template content.
_TEMPLATE_FUNCTIONS: dict[str, str] = {
    "route": render_route_bean.__doc__ or "",
    "component": render_component_bean.__doc__ or "",
    "api": render_api_bean.__doc__ or "",
    "model": render_model_bean.__doc__ or "",
    "auth": render_auth_bean.__doc__ or "",
    "config": render_config_bean.__doc__ or "",
    "crosscutting": render_crosscutting_bean.__doc__ or "",
    "state_mgmt": render_state_mgmt_bean.__doc__ or "",
    "middleware": render_middleware_bean.__doc__ or "",
    "integration": render_integration_bean.__doc__ or "",
    "ui_flow": render_ui_flow_bean.__doc__ or "",
}


def generate_index(
    beans: list[WrittenBean],
    output_dir: Path,
) -> Path:
    """Generate the master index file at ``beans/_index.md``.

    Produces a markdown table listing every bean with its ID, title,
    type, and status. Beans are listed in the order they were generated
    (deterministic per SurfaceCollection iteration order).

    Args:
        beans: List of WrittenBean records from the writer.
        output_dir: Root output directory containing the ``beans/``
            subdirectory.

    Returns:
        Path to the written ``_index.md`` file.
    """
    beans_dir = output_dir / "beans"
    beans_dir.mkdir(parents=True, exist_ok=True)
    index_path = beans_dir / "_index.md"

    lines: list[str] = [
        "# Bean Index",
        "",
        f"Total beans: {len(beans)}",
        "",
        "| ID | Title | Type | Status |",
        "|---|---|---|---|",
    ]

    for bean in beans:
        lines.append(f"| {bean.bean_id} | {bean.title} | {bean.surface_type} | draft |")

    lines.append("")

    index_path.write_text("\n".join(lines), encoding="utf-8")

    logger.info(
        "index_generated",
        extra={
            "path": str(index_path),
            "bean_count": len(beans),
        },
    )

    return index_path


def generate_templates_dir(output_dir: Path) -> Path:
    """Create the ``beans/_templates/`` directory with template text files.

    Each template file describes the sections expected for that bean type,
    matching the spec definitions.

    Args:
        output_dir: Root output directory containing the ``beans/``
            subdirectory.

    Returns:
        Path to the ``_templates/`` directory.
    """
    templates_dir = output_dir / "beans" / "_templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    for surface_type, description in _TEMPLATE_DESCRIPTIONS.items():
        template_path = templates_dir / f"{surface_type}.md"
        docstring = _TEMPLATE_FUNCTIONS.get(surface_type, "")
        # Extract first line of docstring for the template header
        first_line = docstring.strip().split("\n")[0] if docstring else description

        content = f"# {description}\n\n{first_line}\n"
        template_path.write_text(content, encoding="utf-8")

    logger.info(
        "templates_dir_generated",
        extra={
            "path": str(templates_dir),
            "template_count": len(_TEMPLATE_DESCRIPTIONS),
        },
    )

    return templates_dir
