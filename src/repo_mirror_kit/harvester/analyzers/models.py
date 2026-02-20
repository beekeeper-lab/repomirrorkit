"""Model & Entity Analyzer.

Extracts data models and entities from repositories by parsing source files
for ORM definitions, schema files, and SQL migration statements.  Produces
``ModelSurface`` objects with entity names, fields, relationships, and
persistence references.

Supported data technologies:
- Prisma (``schema.prisma``)
- SQLAlchemy (Python model classes)
- Entity Framework (C# entity classes)
- TypeORM / Sequelize (TypeScript/JavaScript decorators)
- Plain SQL (``CREATE TABLE`` statements)
- Alembic (``op.create_table()`` / ``op.add_column()``)
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ModelField,
    ModelSurface,
    SourceRef,
)
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

_MAX_FILE_SIZE = 1_000_000  # 1 MB — skip huge generated files
_MAX_FILES_PER_TECH = 200  # cap files scanned per technology

# ---------------------------------------------------------------------------
# File-matching patterns
# ---------------------------------------------------------------------------

_PRISMA_SCHEMA_RE = re.compile(r"(?:^|/)schema\.prisma$")
_PYTHON_FILE_RE = re.compile(r"\.py$")
_PYTHON_MODEL_FILE_RE = re.compile(r"(?:^|/)models?\.py$")
_CSHARP_FILE_RE = re.compile(r"\.cs$")
_TS_JS_FILE_RE = re.compile(r"\.[jt]sx?$")
_SQL_FILE_RE = re.compile(r"\.sql$")
_ALEMBIC_VERSIONS_RE = re.compile(r"(?:^|/)alembic/versions/.*\.py$")

# ---------------------------------------------------------------------------
# Content-parsing patterns
# ---------------------------------------------------------------------------

# Prisma: model blocks
_PRISMA_MODEL_RE = re.compile(r"^model\s+(\w+)\s*\{", re.MULTILINE)
_PRISMA_FIELD_RE = re.compile(
    r"^\s+(\w+)[ \t]+([\w\[\]?]+)(?:[ \t]+(.*))?$", re.MULTILINE
)
_PRISMA_RELATION_RE = re.compile(r"@relation\b")
_PRISMA_ID_RE = re.compile(r"@id\b")
_PRISMA_UNIQUE_RE = re.compile(r"@unique\b")
_PRISMA_DEFAULT_RE = re.compile(r"@default\b")
_PRISMA_MAP_RE = re.compile(r'@@map\("([^"]+)"\)')

# SQLAlchemy
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

# Entity Framework (C#)
_EF_CLASS_RE = re.compile(r"public\s+class\s+(\w+)\b")
_EF_DBSET_RE = re.compile(r"DbSet<(\w+)>")
_EF_PROPERTY_RE = re.compile(r"public\s+([\w<>?\[\]]+)\s+(\w+)\s*\{\s*get;\s*set;\s*\}")
_EF_KEY_RE = re.compile(r"\[Key\]")
_EF_REQUIRED_RE = re.compile(r"\[Required\]")
_EF_TABLE_RE = re.compile(r'\[Table\("(\w+)"\)\]')
_EF_FK_PROPERTY_RE = re.compile(r"(\w+)Id$")

# TypeORM / Sequelize decorators
_TYPEORM_ENTITY_RE = re.compile(r"@Entity\s*\(")
_TYPEORM_COLUMN_RE = re.compile(
    r"@(Column|PrimaryGeneratedColumn|PrimaryColumn|CreateDateColumn"
    r"|UpdateDateColumn|DeleteDateColumn)\s*\([^)]*\)\s*\n\s*(\w+)\s*[!?]?\s*:\s*([\w\[\]|<> ]+)"
)
_TYPEORM_RELATION_RE = re.compile(
    r"@(?:ManyToOne|OneToMany|OneToOne|ManyToMany)\s*\([^)]*(?:\([^)]*\)[^)]*)*\)\s*\n\s*(\w+)\s*[!?]?\s*:\s*([\w\[\]|<> ]+)"
)
_TYPEORM_CLASS_RE = re.compile(r"class\s+(\w+)\s*(?:extends\s+\w+)?\s*\{")

# Plain SQL
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

# Alembic
_ALEMBIC_CREATE_TABLE_RE = re.compile(r"op\.create_table\s*\(\s*['\"](\w+)['\"]")
_ALEMBIC_COLUMN_RE = re.compile(
    r"sa\.Column\s*\(\s*['\"](\w+)['\"]\s*,\s*sa\.(\w+(?:\([^)]*\))?)"
)
_ALEMBIC_ADD_COLUMN_RE = re.compile(
    r"op\.add_column\s*\(\s*['\"](\w+)['\"]\s*,\s*sa\.Column\s*\(\s*['\"](\w+)['\"]\s*,\s*sa\.(\w+(?:\([^)]*\))?)"
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_models(
    repo_root: Path,
    inventory: InventoryResult,
    profile: StackProfile,
) -> list[ModelSurface]:
    """Extract model/entity surfaces from detected data technologies.

    Only runs extraction strategies for technologies present in the
    ``StackProfile``.  Each strategy reads relevant source files,
    parses them for model definitions, and produces ``ModelSurface``
    objects.

    Args:
        repo_root: Absolute path to the repository working directory.
        inventory: File inventory from the repository scan.
        profile: Detection profile indicating which data stacks are present.

    Returns:
        A list of ``ModelSurface`` objects extracted from the repository.
    """
    detected = set(profile.stacks.keys())
    file_paths = [f.path for f in inventory.files]
    surfaces: list[ModelSurface] = []

    strategies: list[tuple[set[str], _Strategy]] = [
        ({"prisma"}, _extract_prisma),
        ({"sqlalchemy"}, _extract_sqlalchemy),
        ({"entity-framework"}, _extract_entity_framework),
        ({"sql-migrations"}, _extract_typeorm),
        ({"sql-migrations", "flyway", "liquibase"}, _extract_sql),
        ({"alembic"}, _extract_alembic),
    ]

    for trigger_stacks, strategy in strategies:
        if detected & trigger_stacks:
            tech_name = strategy.__name__.replace("_extract_", "")
            logger.info("model_analysis_starting", technology=tech_name)
            try:
                results = strategy(repo_root, file_paths)
                surfaces.extend(results)
                logger.info(
                    "model_analysis_complete",
                    technology=tech_name,
                    models_found=len(results),
                )
            except Exception:
                logger.exception("model_analysis_failed", technology=tech_name)

    # Deduplicate by entity name or persistence ref (keep first occurrence)
    seen_names: set[str] = set()
    seen_tables: set[str] = set()
    unique: list[ModelSurface] = []
    for surface in surfaces:
        name_key = surface.entity_name.lower()
        table_keys = frozenset(r.lower() for r in surface.persistence_refs)
        if name_key in seen_names or (table_keys & seen_tables):
            continue
        seen_names.add(name_key)
        seen_tables.update(table_keys)
        unique.append(surface)

    logger.info(
        "model_analysis_summary",
        total_models=len(unique),
        technologies=list(detected),
    )
    return unique


# ---------------------------------------------------------------------------
# Type alias for strategy callables
# ---------------------------------------------------------------------------

_Strategy = Callable[[Path, list[str]], list[ModelSurface]]


# ---------------------------------------------------------------------------
# File reading helper
# ---------------------------------------------------------------------------


def _read_file(repo_root: Path, rel_path: str) -> str | None:
    """Read a file's text content, returning None on failure.

    Skips files larger than ``_MAX_FILE_SIZE``.

    Args:
        repo_root: Repository root directory.
        rel_path: Repository-relative file path.

    Returns:
        File content as a string, or None if unreadable.
    """
    full_path = repo_root / rel_path
    try:
        if full_path.stat().st_size > _MAX_FILE_SIZE:
            return None
        return full_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Prisma extraction
# ---------------------------------------------------------------------------


def _extract_prisma(repo_root: Path, file_paths: list[str]) -> list[ModelSurface]:
    """Extract models from Prisma schema files.

    Args:
        repo_root: Repository root directory.
        file_paths: All file paths in the inventory.

    Returns:
        ModelSurface objects for each Prisma model found.
    """
    surfaces: list[ModelSurface] = []
    schema_files = [p for p in file_paths if _PRISMA_SCHEMA_RE.search(p)][
        :_MAX_FILES_PER_TECH
    ]

    for rel_path in schema_files:
        content = _read_file(repo_root, rel_path)
        if content is None:
            continue

        # Split into model blocks
        blocks = _split_prisma_blocks(content)
        for model_name, block_text, start_line in blocks:
            fields: list[ModelField] = []
            relationships: list[str] = []
            table_name = model_name

            # Check for @@map to get actual table name
            map_match = _PRISMA_MAP_RE.search(block_text)
            if map_match:
                table_name = map_match.group(1)

            for field_match in _PRISMA_FIELD_RE.finditer(block_text):
                fname = field_match.group(1)
                ftype = field_match.group(2)
                rest = field_match.group(3) or ""

                # Skip Prisma directives that aren't fields
                if fname in ("@@map", "@@id", "@@unique", "@@index"):
                    continue

                constraints: list[str] = []
                if _PRISMA_ID_RE.search(rest):
                    constraints.append("primary_key")
                if _PRISMA_UNIQUE_RE.search(rest):
                    constraints.append("unique")
                if "?" not in ftype:
                    constraints.append("not_null")
                if _PRISMA_DEFAULT_RE.search(rest):
                    constraints.append("has_default")

                # Detect relation fields: explicit @relation or implicit
                # array/model references (type starts with uppercase + [])
                is_relation = _PRISMA_RELATION_RE.search(rest) or (
                    ftype[0].isupper() and "[]" in ftype
                )
                if is_relation:
                    relationships.append(f"{fname} -> {ftype.rstrip('[]?')}")
                else:
                    fields.append(
                        ModelField(
                            name=fname,
                            field_type=ftype.rstrip("?"),
                            constraints=constraints,
                        )
                    )

            surfaces.append(
                ModelSurface(
                    name=model_name,
                    entity_name=model_name,
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


def _split_prisma_blocks(
    content: str,
) -> list[tuple[str, str, int]]:
    """Split Prisma schema content into model blocks.

    Args:
        content: Full text of a ``schema.prisma`` file.

    Returns:
        List of (model_name, block_text, start_line) tuples.
    """
    blocks: list[tuple[str, str, int]] = []
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        match = _PRISMA_MODEL_RE.match(lines[i])
        if match:
            model_name = match.group(1)
            start_line = i + 1  # 1-indexed
            brace_depth = 1
            block_lines = [lines[i]]
            j = i + 1
            while j < len(lines) and brace_depth > 0:
                block_lines.append(lines[j])
                brace_depth += lines[j].count("{") - lines[j].count("}")
                j += 1
            blocks.append((model_name, "\n".join(block_lines), start_line))
            i = j
        else:
            i += 1
    return blocks


# ---------------------------------------------------------------------------
# SQLAlchemy extraction
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Entity Framework extraction
# ---------------------------------------------------------------------------


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


def _extract_braced_block(content: str, open_brace_pos: int) -> str:
    """Extract text inside a brace-delimited block.

    Args:
        content: Full file content.
        open_brace_pos: Index of the opening ``{``.

    Returns:
        The text between the matching braces (exclusive).
    """
    depth = 1
    i = open_brace_pos + 1
    while i < len(content) and depth > 0:
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
        i += 1
    return content[open_brace_pos + 1 : i - 1]


# ---------------------------------------------------------------------------
# TypeORM / Sequelize extraction
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Plain SQL extraction
# ---------------------------------------------------------------------------


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


def _table_to_entity_name(table_name: str) -> str:
    """Convert a snake_case table name to PascalCase entity name.

    Args:
        table_name: SQL table name (e.g. ``user_accounts``).

    Returns:
        PascalCase name (e.g. ``UserAccounts``).
    """
    return "".join(part.capitalize() for part in table_name.split("_"))


# ---------------------------------------------------------------------------
# Alembic extraction
# ---------------------------------------------------------------------------


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


@dataclass
class _AlembicTable:
    """Internal accumulator for Alembic table data."""

    name: str
    fields: list[ModelField]
    source_file: str
    start_line: int
