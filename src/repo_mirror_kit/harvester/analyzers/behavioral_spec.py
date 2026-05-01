"""Behavioral-spec post-pass analyzer (BEAN-054).

Extracts intent signal from docstrings, JSDoc/TSDoc comments, and test
names — sources of human-authored "what this does" content that the
structural analyzers throw away. Each extracted signal is attached to
the relevant surface's ``enrichment`` dict under a new
``behavioral_signals`` key.

Output structure (attached to ``surface.enrichment["behavioral_signals"]``)::

    {
        "docstring": str | None,   # Python/Java-style docstring of the
                                   # enclosing function/class
        "jsdoc": str | None,       # Leading JSDoc/TSDoc block above
                                   # the surface's source line
        "test_names": list[str],   # Test names whose lowercased form
                                   # contains the surface name
    }

Bean rendering (see ``harvester/beans/templates.py``) prefers LLM
``behavioral_description`` when present; otherwise it renders this
signal so beans contain real behavioral content even in offline mode.

Failure mode: unparsable source files, missing files, etc. are
silently skipped — this analyzer is enrichment, not core analysis.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from repo_mirror_kit.harvester.analyzers.surfaces import (
    SourceRef,
    Surface,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import InventoryResult

# Suffixes that hold JSDoc/TSDoc-style comments.
_JS_TS_SUFFIXES: frozenset[str] = frozenset(
    {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
)

# Match a leading ``/** ... */`` block immediately preceding a target line.
# Captures the body without the comment markers.
_JSDOC_RE = re.compile(r"/\*\*(?P<body>[\s\S]*?)\*/\s*$")

# pytest-style top-level test function names.
_PYTEST_FN_RE = re.compile(r"^test_\w+$")

# Jest / Vitest / Mocha test/spec helpers. Captures the description string.
_JS_TEST_RE = re.compile(
    r"""\b(?:it|test|describe|context)\(\s*['"`](?P<name>[^'"`]+)['"`]"""
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze_behavioral_spec(
    inventory: InventoryResult,
    profile: StackProfile,  # reserved for future per-stack tuning
    workdir: Path,
    surfaces: SurfaceCollection,
) -> None:
    """Attach behavioral signals to each surface's enrichment dict.

    Mutates ``surfaces`` in place. Idempotent: a pre-existing
    ``behavioral_signals`` entry is preserved (does not clobber LLM
    enrichment that already populated it).
    """
    cache = _FileCache(workdir)
    test_corpus = _collect_test_names(inventory, workdir)

    for surface in surfaces:
        if "behavioral_signals" in surface.enrichment:
            # Respect any signal already set (e.g. a future analyzer that
            # builds on top of this one). Do not double-attach.
            continue

        docstring = _docstring_for_surface(surface, cache)
        jsdoc = _jsdoc_for_surface(surface, cache)
        test_names = _test_names_for_surface(surface.name, test_corpus)

        if not (docstring or jsdoc or test_names):
            continue

        surface.enrichment["behavioral_signals"] = {
            "docstring": docstring,
            "jsdoc": jsdoc,
            "test_names": test_names,
        }


# ---------------------------------------------------------------------------
# Per-surface extraction
# ---------------------------------------------------------------------------


def _docstring_for_surface(surface: Surface, cache: _FileCache) -> str | None:
    ref = _primary_python_ref(surface)
    if ref is None:
        return None
    tree = cache.python_tree(ref.file_path)
    if tree is None:
        return None
    return _python_docstring_at(tree, ref)


def _jsdoc_for_surface(surface: Surface, cache: _FileCache) -> str | None:
    ref = _primary_jsts_ref(surface)
    if ref is None or ref.start_line is None:
        return None
    lines = cache.lines(ref.file_path)
    if lines is None:
        return None
    return _jsdoc_above(lines, ref.start_line)


def _primary_python_ref(surface: Surface) -> SourceRef | None:
    for ref in surface.source_refs:
        if Path(ref.file_path).suffix.lower() == ".py":
            return ref
    return None


def _primary_jsts_ref(surface: Surface) -> SourceRef | None:
    for ref in surface.source_refs:
        if Path(ref.file_path).suffix.lower() in _JS_TS_SUFFIXES:
            return ref
    return None


# ---------------------------------------------------------------------------
# Python docstring extraction
# ---------------------------------------------------------------------------


def _python_docstring_at(tree: ast.Module, ref: SourceRef) -> str | None:
    """Return the docstring of the smallest function/class enclosing the
    surface's start_line, or the module docstring as a last resort."""
    target = ref.start_line
    if target is None:
        return ast.get_docstring(tree)

    enclosing: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | None = None
    enclosing_start = -1

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = node.lineno
        end = getattr(node, "end_lineno", None) or start
        if start <= target <= end and start > enclosing_start:
            enclosing = node
            enclosing_start = start

    if enclosing is not None:
        doc = ast.get_docstring(enclosing)
        if doc:
            return doc

    return ast.get_docstring(tree)


# ---------------------------------------------------------------------------
# JSDoc / TSDoc extraction
# ---------------------------------------------------------------------------


def _jsdoc_above(lines: list[str], target_line: int) -> str | None:
    """Read backwards from ``target_line`` for the nearest ``/** ... */``
    block. Returns the cleaned body or None if no JSDoc precedes the line."""
    if target_line <= 0 or target_line > len(lines):
        return None

    # Scan upward over blank lines until we hit non-blank content.
    idx = target_line - 2  # 1-based to 0-based, then step above target
    while idx >= 0 and not lines[idx].strip():
        idx -= 1
    if idx < 0:
        return None

    # The nearest non-blank line above the target must end the JSDoc block.
    if not lines[idx].rstrip().endswith("*/"):
        return None

    # Walk upward gathering the block until we find ``/**`` (or fail).
    block_lines: list[str] = []
    while idx >= 0:
        block_lines.insert(0, lines[idx])
        if lines[idx].lstrip().startswith("/**"):
            break
        idx -= 1
    else:
        return None

    block = "\n".join(block_lines)
    match = _JSDOC_RE.search(block)
    if not match:
        return None

    body = match.group("body")
    return _clean_jsdoc_body(body)


def _clean_jsdoc_body(body: str) -> str:
    """Strip leading ``*`` markers and trim whitespace from a JSDoc body."""
    cleaned: list[str] = []
    for raw in body.splitlines():
        stripped = raw.strip()
        if stripped.startswith("*"):
            stripped = stripped[1:].strip()
        if stripped:
            cleaned.append(stripped)
    return "\n".join(cleaned).strip() or ""


# ---------------------------------------------------------------------------
# Test-name harvesting
# ---------------------------------------------------------------------------


def _collect_test_names(
    inventory: InventoryResult, workdir: Path
) -> list[tuple[Path, str]]:
    """Walk the inventory and collect (path, test_name) pairs across all
    detected test files. Best-effort: parse failures are silently skipped."""
    corpus: list[tuple[Path, str]] = []
    for entry in _inventory_entries(inventory):
        rel = Path(entry)
        if not _looks_like_test_file(rel):
            continue
        full = workdir / rel
        if not full.is_file():
            continue
        suffix = rel.suffix.lower()
        try:
            text = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if suffix == ".py":
            for name in _python_test_names(text):
                corpus.append((rel, name))
        elif suffix in _JS_TS_SUFFIXES:
            for name in _JS_TEST_RE.findall(text):
                # findall with named group returns the group value directly.
                corpus.append((rel, name))
    return corpus


def _inventory_entries(inventory: InventoryResult) -> list[str]:
    """Pull a flat list of relative file paths out of the inventory.

    The InventoryResult shape varies across analyzer versions; this helper
    is tolerant — it tries common attribute names and falls back to an
    empty list rather than failing the whole pass.
    """
    for attr in ("entries", "files", "all_files"):
        value = getattr(inventory, attr, None)
        if value is None:
            continue
        # Each entry may be a string path, an object with ``.path``, or an
        # object with ``.relative_path``.
        out: list[str] = []
        for item in value:
            if isinstance(item, str):
                out.append(item)
            elif hasattr(item, "relative_path"):
                out.append(str(item.relative_path))
            elif hasattr(item, "path"):
                out.append(str(item.path))
        if out:
            return out
    return []


def _looks_like_test_file(path: Path) -> bool:
    name = path.name.lower()
    if path.suffix.lower() == ".py":
        return name.startswith("test_") or name.endswith("_test.py")
    if path.suffix.lower() in _JS_TS_SUFFIXES:
        return (
            ".test." in name
            or ".spec." in name
            or "/__tests__/" in path.as_posix().lower()
            or "/tests/" in path.as_posix().lower()
        )
    return False


def _python_test_names(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _PYTEST_FN_RE.match(node.name):
                names.append(node.name)
    return names


def _tokenize_surface_name(name: str) -> set[str]:
    """Split a surface name into lowercase tokens, handling camelCase,
    PascalCase, snake_case, and kebab-case.

    Tokens of length ≤ 2 are dropped to avoid spurious noise like ``id`` or
    ``a`` matching test names that happen to share those substrings.
    """
    # Insert a space at camelCase / PascalCase boundaries before splitting on
    # non-alphanumeric.
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)
    spaced = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", spaced)
    return {
        token.lower() for token in re.split(r"[^A-Za-z0-9]+", spaced) if len(token) > 2
    }


def _test_names_for_surface(
    surface_name: str,
    corpus: list[tuple[Path, str]],
) -> list[str]:
    """Return up to 10 test names whose lowercased form contains any
    surface-name token (camelCase-aware). Surfaces whose name yields no
    tokens of length > 2 (e.g. ``X``, ``id``) match nothing."""
    tokens = _tokenize_surface_name(surface_name)
    if not tokens:
        return []

    matched: list[str] = []
    seen: set[str] = set()
    for _path, name in corpus:
        haystack = name.lower()
        if any(token in haystack for token in tokens):
            if name not in seen:
                seen.add(name)
                matched.append(name)
                if len(matched) >= 10:
                    break
    return matched


# ---------------------------------------------------------------------------
# Per-file caching
# ---------------------------------------------------------------------------


class _FileCache:
    """Memoize parsed Python ASTs and read text lines per harvest run.

    Many surfaces share files (a route module typically defines several
    routes); parsing once per file saves significant CPU on repeat reads.
    """

    def __init__(self, workdir: Path) -> None:
        self._workdir = workdir
        self._py_trees: dict[str, ast.Module | None] = {}
        self._lines: dict[str, list[str] | None] = {}

    def python_tree(self, rel_path: str) -> ast.Module | None:
        if rel_path in self._py_trees:
            return self._py_trees[rel_path]
        full = self._workdir / rel_path
        try:
            text = full.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text)
        except (OSError, SyntaxError, ValueError):
            self._py_trees[rel_path] = None
            return None
        self._py_trees[rel_path] = tree
        return tree

    def lines(self, rel_path: str) -> list[str] | None:
        if rel_path in self._lines:
            return self._lines[rel_path]
        full = self._workdir / rel_path
        try:
            text = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            self._lines[rel_path] = None
            return None
        self._lines[rel_path] = text.splitlines()
        return self._lines[rel_path]


__all__ = ["analyze_behavioral_spec"]


# Type-checking-only re-exports to avoid runtime cycles.
def _unused_export(_: Any) -> None:  # pragma: no cover
    pass
