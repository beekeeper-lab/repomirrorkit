"""TypeORM / Sequelize decorator-based model extractor."""

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

_TS_JS_FILE_RE = re.compile(r"\.[jt]sx?$")

_TYPEORM_ENTITY_RE = re.compile(r"@Entity\s*\(")
_TYPEORM_COLUMN_RE = re.compile(
    r"@(Column|PrimaryGeneratedColumn|PrimaryColumn|CreateDateColumn"
    r"|UpdateDateColumn|DeleteDateColumn)\s*\([^)]*\)\s*\n\s*(\w+)\s*[!?]?\s*:\s*([\w\[\]|<> ]+)"
)
_TYPEORM_RELATION_RE = re.compile(
    r"@(?:ManyToOne|OneToMany|OneToOne|ManyToMany)\s*\([^)]*(?:\([^)]*\)[^)]*)*\)\s*\n\s*(\w+)\s*[!?]?\s*:\s*([\w\[\]|<> ]+)"
)
_TYPEORM_CLASS_RE = re.compile(r"class\s+(\w+)\s*(?:extends\s+\w+)?\s*\{")


def _extract_typeorm(repo_root: Path, file_paths: list[str]) -> list[ModelSurface]:
    """Extract models from TypeORM/Sequelize decorator patterns.

    Args:
        repo_root: Repository root directory.
        file_paths: All file paths in the inventory.

    Returns:
        ModelSurface objects for each TypeORM/Sequelize entity found.
    """
    surfaces: list[ModelSurface] = []
    ts_js_files = [
        p
        for p in file_paths
        if _TS_JS_FILE_RE.search(p) and ("model" in p.lower() or "entity" in p.lower())
    ][:_MAX_FILES_PER_TECH]

    for rel_path in ts_js_files:
        content = _read_file(repo_root, rel_path)
        if content is None:
            continue

        if not _TYPEORM_ENTITY_RE.search(content):
            continue

        for class_match in _TYPEORM_CLASS_RE.finditer(content):
            class_name = class_match.group(1)
            start_pos = class_match.start()
            start_line = content[:start_pos].count("\n") + 1

            # Check that @Entity precedes this class
            preceding = content[max(0, start_pos - 200) : start_pos]
            if not _TYPEORM_ENTITY_RE.search(preceding):
                continue

            body_start = content.find("{", class_match.start())
            if body_start == -1:
                continue
            body = _extract_braced_block(content, body_start)

            fields: list[ModelField] = []
            relationships: list[str] = []

            for col_match in _TYPEORM_COLUMN_RE.finditer(body):
                decorator_name = col_match.group(1)
                col_name = col_match.group(2)
                col_type = col_match.group(3).strip()
                constraints: list[str] = []

                if decorator_name in (
                    "PrimaryGeneratedColumn",
                    "PrimaryColumn",
                ):
                    constraints.append("primary_key")

                fields.append(
                    ModelField(
                        name=col_name,
                        field_type=col_type,
                        constraints=constraints,
                    )
                )

            for rel_match in _TYPEORM_RELATION_RE.finditer(body):
                rel_name = rel_match.group(1)
                rel_type = rel_match.group(2).strip()
                relationships.append(f"{rel_name} -> {rel_type}")

            if fields or relationships:
                surfaces.append(
                    ModelSurface(
                        name=class_name,
                        entity_name=class_name,
                        fields=fields,
                        relationships=relationships,
                        persistence_refs=[class_name],
                        source_refs=[
                            SourceRef(
                                file_path=rel_path,
                                start_line=start_line,
                            )
                        ],
                    )
                )

    return surfaces


__all__ = ["_extract_typeorm"]
