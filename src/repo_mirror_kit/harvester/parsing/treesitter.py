"""tree-sitter loader and tiny query helpers (BEAN-061).

Grammars load lazily and are cached. Everything degrades gracefully: when
tree-sitter or a grammar is unavailable, or a file cannot be parsed,
:func:`parse_source` returns ``None`` so callers can keep their regex result.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import cache
from pathlib import PurePosixPath
from typing import Any

import structlog

logger = structlog.get_logger()

# File extension -> grammar key.
_EXT_TO_LANG: dict[str, str] = {
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".cs": "c_sharp",
}


def language_for_path(path: str) -> str | None:
    """Grammar key for a file path, or None if unsupported."""
    return _EXT_TO_LANG.get(PurePosixPath(path).suffix.lower())


@cache
def _parser_for(lang: str) -> Any | None:
    """Build (once) a Parser for *lang*; None when unavailable."""
    try:
        from tree_sitter import Language, Parser

        if lang in ("typescript", "tsx"):
            import tree_sitter_typescript as mod

            capsule = (
                mod.language_typescript()
                if lang == "typescript"
                else mod.language_tsx()
            )
        elif lang == "javascript":
            import tree_sitter_javascript as mod_js

            capsule = mod_js.language()
        elif lang == "c_sharp":
            import tree_sitter_c_sharp as mod_cs

            capsule = mod_cs.language()
        else:
            return None
        return Parser(Language(capsule))
    except Exception:
        logger.warning("treesitter_grammar_unavailable", lang=lang, exc_info=True)
        return None


@dataclass
class ParsedSource:
    """A parsed file with convenience accessors over tree-sitter nodes."""

    lang: str
    source: bytes
    root: Any

    def text(self, node: Any) -> str:
        """Source text of *node*."""
        return self.source[node.start_byte : node.end_byte].decode(
            "utf-8", errors="replace"
        )

    def walk(self, node: Any | None = None) -> Iterator[Any]:
        """Depth-first iteration over *node* (default: root) and descendants."""
        stack = [node or self.root]
        while stack:
            current = stack.pop()
            yield current
            stack.extend(reversed(current.children))

    def find_all(self, *types: str, node: Any | None = None) -> list[Any]:
        """All descendants whose node type is in *types*."""
        wanted = set(types)
        return [n for n in self.walk(node) if n.type in wanted]

    def find_where(
        self, predicate: Callable[[Any], bool], node: Any | None = None
    ) -> list[Any]:
        """All descendants satisfying *predicate*."""
        return [n for n in self.walk(node) if predicate(n)]

    def line_of(self, node: Any) -> int:
        """1-based start line of *node*."""
        return int(node.start_point[0]) + 1

    def string_value(self, node: Any) -> str | None:
        """Unquoted value of a string / template literal node, else None."""
        if node.type in ("string", "string_literal", "template_string"):
            raw = self.text(node)
            if len(raw) >= 2 and raw[0] in "\"'`@$":
                return raw.lstrip("@$")[1:-1]
        return None

    def child_text(self, node: Any, field: str) -> str | None:
        """Text of the named field child, if present."""
        child = node.child_by_field_name(field)
        return self.text(child) if child is not None else None


def parse_source(path: str, source: bytes | str) -> ParsedSource | None:
    """Parse *source* using the grammar for *path*; None on any failure."""
    lang = language_for_path(path)
    if lang is None:
        return None
    parser = _parser_for(lang)
    if parser is None:
        return None
    data = source.encode("utf-8") if isinstance(source, str) else source
    try:
        tree = parser.parse(data)
    except Exception:
        logger.warning("treesitter_parse_failed", path=path, exc_info=True)
        return None
    return ParsedSource(lang=lang, source=data, root=tree.root_node)
