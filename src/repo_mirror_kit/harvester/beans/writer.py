"""Bean file writer for the harvester pipeline (Stage E).

Iterates a SurfaceCollection in deterministic order, renders each surface
through its template, and writes bean markdown files to disk. Supports
resume (skip already-written beans) and periodic checkpointing via
StateManager.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import SurfaceCollection
from repo_mirror_kit.harvester.beans.templates import render_bean
from repo_mirror_kit.harvester.state import StateManager

logger = logging.getLogger(__name__)


def slugify(name: str) -> str:
    """Generate a URL-safe slug from a surface name.

    Converts to lowercase, replaces non-alphanumeric characters with
    hyphens, collapses consecutive hyphens, and strips leading/trailing
    hyphens.

    Args:
        name: The surface name to slugify.

    Returns:
        A lowercase, hyphen-separated slug with no special characters.
    """
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug if slug else "unnamed"


@dataclass(frozen=True)
class WrittenBean:
    """Record of a bean that was written to disk.

    Attributes:
        bean_number: The 1-based sequential number.
        bean_id: The formatted ID (e.g. "BEAN-001").
        slug: The generated slug.
        surface_type: The type of surface rendered.
        title: The surface name / bean title.
        path: The file path where the bean was written.
        skipped: True if this bean was skipped on resume.
    """

    bean_number: int
    bean_id: str
    slug: str
    surface_type: str
    title: str
    path: Path
    skipped: bool = False


def write_beans(
    collection: SurfaceCollection,
    output_dir: Path,
    state: StateManager | None = None,
) -> list[WrittenBean]:
    """Write bean files from a SurfaceCollection to disk.

    Iterates the collection in deterministic order (routes, components,
    APIs, models, auth, config, crosscutting). Each surface is rendered
    through its template and written as ``BEAN-###-<slug>.md`` inside the
    ``beans/`` subdirectory of ``output_dir``.

    Already-written beans are skipped on resume (based on StateManager
    bean count). Checkpointing occurs every N beans as configured.

    Args:
        collection: The surfaces to render into beans.
        output_dir: Root output directory. Beans are written to
            ``output_dir/beans/``.
        state: Optional StateManager for resume and checkpoint support.

    Returns:
        List of WrittenBean records for all beans (including skipped).
    """
    beans_dir = output_dir / "beans"
    beans_dir.mkdir(parents=True, exist_ok=True)

    results: list[WrittenBean] = []
    bean_number = 0

    for surface in collection:
        bean_number += 1
        bean_id = f"BEAN-{bean_number:03d}"
        slug = slugify(surface.name)
        filename = f"{bean_id}-{slug}.md"
        file_path = beans_dir / filename

        # Resume: skip already-written beans
        if state is not None and state.should_skip_bean(bean_number):
            logger.info(
                "bean_skipped",
                extra={
                    "bean_id": bean_id,
                    "reason": "already_written",
                },
            )
            results.append(
                WrittenBean(
                    bean_number=bean_number,
                    bean_id=bean_id,
                    slug=slug,
                    surface_type=surface.surface_type,
                    title=surface.name,
                    path=file_path,
                    skipped=True,
                )
            )
            continue

        # Render and write
        content = render_bean(surface, bean_id)
        file_path.write_text(content, encoding="utf-8")

        logger.info(
            "bean_written",
            extra={
                "bean_id": bean_id,
                "path": str(file_path),
                "surface_type": surface.surface_type,
            },
        )

        # Checkpoint via state manager
        if state is not None:
            state.record_bean(bean_number)

        results.append(
            WrittenBean(
                bean_number=bean_number,
                bean_id=bean_id,
                slug=slug,
                surface_type=surface.surface_type,
                title=surface.name,
                path=file_path,
            )
        )

    logger.info(
        "bean_generation_complete",
        extra={
            "total_beans": bean_number,
            "written": sum(1 for r in results if not r.skipped),
            "skipped": sum(1 for r in results if r.skipped),
        },
    )

    return results
