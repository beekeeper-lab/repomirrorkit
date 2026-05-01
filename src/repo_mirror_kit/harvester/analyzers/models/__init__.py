"""Model & Entity Analyzer (BEAN-057 — split by framework).

Extracts data models and entities from repositories by parsing source files
for ORM definitions, schema files, and SQL migration statements. Produces
``ModelSurface`` objects with entity names, fields, relationships, and
persistence references.

Supported data technologies (one submodule per framework):

- :mod:`prisma`           — ``schema.prisma`` files
- :mod:`sqlalchemy`       — Python model classes
- :mod:`entity_framework` — C# entity classes
- :mod:`typeorm`          — TypeORM / Sequelize decorators
- :mod:`sql`              — Plain SQL ``CREATE TABLE`` statements
- :mod:`alembic`          — ``op.create_table()`` / ``op.add_column()``

Adding a new framework:

1. Create a new submodule under this package with an
   ``_extract_<framework>(repo_root, file_paths) -> list[ModelSurface]``
   function and any framework-specific patterns.
2. Register it in the ``_strategies`` list below with the stack name(s)
   from :class:`StackProfile` that should trigger it.

The dispatcher's iteration order, dedup logic, and logging shape are
preserved exactly from the pre-split implementation, so output is
byte-identical for the same input.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.models.alembic import _extract_alembic
from repo_mirror_kit.harvester.analyzers.models.entity_framework import (
    _extract_entity_framework,
)
from repo_mirror_kit.harvester.analyzers.models.prisma import _extract_prisma
from repo_mirror_kit.harvester.analyzers.models.sql import _extract_sql
from repo_mirror_kit.harvester.analyzers.models.sqlalchemy import _extract_sqlalchemy
from repo_mirror_kit.harvester.analyzers.models.typeorm import _extract_typeorm
from repo_mirror_kit.harvester.analyzers.surfaces import ModelSurface
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

_Strategy = Callable[[Path, list[str]], list[ModelSurface]]


def analyze_models(
    repo_root: Path,
    inventory: InventoryResult,
    profile: StackProfile,
) -> list[ModelSurface]:
    """Extract model/entity surfaces from detected data technologies.

    Only runs extraction strategies for technologies present in the
    ``StackProfile``. Each strategy reads relevant source files,
    parses them for model definitions, and produces ``ModelSurface``
    objects.

    Args:
        repo_root: Absolute path to the repository working directory.
        inventory: File inventory from the repository scan.
        profile: Detection profile indicating which data stacks are present.

    Returns:
        A list of ``ModelSurface`` objects extracted from the repository.
    """
    detected = set(profile.stacks.keys())
    file_paths = [f.path for f in inventory.files]
    surfaces: list[ModelSurface] = []

    strategies: list[tuple[set[str], _Strategy]] = [
        ({"prisma"}, _extract_prisma),
        ({"sqlalchemy"}, _extract_sqlalchemy),
        ({"entity-framework"}, _extract_entity_framework),
        ({"sql-migrations"}, _extract_typeorm),
        ({"sql-migrations", "flyway", "liquibase"}, _extract_sql),
        ({"alembic"}, _extract_alembic),
    ]

    for trigger_stacks, strategy in strategies:
        if detected & trigger_stacks:
            tech_name = strategy.__name__.replace("_extract_", "")
            logger.info("model_analysis_starting", technology=tech_name)
            try:
                results = strategy(repo_root, file_paths)
                surfaces.extend(results)
                logger.info(
                    "model_analysis_complete",
                    technology=tech_name,
                    models_found=len(results),
                )
            except Exception:
                logger.exception("model_analysis_failed", technology=tech_name)

    # Deduplicate by entity name or persistence ref (keep first occurrence)
    seen_names: set[str] = set()
    seen_tables: set[str] = set()
    unique: list[ModelSurface] = []
    for surface in surfaces:
        name_key = surface.entity_name.lower()
        table_keys = frozenset(r.lower() for r in surface.persistence_refs)
        if name_key in seen_names or (table_keys & seen_tables):
            continue
        seen_names.add(name_key)
        seen_tables.update(table_keys)
        unique.append(surface)

    logger.info(
        "model_analysis_summary",
        total_models=len(unique),
        technologies=list(detected),
    )
    return unique


__all__ = ["analyze_models"]
