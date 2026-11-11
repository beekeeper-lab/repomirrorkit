"""Screen spec YAML + navigation map (BEAN-073).

Turns :class:`ScreenSurface` data into a machine-consumable design artifact a
rebuild agent can implement screens from — deliberately free of visual
styling. Output (``<out>/screens/``):

- ``<screen>.yaml``       one versioned spec per screen (see ``SCREEN_SCHEMA``)
- ``navigation-map.md``   Mermaid flowchart of screen-to-screen navigation
- ``README.md``           index

Output is deterministic: screens are sorted, keys are emitted in a fixed order
and nothing time-dependent is written.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog
import yaml

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ScreenSurface,
    SurfaceCollection,
)

logger = structlog.get_logger()

SCREEN_SPEC_VERSION = "1.0"
SCREENS_DIRNAME = "screens"

SCREEN_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "RepoMirrorKit screen spec",
    "type": "object",
    "required": [
        "schema_version",
        "screen",
        "route",
        "framework",
        "source",
        "fields",
        "actions",
        "navigation",
        "gaps",
    ],
    "properties": {
        "schema_version": {"const": SCREEN_SPEC_VERSION},
        "screen": {"type": "string"},
        "route": {"type": ["string", "null"]},
        "framework": {"type": "string"},
        "source": {"type": ["string", "null"]},
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "name",
                    "input_type",
                    "label",
                    "required",
                    "validation",
                    "binds_to",
                    "gap",
                ],
                "properties": {
                    "name": {"type": "string"},
                    "input_type": {"type": "string"},
                    "label": {"type": "string"},
                    "required": {"type": "boolean"},
                    "validation": {"type": "array", "items": {"type": "string"}},
                    "binds_to": {
                        "type": "object",
                        "required": ["api", "model", "confidence"],
                        "properties": {
                            "api": {"type": ["string", "null"]},
                            "model": {"type": ["string", "null"]},
                            "confidence": {"type": ["string", "null"]},
                        },
                    },
                    "gap": {"type": ["string", "null"]},
                },
            },
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["trigger", "api", "navigates_to"],
                "properties": {
                    "trigger": {"type": "string"},
                    "api": {"type": ["string", "null"]},
                    "navigates_to": {"type": ["string", "null"]},
                },
            },
        },
        "navigation": {"type": "array", "items": {"type": "string"}},
        "uses_components": {"type": "array", "items": {"type": "string"}},
        "gaps": {"type": "array", "items": {"type": "string"}},
    },
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "screen"


def screen_to_spec(screen: ScreenSurface) -> dict[str, Any]:
    """Build the spec dict for one screen (key order is the emitted order)."""
    gaps = [f"field '{f.name}': {f.gap}" for f in screen.fields if f.gap]
    return {
        "schema_version": SCREEN_SPEC_VERSION,
        "screen": screen.screen_name or screen.name,
        "route": screen.route_ref or None,
        "framework": screen.framework or "unknown",
        "source": screen.source_refs[0].file_path if screen.source_refs else None,
        "fields": [
            {
                "name": f.name,
                "input_type": f.input_type,
                "label": f.label,
                "required": f.required,
                "validation": list(f.validation),
                "binds_to": {
                    "api": f.bound_api_field,
                    "model": f.bound_model_field,
                    "confidence": f.mapping_confidence or None,
                },
                "gap": f.gap or None,
            }
            for f in screen.fields
        ],
        "actions": [
            {
                "trigger": a.trigger,
                "api": a.api_ref or None,
                "navigates_to": a.navigation_target or None,
            }
            for a in screen.actions
        ],
        "navigation": list(screen.navigation_targets),
        "uses_components": list(screen.uses_components),
        "gaps": gaps,
    }


def dump_spec(spec: dict[str, Any]) -> str:
    """Deterministic YAML text for a spec dict."""
    text: str = yaml.safe_dump(
        spec, sort_keys=False, allow_unicode=True, default_flow_style=False, width=100
    )
    return text


def _route_key(path: str) -> str:
    p = re.sub(r"\[\.{0,3}[^\]]+\]", "{}", path)
    p = re.sub(r"(?<=/):[A-Za-z_]\w*", "{}", p)
    p = re.sub(r"\{[^}]*\}", "{}", p)
    return p.rstrip("/") or "/"


def navigation_mermaid(screens: list[ScreenSurface]) -> str:
    """Mermaid flowchart: screens are nodes, navigation targets are edges."""
    ids = {id(s): f"S{i}" for i, s in enumerate(screens, start=1)}
    by_route: dict[str, ScreenSurface] = {}
    for s in screens:
        if s.route_ref:
            by_route.setdefault(_route_key(s.route_ref), s)
    lines = ["flowchart TD"]
    for s in screens:
        label = (s.screen_name or s.name).replace('"', "'")
        route = f"<br/>{s.route_ref}" if s.route_ref else ""
        node = ids[id(s)]
        lines.append(
            f'    {node}(["{label}{route}"])'
            if s.route_ref
            else f'    {node}["{label}"]'
        )
    externals: dict[str, str] = {}
    edges: list[str] = []
    for s in screens:
        targets = list(s.navigation_targets)
        for a in s.actions:
            if a.navigation_target and a.navigation_target not in targets:
                targets.append(a.navigation_target)
        for t in targets:
            dest = by_route.get(_route_key(t))
            if dest is not None:
                dst_id = ids[id(dest)]
            else:
                dst_id = externals.setdefault(t, f"X{len(externals) + 1}")
            edge = f"    {ids[id(s)]} --> {dst_id}"
            if edge not in edges:
                edges.append(edge)
    for target, node in externals.items():
        lines.append(f'    {node}[/"{target.replace(chr(34), chr(39))}"/]')
    lines.extend(edges)
    return "\n".join(lines)


def generate_screen_specs(
    surfaces: SurfaceCollection, output_dir: Path, project_name: str
) -> list[Path]:
    """Write ``<output_dir>/screens/`` and return the created files.

    Returns an empty list when no screens were detected.
    """
    screens = sorted(
        (s for s in surfaces.screens),
        key=lambda s: (
            (s.screen_name or s.name).lower(),
            s.source_refs[0].file_path if s.source_refs else "",
        ),
    )
    if not screens:
        return []
    root = output_dir / SCREENS_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    for stale in root.glob("*.yaml"):
        stale.unlink()
    written: list[Path] = []
    used: set[str] = set()
    index: list[tuple[str, ScreenSurface]] = []
    for screen in screens:
        slug = _slug(screen.screen_name or screen.name)
        base, n = slug, 2
        while slug in used:
            slug, n = f"{base}-{n}", n + 1
        used.add(slug)
        path = root / f"{slug}.yaml"
        path.write_text(dump_spec(screen_to_spec(screen)), encoding="utf-8")
        written.append(path)
        index.append((slug, screen))

    nav = root / "navigation-map.md"
    nav.write_text(
        "# Screen navigation map\n\n"
        "Rendered from the screen specs in this directory (rounded nodes are "
        "routable screens; slanted nodes are navigation targets with no "
        "detected screen).\n\n```mermaid\n" + navigation_mermaid(screens) + "\n```\n",
        encoding="utf-8",
    )
    written.append(nav)

    rows = [
        f"| [`{slug}.yaml`]({slug}.yaml) | {s.route_ref or '-'} | {len(s.fields)} | "
        f"{len(s.actions)} | {sum(1 for f in s.fields if f.gap)} |"
        for slug, s in index
    ]
    readme = root / "README.md"
    readme.write_text(
        f"# {project_name} — screen specs\n\n"
        f"Schema version `{SCREEN_SPEC_VERSION}` (see `docs/screen-spec-schema.md` in "
        "RepoMirrorKit). No visual styling is captured by design.\n\n"
        "See also: [navigation map](navigation-map.md).\n\n"
        "| Spec | Route | Fields | Actions | Field gaps |\n"
        "|------|-------|--------|---------|------------|\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    written.append(readme)
    logger.info("screen_specs_written", screens=len(screens), path=str(root))
    return written
