"""SQLAlchemy model extractor."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from repo_mirror_kit.harvester.analyzers.literals import sanitize_captured_literal
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

# BEAN-082: exact-value extraction. ``default=`` / ``server_default=`` capture
# the literal up to the next top-level comma or the column's closing paren.
_SA_DEFAULT_RE = re.compile(r"(?<![\w])default\s*=\s*([^,)]+)")
_SA_SERVER_DEFAULT_RE = re.compile(r"server_default\s*=\s*([^,)]+)")
# ``Enum("a", "b", name="x")`` — inner arg list; string members are kept and
# joined with ``|``; keyword args (``name=``, ``native_enum=``) are skipped.
_SA_ENUM_RE = re.compile(r"Enum\s*\(([^)]*)\)")
# ``CheckConstraint("<expr>", name="<name>")`` anywhere in the class body.
_SA_CHECK_RE = re.compile(
    r"CheckConstraint\s*\(\s*([\"'])(.+?)\1(?:\s*,\s*name\s*=\s*[\"'](\w+)[\"'])?",
    re.DOTALL,
)


def _exact_rule(
    field: str,
    rule: str,
    value: str = "",
    error_message: str | None = None,
) -> dict[str, Any]:
    """Build one ``exact_rules`` entry (BEAN-081 contract, declared confidence).

    ``value`` is the exact literal copied verbatim from source and is always
    routed through the BEAN-083 chokepoint before it is stored.
    """
    return {
        "field": field,
        "rule": rule,
        "value": sanitize_captured_literal(value) if value else "",
        "error_message": error_message,
        "confidence": "declared",
    }


def _enum_members(col_full: str) -> str | None:
    """Return ``"a|b|c"`` for an ``Enum(...)`` column, or None when absent."""
    match = _SA_ENUM_RE.search(col_full)
    if match is None:
        return None
    members: list[str] = []
    for raw in match.group(1).split(","):
        arg = raw.strip()
        if not arg or "=" in arg:  # skip keyword args (name=, native_enum=, ...)
            continue
        if arg[:1] in "\"'" and arg[-1:] in "\"'":
            members.append(arg[1:-1])
    if not members:
        return None
    return "|".join(members)


def _column_exact_rules(col_name: str, col_full: str) -> list[dict[str, Any]]:
    """Derive exact validation rules for a single SQLAlchemy column line."""
    rules: list[dict[str, Any]] = []
    if _SA_NULLABLE_RE.search(col_full):
        rules.append(_exact_rule(col_name, "NOT NULL"))
    if _SA_UNIQUE_COLUMN_RE.search(col_full):
        rules.append(_exact_rule(col_name, "unique"))
    members = _enum_members(col_full)
    if members is not None:
        rules.append(_exact_rule(col_name, "allowed values", members))
    for regex, label in (
        (_SA_SERVER_DEFAULT_RE, "server default"),
        (_SA_DEFAULT_RE, "default"),
    ):
        match = regex.search(col_full)
        if match is not None:
            rules.append(_exact_rule(col_name, label, match.group(1).strip()))
            break
    return rules


def _check_constraint_rules(body: str) -> list[dict[str, Any]]:
    """Derive exact rules for every ``CheckConstraint(...)`` in a class body."""
    rules: list[dict[str, Any]] = []
    for match in _SA_CHECK_RE.finditer(body):
        expr = match.group(2).strip()
        name = match.group(3) or "check_constraint"
        rules.append(_exact_rule(name, "check constraint", expr))
    return rules


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
            exact_rules: list[dict[str, Any]] = []
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
                exact_rules.extend(_column_exact_rules(col_name, col_full))

            # Table-level check constraints (e.g. in ``__table_args__``).
            exact_rules.extend(_check_constraint_rules(body))

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

            surface = ModelSurface(
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
            # BEAN-082: exact validation rules feed BEAN-081's rule table.
            if exact_rules:
                surface.enrichment["exact_rules"] = exact_rules
            surfaces.append(surface)

    return surfaces


__all__ = ["_extract_sqlalchemy"]
