"""UI flow analyzer for multi-step interactions and navigation patterns.

Discovers wizard flows, navigation guards, modal chains, and onboarding
sequences by scanning frontend source files.  Produces ``UIFlowSurface``
objects with flow type, step names, entry points, and exit points.

Supported patterns:
- Multi-step form wizards (Stepper, Wizard, Step components)
- Router navigation guards (beforeRouteEnter, canActivate, beforeEach)
- Modal open/close chains (dialog/modal state management)
- Onboarding / welcome flows (onboarding/welcome/getting-started components)

Uses heuristic-based extraction (pattern matching, not full AST) per spec v1.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import SourceRef, UIFlowSurface
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# Extensions scanned for UI flow patterns.
_JS_TS_EXTENSIONS: frozenset[str] = frozenset({".js", ".jsx", ".ts", ".tsx"})
_PY_EXTENSIONS: frozenset[str] = frozenset({".py"})
_ALL_EXTENSIONS: frozenset[str] = _JS_TS_EXTENSIONS | _PY_EXTENSIONS

_MAX_FILE_READ_BYTES: int = 512_000  # 500 KB limit for heuristic scanning.

# ---------------------------------------------------------------------------
# Wizard / stepper patterns
# ---------------------------------------------------------------------------

# JSX components: <Stepper>, <Wizard>, <Step>, <WizardStep>, <FormStep>
_WIZARD_COMPONENT_RE = re.compile(
    r"""<(Stepper|Wizard|WizardStep|FormWizard|MultiStepForm)\b[^>]*>""",
    re.IGNORECASE,
)

# Individual step definitions: <Step label="Review">
_STEP_LABEL_RE = re.compile(
    r"""<(?:Step|WizardStep|FormStep)\b[^>]*?(?:label|title|name)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# Step components by convention: <StepOne>, <Step1>, <StepReview>
_STEP_NAMED_RE = re.compile(
    r"""<(Step\w+)\b""",
)

# steps array: steps = [{ ... }, { ... }] or steps: [...]
_STEPS_ARRAY_RE = re.compile(
    r"""steps\s*[:=]\s*\[([^\]]+)\]""",
    re.DOTALL,
)

# Step label/title within array: { label: "Step 1", ... }
_STEP_ARRAY_LABEL_RE = re.compile(
    r"""(?:label|title|name)\s*:\s*["']([^"']+)["']""",
)

# activeStep / currentStep state variable (indicates wizard pattern)
_ACTIVE_STEP_RE = re.compile(
    r"""(?:activeStep|currentStep|stepIndex|step)\s*[,=]""",
)

# ---------------------------------------------------------------------------
# Navigation guard patterns
# ---------------------------------------------------------------------------

# Vue Router: beforeRouteEnter, beforeRouteLeave, beforeEach
_VUE_NAV_GUARD_RE = re.compile(
    r"""(?:beforeRouteEnter|beforeRouteLeave|beforeRouteUpdate|beforeEach|afterEach)\s*[:(]""",
)

# Angular: canActivate, canDeactivate, resolve guards
_ANGULAR_GUARD_RE = re.compile(
    r"""(?:canActivate|canDeactivate|canLoad|canActivateChild|resolve)\s*[:(]""",
)

# Angular guard class pattern: class FooGuard implements CanActivate
_ANGULAR_GUARD_CLASS_RE = re.compile(
    r"""class\s+(\w+Guard)\s+implements\s+(?:CanActivate|CanDeactivate|CanLoad|Resolve)""",
)

# React Router: loader, action, shouldRevalidate (v6.4+)
_REACT_ROUTER_GUARD_RE = re.compile(
    r"""(?:loader|action|shouldRevalidate)\s*[:=]\s*(?:async\s+)?\(""",
)

# Navigation event patterns: onNavigate, onBeforeNavigate
_NAV_EVENT_RE = re.compile(
    r"""(?:onNavigate|onBeforeNavigate|onAfterNavigate|navigationGuard)\s*[:(=]""",
)

