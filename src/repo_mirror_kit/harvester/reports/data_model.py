"""Data-model relationships report (BEAN-055).

Extracts foreign-key / relationship edges from `ModelSurface` source
files (SQLAlchemy + Django patterns), populates each surface's
`relationship_details` list, and writes a top-level
``<output_dir>/data-model.md`` with:

  - One section per detected model listing fields and outgoing
    relationships
  - A Mermaid ``erDiagram`` block summarizing all detected edges
  - A relationships table (source, target, kind, FK column, source file)

The bean's full scope mentions Prisma and Entity Framework. Those
frameworks are recognised by the existing `analyze_models` (so they
appear as ModelSurface entries), but FK extraction here covers the two
most common ORMs in the harvester's target stacks. Adding Prisma/EF is
a clean follow-up — a new ``_extract_*`` function, register it, done.
"""

from __future__ import annotations

import re
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ModelRelationship,
    ModelSurface,
    SurfaceCollection,
)

# ---------------------------------------------------------------------------
# Per-framework extraction patterns
# ---------------------------------------------------------------------------

# Django: ForeignKey('Other'), ForeignKey(Other), with optional on_delete.
# Examples matched:
#   author = models.ForeignKey(User, on_delete=models.CASCADE)
#   author = models.ForeignKey('auth.User', on_delete=models.SET_NULL)
_DJANGO_FK_RE = re.compile(
    r"""(?P<col>\w+)\s*=\s*(?:models\.)?
        (?P<kind>ForeignKey|OneToOneField|ManyToManyField)\s*\(
        \s*['"]?(?P<target>[\w\.]+)['"]?
        (?P<rest>[^)]*)\)
    """,
    re.VERBOSE,
)

# SQLAlchemy ForeignKey column: e.g. ``Column(Integer, ForeignKey('users.id'))``.
_SQLA_FK_RE = re.compile(
    r"""(?P<col>\w+)\s*=\s*(?:Column|mapped_column)\s*\(
        [^)]*?ForeignKey\s*\(\s*['"](?P<target>[\w\.]+)['"][^)]*\)
    """,
    re.VERBOSE,
)

# SQLAlchemy relationship() call: e.g. ``posts = relationship("Post", back_populates="author")``.
_SQLA_REL_RE = re.compile(
    r"""(?P<col>\w+)\s*=\s*relationship\s*\(
        \s*['"](?P<target>[\w\.]+)['"]
        (?P<rest>[^)]*)\)
    """,
    re.VERBOSE,
)


