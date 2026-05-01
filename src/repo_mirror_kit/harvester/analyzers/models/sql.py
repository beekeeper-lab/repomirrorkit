"""Plain-SQL ``CREATE TABLE`` extractor."""

from __future__ import annotations

import re
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

_SQL_FILE_RE = re.compile(r"\.sql$")

_SQL_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:`|\"|')?(\w+)(?:`|\"|')?\s*\(",
    re.IGNORECASE,
)
_SQL_COLUMN_RE = re.compile(
    r"^\s+(?:`|\"|')?(\w+)(?:`|\"|')?\s+([\w()]+(?:\(\d+(?:,\s*\d+)?\))?)"
    r"((?:\s+(?:NOT\s+NULL|PRIMARY\s+KEY|UNIQUE|DEFAULT\s+\S+|REFERENCES\s+\w+))*)",
    re.IGNORECASE | re.MULTILINE,
)
_SQL_FK_RE = re.compile(
    r"REFERENCES\s+(?:`|\"|')?(\w+)(?:`|\"|')?",
    re.IGNORECASE,
)
_SQL_PK_INLINE_RE = re.compile(r"PRIMARY\s+KEY", re.IGNORECASE)
_SQL_NOT_NULL_RE = re.compile(r"NOT\s+NULL", re.IGNORECASE)
_SQL_UNIQUE_INLINE_RE = re.compile(r"\bUNIQUE\b", re.IGNORECASE)


def _extract_sql(repo_root: Path, file_paths: list[str]) -> list[ModelSurface]:
    """Extract models from SQL CREATE TABLE statements.

    Args:
        repo_root: Repository root directory.
        file_paths: All file paths in the inventory.

    Returns:
        ModelSurface objects for each SQL table found.
    """
    surfaces: list[ModelSurface] = []
    sql_files = [p for p in file_paths if _SQL_FILE_RE.search(p)][:_MAX_FILES_PER_TECH]

    for rel_path in sql_files:
        content = _read_file(repo_root, rel_path)
        if content is None:
            continue

        for create_match in _SQL_CREATE_TABLE_RE.finditer(content):
            table_name = create_match.group(1)
            start_pos = create_match.start()
            start_line = content[:start_pos].count("\n") + 1

            # Extract the parenthesized column definitions
            paren_start = content.find("(", create_match.end() - 1)
            if paren_start == -1:
                continue
            paren_end = _find_matching_paren(content, paren_start)
            if paren_end == -1:
                continue
            body = content[paren_start + 1 : paren_end]

            fields: list[ModelField] = []
            relationships: list[str] = []

            for col_match in _SQL_COLUMN_RE.finditer(body):
                col_name = col_match.group(1)
                col_type = col_match.group(2)
                rest = col_match.group(3) or ""

                # Skip SQL keywords that appear as column names
                if col_name.upper() in (
                    "PRIMARY",
                    "UNIQUE",
                    "CHECK",
                    "FOREIGN",
                    "CONSTRAINT",
                    "INDEX",
                    "KEY",
                ):
                    continue

                constraints: list[str] = []
                if _SQL_PK_INLINE_RE.search(rest):
                    constraints.append("primary_key")
                if _SQL_NOT_NULL_RE.search(rest):
                    constraints.append("not_null")
                if _SQL_UNIQUE_INLINE_RE.search(rest):
                    constraints.append("unique")

                fk_match = _SQL_FK_RE.search(rest)
                if fk_match:
                    relationships.append(f"FK {col_name} -> {fk_match.group(1)}")

                fields.append(
                    ModelField(
                        name=col_name,
                        field_type=col_type,
                        constraints=constraints,
                    )
                )

            # Convert table name to PascalCase for entity name
            entity_name = _table_to_entity_name(table_name)

            surfaces.append(
                ModelSurface(
                    name=entity_name,
                    entity_name=entity_name,
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


def _find_matching_paren(content: str, open_pos: int) -> int:
    """Find the matching closing parenthesis.

    Args:
        content: Full text content.
        open_pos: Index of the opening ``(``.

    Returns:
        Index of the matching ``)``, or -1 if not found.
    """
    depth = 1
    i = open_pos + 1
    while i < len(content) and depth > 0:
        if content[i] == "(":
            depth += 1
        elif content[i] == ")":
            depth -= 1
        i += 1
    return i - 1 if depth == 0 else -1


__all__ = ["_extract_sql"]