# ---------------------------------------------------------------------------
# Modal chain patterns
# ---------------------------------------------------------------------------

# Modal/Dialog state: showModal, isOpen, setIsOpen, openDialog
_MODAL_STATE_RE = re.compile(
    r"""(?:showModal|isModalOpen|setIsModalOpen|openModal|closeModal|showDialog|isDialogOpen|openDialog|closeDialog)\s*[(:=]""",
    re.IGNORECASE,
)

# Modal components: <Modal>, <Dialog>, <Drawer>, <Sheet>
_MODAL_COMPONENT_RE = re.compile(
    r"""<(Modal|Dialog|Drawer|Sheet|Overlay|Popover)\b[^>]*?(?:open|visible|show|isOpen)\s*[={]""",
    re.IGNORECASE,
)

# Multiple modals in one file (chain indicator)
_MODAL_NAME_RE = re.compile(
    r"""<(Modal|Dialog)\b[^>]*?(?:title|name|id|aria-label)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Onboarding / welcome flow patterns
# ---------------------------------------------------------------------------

# File path patterns indicating onboarding flows.
_ONBOARDING_PATH_RE = re.compile(
    r"""(?:onboarding|welcome|getting[_-]started|first[_-]run|setup[_-]wizard|tour)""",
    re.IGNORECASE,
)

# Component names indicating onboarding.
_ONBOARDING_COMPONENT_RE = re.compile(
    r"""<(Onboarding\w*|Welcome\w*|GettingStarted\w*|SetupWizard\w*|Tour\w*|Walkthrough\w*)\b""",
    re.IGNORECASE,
)

# Onboarding step/page patterns
_ONBOARDING_STEP_RE = re.compile(
    r"""<(OnboardingStep|WelcomeStep|TourStep)\b[^>]*?(?:title|label)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)


def analyze_ui_flows(
    inventory: InventoryResult,
    profile: StackProfile,
    workdir: Path | None = None,
) -> list[UIFlowSurface]:
    """Discover UI interaction flows across the repository.

    Scans frontend source files for multi-step wizards, navigation guards,
    modal chains, and onboarding flows.

    Args:
        inventory: The scanned file inventory.
        profile: Detection results identifying which stacks are present.
        workdir: Repository working directory for reading file contents.

    Returns:
        A list of ``UIFlowSurface`` objects, one per discovered flow.
    """
    if workdir is None:
        logger.debug("ui_flows_skipped", reason="no_workdir")
        return []

    surfaces: list[UIFlowSurface] = []

    for entry in inventory.files:
        if entry.extension not in _ALL_EXTENSIONS:
            continue

        content = _read_file_safe(workdir / entry.path)
        if content is None:
            continue

        surfaces.extend(_scan_wizards(content, entry.path))
        surfaces.extend(_scan_nav_guards(content, entry.path))
        surfaces.extend(_scan_modal_chains(content, entry.path))
        surfaces.extend(_scan_onboarding(content, entry.path))

    logger.info("ui_flow_analysis_complete", total_surfaces=len(surfaces))
    return surfaces


# ---------------------------------------------------------------------------
# Flow-type scanners
# ---------------------------------------------------------------------------


