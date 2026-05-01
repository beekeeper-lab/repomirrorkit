"""Top-level ``REQUIREMENTS.md`` aggregator (BEAN-051).

Consolidates the surface analysis into a single human- and AI-consumable
specification at the root of the harvest output directory. Each detected
surface is listed with a one-line summary and a relative link to its bean
file. The file is the "front door" of the harvest — a reader who only
opens this one document gets a complete picture of what would need to be
built to recreate the analyzed project.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    Surface,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.beans.writer import WrittenBean
from repo_mirror_kit.harvester.detectors.base import StackProfile

# Sections rendered in this order. Each tuple is (section title,
# surface_type discriminator, getter returning the list, "(none)" hint).
_SECTIONS: tuple[tuple[str, str, str, str], ...] = (
    ("Routes / Pages", "route", "routes", "No HTTP routes or UI pages detected."),
    ("APIs", "api", "apis", "No API endpoints detected."),
    ("Data Models", "model", "models", "No data models detected."),
    ("Authentication & Authorization", "auth", "auth", "No auth surfaces detected."),
    ("UI Components", "component", "components", "No reusable UI components detected."),
    ("UI Flows", "ui_flow", "ui_flows", "No multi-step UI flows detected."),
    (
        "State Management",
        "state_mgmt",
        "state_mgmt",
        "No client-side state stores detected.",
    ),
    ("Middleware", "middleware", "middleware", "No middleware surfaces detected."),
    (
        "Configuration & Environment",
        "config",
        "config",
        "No configuration / env-var usage detected.",
    ),
    (
        "External Integrations",
        "integration",
        "integrations",
        "No external integrations detected.",
    ),
    (
        "Cross-Cutting Concerns",
        "crosscutting",
        "crosscutting",
        "No cross-cutting concerns detected (logging/errors/telemetry/jobs).",
    ),
    (
        "Dependencies",
        "dependency",
        "dependencies",
        "No declared dependencies detected.",
    ),
    (
        "Build & Deploy",
        "build_deploy",
        "build_deploy",
        "No build/deploy configuration detected.",
    ),
    ("Testing", "test_pattern", "test_patterns", "No tests detected."),
    (
        "Other Logic",
        "general_logic",
        "general_logic",
        "No additional uncovered logic detected.",
    ),
)


def generate_requirements_md(
    project_name: str,
    surfaces: SurfaceCollection,
    profile: StackProfile,
    beans: list[WrittenBean],
    output_dir: Path,
) -> Path:
    """Render ``<output_dir>/REQUIREMENTS.md`` and return its path.

    Args:
        project_name: Human-readable project name (typically derived from
            the source repo URL by the pipeline).
        surfaces: All extracted surfaces.
        profile: Detected technology stack profile.
        beans: WrittenBean records (one per surface) for resolving links.
        output_dir: The harvest output root. ``REQUIREMENTS.md`` is
            written at the top level of this directory.

    Returns:
        The absolute path of the written ``REQUIREMENTS.md``.
    """
    bean_index = _index_beans_by_surface(beans)
    text = _render(project_name, surfaces, profile, bean_index, len(beans))
    path = output_dir / "REQUIREMENTS.md"
    path.write_text(text, encoding="utf-8")
    return path


def _index_beans_by_surface(
    beans: Iterable[WrittenBean],
) -> dict[tuple[str, str], WrittenBean]:
    """Build a (surface_type, surface_name) -> WrittenBean map for link resolution."""
    return {(b.surface_type, b.title): b for b in beans}


def _render(
    project_name: str,
    surfaces: SurfaceCollection,
    profile: StackProfile,
    bean_index: dict[tuple[str, str], WrittenBean],
    bean_count: int,
) -> str:
    """Render the full document to a string."""
    parts: list[str] = []
    parts.append(_render_header(project_name, profile, bean_count))
    parts.append(_render_tech_stack(profile))
    parts.append("## Functional Requirements\n")

    for section_title, surface_type, attr_name, empty_hint in _SECTIONS:
        items: list[Surface] = list(getattr(surfaces, attr_name))
        parts.append(
            _render_section(section_title, surface_type, items, empty_hint, bean_index)
        )

    parts.append(_render_reports_footer())
    return "\n".join(parts)


def _render_header(project_name: str, profile: StackProfile, bean_count: int) -> str:
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    detected = ", ".join(sorted(profile.stacks)) or "(none detected)"
    return (
        f"# {project_name} — Requirements Specification\n"
        "\n"
        "| Field | Value |\n"
        "|-------|-------|\n"
        f"| Generated | {timestamp} |\n"
        f"| Project | {project_name} |\n"
        f"| Total beans | {bean_count} |\n"
        f"| Tech stacks detected | {detected} |\n"
        "\n"
        "This document is the front door of the harvest. Each section "
        "lists detected surfaces with a one-line summary and a relative "
        "link to its per-surface bean file. With LLM enrichment enabled, "
        "individual beans contain behavioral descriptions, acceptance "
        "criteria, and inferred intent.\n"
    )


def _render_tech_stack(profile: StackProfile) -> str:
    lines = ["## Tech Stack", ""]
    if not profile.stacks:
        lines.append("No technology stack signals detected.\n")
        return "\n".join(lines) + "\n"
    lines.append("| Stack | Confidence | Evidence (sample) |")
    lines.append("|-------|-----------:|-------------------|")
    for name in sorted(profile.stacks):
        confidence = profile.stacks[name]
        evidence = profile.evidence.get(name, [])
        sample = ", ".join(evidence[:3]) if evidence else "—"
        lines.append(f"| {name} | {confidence:.2f} | {sample} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def _render_section(
    title: str,
    surface_type: str,
    items: list[Surface],
    empty_hint: str,
    bean_index: dict[tuple[str, str], WrittenBean],
) -> str:
    """Render a single domain section."""
    count = len(items)
    lines = [f"### {title} ({count})", ""]

    if not items:
        lines.append(f"_{empty_hint}_\n")
        return "\n".join(lines) + "\n"

    lines.append("| Surface | Source | Bean |")
    lines.append("|---------|--------|------|")
    for surface in items:
        source = _format_source(surface)
        bean_link = _format_bean_link(surface_type, surface.name, bean_index)
        # Pipe characters in surface names break markdown tables; replace.
        safe_name = surface.name.replace("|", "\\|")
        lines.append(f"| {safe_name} | {source} | {bean_link} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def _format_source(surface: Surface) -> str:
    if not surface.source_refs:
        return "—"
    ref = surface.source_refs[0]
    if ref.start_line is not None:
        return f"`{ref.file_path}:{ref.start_line}`"
    return f"`{ref.file_path}`"


def _format_bean_link(
    surface_type: str,
    surface_name: str,
    bean_index: dict[tuple[str, str], WrittenBean],
) -> str:
    bean = bean_index.get((surface_type, surface_name))
    if bean is None:
        return "—"
    rel = Path("beans") / bean.path.name
    # Markdown link with bean ID as anchor text.
    return f"[{bean.bean_id}]({rel.as_posix()})"


def _render_reports_footer() -> str:
    return (
        "## Reports & Traceability\n"
        "\n"
        "- [Data model & ER diagram](data-model.md)\n"
        "- [Coverage report](reports/coverage.md)\n"
        "- [Gap analysis](reports/gaps.md)\n"
        "- [File coverage](reports/file-coverage.md)\n"
        "- [Surface map](reports/surface-map.md)\n"
        "- [Inventory](reports/inventory.json)\n"
        "- Per-surface beans: see [`beans/`](beans/)\n"
        "- Generated Claude Code project scaffold: see [`project-folder/`](project-folder/)\n"
    )
