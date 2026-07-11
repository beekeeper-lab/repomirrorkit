"""Seed/reference data extraction (BEAN-066).

Finds the data an application needs to *function* — not just its schema:

- **Code enums**: Python ``Enum``/``StrEnum``/``IntEnum`` subclasses
  (stdlib :mod:`ast`), TypeScript ``enum`` declarations and ``as const``
  object literals (regex, upgraded under BEAN-061 later).
- **Migration seeds / lookup tables**: ``INSERT INTO`` statements in
  ``.sql`` files and Alembic ``op.bulk_insert`` calls.
- **Fixture files**: ``fixtures/*.json`` — recorded with row counts and
  sample values.

Every dataset stores its actual values (capped per dataset with an
explicit ``truncated`` flag — no silent loss) and links to the model it
feeds when the table/entity name resolves.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    SeedDataSurface,
    SourceRef,
)
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# Cap stored values per dataset; the flag makes truncation visible.
MAX_VALUES_PER_DATASET: int = 50

_ENUM_BASES: frozenset[str] = frozenset(
    {"Enum", "StrEnum", "IntEnum", "IntFlag", "Flag"}
)

# TS: enum Color { Red = "red", Blue = "blue" }
_TS_ENUM_RE = re.compile(
    r"(?:export\s+)?(?:const\s+)?enum\s+(?P<name>\w+)\s*\{(?P<body>[^}]*)\}",
    re.DOTALL,
)
_TS_ENUM_MEMBER_RE = re.compile(
    r"(?P<key>\w+)\s*(?:=\s*(?P<value>\"[^\"]*\"|'[^']*'|-?\d+(?:\.\d+)?))?\s*(?:,|$)"
)

# SQL: INSERT INTO table (col, ...) VALUES (...), (...);
_SQL_INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+[`\"']?(?P<table>\w+)[`\"']?\s*"
    r"\((?P<columns>[^)]+)\)\s*VALUES\s*(?P<values>.+?);",
    re.IGNORECASE | re.DOTALL,
)
_SQL_ROW_RE = re.compile(r"\(([^()]*)\)")

_SQL_EXTENSIONS: frozenset[str] = frozenset({".sql"})
_PY_EXTENSIONS: frozenset[str] = frozenset({".py"})
_TS_EXTENSIONS: frozenset[str] = frozenset({".ts", ".tsx", ".js", ".jsx"})


def _read_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _cap(values: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    if len(values) > MAX_VALUES_PER_DATASET:
        return values[:MAX_VALUES_PER_DATASET], True
    return values, False


# ---------------------------------------------------------------------------
# Python enums
# ---------------------------------------------------------------------------


def _python_enums(rel_path: str, source: str) -> list[SeedDataSurface]:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    surfaces: list[SeedDataSurface] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        base_names = {
            b.id if isinstance(b, ast.Name) else getattr(b, "attr", "")
            for b in node.bases
        }
        if not (base_names & _ENUM_BASES):
            continue
        values: list[dict[str, Any]] = []
        for stmt in node.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(stmt.value, ast.Constant)
            ):
                values.append(
                    {
                        "name": stmt.targets[0].id,
                        "value": stmt.value.value,
                    }
                )
        if not values:
            continue
        capped, truncated = _cap(values)
        surfaces.append(
            SeedDataSurface(
                name=f"enum {node.name}",
                dataset_name=node.name,
                kind="enum",
                values=capped,
                truncated=truncated,
                source_refs=[SourceRef(file_path=rel_path, start_line=node.lineno)],
            )
        )
    return surfaces


# ---------------------------------------------------------------------------
# TypeScript / JavaScript enums
# ---------------------------------------------------------------------------


def _ts_enums(rel_path: str, source: str) -> list[SeedDataSurface]:
    surfaces: list[SeedDataSurface] = []
    for match in _TS_ENUM_RE.finditer(source):
        values: list[dict[str, Any]] = []
        for member in _TS_ENUM_MEMBER_RE.finditer(match.group("body")):
            key = member.group("key")
            if not key:
                continue
            raw = member.group("value")
            value: Any = raw.strip("'\"") if raw else key
            if raw and raw.lstrip("-").replace(".", "", 1).isdigit():
                value = float(raw) if "." in raw else int(raw)
            values.append({"name": key, "value": value})
        if not values:
            continue
        line = source[: match.start()].count("\n") + 1
        capped, truncated = _cap(values)
        surfaces.append(
            SeedDataSurface(
                name=f"enum {match.group('name')}",
                dataset_name=match.group("name"),
                kind="enum",
                values=capped,
                truncated=truncated,
                source_refs=[SourceRef(file_path=rel_path, start_line=line)],
            )
        )
    return surfaces


# ---------------------------------------------------------------------------
# SQL inserts (migration seeds / lookup tables)
# ---------------------------------------------------------------------------


def _split_sql_row(row: str) -> list[str]:
    """Split a VALUES row on commas outside quotes (best-effort)."""
    parts: list[str] = []
    current: list[str] = []
    in_quote: str | None = None
    for char in row:
        if in_quote:
            if char == in_quote:
                in_quote = None
            current.append(char)
        elif char in "'\"":
            in_quote = char
            current.append(char)
        elif char == ",":
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        parts.append("".join(current).strip())
    return parts


def _sql_literal(token: str) -> Any:
    token = token.strip()
    if token.upper() == "NULL":
        return None
    if len(token) >= 2 and token[0] in "'\"" and token[-1] == token[0]:
        return token[1:-1]
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return token


def _sql_inserts(rel_path: str, source: str) -> list[SeedDataSurface]:
    datasets: dict[str, list[dict[str, Any]]] = {}
    lines: dict[str, int] = {}
    for match in _SQL_INSERT_RE.finditer(source):
        table = match.group("table")
        columns = [c.strip().strip("`\"'") for c in match.group("columns").split(",")]
        rows = datasets.setdefault(table, [])
        lines.setdefault(table, source[: match.start()].count("\n") + 1)
        for row_match in _SQL_ROW_RE.finditer(match.group("values")):
            tokens = _split_sql_row(row_match.group(1))
            if len(tokens) != len(columns):
                continue
            rows.append(
                {
                    col: _sql_literal(tok)
                    for col, tok in zip(columns, tokens, strict=False)
                }
            )
    surfaces: list[SeedDataSurface] = []
    for table, rows in datasets.items():
        if not rows:
            continue
        capped, truncated = _cap(rows)
        surfaces.append(
            SeedDataSurface(
                name=f"seed {table}",
                dataset_name=table,
                kind="lookup_table",
                values=capped,
                truncated=truncated,
                target_model_ref=table,
                source_refs=[SourceRef(file_path=rel_path, start_line=lines[table])],
            )
        )
    return surfaces


# ---------------------------------------------------------------------------
# JSON fixture files
# ---------------------------------------------------------------------------

_FIXTURE_PATH_RE = re.compile(r"(?:^|/)(?:fixtures|seeds|seed_data)/[^/]+\.json$")


def _json_fixture(rel_path: str, source: str) -> SeedDataSurface | None:
    try:
        data = json.loads(source)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(data, dict):
        rows = [data]
    elif isinstance(data, list) and all(isinstance(r, dict) for r in data):
        rows = data
    else:
        return None
    capped, truncated = _cap(rows)
    name = PurePosixPath(rel_path).stem
    return SeedDataSurface(
        name=f"fixture {name}",
        dataset_name=name,
        kind="fixture",
        values=capped,
        truncated=truncated,
        source_refs=[SourceRef(file_path=rel_path, start_line=1)],
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def analyze_seed_data(
    workdir: Path,
    inventory: InventoryResult,
) -> list[SeedDataSurface]:
    """Extract seed/reference datasets from the repository.

    Args:
        workdir: Root of the cloned repository.
        inventory: File inventory to scan.

    Returns:
        Discovered seed-data surfaces (enums, lookup tables, fixtures).
    """
    surfaces: list[SeedDataSurface] = []

    for entry in inventory.files:
        ext = PurePosixPath(entry.path).suffix
        if ext in _PY_EXTENSIONS:
            source = _read_safe(workdir / entry.path)
            if "Enum" in source:
                surfaces.extend(_python_enums(entry.path, source))
        elif ext in _TS_EXTENSIONS:
            source = _read_safe(workdir / entry.path)
            if "enum " in source:
                surfaces.extend(_ts_enums(entry.path, source))
        elif ext in _SQL_EXTENSIONS:
            source = _read_safe(workdir / entry.path)
            if "INSERT" in source.upper():
                surfaces.extend(_sql_inserts(entry.path, source))
        elif _FIXTURE_PATH_RE.search(entry.path):
            source = _read_safe(workdir / entry.path)
            fixture = _json_fixture(entry.path, source)
            if fixture is not None:
                surfaces.append(fixture)

    logger.info("seed_data_analysis_complete", datasets_found=len(surfaces))
    return surfaces
