"""Alembic migration extractor."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.models._common import (
    _MAX_FILES_PER_TECH,
    _read_file,
    _table_to_entity_name,
)
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ModelField,
    ModelSurface,
    SourceRef,
)

_ALEMBIC_VERSIONS_RE = re.compile(r"(?:^|/)alembic/versions/.*\.py$")

_ALEMBIC_CREATE_TABLE_RE = re.compile(r"op\.create_table\s*\(\s*['\"](\w+)['\"]")
_ALEMBIC_COLUMN_RE = re.compile(
    r"sa\.Column\s*\(\s*['\"](\w+)['\"]\s*,\s*sa\.(\w+(?:\([^)]*\))?)"
)
_ALEMBIC_ADD_COLUMN_RE = re.compile(
    r"op\.add_column\s*\(\s*['\"](\w+)['\"]\s*,\s*sa\.Column\s*\(\s*['\"](\w+)['\"]\s*,\s*sa\.(\w+(?:\([^)]*\))?)"
)


@dataclass
class _AlembicTable:
    """Internal accumulator for Alembic table data."""

    name: str
    fields: list[ModelField]
    source_file: str
    start_line: int


def _extract_alembic(repo_root: Path, file_paths: list[str]) -> list[ModelSurface]:
    """Extract models from Alembic migration files.

    Parses ``op.create_table()`` and ``op.add_column()`` calls.

    Args:
        repo_root: Repository root directory.
        file_paths: All file paths in the inventory.

    Returns:
        ModelSurface objects for each table created in Alembic migrations.
    """
    surfaces: list[ModelSurface] = []
    migration_files = [p for p in file_paths if _ALEMBIC_VERSIONS_RE.search(p)][
        :_MAX_FILES_PER_TECH
    ]

    # Collect all tables and their columns across migration files
    tables: dict[str, _AlembicTable] = {}

    for rel_path in migration_files:
        content = _read_file(repo_root, rel_path)
        if content is None:
            continue

        # op.create_table()
        for create_match in _ALEMBIC_CREATE_TABLE_RE.finditer(content):
            tbl_name = create_match.group(1)
            start_line = content[: create_match.start()].count("\n") + 1

            if tbl_name not in tables:
                tables[tbl_name] = _AlembicTable(
                    name=tbl_name,
                    fields=[],
                    source_file=rel_path,
                    start_line=start_line,
                )

            # Find columns in the create_table call
            call_start = create_match.end()
            for col_match in _ALEMBIC_COLUMN_RE.finditer(
                content[call_start : call_start + 2000]
            ):
                col_name = col_match.group(1)
                col_type = col_match.group(2)
                tables[tbl_name].fields.append(
                    ModelField(
                        name=col_name,
                        field_type=col_type,
                        constraints=[],
                    )
                )

        # op.add_column()
        for add_match in _ALEMBIC_ADD_COLUMN_RE.finditer(content):
            tbl_name = add_match.group(1)
            col_name = add_match.group(2)
            col_type = add_match.group(3)

            if tbl_name not in tables:
                start_line = content[: add_match.start()].count("\n") + 1
                tables[tbl_name] = _AlembicTable(
                    name=tbl_name,
                    fields=[],
                    source_file=rel_path,
                    start_line=start_line,
                )

            tables[tbl_name].fields.append(
                ModelField(
                    name=col_name,
                    field_type=col_type,
                    constraints=[],
                )
            )

    for tbl_name, tbl in tables.items():
        entity_name = _table_to_entity_name(tbl_name)
        surfaces.append(
            ModelSurface(
                name=entity_name,
                entity_name=entity_name,
                fields=tbl.fields,
                relationships=[],
                persistence_refs=[tbl_name],
                source_refs=[
                    SourceRef(
                        file_path=tbl.source_file,
                        start_line=tbl.start_line,
                    )
                ],
            )
        )

    return surfaces


__all__ = ["_extract_alembic"]