_DJANGO_KIND_MAP: dict[str, str] = {
    "ForeignKey": "many_to_one",
    "OneToOneField": "one_to_one",
    "ManyToManyField": "many_to_many",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def write_data_model_report(
    surfaces: SurfaceCollection,
    output_dir: Path,
    workdir: Path | None = None,
) -> Path:
    """Extract relationships, write ``<output_dir>/data-model.md``, return its path.

    ``workdir`` is the cloned repository root used to resolve each
    ``ModelSurface``'s source file. When None, source-based extraction is
    skipped — only relationships already present on `relationship_details`
    are rendered. (This makes the report easy to test with synthetic
    surfaces.)
    """
    if workdir is not None:
        _populate_relationships_from_source(surfaces.models, workdir)
    text = _render(surfaces.models)
    path = output_dir / "data-model.md"
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Source-based relationship extraction
# ---------------------------------------------------------------------------


def _populate_relationships_from_source(
    models: list[ModelSurface],
    workdir: Path,
) -> None:
    """Walk each model's source file and append discovered relationships.

    Idempotent: relationships already present on a surface (with the same
    source/target/kind tuple) are not duplicated.
    """
    by_name: dict[str, ModelSurface] = {
        (m.entity_name or m.name): m for m in models if (m.entity_name or m.name)
    }
    file_cache: dict[Path, str] = {}

    for model in models:
        if not model.source_refs:
            continue
        ref = model.source_refs[0]
        full = workdir / ref.file_path
        if full not in file_cache:
            try:
                file_cache[full] = full.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                file_cache[full] = ""
        text = file_cache[full]
        if not text:
            continue

        source_name = model.entity_name or model.name
        for rel in _scan_relationships(text, source_name, ref.file_path, by_name):
            _append_unique(model, rel)


def _scan_relationships(
    source_text: str,
    source_name: str,
    source_file: str,
    by_name: dict[str, ModelSurface],
) -> list[ModelRelationship]:
    """Return all relationships discovered in *source_text*."""
    rels: list[ModelRelationship] = []

    for match in _DJANGO_FK_RE.finditer(source_text):
        kind = _DJANGO_KIND_MAP.get(match.group("kind"), "many_to_one")
        target = _normalize_model_name(match.group("target"))
        cascade = _extract_cascade(match.group("rest") or "")
        rels.append(
            ModelRelationship(
                source_model=source_name,
                target_model=target,
                kind=kind,
                fk_column=match.group("col"),
                cascade=cascade,
                source_file=source_file,
            )
        )

    for match in _SQLA_FK_RE.finditer(source_text):
        # ForeignKey('users.id') → target table 'users'. Try to look up a
        # model whose tablename matches; fall back to the literal target.
        raw_target = match.group("target").split(".")[0]
        target = _resolve_sqla_target(raw_target, by_name)
        rels.append(
            ModelRelationship(
                source_model=source_name,
                target_model=target,
                kind="many_to_one",
                fk_column=match.group("col"),
                cascade=None,
                source_file=source_file,
            )
        )

    for match in _SQLA_REL_RE.finditer(source_text):
        target = _normalize_model_name(match.group("target"))
        rest = match.group("rest") or ""
        kind = "one_to_many" if "uselist" not in rest or "uselist=True" in rest else "one_to_one"
        cascade = _extract_cascade(rest)
        rels.append(
            ModelRelationship(
                source_model=source_name,
                target_model=target,
                kind=kind,
                fk_column=None,
                cascade=cascade,
                source_file=source_file,
            )
        )

    return rels


def _normalize_model_name(target: str) -> str:
    """Strip Django app prefixes (``auth.User`` → ``User``)."""
    return target.split(".")[-1]


def _resolve_sqla_target(table_name: str, by_name: dict[str, ModelSurface]) -> str:
    """Best-effort: find a ModelSurface whose name matches the table_name in
    titlecase. Otherwise return the table_name as-is."""
    candidate = by_name.get(table_name.title())
    return candidate.entity_name if candidate else table_name


def _extract_cascade(rest: str) -> str | None:
    """Pull a cascade hint out of an attribute clause (Django on_delete=,
    SQLAlchemy cascade=)."""
    m = re.search(
        r"""(?:on_delete\s*=\s*(?:models\.)?(?P<dj>\w+)|cascade\s*=\s*['"](?P<sa>[^'"]+)['"])""",
        rest,
    )
    if not m:
        return None
    return m.group("dj") or m.group("sa")


def _append_unique(model: ModelSurface, rel: ModelRelationship) -> None:
    key = (rel.source_model, rel.target_model, rel.kind, rel.fk_column)
    for existing in model.relationship_details:
        if (
            existing.source_model,
            existing.target_model,
            existing.kind,
            existing.fk_column,
        ) == key:
            return
    model.relationship_details.append(rel)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render(models: list[ModelSurface]) -> str:
    parts: list[str] = []
    parts.append(_render_header(models))
    parts.append(_render_mermaid(models))
    parts.append(_render_models_section(models))
    parts.append(_render_relationships_table(models))
    return "\n".join(parts)


def _render_header(models: list[ModelSurface]) -> str:
    total_rels = sum(len(m.relationship_details) for m in models)
    return (
        "# Data Model — Relationships & ER Diagram\n"
        "\n"
        "Generated by RepoMirrorKit (BEAN-055). Lists every detected\n"
        "data-model surface with its fields and outgoing relationships,\n"
        "plus a Mermaid ER diagram for visual rendering.\n"
        "\n"
        f"**Models:** {len(models)} — **Relationships:** {total_rels}\n"
    )


def _render_mermaid(models: list[ModelSurface]) -> str:
    lines = ["## ER Diagram", ""]

    if not any(m.relationship_details for m in models):
        lines.append(
            "_(no relationships detected — Mermaid ER diagram skipped)_\n"
        )
        return "\n".join(lines) + "\n"

    lines.append("```mermaid")
    lines.append("erDiagram")

    # Entities — emit one entity block per model so Mermaid renders boxes
    # even for models with no fields.
    seen_entities: set[str] = set()
    for model in models:
        name = (model.entity_name or model.name).strip()
        if not name or name in seen_entities:
            continue
        seen_entities.add(name)
        clean = _mermaid_entity_name(name)
        lines.append(f"    {clean} {{")
        for fld in model.fields[:8]:  # cap to keep the diagram readable
            ftype = re.sub(r"[^A-Za-z0-9_]", "_", fld.field_type or "any")
            lines.append(f"        {ftype} {fld.name}")
        if not model.fields:
            lines.append("        any _placeholder")
        lines.append("    }")

    # Edges — Mermaid syntax: ``A ||--o{ B : "label"``.
    for model in models:
        src = _mermaid_entity_name(model.entity_name or model.name)
        for rel in model.relationship_details:
            tgt = _mermaid_entity_name(rel.target_model)
            connector = _mermaid_connector(rel.kind)
            label = rel.fk_column or rel.kind
            lines.append(f'    {src} {connector} {tgt} : "{label}"')

    lines.append("```")
    lines.append("")
    return "\n".join(lines) + "\n"


def _render_models_section(models: list[ModelSurface]) -> str:
    lines = ["## Models", ""]

    if not models:
        lines.append("_(no data-model surfaces detected)_\n")
        return "\n".join(lines) + "\n"

    for model in models:
        name = model.entity_name or model.name
        lines.append(f"### {name}")
        lines.append("")
        if model.source_refs:
            ref = model.source_refs[0]
            line_part = f":{ref.start_line}" if ref.start_line is not None else ""
            lines.append(f"_Source: `{ref.file_path}{line_part}`_")
            lines.append("")

        if model.fields:
            lines.append("**Fields**")
            lines.append("")
            lines.append("| Name | Type | Constraints |")
            lines.append("|------|------|-------------|")
            for fld in model.fields:
                cons = ", ".join(fld.constraints) if fld.constraints else "—"
                lines.append(f"| `{fld.name}` | `{fld.field_type or '—'}` | {cons} |")
            lines.append("")

        if model.relationship_details:
            lines.append("**Outgoing relationships**")
            lines.append("")
            lines.append("| Target | Kind | FK column | Cascade |")
            lines.append("|--------|------|-----------|---------|")
            for rel in model.relationship_details:
                lines.append(
                    f"| `{rel.target_model}` | {rel.kind} | "
                    f"{('`' + rel.fk_column + '`') if rel.fk_column else '—'} | "
                    f"{rel.cascade or '—'} |"
                )
            lines.append("")
        else:
            lines.append("_(no relationships detected for this model)_")
            lines.append("")

    return "\n".join(lines) + "\n"


def _render_relationships_table(models: list[ModelSurface]) -> str:
    lines = ["## All Relationships", ""]
    rels = [
        (model, rel)
        for model in models
        for rel in model.relationship_details
    ]
    if not rels:
        lines.append("_(no relationships detected across all models)_\n")
        return "\n".join(lines) + "\n"

    lines.append("| Source | Target | Kind | FK column | Cascade | Source file |")
    lines.append("|--------|--------|------|-----------|---------|-------------|")
    for _, rel in rels:
        src_file = f"`{rel.source_file}`" if rel.source_file else "—"
        fk = f"`{rel.fk_column}`" if rel.fk_column else "—"
        lines.append(
            f"| `{rel.source_model}` | `{rel.target_model}` | {rel.kind} | "
            f"{fk} | {rel.cascade or '—'} | {src_file} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _mermaid_entity_name(name: str) -> str:
    """Sanitize a model name for Mermaid syntax (alphanumeric + underscore only)."""
    return re.sub(r"[^A-Za-z0-9_]", "_", name) or "Entity"


def _mermaid_connector(kind: str) -> str:
    """Return Mermaid relationship connector for a relationship kind."""
    return {
        "one_to_one": "||--||",
        "one_to_many": "||--o{",
        "many_to_one": "}o--||",
        "many_to_many": "}o--o{",
    }.get(kind, "||--o{")
