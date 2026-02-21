"""File coverage analyzer: detects source files with no surface references.

Cross-references the file inventory (Stage B) against all surface
``source_refs`` to identify uncovered files, then generates catch-all
``GeneralLogicSurface`` instances for each uncovered source file.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path, PurePosixPath

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    GeneralLogicSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# Default exclusion patterns — files/directories that rarely need
# behavioral requirements.
DEFAULT_EXCLUSION_PATTERNS: tuple[str, ...] = (
    "**/__pycache__/**",
    "**/.git/**",
    "**/node_modules/**",
    "**/vendor/**",
    "**/migrations/**",
    "**/migrate/**",
    "**/alembic/**",
    "**/.tox/**",
    "**/.venv/**",
    "**/.mypy_cache/**",
    "**/.pytest_cache/**",
    "**/__pypackages__/**",
    "**/.eggs/**",
    "**/*.egg-info/**",
    "**/dist/**",
    "**/build/**",
    "**/*.min.js",
    "**/*.min.css",
    "**/*.lock",
    "**/package-lock.json",
    "**/yarn.lock",
    "**/pnpm-lock.yaml",
    "**/poetry.lock",
    "**/uv.lock",
    "**/Pipfile.lock",
    "**/*.generated.*",
    "**/*.auto.*",
    "**/__init__.py",
)

# Categories from inventory that are source code
_SOURCE_CATEGORIES: frozenset[str] = frozenset({"source", "test"})


def find_uncovered_files(
    inventory: InventoryResult,
    surfaces: SurfaceCollection,
    exclusion_patterns: tuple[str, ...] = DEFAULT_EXCLUSION_PATTERNS,
) -> list[Path]:
    """Identify source files with zero surface references.

    Compares inventory file paths against all surface ``source_refs``.
    Files that are non-source (assets, docs, configs) or match exclusion
    patterns are skipped.

    Args:
        inventory: File inventory from Stage B.
        surfaces: Extracted surfaces from Stage C.
        exclusion_patterns: Glob patterns for files to exclude.

    Returns:
        Sorted list of uncovered source file paths (repo-relative).
    """
    # Collect all file paths referenced by any surface
    covered_files: set[str] = set()
    for surface in surfaces:
        for ref in surface.source_refs:
            covered_files.add(ref.file_path)

    uncovered: list[Path] = []
    for entry in inventory.files:
        # Only consider source files
        if entry.category not in _SOURCE_CATEGORIES:
            continue

        # Check exclusion patterns
        if _matches_any_exclusion(entry.path, exclusion_patterns):
            continue

        # Check if any surface references this file
        if entry.path not in covered_files:
            uncovered.append(Path(entry.path))

    uncovered.sort()

    logger.info(
        "file_coverage_analysis",
        total_source_files=sum(
            1
            for f in inventory.files
            if f.category in _SOURCE_CATEGORIES
            and not _matches_any_exclusion(f.path, exclusion_patterns)
        ),
        covered=len(covered_files),
        uncovered=len(uncovered),
    )

    return uncovered


def analyze_uncovered_files(
    uncovered_files: list[Path],
    inventory: InventoryResult,
    profile: StackProfile,
    workdir: Path,
) -> list[GeneralLogicSurface]:
    """Generate GeneralLogicSurface for each uncovered file.

    Extracts module-level information (top-level classes, functions,
    docstrings) to populate catch-all surfaces.

    Args:
        uncovered_files: List of uncovered file paths (repo-relative).
        inventory: File inventory for metadata lookup.
        profile: Stack profile (unused currently, reserved for future).
        workdir: Repository working directory.

    Returns:
        List of GeneralLogicSurface instances.
    """
    surfaces: list[GeneralLogicSurface] = []

    for rel_path in uncovered_files:
        abs_path = workdir / rel_path
        try:
            info = _extract_module_info(abs_path)
        except Exception:
            logger.warning(
                "file_coverage_extraction_failed",
                file=str(rel_path),
                exc_info=True,
            )
            info = _ModuleInfo(
                purpose="Could not parse module",
                exports=[],
                complexity="simple",
            )

        surface = GeneralLogicSurface(
            name=str(rel_path),
            source_refs=[SourceRef(file_path=str(rel_path))],
            file_path=str(rel_path),
            module_purpose=info.purpose,
            exports=info.exports,
            complexity_hint=info.complexity,
        )
        surfaces.append(surface)

    logger.info(
        "file_coverage_surfaces_generated",
        count=len(surfaces),
    )

    return surfaces


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _ModuleInfo:
    """Extracted module-level information."""

    __slots__ = ("complexity", "exports", "purpose")

    def __init__(
        self,
        purpose: str,
        exports: list[str],
        complexity: str,
    ) -> None:
        self.purpose = purpose
        self.exports = exports
        self.complexity = complexity


def _extract_module_info(filepath: Path) -> _ModuleInfo:
    """Extract module-level information from a source file.

    For Python files, uses AST parsing. For other languages, falls back
    to regex-based heuristic extraction.
    """
    ext = filepath.suffix.lower()
    if ext in (".py",):
        return _extract_python_info(filepath)
    if ext in (".js", ".jsx", ".ts", ".tsx"):
        return _extract_js_ts_info(filepath)
    return _extract_generic_info(filepath)


def _extract_python_info(filepath: Path) -> _ModuleInfo:
    """Extract info from a Python file using AST."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except OSError:
        return _ModuleInfo(
            purpose="Could not read file", exports=[], complexity="simple"
        )

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _extract_generic_info(filepath)

    # Module docstring
    purpose = ast.get_docstring(tree) or ""
    if purpose:
        # Take first line/sentence
        purpose = purpose.split("\n")[0].strip()

    exports: list[str] = []
    function_count = 0
    class_count = 0

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if not node.name.startswith("_"):
                exports.append(f"def {node.name}()")
            function_count += 1
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                exports.append(f"class {node.name}")
            class_count += 1

    total = function_count + class_count
    if total > 10:
        complexity = "complex"
    elif total > 4:
        complexity = "moderate"
    else:
        complexity = "simple"

    return _ModuleInfo(purpose=purpose, exports=exports, complexity=complexity)


