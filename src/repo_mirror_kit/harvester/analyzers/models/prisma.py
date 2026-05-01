"""Prisma schema model extractor."""

from __future__ import annotations

import re
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.models._common import (
    _MAX_FILES_PER_TECH,
    _read_file,
)
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ModelField,
    ModelSurface,
    SourceRef,
)

_PRISMA_SCHEMA_RE = re.compile(r"(?:^|/)schema\.prisma$")
_PRISMA_MODEL_RE = re.compile(r"^model\s+(\w+)\s*\{", re.MULTILINE)
_PRISMA_FIELD_RE = re.compile(
    r"^\s+(\w+)[ \t]+([\w\[\]?]+)(?:[ \t]+(.*))?$", re.MULTILINE
)
_PRISMA_RELATION_RE = re.compile(r"@relation\b")
_PRISMA_ID_RE = re.compile(r"@id\b")
_PRISMA_UNIQUE_RE = re.compile(r"@unique\b")
_PRISMA_DEFAULT_RE = re.compile(r"@default\b")
_PRISMA_MAP_RE = re.compile(r'@@map\("([^"]+)"\)')


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


__all__ = ["_extract_prisma"]
