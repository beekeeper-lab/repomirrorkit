"""SQLAlchemy model extractor.

Supports the classic ``db.Column(...)`` style (regex) and SQLAlchemy 2.0
declarative style — ``id: Mapped[int] = mapped_column(primary_key=True)`` with
``relationship(...)`` — via ``ast`` (found missing by the microblog real-world
eval: 5 models, 0 fields).
"""

from __future__ import annotations

import ast
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
    ModelRelationship,
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
_SA_LENGTH_RE = re.compile(r"String\s*\(\s*(\d+)\s*\)")

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

        file_start = len(surfaces)
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
                fk_match = _SA_FK_RE.search(col_full)
                if fk_match:
                    constraints.append(f"fk={fk_match.group(1)}")
                length = _SA_LENGTH_RE.search(col_full)
                if length:
                    constraints.append(f"max_length={length.group(1)}")

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
        _fill_sa2(content, surfaces[file_start:])

    return surfaces


def _ann_inner(node: ast.expr | None) -> tuple[str, bool]:
    """(inner type text, optional?) of ``Mapped[...]`` / ``WriteOnlyMapped[...]``."""
    if isinstance(node, ast.Subscript):
        outer = ast.unparse(node.value)
        inner = node.slice
        if outer.rsplit(".", 1)[-1] in ("Mapped", "WriteOnlyMapped", "DynamicMapped"):
            text = ast.unparse(inner)
            optional = (
                text.startswith("Optional[") or "| None" in text or "None |" in text
            )
            if text.startswith("Optional["):
                text = text[len("Optional[") : -1]
            text = text.replace(" | None", "").replace("None | ", "")
            return text.strip("'\""), optional
    return "", False


def _kw_true(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _kw_false(node: ast.expr | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is False


def _sa2_class_fields(
    cls: ast.ClassDef,
) -> tuple[list[ModelField], list[str], list[ModelRelationship], str | None]:
    fields: list[ModelField] = []
    relationships: list[str] = []
    details: list[ModelRelationship] = []
    table: str | None = None
    pending: list[tuple[str, str, bool]] = []
    for stmt in cls.body:
        if isinstance(stmt, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__tablename__" for t in stmt.targets
        ):
            if isinstance(stmt.value, ast.Constant) and isinstance(
                stmt.value.value, str
            ):
                table = stmt.value.value
            continue
        if not (isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)):
            continue
        name = stmt.target.id
        inner, optional = _ann_inner(stmt.annotation)
        call = stmt.value if isinstance(stmt.value, ast.Call) else None
        callee = ast.unparse(call.func).rsplit(".", 1)[-1] if call else ""
        if callee == "mapped_column":
            constraints: list[str] = []
            kws = {k.arg: k.value for k in call.keywords if k.arg} if call else {}
            col_type = inner or "unknown"
            fk: str | None = None
            for arg in call.args if call else []:
                text = ast.unparse(arg)
                if isinstance(arg, ast.Call) and ast.unparse(arg.func).endswith(
                    "ForeignKey"
                ):
                    if arg.args and isinstance(arg.args[0], ast.Constant):
                        fk = str(arg.args[0].value)
                    elif arg.args:
                        fk = ast.unparse(arg.args[0])  # e.g. User.id
                elif isinstance(
                    arg, (ast.Call, ast.Attribute, ast.Name)
                ) and not text.startswith(("'", '"')):
                    col_type = text
                    length = re.search(r"\(\s*(\d+)\s*\)", text)
                    if length:
                        constraints.append(f"max_length={length.group(1)}")
            if _kw_true(kws.get("primary_key")):
                constraints.append("primary_key")
            elif _kw_false(kws.get("nullable")) or (
                not optional and "nullable" not in kws
            ):
                constraints.append("not_null")
            if _kw_true(kws.get("unique")):
                constraints.append("unique")
            if fk:
                constraints.append(f"fk={fk}")
                relationships.append(f"FK -> {fk}")
            fields.append(
                ModelField(name=name, field_type=col_type, constraints=constraints)
            )
        elif callee == "relationship":
            target = inner
            is_list = target.startswith(("list[", "List[", "set["))
            if is_list:
                target = target[target.index("[") + 1 : -1].strip("'\"")
            if (
                not target
                and call
                and call.args
                and isinstance(call.args[0], ast.Constant)
            ):
                target = str(call.args[0].value)
            if target:
                relationships.append(f"{name} -> {target}")
                outer = (
                    ast.unparse(stmt.annotation.value).rsplit(".", 1)[-1]
                    if isinstance(stmt.annotation, ast.Subscript)
                    else ""
                )
                many = is_list or outer in ("WriteOnlyMapped", "DynamicMapped")
                pending.append((name, target, many))
    # Resolve FK columns for many-to-one relationships from mapped_column FKs.
    for _rel_name, target, many in pending:
        fk_col: str | None = None
        if not many:
            for f in fields:
                fk = next((c[3:] for c in f.constraints if c.startswith("fk=")), None)
                if fk and fk.split(".")[0].lower().rstrip("s") == target.lower().rstrip(
                    "s"
                ):
                    fk_col = f.name
                    break
        details.append(
            ModelRelationship(
                source_model=cls.name,
                target_model=target,
                kind="one_to_many" if many else "many_to_one",
                fk_column=fk_col,
            )
        )
    return fields, relationships, details, table


def _fill_sa2(content: str, surfaces: list[ModelSurface]) -> None:
    """Populate fields/relationships of empty surfaces from SA 2.0 declarations."""
    empty = {s.entity_name: s for s in surfaces if not s.fields}
    if not empty or "mapped_column" not in content:
        return
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        surface = empty.get(cls.name)
        if surface is None:
            continue
        fields, rels, details, table = _sa2_class_fields(cls)
        if fields:
            surface.fields = fields
            surface.relationships = rels
            surface.relationship_details = details
            if table:
                surface.persistence_refs = [table]


__all__ = ["_extract_sqlalchemy"]