def _scan_wizards(content: str, file_path: str) -> list[UIFlowSurface]:
    """Scan content for multi-step form wizard patterns.

    Looks for Stepper/Wizard components, step arrays, and activeStep
    state management indicating a multi-step flow.

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``UIFlowSurface`` objects for discovered wizards.
    """
    surfaces: list[UIFlowSurface] = []

    # Check for wizard/stepper components.
    wizard_matches = list(_WIZARD_COMPONENT_RE.finditer(content))
    if not wizard_matches and not _ACTIVE_STEP_RE.search(content):
        return []

    # Extract step labels from JSX attributes.
    steps: list[str] = []
    for match in _STEP_LABEL_RE.finditer(content):
        label = match.group(1)
        if label not in steps:
            steps.append(label)

    # Extract steps from a steps array definition.
    if not steps:
        for array_match in _STEPS_ARRAY_RE.finditer(content):
            array_content = array_match.group(1)
            for label_match in _STEP_ARRAY_LABEL_RE.finditer(array_content):
                label = label_match.group(1)
                if label not in steps:
                    steps.append(label)

    # Fall back to named step components.
    if not steps:
        for match in _STEP_NAMED_RE.finditer(content):
            name = match.group(1)
            if name not in steps:
                steps.append(name)

    first_match = wizard_matches[0] if wizard_matches else _ACTIVE_STEP_RE.search(content)
    if first_match is None:
        return []

    component_name = PurePosixPath(file_path).stem
    surfaces.append(
        UIFlowSurface(
            name=f"wizard:{component_name}",
            flow_type="wizard",
            steps=steps,
            entry_point=steps[0] if steps else component_name,
            exit_points=[steps[-1]] if steps else [],
            source_refs=[
                SourceRef(
                    file_path=file_path,
                    start_line=_line_number(content, first_match.start()),
                )
            ],
        )
    )

    return surfaces


def _scan_nav_guards(content: str, file_path: str) -> list[UIFlowSurface]:
    """Scan content for router navigation guard patterns.

    Detects Vue Router guards, Angular route guards, and React Router
    loader/action patterns that control navigation flow.

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``UIFlowSurface`` objects for discovered navigation guards.
    """
    surfaces: list[UIFlowSurface] = []

    # Vue navigation guards
    for match in _VUE_NAV_GUARD_RE.finditer(content):
        guard_name = match.group(0).split("(")[0].split(":")[0].strip()
        surfaces.append(
            UIFlowSurface(
                name=f"navigation:{guard_name}:{file_path}",
                flow_type="navigation",
                steps=[guard_name],
                entry_point=guard_name,
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # Angular guard classes
    for match in _ANGULAR_GUARD_CLASS_RE.finditer(content):
        guard_class = match.group(1)
        surfaces.append(
            UIFlowSurface(
                name=f"navigation:{guard_class}",
                flow_type="navigation",
                steps=[guard_class],
                entry_point=guard_class,
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    # Angular guard properties (only if no guard classes found in file)
    if not _ANGULAR_GUARD_CLASS_RE.search(content):
        for match in _ANGULAR_GUARD_RE.finditer(content):
            guard_type = match.group(0).split("(")[0].split(":")[0].strip()
            surfaces.append(
                UIFlowSurface(
                    name=f"navigation:{guard_type}:{file_path}",
                    flow_type="navigation",
                    steps=[guard_type],
                    entry_point=guard_type,
                    source_refs=[
                        SourceRef(
                            file_path=file_path,
                            start_line=_line_number(content, match.start()),
                        )
                    ],
                )
            )

    # Generic navigation events
    for match in _NAV_EVENT_RE.finditer(content):
        event_name = match.group(0).split("(")[0].split(":")[0].split("=")[0].strip()
        surfaces.append(
            UIFlowSurface(
                name=f"navigation:{event_name}:{file_path}",
                flow_type="navigation",
                steps=[event_name],
                entry_point=event_name,
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, match.start()),
                    )
                ],
            )
        )

    return surfaces


def _scan_modal_chains(content: str, file_path: str) -> list[UIFlowSurface]:
    """Scan content for modal/dialog chain patterns.

    Detects files with multiple modal or dialog components that suggest
    a chained interaction flow (e.g., confirm -> details -> success).

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``UIFlowSurface`` objects for discovered modal chains.
    """
    surfaces: list[UIFlowSurface] = []

    # Collect named modals/dialogs.
    modal_names: list[str] = []
    first_offset: int | None = None

    for match in _MODAL_NAME_RE.finditer(content):
        name = match.group(2)
        if name not in modal_names:
            modal_names.append(name)
            if first_offset is None:
                first_offset = match.start()

    # A chain requires at least two modals in one file.
    if len(modal_names) >= 2 and first_offset is not None:
        component_name = PurePosixPath(file_path).stem
        surfaces.append(
            UIFlowSurface(
                name=f"modal_chain:{component_name}",
                flow_type="modal_chain",
                steps=modal_names,
                entry_point=modal_names[0],
                exit_points=[modal_names[-1]],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(content, first_offset),
                    )
                ],
            )
        )
        return surfaces

    # Detect single modals with complex state (open/close cycles).
    modal_components = list(_MODAL_COMPONENT_RE.finditer(content))
    modal_states = list(_MODAL_STATE_RE.finditer(content))

    # Multiple state toggles with modal components suggest a flow.
    if len(modal_states) >= 3 and modal_components:
        component_name = PurePosixPath(file_path).stem
        state_names = []
        for match in modal_states:
            name = match.group(0).split("(")[0].split(":")[0].split("=")[0].strip()
            if name not in state_names:
                state_names.append(name)

        surfaces.append(
            UIFlowSurface(
                name=f"modal_chain:{component_name}",
                flow_type="modal_chain",
                steps=state_names,
                entry_point=state_names[0] if state_names else component_name,
                exit_points=[state_names[-1]] if state_names else [],
                source_refs=[
                    SourceRef(
                        file_path=file_path,
                        start_line=_line_number(
                            content, modal_components[0].start()
                        ),
                    )
                ],
            )
        )

    return surfaces


