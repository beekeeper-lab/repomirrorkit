"""Database-design diff between an original and a rebuild (BEAN-078).

Compares the harvester's own ``db-design/schema.sql`` for the original harvest
and for a re-harvest of the rebuild: tables, columns (by name) and foreign
keys. Both DDL files are loaded into in-memory SQLite and inspected with
``PRAGMA`` so the comparison is dialect-independent. Returns ``None`` when the
original has no database design (the family is then N/A, never a free pass).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SchemaDiff:
    tables_expected: int
    tables_found: int
    columns_expected: int
    columns_found: int
    fks_expected: int
    fks_found: int
    missing_tables: list[str]
    missing_columns: list[str]

    @property
    def score(self) -> float:
        expected = self.tables_expected + self.columns_expected + self.fks_expected
        found = self.tables_found + self.columns_found + self.fks_found
        return found / expected if expected else 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "tables": {"expected": self.tables_expected, "found": self.tables_found},
            "columns": {"expected": self.columns_expected, "found": self.columns_found},
            "foreign_keys": {"expected": self.fks_expected, "found": self.fks_found},
            "missing_tables": self.missing_tables,
            "missing_columns": self.missing_columns[:30],
        }


def _describe(
    ddl: str,
) -> tuple[set[str], set[tuple[str, str]], set[tuple[str, str, str]]]:
    con = sqlite3.connect(":memory:")
    try:
        con.executescript(ddl)
        tables = {
            r[0].lower()
            for r in con.execute(
                "select name from sqlite_master where type='table' and name not like 'sqlite_%'"
            )
        }
        columns: set[tuple[str, str]] = set()
        fks: set[tuple[str, str, str]] = set()
        for t in tables:
            for row in con.execute(f'PRAGMA table_info("{t}")'):
                columns.add((t, str(row[1]).lower()))
            for row in con.execute(f'PRAGMA foreign_key_list("{t}")'):
                fks.add((t, str(row[3]).lower(), str(row[2]).lower()))
        return tables, columns, fks
    finally:
        con.close()


def diff_schemas(original_harvest: Path, rebuild_harvest: Path) -> SchemaDiff | None:
    """Diff ``db-design/schema.sql`` of two harvest directories."""
    original = original_harvest / "db-design" / "schema.sql"
    if not original.is_file():
        return None
    rebuilt = rebuild_harvest / "db-design" / "schema.sql"
    o_tables, o_cols, o_fks = _describe(original.read_text(encoding="utf-8"))
    if rebuilt.is_file():
        r_tables, r_cols, r_fks = _describe(rebuilt.read_text(encoding="utf-8"))
    else:
        r_tables, r_cols, r_fks = set(), set(), set()
    return SchemaDiff(
        tables_expected=len(o_tables),
        tables_found=len(o_tables & r_tables),
        columns_expected=len(o_cols),
        columns_found=len(o_cols & r_cols),
        fks_expected=len(o_fks),
        fks_found=len(o_fks & r_fks),
        missing_tables=sorted(o_tables - r_tables),
        missing_columns=sorted(f"{t}.{c}" for t, c in o_cols - r_cols),
    )
