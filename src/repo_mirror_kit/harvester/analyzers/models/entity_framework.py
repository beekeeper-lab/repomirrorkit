"""Entity Framework (C#) model extractor."""

from __future__ import annotations

import re
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.models._common import (
    _MAX_FILES_PER_TECH,
    _extract_braced_block,
    _read_file,
)
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ModelField,
    ModelSurface,
    SourceRef,
)

_CSHARP_FILE_RE = re.compile(r"\.cs$")

_EF_CLASS_RE = re.compile(r"public\s+class\s+(\w+)\b")
_EF_DBSET_RE = re.compile(r"DbSet<(\w+)>")
_EF_PROPERTY_RE = re.compile(r"public\s+([\w<>?\[\]]+)\s+(\w+)\s*\{\s*get;\s*set;\s*\}")
_EF_KEY_RE = re.compile(r"\[Key\]")
_EF_REQUIRED_RE = re.compile(r"\[Required\]")
_EF_TABLE_RE = re.compile(r'\[Table\("(\w+)"\)\]')
_EF_FK_PROPERTY_RE = re.compile(r"(\w+)Id$")


def _extract_entity_framework(
    repo_root: Path, file_paths: list[str]
) -> list[ModelSurface]:
    """Extract models from Entity Framework C# entity classes.

    Scans for DbContext classes to find DbSet properties (entity names),
    then extracts properties from entity classes.

    Args:
        repo_root: Repository root directory.
        file_paths: All file paths in the inventory.

    Returns:
        ModelSurface objects for each EF entity found.
    """
    surfaces: list[ModelSurface] = []
    cs_files = [p for p in file_paths if _CSHARP_FILE_RE.search(p)][
        :_MAX_FILES_PER_TECH
    ]

    # First pass: collect DbSet entity names from DbContext files
    entity_names: set[str] = set()
    for rel_path in cs_files:
        content = _read_file(repo_root, rel_path)
        if content is None:
            continue
        for dbset_match in _EF_DBSET_RE.finditer(content):
            entity_names.add(dbset_match.group(1))

    # Second pass: find classes matching entity names and extract properties
    for rel_path in cs_files:
        content = _read_file(repo_root, rel_path)
        if content is None:
            continue

        for class_match in _EF_CLASS_RE.finditer(content):
            class_name = class_match.group(1)
            if entity_names and class_name not in entity_names:
                continue
            if not entity_names:
                # No DbContext found — skip classes that look like infrastructure
                if class_name.endswith("Context") or class_name.endswith("Migration"):
                    continue

            start_pos = class_match.start()
            start_line = content[:start_pos].count("\n") + 1

            # Extract class body
            body_start = content.find("{", class_match.end())
            if body_start == -1:
                continue
            body = _extract_braced_block(content, body_start)

            # Table annotation
            table_match = _EF_TABLE_RE.search(
                content[max(0, start_pos - 100) : start_pos]
            )
            table_name = table_match.group(1) if table_match else class_name + "s"

            # Properties
            fields: list[ModelField] = []
            relationships: list[str] = []
            prev_line_end = 0

            for prop_match in _EF_PROPERTY_RE.finditer(body):
                prop_type = prop_match.group(1)
                prop_name = prop_match.group(2)

                # Look at preceding lines for data annotations
                prop_start = prop_match.start()
                preceding = body[prev_line_end:prop_start]
                prev_line_end = prop_match.end()

                constraints: list[str] = []
                if _EF_KEY_RE.search(preceding) or prop_name == "Id":
                    constraints.append("primary_key")
                if _EF_REQUIRED_RE.search(preceding):
                    constraints.append("not_null")

                # Check for navigation properties (relationships)
                if prop_type.startswith("ICollection") or prop_type.startswith("List"):
                    relationships.append(f"{prop_name} -> {prop_type}")
                    continue

                # Check for FK pattern (e.g. UserId)
                fk_match = _EF_FK_PROPERTY_RE.match(prop_name)
                if fk_match and prop_type in (
                    "int",
                    "int?",
                    "Guid",
                    "Guid?",
                    "long",
                    "long?",
                ):
                    relationships.append(f"FK {prop_name} -> {fk_match.group(1)}")

                fields.append(
                    ModelField(
                        name=prop_name,
                        field_type=prop_type,
                        constraints=constraints,
                    )
                )

            if fields or relationships:
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


__all__ = ["_extract_entity_framework"]
