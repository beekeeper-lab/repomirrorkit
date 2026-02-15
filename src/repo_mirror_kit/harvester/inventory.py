"""Repository inventory and file discovery.

Scans a cloned repository working directory, applies include/exclude
glob filters, categorizes files, computes hashes, and produces a
structured inventory for downstream pipeline stages.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

import structlog

from repo_mirror_kit.harvester.config import HarvestConfig

logger = structlog.get_logger()

_BINARY_CHECK_BYTES = 8192

# --- Extension and path maps for categorization ---

_SOURCE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".c",
        ".cpp",
        ".cc",
        ".h",
        ".hpp",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".kts",
        ".scala",
        ".cs",
        ".vue",
        ".svelte",
        ".lua",
        ".pl",
        ".pm",
        ".r",
        ".dart",
        ".ex",
        ".exs",
        ".erl",
        ".hs",
        ".ml",
        ".fs",
        ".clj",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".bat",
        ".cmd",
    }
)

_CONFIG_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".env",
        ".xml",
        ".properties",
        ".plist",
    }
)

_CONFIG_FILENAMES: frozenset[str] = frozenset(
    {
        "Dockerfile",
        "Makefile",
        "Vagrantfile",
        "Procfile",
        ".gitignore",
        ".gitattributes",
        ".editorconfig",
        ".eslintrc",
        ".prettierrc",
        ".babelrc",
        ".env",
        "tox.ini",
        "setup.cfg",
    }
)

_DOC_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".md",
        ".rst",
        ".txt",
        ".adoc",
        ".tex",
    }
)

_ASSET_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".bmp",
        ".webp",
        ".mp3",
        ".mp4",
        ".wav",
        ".ogg",
        ".avi",
        ".mov",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".otf",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".rar",
        ".7z",
        ".bin",
        ".dat",
        ".db",
        ".sqlite",
    }
)

_TEST_DIR_NAMES: frozenset[str] = frozenset(
    {
        "test",
        "tests",
        "spec",
        "specs",
        "__tests__",
    }
)

_MIGRATION_DIR_NAMES: frozenset[str] = frozenset(
    {
        "migration",
        "migrations",
        "migrate",
        "alembic",
    }
)


@dataclass
class FileEntry:
    """A single inventoried file.

    Args:
        path: Repository-relative path using forward slashes.
        size: File size in bytes.
        extension: File extension including the dot, or empty string.
        hash: Hex-encoded MD5 hash of the file content.
        category: Guessed category (source, config, test, asset,
            documentation, migration).
    """

    path: str
    size: int
    extension: str
    hash: str
    category: str


@dataclass
class SkippedFile:
    """A file or directory that was skipped during scanning.

    Args:
        path: Repository-relative path.
        reason: Why the file was skipped (excluded, too_large, binary).
        size: File size in bytes, if available.
    """

    path: str
    reason: str
    size: int | None = None


@dataclass
class InventoryResult:
    """Result of a repository inventory scan.

    Args:
        files: Inventoried file entries, sorted by path.
        skipped: Skipped files and directories with reasons.
        total_files: Number of files inventoried.
        total_size: Total size of all inventoried files in bytes.
        total_skipped: Number of skipped entries.
    """

    files: list[FileEntry]
    skipped: list[SkippedFile]
    total_files: int
    total_size: int
    total_skipped: int


def scan(workdir: Path, config: HarvestConfig) -> InventoryResult:
    """Scan a repository working directory and build a file inventory.

    Walks the directory tree, applying include/exclude filters, size
    limits, and binary detection. Returns a structured inventory with
    file metadata and skip records.

    Args:
        workdir: Root of the cloned repository to scan.
        config: Harvest configuration with filter settings.

    Returns:
        An InventoryResult with all included files and skip records.
    """
    logger.info("inventory_scan_starting", workdir=str(workdir))

    simple_excludes, glob_excludes = _split_patterns(config.exclude)

    files: list[FileEntry] = []
    skipped: list[SkippedFile] = []

    for dirpath_str, dirnames, filenames in os.walk(workdir):
        current = Path(dirpath_str)

        # Prune excluded directories (sort for deterministic traversal)
        kept_dirs: list[str] = []
        for d in sorted(dirnames):
            if d in simple_excludes:
                rel = str(Path(dirpath_str, d).relative_to(workdir))
                skipped.append(SkippedFile(path=rel, reason="excluded"))
            else:
                kept_dirs.append(d)
        dirnames[:] = kept_dirs

        for name in sorted(filenames):
            filepath = current / name

            # Skip symlinks
            if filepath.is_symlink():
                continue

            rel_path = filepath.relative_to(workdir)
            rel_str = str(PurePosixPath(rel_path))

            # Check glob-based excludes
            if _matches_any_glob(rel_str, glob_excludes):
                skipped.append(SkippedFile(path=rel_str, reason="excluded"))
                continue

            # Check includes (empty tuple means include everything)
            if config.include and not _matches_any_glob(rel_str, config.include):
                continue

            # Get file metadata
            try:
                stat = filepath.stat()
            except OSError:
                continue
            size = stat.st_size

            # Check size limit
            if size > config.max_file_bytes:
                skipped.append(SkippedFile(path=rel_str, reason="too_large", size=size))
                continue

            # Check for binary content
            if _is_binary(filepath):
                skipped.append(SkippedFile(path=rel_str, reason="binary", size=size))
                continue

            # Compute hash and categorize
            file_hash = _compute_hash(filepath)
            category = _categorize_file(rel_str)
            extension = filepath.suffix

            files.append(
                FileEntry(
                    path=rel_str,
                    size=size,
                    extension=extension,
                    hash=file_hash,
                    category=category,
                )
            )

    # Sort for deterministic iteration order
    files.sort(key=lambda f: f.path)
    skipped.sort(key=lambda s: s.path)

    total_size = sum(f.size for f in files)

    result = InventoryResult(
        files=files,
        skipped=skipped,
        total_files=len(files),
        total_size=total_size,
        total_skipped=len(skipped),
    )

    logger.info(
        "inventory_scan_complete",
        total_files=result.total_files,
        total_size=result.total_size,
        total_skipped=result.total_skipped,
    )

    return result


def write_report(output_dir: Path, result: InventoryResult) -> Path:
    """Write the inventory to reports/inventory.json.

    Uses atomic write (write to .tmp then rename) to prevent partial
    files on failure.

    Args:
        output_dir: Root output directory for reports.
        result: The inventory scan result to serialize.

    Returns:
        Path to the written inventory.json file.
    """
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "inventory.json"

    data: dict[str, object] = {
        "files": [asdict(f) for f in result.files],
        "skipped": [
            {k: v for k, v in asdict(s).items() if v is not None}
            for s in result.skipped
        ],
        "summary": {
            "total_files": result.total_files,
            "total_size": result.total_size,
            "total_skipped": result.total_skipped,
        },
    }

    tmp_path = report_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(report_path)

    logger.info("inventory_report_written", path=str(report_path))
    return report_path


def _split_patterns(
    patterns: tuple[str, ...],
) -> tuple[frozenset[str], tuple[str, ...]]:
    """Split patterns into simple directory names and glob patterns.

    Simple names (no wildcards or path separators) are used for
    directory-level pruning during walk. Glob patterns are matched
    against individual file paths.

    Args:
        patterns: Tuple of exclude or include patterns.

    Returns:
        A tuple of (simple_names frozenset, glob_patterns tuple).
    """
    simple: set[str] = set()
    globs: list[str] = []
    for p in patterns:
        if any(c in p for c in ("*", "?", "[", "/")):
            globs.append(p)
        else:
            simple.add(p)
    return frozenset(simple), tuple(globs)


def _matches_any_glob(path: str, patterns: tuple[str, ...]) -> bool:
    """Check if a path matches any of the given glob patterns.

    Uses PurePosixPath.match() which supports ``**`` recursive
    wildcards in Python 3.12+.  For patterns starting with ``**/``,
    also tries matching without that prefix so that root-level files
    are correctly matched (``**`` should match zero or more directories).

    Args:
        path: Repository-relative path with forward slashes.
        patterns: Glob patterns to match against.

    Returns:
        True if the path matches at least one pattern.
    """
    posix_path = PurePosixPath(path)
    for p in patterns:
        if posix_path.match(p):
            return True
        # **/ should match zero or more directories, including zero
        if p.startswith("**/") and posix_path.match(p[3:]):
            return True
    return False


def _is_binary(filepath: Path) -> bool:
    """Detect if a file is binary by checking for null bytes.

    Reads the first 8 KiB of the file and looks for null bytes, which
    indicate binary content.

    Args:
        filepath: Path to the file to check.

    Returns:
        True if the file appears to be binary.
    """
    try:
        with filepath.open("rb") as f:
            chunk = f.read(_BINARY_CHECK_BYTES)
    except OSError:
        return False
    return b"\x00" in chunk


def _compute_hash(filepath: Path) -> str:
    """Compute an MD5 hash of a file's contents.

    MD5 is used for fast fingerprinting, not for cryptographic purposes.

    Args:
        filepath: Path to the file to hash.

    Returns:
        Hex-encoded MD5 digest string, or empty string on read error.
    """
    hasher = hashlib.md5()  # noqa: S324 — fingerprinting, not cryptography
    try:
        with filepath.open("rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
    except OSError:
        return ""
    return hasher.hexdigest()


def _categorize_file(rel_path: str) -> str:
    """Guess the category of a file based on its path and extension.

    Categories: source, config, test, asset, documentation, migration.

    Path-based rules (test directories, migration directories) take
    priority over extension-based rules.

    Args:
        rel_path: Repository-relative path.

    Returns:
        The guessed category string.
    """
    parts = PurePosixPath(rel_path).parts
    name = parts[-1] if parts else ""
    ext = PurePosixPath(name).suffix.lower()

    # Path-based checks (directory names)
    dir_parts = frozenset(p.lower() for p in parts[:-1])
    if dir_parts & _MIGRATION_DIR_NAMES:
        return "migration"
    if dir_parts & _TEST_DIR_NAMES:
        return "test"

    # Filename-based test detection
    lower_name = name.lower()
    if lower_name.startswith("test_") or lower_name.endswith("_test.py"):
        return "test"

    # Filename-based config detection
    if name in _CONFIG_FILENAMES:
        return "config"

    # Extension-based checks
    if ext in _ASSET_EXTENSIONS:
        return "asset"
    if ext in _DOC_EXTENSIONS:
        return "documentation"
    if ext in _CONFIG_EXTENSIONS:
        return "config"
    if ext in _SOURCE_EXTENSIONS:
        return "source"

    # Default for unknown extensions
    return "source"