def _scan_onboarding(content: str, file_path: str) -> list[UIFlowSurface]:
    """Scan content and file paths for onboarding/welcome flow patterns.

    Detects onboarding flows from both file naming conventions and
    component usage within the file.

    Args:
        content: The full file content.
        file_path: Repository-relative file path.

    Returns:
        A list of ``UIFlowSurface`` objects for discovered onboarding flows.
    """
    surfaces: list[UIFlowSurface] = []
    is_onboarding_file = bool(_ONBOARDING_PATH_RE.search(file_path))

    # Onboarding components in the content.
    component_matches = list(_ONBOARDING_COMPONENT_RE.finditer(content))

    if not is_onboarding_file and not component_matches:
        return []

    # Extract onboarding steps.
    steps: list[str] = []
    for match in _ONBOARDING_STEP_RE.finditer(content):
        label = match.group(2)
        if label not in steps:
            steps.append(label)

    # Fall back to component names as steps.
    if not steps and component_matches:
        for match in component_matches:
            name = match.group(1)
            if name not in steps:
                steps.append(name)

    component_name = PurePosixPath(file_path).stem
    first_match = component_matches[0] if component_matches else None
    start_line = (
        _line_number(content, first_match.start()) if first_match else 1
    )

    surfaces.append(
        UIFlowSurface(
            name=f"onboarding:{component_name}",
            flow_type="form_sequence",
            steps=steps,
            entry_point=steps[0] if steps else component_name,
            exit_points=[steps[-1]] if steps else [],
            source_refs=[
                SourceRef(
                    file_path=file_path,
                    start_line=start_line,
                )
            ],
        )
    )

    return surfaces


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_file_safe(file_path: Path) -> str | None:
    """Read a file's text content safely, returning None on failure.

    Args:
        file_path: Absolute path to the file to read.

    Returns:
        The file content as a string, or None if reading failed.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        if len(content) > _MAX_FILE_READ_BYTES:
            logger.debug(
                "ui_flow_file_too_large",
                path=str(file_path),
                size=len(content),
            )
            return None
        return content
    except OSError:
        logger.debug("ui_flow_file_read_failed", path=str(file_path))
        return None


def _line_number(content: str, char_offset: int) -> int:
    """Calculate the 1-based line number for a character offset.

    Args:
        content: The full file content.
        char_offset: Zero-based character position.

    Returns:
        The 1-based line number.
    """
    return content[:char_offset].count("\n") + 1
