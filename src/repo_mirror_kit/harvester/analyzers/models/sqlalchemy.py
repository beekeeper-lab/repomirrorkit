"""SQLAlchemy model extractor."""

from __future__ import annotations

import re
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.models._common import (
    _MAX_FILES_PER_TECH,
    _read_file,
)
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ModelField,
    ModelSurface,
    SourceRef,
)

_PYTHON_FILE_RE = re.compile(r"\.py$")
_PYTHON_MODEL_FILE_RE = re.compile(r"(?:^|/)models?\.py$")

_SA_CLASS_RE = re.compile(
    r"^class\s+(\w+)\s*\(.*(?:Base|Model|db\.Model)\b.*\)\s*:",
    re.MULTILINE,
)
_SA_TABLENAME_RE = re.compile(r'__tablename__\s*=\s*["\'](\w+)["\']')
_SA_COLUMN_RE = re.compile(r"(\w+)\s*=\s*(?:db\.)?Column\s*\(\s*([\w.]+)")
_SA_RELATIONSHIP_RE = re.compile(
    r"(\w+)\s*=\s*(?:db\.)?relationship\s*\(\s*['\"](\w+)['\"]"
)
_SA_FK_RE = re.compile(r"ForeignKey\s*\(\s*['\"]([^'\"]+)['\"]")
_SA_PK_RE = re.compile(r"primary_key\s*=\s*True")
_SA_NULLABLE_RE = re.compile(r"nullable\s*=\s*False")
_SA_UNIQUE_COLUMN_RE = re.compile(r"unique\s*=\s*True")


def _extract_sqlalchemy(repo_root: Path, file_paths: list[str]) -> list[ModelSurface]:
    """Extract models from SQLAlchemy model classes.

    Args:
        repo_root: Repository root directory.
        file_paths: All file paths in the inventory.

    Returns:
        ModelSurface objects for each SQLAlchemy model found.
    """
    surfaces: list[ModelSurface] = []
    model_files = [
        p
        for p in file_paths
        if _PYTHON_MODEL_FILE_RE.search(p) and _PYTHON_FILE_RE.search(p)
    ][:_MAX_FILES_PER_TECH]

    for rel_path in model_files:
        content = _read_file(repo_root, rel_path)
        if content is None:
            continue

        for class_match in _SA_CLASS_RE.finditer(content):
            class_name = class_match.group(1)
            start_pos = class_match.start()
            start_line = content[:start_pos].count("\n") + 1

            # Extract class body (rough: until next class or end)
            body_start = class_match.end()
            next_class = _SA_CLASS_RE.search(content, body_start)
            body_end = next_class.start() if next_class else len(content)
            body = content[body_start:body_end]

            # Table name
            table_match = _SA_TABLENAME_RE.search(body)
            table_name = table_match.group(1) if table_match else class_name.lower()

            # Columns
            fields: list[ModelField] = []
            for col_match in _SA_COLUMN_RE.finditer(body):
                col_name = col_match.group(1)
                col_type = col_match.group(2)

                # Get the full column definition for constraints
                col_line_start = body.rfind("\n", 0, col_match.start())
                col_line_end = body.find("\n", col_match.end())
                if col_line_end == -1:
                    col_line_end = len(body)
                col_full = body[col_line_start:col_line_end]

                constraints: list[str] = []
                if _SA_PK_RE.search(col_full):
                    constraints.append("primary_key")
                if _SA_NULLABLE_RE.search(col_full):
                    constraints.append("not_null")
                if _SA_UNIQUE_COLUMN_RE.search(col_full):
                    constraints.append("unique")

                fields.append(
                    ModelField(
                        name=col_name,
                        field_type=col_type,
                        constraints=constraints,
                    )
                )

            # Relationships
            relationships: list[str] = []
            for rel_match in _SA_RELATIONSHIP_RE.finditer(body):
                rel_name = rel_match.group(1)
                target = rel_match.group(2)
                relationships.append(f"{rel_name} -> {target}")

            # Foreign keys
            for fk_match in _SA_FK_RE.finditer(body):
                fk_ref = fk_match.group(1)
                if fk_ref not in relationships:
                    relationships.append(f"FK -> {fk_ref}")

            surfaces.append(
                ModelSurface(
                    name=class_name,
                    entity_name=class_name,
                    fields=fields,
                    relationships=relationships,
                    persistence_refs=[table_name],
                    source_refs=[
                        SourceRef(
                            file_path=rel_path,
                            start_line=start_line,
                        )
                    ],
                )
            )

    return surfaces


__all__ = ["_extract_sqlalchemy"]
