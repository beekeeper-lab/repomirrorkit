"""Dependency & package analyzer.

Extracts declared dependencies from manifest files across ecosystems
(JavaScript, Python, Go, .NET, Ruby, Rust), classifies them by purpose
(runtime, dev, test, build, peer), and detects lock file presence.

Produces DependencySurface objects for downstream bean generation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import DependencySurface, SourceRef
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_FILE_SIZE = 512_000  # Skip files larger than 512 KB

_LOCK_FILES: frozenset[str] = frozenset(
    {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "uv.lock",
        "poetry.lock",
        "Pipfile.lock",
        "go.sum",
        "Cargo.lock",
        "Gemfile.lock",
        "packages.lock.json",
    }
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_file_safe(path: Path) -> str | None:
    """Read a file, returning None if unreadable or too large."""
    try:
        if path.stat().st_size > _MAX_FILE_SIZE:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _find_files(
    inventory: InventoryResult, name_pattern: re.Pattern[str]
) -> list[FileEntry]:
    """Return inventory files whose basename matches *name_pattern*."""
    matches: list[FileEntry] = []
    for f in inventory.files:
        basename = f.path.rsplit("/", 1)[-1] if "/" in f.path else f.path
        if name_pattern.search(basename):
            matches.append(f)
    return matches


def _find_lock_files(inventory: InventoryResult) -> list[str]:
    """Return list of lock file basenames present in the inventory."""
    found: list[str] = []
    for f in inventory.files:
        basename = f.path.rsplit("/", 1)[-1] if "/" in f.path else f.path
        if basename in _LOCK_FILES:
            if basename not in found:
                found.append(basename)
    return found


# ---------------------------------------------------------------------------
# JavaScript / TypeScript: package.json
# ---------------------------------------------------------------------------

_PACKAGE_JSON_RE = re.compile(r"^package\.json$")


def _extract_js_dependencies(
    inventory: InventoryResult,
    workdir: Path,
) -> list[DependencySurface]:
    """Extract dependencies from package.json files."""
    surfaces: list[DependencySurface] = []
    files = _find_files(inventory, _PACKAGE_JSON_RE)

    group_purpose_map = {
        "dependencies": "runtime",
        "devDependencies": "dev",
        "peerDependencies": "peer",
        "optionalDependencies": "runtime",
    }

    for fe in files:
        content = _read_file_safe(workdir / fe.path)
        if content is None:
            continue
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            continue

        if not isinstance(data, dict):
            continue

        for group, purpose in group_purpose_map.items():
            deps = data.get(group, {})
            if not isinstance(deps, dict):
                continue
            for pkg_name, version in deps.items():
                surfaces.append(
                    DependencySurface(
                        name=pkg_name,
                        version_constraint=str(version),
                        purpose=purpose,
                        manifest_file=fe.path,
                        is_direct=True,
                        source_refs=[SourceRef(file_path=fe.path)],
                    )
                )

    return surfaces


# ---------------------------------------------------------------------------
# Python: pyproject.toml, requirements*.txt, setup.cfg, Pipfile
# ---------------------------------------------------------------------------

_PYPROJECT_RE = re.compile(r"^pyproject\.toml$")
_REQUIREMENTS_RE = re.compile(r"^requirements.*\.txt$")
_SETUP_CFG_RE = re.compile(r"^setup\.cfg$")
_PIPFILE_RE = re.compile(r"^Pipfile$")

# Match pip requirement lines: package-name>=1.0,<2.0 or package-name==1.2.3
_PIP_REQ_RE = re.compile(
    r"^\s*([A-Za-z0-9][-A-Za-z0-9_.]*[A-Za-z0-9]?)\s*([>=<!~^][^\s;#]*)?",
)


def _classify_python_purpose(filename: str) -> str:
    """Classify a Python requirements file by purpose based on its name."""
    lower = filename.lower()
    if "dev" in lower:
        return "dev"
    if "test" in lower:
        return "test"
    if "build" in lower or "ci" in lower:
        return "build"
    return "runtime"


def _extract_python_dependencies(
    inventory: InventoryResult,
    workdir: Path,
) -> list[DependencySurface]:
    """Extract dependencies from Python manifests."""
    surfaces: list[DependencySurface] = []

    # --- pyproject.toml ---
    for fe in _find_files(inventory, _PYPROJECT_RE):
        content = _read_file_safe(workdir / fe.path)
        if content is None:
            continue
        try:
            import tomllib

            data = tomllib.loads(content)
        except Exception:
            logger.debug("pyproject_toml_parse_failed", path=fe.path)
            continue

        # [project].dependencies
        project_deps = data.get("project", {}).get("dependencies", [])
        if isinstance(project_deps, list):
            for dep_str in project_deps:
                m = _PIP_REQ_RE.match(str(dep_str))
                if m:
                    surfaces.append(
                        DependencySurface(
                            name=m.group(1),
                            version_constraint=m.group(2) or "",
                            purpose="runtime",
                            manifest_file=fe.path,
                            is_direct=True,
                            source_refs=[SourceRef(file_path=fe.path)],
                        )
                    )

        # [project.optional-dependencies]
        opt_deps = data.get("project", {}).get("optional-dependencies", {})
        if isinstance(opt_deps, dict):
            for group_name, dep_list in opt_deps.items():
                purpose = _classify_python_purpose(group_name)
                if isinstance(dep_list, list):
                    for dep_str in dep_list:
                        m = _PIP_REQ_RE.match(str(dep_str))
                        if m:
                            surfaces.append(
                                DependencySurface(
                                    name=m.group(1),
                                    version_constraint=m.group(2) or "",
                                    purpose=purpose,
                                    manifest_file=fe.path,
                                    is_direct=True,
                                    source_refs=[SourceRef(file_path=fe.path)],
                                )
                            )

        # [build-system].requires
        build_deps = data.get("build-system", {}).get("requires", [])
        if isinstance(build_deps, list):
            for dep_str in build_deps:
                m = _PIP_REQ_RE.match(str(dep_str))
                if m:
                    surfaces.append(
                        DependencySurface(
                            name=m.group(1),
                            version_constraint=m.group(2) or "",
                            purpose="build",
                            manifest_file=fe.path,
                            is_direct=True,
                            source_refs=[SourceRef(file_path=fe.path)],
                        )
                    )

    # --- requirements*.txt ---
    for fe in _find_files(inventory, _REQUIREMENTS_RE):
        content = _read_file_safe(workdir / fe.path)
        if content is None:
            continue
        basename = fe.path.rsplit("/", 1)[-1] if "/" in fe.path else fe.path
        purpose = _classify_python_purpose(basename)
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            m = _PIP_REQ_RE.match(line)
            if m:
                surfaces.append(
                    DependencySurface(
                        name=m.group(1),
                        version_constraint=m.group(2) or "",
                        purpose=purpose,
                        manifest_file=fe.path,
                        is_direct=True,
                        source_refs=[SourceRef(file_path=fe.path)],
                    )
                )

    # --- setup.cfg ---
    for fe in _find_files(inventory, _SETUP_CFG_RE):
        content = _read_file_safe(workdir / fe.path)
        if content is None:
            continue
        in_install_requires = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                in_install_requires = False
            if stripped == "install_requires =":
                in_install_requires = True
                continue
            if in_install_requires and stripped:
                if not line[0].isspace():
                    in_install_requires = False
                    continue
                m = _PIP_REQ_RE.match(stripped)
                if m:
                    surfaces.append(
                        DependencySurface(
                            name=m.group(1),
                            version_constraint=m.group(2) or "",
                            purpose="runtime",
                            manifest_file=fe.path,
                            is_direct=True,
                            source_refs=[SourceRef(file_path=fe.path)],
                        )
                    )

    # --- Pipfile ---
    for fe in _find_files(inventory, _PIPFILE_RE):
        content = _read_file_safe(workdir / fe.path)
        if content is None:
            continue
        current_purpose = ""
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == "[packages]":
                current_purpose = "runtime"
                continue
            if stripped == "[dev-packages]":
                current_purpose = "dev"
                continue
            if stripped.startswith("["):
                current_purpose = ""
                continue
            if current_purpose and "=" in stripped:
                pkg = stripped.split("=", 1)[0].strip().strip('"').strip("'")
                version_part = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                if pkg:
                    surfaces.append(
                        DependencySurface(
                            name=pkg,
                            version_constraint=version_part
                            if version_part != "*"
                            else "",
                            purpose=current_purpose,
                            manifest_file=fe.path,
                            is_direct=True,
                            source_refs=[SourceRef(file_path=fe.path)],
                        )
                    )

    return surfaces


# ---------------------------------------------------------------------------
# Go: go.mod
# ---------------------------------------------------------------------------

_GO_MOD_RE = re.compile(r"^go\.mod$")
_GO_REQUIRE_RE = re.compile(r"^\s*([^\s]+)\s+(v[^\s]+)")


def _extract_go_dependencies(
    inventory: InventoryResult,
    workdir: Path,
) -> list[DependencySurface]:
    """Extract dependencies from go.mod files."""
    surfaces: list[DependencySurface] = []

    for fe in _find_files(inventory, _GO_MOD_RE):
        content = _read_file_safe(workdir / fe.path)
        if content is None:
            continue

        in_require = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("require ("):
                in_require = True
                continue
            if stripped == ")" and in_require:
                in_require = False
                continue

            # Single-line require
            if stripped.startswith("require ") and "(" not in stripped:
                m = _GO_REQUIRE_RE.match(stripped.removeprefix("require ").strip())
                if m:
                    surfaces.append(
                        DependencySurface(
                            name=m.group(1),
                            version_constraint=m.group(2),
                            purpose="runtime",
                            manifest_file=fe.path,
                            is_direct=True,
                            source_refs=[SourceRef(file_path=fe.path)],
                        )
                    )
            elif in_require:
                # Check for // indirect comment
                is_indirect = "// indirect" in stripped
                m = _GO_REQUIRE_RE.match(stripped)
                if m:
                    surfaces.append(
                        DependencySurface(
                            name=m.group(1),
                            version_constraint=m.group(2),
                            purpose="runtime",
                            manifest_file=fe.path,
                            is_direct=not is_indirect,
                            source_refs=[SourceRef(file_path=fe.path)],
                        )
                    )

    return surfaces


# ---------------------------------------------------------------------------
# .NET: *.csproj
# ---------------------------------------------------------------------------

_CSPROJ_RE = re.compile(r"\.csproj$")
_PKG_REF_RE = re.compile(
    r'<PackageReference\s+Include="([^"]+)"'
    r'(?:\s+Version="([^"]*)")?',
)


def _extract_dotnet_dependencies(
    inventory: InventoryResult,
    workdir: Path,
) -> list[DependencySurface]:
    """Extract dependencies from .csproj PackageReference entries."""
    surfaces: list[DependencySurface] = []

    for fe in _find_files(inventory, _CSPROJ_RE):
        content = _read_file_safe(workdir / fe.path)
        if content is None:
            continue

        for m in _PKG_REF_RE.finditer(content):
            surfaces.append(
                DependencySurface(
                    name=m.group(1),
                    version_constraint=m.group(2) or "",
                    purpose="runtime",
                    manifest_file=fe.path,
                    is_direct=True,
                    source_refs=[SourceRef(file_path=fe.path)],
                )
            )

    return surfaces


# ---------------------------------------------------------------------------
# Ruby: Gemfile
# ---------------------------------------------------------------------------

_GEMFILE_RE = re.compile(r"^Gemfile$")
_GEM_LINE_RE = re.compile(
    r"""^\s*gem\s+['"]([^'"]+)['"]\s*(?:,\s*['"]([^'"]*)['"]\s*)?""",
)


def _extract_ruby_dependencies(
    inventory: InventoryResult,
    workdir: Path,
) -> list[DependencySurface]:
    """Extract dependencies from Gemfile."""
    surfaces: list[DependencySurface] = []

    for fe in _find_files(inventory, _GEMFILE_RE):
        content = _read_file_safe(workdir / fe.path)
        if content is None:
            continue

        current_group: str | None = None
        for line in content.splitlines():
            stripped = line.strip()

            # Track groups
            if stripped.startswith("group "):
                group_match = re.search(r":(\w+)", stripped)
                if group_match:
                    group_name = group_match.group(1)
                    if group_name in ("development", "dev"):
                        current_group = "dev"
                    elif group_name == "test":
                        current_group = "test"
                    else:
                        current_group = "runtime"
                continue
            if stripped == "end":
                current_group = None
                continue

            m = _GEM_LINE_RE.match(stripped)
            if m:
                purpose = current_group or "runtime"
                surfaces.append(
                    DependencySurface(
                        name=m.group(1),
                        version_constraint=m.group(2) or "",
                        purpose=purpose,
                        manifest_file=fe.path,
                        is_direct=True,
                        source_refs=[SourceRef(file_path=fe.path)],
                    )
                )

    return surfaces


# ---------------------------------------------------------------------------
# Rust: Cargo.toml
# ---------------------------------------------------------------------------

_CARGO_TOML_RE = re.compile(r"^Cargo\.toml$")


def _extract_rust_dependencies(
    inventory: InventoryResult,
    workdir: Path,
) -> list[DependencySurface]:
    """Extract dependencies from Cargo.toml files."""
    surfaces: list[DependencySurface] = []

    for fe in _find_files(inventory, _CARGO_TOML_RE):
        content = _read_file_safe(workdir / fe.path)
        if content is None:
            continue
        try:
            import tomllib

            data = tomllib.loads(content)
        except Exception:
            logger.debug("cargo_toml_parse_failed", path=fe.path)
            continue

        section_purpose_map = {
            "dependencies": "runtime",
            "dev-dependencies": "dev",
            "build-dependencies": "build",
        }

        for section, purpose in section_purpose_map.items():
            deps = data.get(section, {})
            if not isinstance(deps, dict):
                continue
            for pkg_name, value in deps.items():
                if isinstance(value, str):
                    version = value
                elif isinstance(value, dict):
                    version = value.get("version", "")
                else:
                    version = ""
                surfaces.append(
                    DependencySurface(
                        name=pkg_name,
                        version_constraint=str(version),
                        purpose=purpose,
                        manifest_file=fe.path,
                        is_direct=True,
                        source_refs=[SourceRef(file_path=fe.path)],
                    )
                )

    return surfaces


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_dependencies(
    inventory: InventoryResult,
    profile: StackProfile,
    workdir: Path,
) -> list[DependencySurface]:
    """Extract declared dependencies from manifest files.

    Scans supported ecosystem manifest files, classifies dependencies
    by purpose, detects lock files, and returns DependencySurface objects.

    Args:
        inventory: File inventory from Stage B.
        profile: Detected stack profile.
        workdir: Repository working directory.

    Returns:
        List of DependencySurface instances, one per declared dependency.
    """
    surfaces: list[DependencySurface] = []

    # Always run all extractors — manifests may be present even if the
    # framework wasn't detected (e.g. a monorepo with multiple stacks)
    surfaces.extend(_extract_js_dependencies(inventory, workdir))
    surfaces.extend(_extract_python_dependencies(inventory, workdir))
    surfaces.extend(_extract_go_dependencies(inventory, workdir))
    surfaces.extend(_extract_dotnet_dependencies(inventory, workdir))
    surfaces.extend(_extract_ruby_dependencies(inventory, workdir))
    surfaces.extend(_extract_rust_dependencies(inventory, workdir))

    # Attach lock file metadata to all surfaces
    lock_files = _find_lock_files(inventory)
    if lock_files:
        for s in surfaces:
            s.lock_files = lock_files

    logger.info(
        "dependencies_analyzed",
        total=len(surfaces),
        lock_files=lock_files,
    )
    return surfaces
