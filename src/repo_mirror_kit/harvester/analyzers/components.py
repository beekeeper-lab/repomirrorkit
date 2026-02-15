"""Component analyzer for discovering shared UI components.

Discovers shared UI components across detected frontend frameworks (React,
Vue, Svelte), extracting their interfaces (props, events/outputs) and usage
locations.  Produces ``ComponentSurface`` objects for each discovered
component.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ComponentSurface,
    SourceRef,
)
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# Directories conventionally holding shared components.
_SHARED_COMPONENT_DIRS: frozenset[str] = frozenset(
    {"components", "shared", "ui", "common", "lib"}
)

# Extensions by framework.
_REACT_EXTENSIONS: frozenset[str] = frozenset({".jsx", ".tsx"})
_VUE_EXTENSIONS: frozenset[str] = frozenset({".vue"})
_SVELTE_EXTENSIONS: frozenset[str] = frozenset({".svelte"})

# Stack names that trigger each extraction strategy.
_REACT_STACKS: frozenset[str] = frozenset({"react", "nextjs"})
_VUE_STACKS: frozenset[str] = frozenset({"vue"})
_SVELTE_STACKS: frozenset[str] = frozenset({"svelte", "sveltekit"})

# Regexes for React prop extraction.
_REACT_INTERFACE_RE = re.compile(
    r"(?:interface|type)\s+(\w*Props\w*)\s*(?:=\s*)?\{([^}]*)\}",
    re.DOTALL,
)
_REACT_PROP_FIELD_RE = re.compile(r"(\w+)\s*[?]?\s*:")
_REACT_PROPTYPES_RE = re.compile(
    r"(\w+)\.propTypes\s*=\s*\{([^}]*)\}",
    re.DOTALL,
)
_REACT_PROPTYPE_FIELD_RE = re.compile(r"(\w+)\s*:")
_REACT_FUNCTION_PROPS_RE = re.compile(
    r"(?:function\s+\w+|const\s+\w+\s*=\s*(?:\([^)]*\)\s*=>|function))"
    r"\s*\(\s*\{\s*([^}]*)\}\s*(?::[^)]*)?(?:\)|,)",
)

# Regex for callback/event props (React).
_REACT_CALLBACK_RE = re.compile(r"\bon[A-Z]\w+")

# Regex for Vue defineProps.
_VUE_DEFINE_PROPS_RE = re.compile(
    r"defineProps\s*(?:<\s*\{([^}]*)\}\s*>|"
    r"\(\s*\{([^}]*)\}\s*\))",
    re.DOTALL,
)
_VUE_PROPS_OPTION_RE = re.compile(
    r"props\s*:\s*(?:\[([^\]]*)\]|\{([^}]*)\})",
    re.DOTALL,
)
_VUE_EMIT_RE = re.compile(
    r"defineEmits\s*(?:<[^>]*>)?\s*\(\s*\[([^\]]*)\]",
    re.DOTALL,
)
_VUE_EMIT_OPTION_RE = re.compile(
    r"emits\s*:\s*\[([^\]]*)\]",
    re.DOTALL,
)

# Regex for Svelte export let (props).
_SVELTE_EXPORT_LET_RE = re.compile(r"export\s+let\s+(\w+)")
# Regex for Svelte dispatcher events.
_SVELTE_DISPATCH_RE = re.compile(r"dispatch\(\s*['\"](\w+)['\"]")

# Regex for state patterns (conditional rendering).
_STATE_PATTERNS: dict[str, re.Pattern[str]] = {
    "loading": re.compile(r"(?:isLoading|loading|isSpinning)\b", re.IGNORECASE),
    "error": re.compile(r"(?:isError|error|hasError)\b", re.IGNORECASE),
    "empty": re.compile(r"(?:isEmpty|empty|noData|no[A-Z]\w*Found)\b", re.IGNORECASE),
}

# Import patterns for usage tracking.
_IMPORT_RE = re.compile(
    r"import\s+(?:\{[^}]*\}|[\w]+|\*\s+as\s+\w+)"
    r"\s+from\s+['\"]([^'\"]+)['\"]"
)
_REQUIRE_RE = re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)")
_VUE_COMPONENT_TAG_RE = re.compile(r"<([A-Z]\w+)")

_MAX_FILES_TO_SCAN = 200


@dataclass
class _RawComponent:
    """Internal representation of a discovered component before finalization."""

    name: str
    file_path: str
    framework: str
    props: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    states: list[str] = field(default_factory=list)
    usage_locations: list[str] = field(default_factory=list)


def analyze_components(
    inventory: InventoryResult,
    profile: StackProfile,
    workdir: Path,
) -> list[ComponentSurface]:
    """Discover shared UI components and extract their interfaces.

    Examines the file inventory for component files matching detected
    frontend frameworks.  For each component found in a shared directory,
    extracts props, events/outputs, and conditional rendering states.
    Tracks usage locations by scanning import statements in other files.

    Args:
        inventory: The scanned file inventory.
        profile: Detection results indicating which stacks are present.
        workdir: Path to the repository working directory for file reads.

    Returns:
        A list of ``ComponentSurface`` objects, one per discovered component.
    """
    detected_stacks = set(profile.stacks.keys())
    frameworks = _resolve_frameworks(detected_stacks)

    if not frameworks:
        logger.info("component_analyzer_skipped", reason="no_frontend_frameworks")
        return []

    logger.info("component_analyzer_starting", frameworks=sorted(frameworks))

    raw_components = _discover_components(inventory, frameworks, workdir)

    if not raw_components:
        logger.info("component_analyzer_complete", components_found=0)
        return []

    _track_usage(raw_components, inventory, workdir)

    surfaces = _build_surfaces(raw_components)

    logger.info(
        "component_analyzer_complete",
        components_found=len(surfaces),
        shared_count=sum(1 for s in surfaces if len(s.usage_locations) >= 2),
    )

    return surfaces


def _resolve_frameworks(detected_stacks: set[str]) -> set[str]:
    """Map detected stack names to framework categories.

    Args:
        detected_stacks: Stack names from the detection profile.

    Returns:
        A set of framework identifiers (``react``, ``vue``, ``svelte``).
    """
    frameworks: set[str] = set()
    if detected_stacks & _REACT_STACKS:
        frameworks.add("react")
    if detected_stacks & _VUE_STACKS:
        frameworks.add("vue")
    if detected_stacks & _SVELTE_STACKS:
        frameworks.add("svelte")
    return frameworks


def _is_in_shared_dir(path: str) -> bool:
    """Check if a file path is under a shared component directory.

    Args:
        path: Repository-relative path.

    Returns:
        True if any path segment matches a known shared directory name.
    """
    parts = PurePosixPath(path).parts
    return any(p.lower() in _SHARED_COMPONENT_DIRS for p in parts[:-1])


def _component_name_from_path(path: str) -> str:
    """Derive a component name from a file path.

    Uses the file stem, converting kebab-case to PascalCase.

    Args:
        path: Repository-relative path.

    Returns:
        The derived component name.
    """
    stem = PurePosixPath(path).stem
    # Convert kebab-case or snake_case to PascalCase.
    parts = re.split(r"[-_]", stem)
    return "".join(p.capitalize() for p in parts if p)


def _discover_components(
    inventory: InventoryResult,
    frameworks: set[str],
    workdir: Path,
) -> list[_RawComponent]:
    """Discover component files matching the detected frameworks.

    Args:
        inventory: The file inventory.
        frameworks: Set of framework identifiers to look for.
        workdir: Repository root for reading file contents.

    Returns:
        A list of raw component records with extracted metadata.
    """
    components: list[_RawComponent] = []
    extensions: set[str] = set()

    if "react" in frameworks:
        extensions.update(_REACT_EXTENSIONS)
    if "vue" in frameworks:
        extensions.update(_VUE_EXTENSIONS)
    if "svelte" in frameworks:
        extensions.update(_SVELTE_EXTENSIONS)

    for entry in inventory.files:
        if entry.extension not in extensions:
            continue
        if entry.category == "test":
            continue
        if not _is_in_shared_dir(entry.path):
            continue

        framework = _classify_framework(entry.extension)
        name = _component_name_from_path(entry.path)

        raw = _RawComponent(
            name=name,
            file_path=entry.path,
            framework=framework,
        )

        content = _read_file(workdir, entry.path)
        if content is not None:
            _extract_metadata(raw, content)

        components.append(raw)

    return components


def _classify_framework(extension: str) -> str:
    """Determine the framework from a file extension.

    Args:
        extension: The file extension (e.g. ``.jsx``).

    Returns:
        Framework identifier string.
    """
    if extension in _REACT_EXTENSIONS:
        return "react"
    if extension in _VUE_EXTENSIONS:
        return "vue"
    if extension in _SVELTE_EXTENSIONS:
        return "svelte"
    return "unknown"


def _read_file(workdir: Path, rel_path: str) -> str | None:
    """Read a file from the working directory.

    Args:
        workdir: Repository root.
        rel_path: Repository-relative path.

    Returns:
        File contents as a string, or None on failure.
    """
    try:
        return (workdir / rel_path).read_text(encoding="utf-8")
    except OSError:
        logger.debug("component_file_read_failed", path=rel_path)
        return None


def _extract_metadata(raw: _RawComponent, content: str) -> None:
    """Extract props, outputs, and states from file content.

    Dispatches to the appropriate extraction function based on the
    component's framework.

    Args:
        raw: The raw component to populate.
        content: The file content.
    """
    if raw.framework == "react":
        _extract_react_metadata(raw, content)
    elif raw.framework == "vue":
        _extract_vue_metadata(raw, content)
    elif raw.framework == "svelte":
        _extract_svelte_metadata(raw, content)

    _extract_states(raw, content)


def _extract_react_metadata(raw: _RawComponent, content: str) -> None:
    """Extract React component props and callback outputs.

    Args:
        raw: The raw component to populate.
        content: The file content.
    """
    props: list[str] = []

    # Try TypeScript interface/type Props.
    match = _REACT_INTERFACE_RE.search(content)
    if match:
        body = match.group(2)
        props.extend(_REACT_PROP_FIELD_RE.findall(body))

    # Try PropTypes.
    if not props:
        pt_match = _REACT_PROPTYPES_RE.search(content)
        if pt_match:
            body = pt_match.group(2)
            props.extend(_REACT_PROPTYPE_FIELD_RE.findall(body))

    # Try destructured function parameters.
    if not props:
        fn_match = _REACT_FUNCTION_PROPS_RE.search(content)
        if fn_match:
            params = fn_match.group(1)
            props.extend(
                p.strip().rstrip(",")
                for p in params.split(",")
                if p.strip() and not p.strip().startswith("...")
            )

    raw.props = _deduplicate(props)

    # Extract callback props as outputs.
    callbacks = _REACT_CALLBACK_RE.findall(content)
    raw.outputs = _deduplicate(callbacks)


def _extract_vue_metadata(raw: _RawComponent, content: str) -> None:
    """Extract Vue component props and emits.

    Args:
        raw: The raw component to populate.
        content: The file content.
    """
    props: list[str] = []

    # Try Composition API defineProps.
    dp_match = _VUE_DEFINE_PROPS_RE.search(content)
    if dp_match:
        body = dp_match.group(1) or dp_match.group(2) or ""
        props.extend(_REACT_PROP_FIELD_RE.findall(body))

    # Try Options API props.
    if not props:
        opt_match = _VUE_PROPS_OPTION_RE.search(content)
        if opt_match:
            if opt_match.group(1):
                # Array syntax: props: ['title', 'count']
                props.extend(
                    s.strip().strip("'\"")
                    for s in opt_match.group(1).split(",")
                    if s.strip().strip("'\"")
                )
            elif opt_match.group(2):
                # Object syntax: props: { title: String }
                props.extend(_REACT_PROP_FIELD_RE.findall(opt_match.group(2)))

    raw.props = _deduplicate(props)

    # Extract emits.
    emits: list[str] = []
    emit_match = _VUE_EMIT_RE.search(content)
    if emit_match:
        emits.extend(
            s.strip().strip("'\"")
            for s in emit_match.group(1).split(",")
            if s.strip().strip("'\"")
        )

    if not emits:
        emit_opt = _VUE_EMIT_OPTION_RE.search(content)
        if emit_opt:
            emits.extend(
                s.strip().strip("'\"")
                for s in emit_opt.group(1).split(",")
                if s.strip().strip("'\"")
            )

    raw.outputs = _deduplicate(emits)


def _extract_svelte_metadata(raw: _RawComponent, content: str) -> None:
    """Extract Svelte component props and dispatched events.

    Args:
        raw: The raw component to populate.
        content: The file content.
    """
    raw.props = _deduplicate(_SVELTE_EXPORT_LET_RE.findall(content))
    raw.outputs = _deduplicate(_SVELTE_DISPATCH_RE.findall(content))


def _extract_states(raw: _RawComponent, content: str) -> None:
    """Detect conditional rendering state patterns in content.

    Args:
        raw: The raw component to populate.
        content: The file content.
    """
    states: list[str] = []
    for state_name, pattern in _STATE_PATTERNS.items():
        if pattern.search(content):
            states.append(state_name)
    raw.states = states


def _track_usage(
    components: list[_RawComponent],
    inventory: InventoryResult,
    workdir: Path,
) -> None:
    """Scan source files for import references to discovered components.

    Args:
        components: The components to track usage for.
        inventory: The file inventory.
        workdir: Repository root.
    """
    # Build a mapping from component name/path to component for fast lookup.
    component_stems: dict[str, list[_RawComponent]] = {}
    for comp in components:
        stem = PurePosixPath(comp.file_path).stem
        component_stems.setdefault(stem, []).append(comp)
        component_stems.setdefault(comp.name, []).append(comp)

    component_paths: set[str] = {c.file_path for c in components}

    scannable_extensions = frozenset({".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"})

    files_to_scan = [
        entry
        for entry in inventory.files
        if entry.extension in scannable_extensions
        and entry.path not in component_paths
        and entry.category != "test"
    ][:_MAX_FILES_TO_SCAN]

    for entry in files_to_scan:
        content = _read_file(workdir, entry.path)
        if content is None:
            continue

        _scan_imports_for_usage(content, entry.path, component_stems)
        _scan_template_tags_for_usage(content, entry.path, component_stems)


def _scan_imports_for_usage(
    content: str,
    source_path: str,
    component_stems: dict[str, list[_RawComponent]],
) -> None:
    """Scan import statements for references to known components.

    Args:
        content: File content to scan.
        source_path: Path of the file being scanned.
        component_stems: Mapping from name/stem to components.
    """
    for match in _IMPORT_RE.finditer(content):
        import_path = match.group(1)
        # Check the last segment of the import path.
        import_stem = PurePosixPath(import_path).stem
        if import_stem in component_stems:
            for comp in component_stems[import_stem]:
                if source_path not in comp.usage_locations:
                    comp.usage_locations.append(source_path)

    for match in _REQUIRE_RE.finditer(content):
        import_path = match.group(1)
        import_stem = PurePosixPath(import_path).stem
        if import_stem in component_stems:
            for comp in component_stems[import_stem]:
                if source_path not in comp.usage_locations:
                    comp.usage_locations.append(source_path)


def _scan_template_tags_for_usage(
    content: str,
    source_path: str,
    component_stems: dict[str, list[_RawComponent]],
) -> None:
    """Scan template/JSX for component tag usage.

    Args:
        content: File content to scan.
        source_path: Path of the file being scanned.
        component_stems: Mapping from name/stem to components.
    """
    for match in _VUE_COMPONENT_TAG_RE.finditer(content):
        tag_name = match.group(1)
        if tag_name in component_stems:
            for comp in component_stems[tag_name]:
                if source_path not in comp.usage_locations:
                    comp.usage_locations.append(source_path)


def _build_surfaces(components: list[_RawComponent]) -> list[ComponentSurface]:
    """Convert raw component records to ComponentSurface objects.

    Args:
        components: The raw component records.

    Returns:
        A list of ComponentSurface objects.
    """
    surfaces: list[ComponentSurface] = []
    for comp in components:
        surface = ComponentSurface(
            name=comp.name,
            props=comp.props,
            outputs=comp.outputs,
            usage_locations=comp.usage_locations,
            states=comp.states,
            source_refs=[SourceRef(file_path=comp.file_path)],
        )
        surfaces.append(surface)
    return surfaces


def _deduplicate(items: list[str]) -> list[str]:
    """Remove duplicates while preserving order.

    Args:
        items: List of strings.

    Returns:
        Deduplicated list preserving first occurrence order.
    """
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
