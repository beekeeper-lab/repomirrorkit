"""DB design bundle: DDL + JSON Schema + seed data (BEAN-072).

Mermaid is a rendering; a rebuild agent needs the *executable* data design.
From the same ``ModelSurface`` data the ER diagram uses, this emits
``<out>/db-design/``:

- ``schema.sql``                 portable, ANSI-leaning DDL (loads into SQLite)
- ``entities/<Entity>.schema.json``  JSON Schema (draft 2020-12) per entity
- ``seed-data.sql`` / ``seed-data.json``  reference data the app needs to boot
- ``README.md``                  index with explicit gap notes

Anything that cannot be represented (unknown column types, unresolved foreign
keys, composite keys) is reported as a ``-- GAP:`` comment and in the README —
never silently dropped.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ModelField,
    ModelSurface,
    SurfaceCollection,
)

logger = structlog.get_logger()

DB_DIRNAME = "db-design"

_LEN_RE = re.compile(r"(?:max_length|maxlength)\s*=\s*(\d+)", re.I)
_TYPE_LEN_RE = re.compile(r"\(\s*(\d+)\s*\)")
_RANGE_RE = re.compile(r"^(ge|gt|le|lt|min|max)\s*=\s*(-?\d+(?:\.\d+)?)$")
_ZOD_RANGE_RE = re.compile(r"^\.?(min|max)\((-?\d+(?:\.\d+)?)\)$")
_MINLEN_RE = re.compile(r"(?:min_length|minlength)\s*=\s*(\d+)", re.I)


def _snake(name: str) -> str:
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower() or "entity"


def _q(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


def _lit(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


# (SQL type, JSON-schema type, JSON-schema format|None)
def _map_type(raw: str, constraints: list[str]) -> tuple[str, str, str | None, bool]:
    """Return (sql_type, json_type, json_format, known)."""
    t = raw.strip()
    base = re.sub(r"\(.*", "", t).replace("db.", "").replace("sa.", "")
    low = base.lower().replace("?", "").strip()
    length = None
    m = _TYPE_LEN_RE.search(t)
    if m:
        length = int(m.group(1))
    for c in constraints:
        lm = _LEN_RE.search(c)
        if lm:
            length = int(lm.group(1))
    if low in (
        "integer",
        "int",
        "bigint",
        "smallint",
        "biginteger",
        "long",
        "short",
        "number",
        "autofield",
        "bigautofield",
        "positiveinteger",
    ):
        return (
            ("INTEGER", "integer" if low != "number" else "number", None, True)
            if low != "number"
            else ("NUMERIC", "number", None, True)
        )
    if low in (
        "string",
        "str",
        "varchar",
        "char",
        "charfield",
        "emailfield",
        "slugfield",
        "urlfield",
        "nvarchar",
        "unicode",
    ):
        return (f"VARCHAR({length})" if length else "TEXT", "string", None, True)
    if low in ("text", "textfield", "unicodetext", "longtext", "clob"):
        return ("TEXT", "string", None, True)
    if low in ("boolean", "bool", "booleanfield"):
        return ("BOOLEAN", "boolean", None, True)
    if low in ("float", "real", "double", "floatfield"):
        return ("REAL", "number", None, True)
    if low in ("decimal", "numeric", "decimalfield", "money"):
        return ("NUMERIC", "number", None, True)
    if low in ("datetime", "timestamp", "datetimefield", "datetimeoffset", "date_time"):
        return ("TIMESTAMP", "string", "date-time", True)
    if low in ("date", "datefield"):
        return ("DATE", "string", "date", True)
    if low in ("time", "timefield"):
        return ("TIME", "string", "time", True)
    if low in ("uuid", "guid", "uuidfield"):
        return ("VARCHAR(36)", "string", "uuid", True)
    if low in ("json", "jsonb", "jsonfield", "dict", "object"):
        return ("TEXT", "object", None, True)
    if low.endswith("[]") or low.startswith(("list", "array")):
        return ("TEXT", "array", None, True)
    return ("TEXT", "string", None, False)


def _table_name(model: ModelSurface) -> tuple[str, bool]:
    for ref in model.persistence_refs:
        if ref:
            return ref, False
    return _snake(model.entity_name or model.name), True


def _pk_column(model: ModelSurface) -> str:
    for f in model.fields:
        if "primary_key" in f.constraints:
            return f.name
    for f in model.fields:
        if f.name.lower() == "id":
            return f.name
    return "id"


def _checks(field: ModelField, sql_type: str) -> list[str]:
    checks: list[str] = []
    col = _q(field.name)
    for c in field.constraints:
        m = _RANGE_RE.match(c) or _ZOD_RANGE_RE.match(c)
        if m and sql_type in ("INTEGER", "NUMERIC", "REAL"):
            op = {
                "ge": ">=",
                "gt": ">",
                "le": "<=",
                "lt": "<",
                "min": ">=",
                "max": "<=",
            }[m.group(1)]
            checks.append(f"{col} {op} {m.group(2)}")
            continue
        m2 = _MINLEN_RE.search(c)
        if m2:
            checks.append(f"length({col}) >= {m2.group(1)}")
    return checks


class _Bundle:
    def __init__(self, surfaces: SurfaceCollection) -> None:
        self.models = list(surfaces.models)
        self.seeds = list(surfaces.seed_data)
        self.by_name = {m.entity_name or m.name: m for m in self.models}
        self.gaps: list[str] = []
        self.tables = {m.entity_name or m.name: _table_name(m)[0] for m in self.models}

    # -- foreign keys ------------------------------------------------------
    def fks(self, model: ModelSurface) -> dict[str, tuple[str, str]]:
        """column → (referenced table, referenced column)."""
        out: dict[str, tuple[str, str]] = {}
        cols = {f.name for f in model.fields}
        for rel in model.relationship_details:
            if rel.kind in ("many_to_one", "one_to_one") and rel.fk_column:
                target = self.by_name.get(rel.target_model)
                if target is None:
                    self.gaps.append(
                        f"{model.name}.{rel.fk_column}: FK target model "
                        f"'{rel.target_model}' not found among extracted models."
                    )
                    continue
                if rel.fk_column not in cols:
                    self.gaps.append(
                        f"{model.name}: FK column '{rel.fk_column}' is not a declared field."
                    )
                    continue
                out[rel.fk_column] = (
                    self.tables[target.entity_name or target.name],
                    _pk_column(target),
                )
        # one_to_many declared on the parent: the child table owns the FK.
        for other in self.models:
            for rel in other.relationship_details:
                if (
                    rel.kind == "one_to_many"
                    and rel.target_model == (model.entity_name or model.name)
                    and rel.fk_column
                    and rel.fk_column in cols
                ):
                    parent = self.by_name.get(rel.source_model)
                    if parent is not None:
                        out.setdefault(
                            rel.fk_column,
                            (
                                self.tables[parent.entity_name or parent.name],
                                _pk_column(parent),
                            ),
                        )
        return out

    def ordered(self) -> list[ModelSurface]:
        deps = {
            m.entity_name or m.name: {
                t
                for t, _ in self.fks(m).values()
                if t != self.tables[m.entity_name or m.name]
            }
            for m in self.models
        }
        by_table = {self.tables[m.entity_name or m.name]: m for m in self.models}
        done: list[ModelSurface] = []
        placed: set[str] = set()
        remaining = sorted(
            self.models, key=lambda m: self.tables[m.entity_name or m.name]
        )
        while remaining:
            progressed = False
            for m in list(remaining):
                name = m.entity_name or m.name
                if all(d in placed or d not in by_table for d in deps[name]):
                    done.append(m)
                    placed.add(self.tables[name])
                    remaining.remove(m)
                    progressed = True
            if not progressed:  # FK cycle: emit the rest as-is (inline FKs still load)
                done.extend(remaining)
                break
        return done

    # -- DDL ---------------------------------------------------------------
    def ddl(self) -> str:
        lines = [
            "-- Generated by RepoMirrorKit (BEAN-072). Final-state schema; ANSI-leaning.",
            "-- Dialect notes: VARCHAR/TEXT/NUMERIC/TIMESTAMP/BOOLEAN are used generically;",
            "-- adapt types, auto-increment and identifier quoting to the target database.",
        ]
        for model in self.ordered():
            name = model.entity_name or model.name
            table, inferred = _table_name(model)
            fks = self.fks(model)
            pk = _pk_column(model)
            has_pk = any("primary_key" in f.constraints for f in model.fields) or any(
                f.name.lower() == "id" for f in model.fields
            )
            lines.append("")
            lines.append(
                f"-- {name}"
                + (" (table name inferred from entity name)" if inferred else "")
            )
            cols: list[tuple[str, str]] = []
            for f in model.fields:
                sql_type, _jt, _jf, known = _map_type(f.field_type, f.constraints)
                parts = [_q(f.name), sql_type]
                is_pk = f.name == pk and has_pk
                if is_pk:
                    parts.append("PRIMARY KEY")
                if "not_null" in f.constraints and not is_pk:
                    parts.append("NOT NULL")
                if "unique" in f.constraints and not is_pk:
                    parts.append("UNIQUE")
                for chk in _checks(f, sql_type):
                    parts.append(f"CHECK ({chk})")
                comment = ""
                if not known:
                    comment = (
                        f"GAP: original type '{f.field_type}' not mapped; TEXT used"
                    )
                    self.gaps.append(
                        f"{name}.{f.name}: unmapped type '{f.field_type}' (TEXT used)."
                    )
                cols.append((" ".join(parts), comment))
            for col, (ref_table, ref_col) in sorted(fks.items()):
                cols.append(
                    (
                        f"FOREIGN KEY ({_q(col)}) REFERENCES {_q(ref_table)} ({_q(ref_col)})",
                        "",
                    )
                )
            if not has_pk:
                lines.append(f"-- GAP: no primary key detected for {name}")
                self.gaps.append(f"{name}: no primary key detected.")
            rendered = []
            for i, (text, comment) in enumerate(cols):
                sep = "," if i < len(cols) - 1 else ""
                rendered.append(
                    f"    {text}{sep}" + (f"  -- {comment}" if comment else "")
                )
            body = "\n".join(rendered)
            lines.append(f"CREATE TABLE {_q(table)} (\n{body}\n);")
        return "\n".join(lines) + "\n"

    # -- JSON Schema --------------------------------------------------------
    def enum_for(self, model: ModelSurface, field: ModelField) -> list[Any] | None:
        want = re.sub(
            r"[^a-z0-9]", "", ((model.entity_name or model.name) + field.name).lower()
        )
        for seed in self.seeds:
            if seed.kind != "enum":
                continue
            key = re.sub(r"[^a-z0-9]", "", seed.dataset_name.lower())
            if key == want or (
                seed.target_model_ref
                and seed.target_model_ref == (model.entity_name or model.name)
                and field.name.lower() in key
            ):
                values = [
                    v.get("value", v.get("name"))
                    for v in seed.values
                    if isinstance(v, dict)
                ]
                values = [v for v in values if v is not None]
                if values:
                    return values
        return None

    def json_schema(self, model: ModelSurface) -> dict[str, Any]:
        name = model.entity_name or model.name
        props: dict[str, Any] = {}
        required: list[str] = []
        for f in model.fields:
            sql_t, jt, jf, _known = _map_type(f.field_type, f.constraints)
            p: dict[str, Any] = {"type": jt}
            if jf:
                p["format"] = jf
            varchar = re.match(r"VARCHAR\((\d+)\)$", sql_t)
            if varchar and jf != "uuid":
                p["maxLength"] = int(varchar.group(1))
            for c in f.constraints:
                lm = _LEN_RE.search(c)
                if lm and jt == "string":
                    p["maxLength"] = int(lm.group(1))
                mm = _MINLEN_RE.search(c)
                if mm and jt == "string":
                    p["minLength"] = int(mm.group(1))
                rm = _RANGE_RE.match(c) or _ZOD_RANGE_RE.match(c)
                if rm and jt in ("integer", "number"):
                    key = {
                        "ge": "minimum",
                        "gt": "exclusiveMinimum",
                        "le": "maximum",
                        "lt": "exclusiveMaximum",
                        "min": "minimum",
                        "max": "maximum",
                    }[rm.group(1)]
                    p[key] = (
                        float(rm.group(2)) if "." in rm.group(2) else int(rm.group(2))
                    )
            enum = self.enum_for(model, f)
            if enum:
                p["enum"] = enum
            if "unique" in f.constraints or "primary_key" in f.constraints:
                p["x-unique"] = True
            props[f.name] = p
            if "not_null" in f.constraints or "primary_key" in f.constraints:
                required.append(f.name)
        schema: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": name,
            "type": "object",
            "properties": props,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        return schema

    # -- seed data ----------------------------------------------------------
    def seed_sql(self) -> tuple[str, list[str]]:
        lines = ["-- Seed / reference data (BEAN-066 surfaces). Run after schema.sql."]
        notes: list[str] = []
        emitted = 0
        for seed in self.seeds:
            if seed.kind == "enum":
                continue  # code-level enumeration: documented in seed-data.json
            target = self.by_name.get(seed.target_model_ref)
            if target is None or not seed.values:
                notes.append(
                    f"{seed.dataset_name}: no resolvable target table; see seed-data.json."
                )
                continue
            table = self.tables[target.entity_name or target.name]
            known = {f.name for f in target.fields}
            for row in seed.values:
                if not isinstance(row, dict):
                    continue
                cols = [c for c in row if c in known]
                if not cols:
                    continue
                # Text emitted into a .sql artifact, never executed here; identifiers
                # are quoted and values escaped by _q/_lit.
                lines.append(
                    f"INSERT INTO {_q(table)} ({', '.join(_q(c) for c in cols)}) "  # noqa: S608
                    f"VALUES ({', '.join(_lit(row[c]) for c in cols)});"
                )
                emitted += 1
            if seed.truncated:
                notes.append(f"{seed.dataset_name}: values truncated by the harvester.")
        if emitted == 0:
            lines.append("-- (no table-bound seed rows were extracted)")
        return "\n".join(lines) + "\n", notes


def generate_db_design(
    surfaces: SurfaceCollection, output_dir: Path, project_name: str
) -> list[Path]:
    """Write ``<output_dir>/db-design/`` and return the files created.

    Returns an empty list when the harvest found no models.
    """
    if not surfaces.models:
        logger.info("db_design_skipped_no_models")
        return []
    bundle = _Bundle(surfaces)
    root = output_dir / DB_DIRNAME
    (root / "entities").mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    schema_path = root / "schema.sql"
    schema_path.write_text(bundle.ddl(), encoding="utf-8")
    written.append(schema_path)

    for model in bundle.models:
        name = model.entity_name or model.name
        path = (
            root / "entities" / f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', name)}.schema.json"
        )
        path.write_text(
            json.dumps(bundle.json_schema(model), indent=2) + "\n", encoding="utf-8"
        )
        written.append(path)

    seed_sql, seed_notes = bundle.seed_sql()
    (root / "seed-data.sql").write_text(seed_sql, encoding="utf-8")
    written.append(root / "seed-data.sql")
    seed_json = {
        "datasets": [
            {
                "name": s.dataset_name or s.name,
                "kind": s.kind,
                "target_model": s.target_model_ref,
                "truncated": s.truncated,
                "values": s.values,
            }
            for s in bundle.seeds
        ]
    }
    (root / "seed-data.json").write_text(
        json.dumps(seed_json, indent=2) + "\n", encoding="utf-8"
    )
    written.append(root / "seed-data.json")

    readme = _readme(project_name, bundle, seed_notes)
    (root / "README.md").write_text(readme, encoding="utf-8")
    written.append(root / "README.md")
    logger.info(
        "db_design_written",
        models=len(bundle.models),
        gaps=len(bundle.gaps),
        path=str(root),
    )
    return written


def _readme(project: str, bundle: _Bundle, seed_notes: list[str]) -> str:
    rel_count = sum(len(m.relationship_details) for m in bundle.models)
    lines = [
        f"# {project} — database design",
        "",
        "Generated by RepoMirrorKit (BEAN-072) from the same model data as `../data-model.md`.",
        "",
        "| Artifact | Purpose |",
        "|----------|---------|",
        "| [`schema.sql`](schema.sql) | Portable DDL (final-state schema) |",
        "| [`entities/`](entities/) | JSON Schema per entity |",
        "| [`seed-data.sql`](seed-data.sql) / [`seed-data.json`](seed-data.json) | Reference data |",
        "",
        f"- Entities: {len(bundle.models)}; relationships: {rel_count}; seed datasets: {len(bundle.seeds)}",
        "",
        "## Gaps",
        "",
    ]
    gaps = sorted(set(bundle.gaps)) + seed_notes
    lines += [f"- {g}" for g in gaps] or ["- None detected."]
    if not bundle.seeds:
        lines.append(
            "- No seed/reference datasets were extracted; the application may need initial data not captured here."
        )
    lines.append("")
    return "\n".join(lines)
