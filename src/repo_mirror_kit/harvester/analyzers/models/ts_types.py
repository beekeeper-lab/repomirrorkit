"""TypeScript domain-type model extractor (BEAN-064).

Many TS apps (Next.js, Express) keep their domain model as plain
``interface`` / ``type`` declarations — and zod object schemas — rather than
ORM decorators. Declarations in conventional model locations
(``models/``, ``entities/``, ``domain/``, ``schemas/``, ``types/``, or
``*.model.ts`` / ``*.entity.ts`` / ``*.schema.ts``) become ``ModelSurface``
objects so screens and APIs can map onto them.
"""

from __future__ import annotations

import re
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.api_contracts_js import zod_schemas
from repo_mirror_kit.harvester.analyzers.models._common import (
    _MAX_FILES_PER_TECH,
    _read_file,
)
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ModelField,
    ModelSurface,
    SourceRef,
)
from repo_mirror_kit.harvester.parsing import parse_source

_TS_FILE_RE = re.compile(r"\.tsx?$")
_MODEL_PATH_RE = re.compile(
    r"(^|/)(models?|entities|entity|domain|schemas?|types)(/|$)"
    r"|\.(model|entity|schema)\.tsx?$",
    re.IGNORECASE,
)
_SKIP_NAME_RE = re.compile(r"(Props|State|Context|Options|Config|Params|Args|Result)$")


def _extract_ts_types(repo_root: Path, file_paths: list[str]) -> list[ModelSurface]:
    """Extract models from TS interfaces/types/zod schemas in model locations."""
    surfaces: list[ModelSurface] = []
    candidates = [
        p
        for p in file_paths
        if _TS_FILE_RE.search(p)
        and _MODEL_PATH_RE.search(p)
        and not p.endswith(".d.ts")
        and ".test." not in p
    ][:_MAX_FILES_PER_TECH]

    for rel in candidates:
        content = _read_file(repo_root, rel)
        if content is None:
            continue
        ps = parse_source(rel, content)
        if ps is None:
            continue
        for decl in ps.find_all("interface_declaration", "type_alias_declaration"):
            name_node = decl.child_by_field_name("name")
            body = decl.child_by_field_name("body") or decl.child_by_field_name("value")
            if (
                name_node is None
                or body is None
                or body.type not in ("interface_body", "object_type")
            ):
                continue
            name = ps.text(name_node)
            if _SKIP_NAME_RE.search(name):
                continue
            fields: list[ModelField] = []
            for member in body.children:
                if member.type != "property_signature":
                    continue
                fname = member.child_by_field_name("name")
                ftype = member.child_by_field_name("type")
                if fname is None:
                    continue
                optional = any(c.type == "?" for c in member.children)
                fields.append(
                    ModelField(
                        name=ps.text(fname),
                        field_type=ps.text(ftype).lstrip(":").strip()
                        if ftype is not None
                        else "unknown",
                        constraints=[] if optional else ["not_null"],
                    )
                )
            if fields:
                surfaces.append(
                    ModelSurface(
                        name=name,
                        entity_name=name,
                        fields=fields,
                        source_refs=[
                            SourceRef(file_path=rel, start_line=ps.line_of(decl))
                        ],
                    )
                )
        for schema_name, zfields in zod_schemas(ps).items():
            entity = re.sub(r"Schema$", "", schema_name)
            entity = entity[:1].upper() + entity[1:]
            surfaces.append(
                ModelSurface(
                    name=entity,
                    entity_name=entity,
                    fields=[
                        ModelField(
                            name=f["name"],
                            field_type=f["type"],
                            constraints=([] if not f["required"] else ["not_null"])
                            + list(f.get("rules", [])),
                        )
                        for f in zfields
                    ],
                    source_refs=[SourceRef(file_path=rel)],
                )
            )
    return surfaces
