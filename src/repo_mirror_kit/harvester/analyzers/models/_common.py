"""Shared helpers for the per-framework model extractors (BEAN-057).

The constants and helpers in this module are used by two or more
framework submodules. Single-use helpers stay with their framework
file so the module boundaries are tight.
"""

from __future__ import annotations

from pathlib import Path

# Skip files larger than this — typically generated/minified content.
_MAX_FILE_SIZE = 1_000_000  # 1 MB

# Cap on how many files any single extractor will read. Bounds runtime
# on monorepos and prevents pathological inputs from dominating the
# pipeline budget.
_MAX_FILES_PER_TECH = 200


def _read_file(repo_root: Path, rel_path: str) -> str | None:
    """Read a file's text content, returning None on failure.

    Skips files larger than ``_MAX_FILE_SIZE``.
    """
    full_path = repo_root / rel_path
    try:
        if full_path.stat().st_size > _MAX_FILE_SIZE:
            return None
        return full_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


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


def _table_to_entity_name(table_name: str) -> str:
    """Convert a snake_case table name to PascalCase entity name.

    Args:
        table_name: SQL table name (e.g. ``user_accounts``).

    Returns:
        PascalCase name (e.g. ``UserAccounts``).
    """
    return "".join(part.capitalize() for part in table_name.split("_"))


__all__ = [
    "_MAX_FILES_PER_TECH",
    "_MAX_FILE_SIZE",
    "_extract_braced_block",
    "_read_file",
    "_table_to_entity_name",
]