_JS_EXPORT_RE = re.compile(
    r"export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)"
)
_JS_FUNCTION_RE = re.compile(r"(?:function|const|let|var)\s+(\w+)")


def _extract_js_ts_info(filepath: Path) -> _ModuleInfo:
    """Extract info from JS/TS files using regex heuristics."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except OSError:
        return _ModuleInfo(
            purpose="Could not read file", exports=[], complexity="simple"
        )

    exports: list[str] = list(dict.fromkeys(_JS_EXPORT_RE.findall(source)))
    if not exports:
        exports = list(dict.fromkeys(_JS_FUNCTION_RE.findall(source)))[:10]

    line_count = source.count("\n")
    if line_count > 300:
        complexity = "complex"
    elif line_count > 100:
        complexity = "moderate"
    else:
        complexity = "simple"

    # First comment block as purpose
    purpose = ""
    lines = source.lstrip().splitlines()
    if lines and lines[0].strip().startswith("//"):
        purpose = lines[0].strip().lstrip("/").strip()
    elif lines and lines[0].strip().startswith("/*"):
        comment_lines: list[str] = []
        for line in lines:
            comment_lines.append(line.strip().lstrip("/*").rstrip("*/").strip())
            if "*/" in line:
                break
        purpose = " ".join(comment_lines).strip()
        if len(purpose) > 200:
            purpose = purpose[:200]

    return _ModuleInfo(purpose=purpose, exports=exports, complexity=complexity)


def _extract_generic_info(filepath: Path) -> _ModuleInfo:
    """Fallback extraction for unknown file types."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except OSError:
        return _ModuleInfo(
            purpose="Could not read file", exports=[], complexity="simple"
        )

    line_count = source.count("\n")
    if line_count > 300:
        complexity = "complex"
    elif line_count > 100:
        complexity = "moderate"
    else:
        complexity = "simple"

    # First non-empty line as purpose hint
    purpose = ""
    for line in source.splitlines()[:5]:
        stripped = line.strip().lstrip("#/;-*").strip()
        if stripped:
            purpose = stripped[:200]
            break

    return _ModuleInfo(purpose=purpose, exports=[], complexity=complexity)


def _matches_any_exclusion(path: str, patterns: tuple[str, ...]) -> bool:
    """Check if a path matches any exclusion pattern."""
    posix = PurePosixPath(path)
    for p in patterns:
        if posix.match(p):
            return True
        if p.startswith("**/") and posix.match(p[3:]):
            return True
    return False
