"""State management analyzer for frontend and backend frameworks.

Discovers state management patterns by scanning source files for store
definitions, reactive state declarations, and context providers.
Produces ``StateMgmtSurface`` objects with store names, detected pattern
type, action names, and selector names.

Supported patterns:
- Redux (createStore, configureStore, createSlice)
- Zustand (create())
- Pinia (defineStore)
- React Context (createContext, useContext)
- Vuex (createStore with Vuex imports)
- MobX (observable, makeObservable, makeAutoObservable)

Uses heuristic-based extraction (pattern matching, not full AST) per spec v1.
"""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import SourceRef, StateMgmtSurface
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# Extensions scanned for state management patterns.
_JS_TS_EXTENSIONS: frozenset[str] = frozenset({".js", ".jsx", ".ts", ".tsx"})
_PY_EXTENSIONS: frozenset[str] = frozenset({".py"})
_ALL_EXTENSIONS: frozenset[str] = _JS_TS_EXTENSIONS | _PY_EXTENSIONS

_MAX_FILE_READ_BYTES: int = 512_000  # 500 KB limit for heuristic scanning.

# ---------------------------------------------------------------------------
# Redux patterns
# ---------------------------------------------------------------------------

# createSlice({ name: "counter", ... })
_REDUX_CREATE_SLICE_RE = re.compile(
    r"""createSlice\s*\(\s*\{[^}]*?name\s*:\s*["'](\w+)["']""",
    re.DOTALL,
)

# configureStore / createStore calls
_REDUX_CONFIGURE_STORE_RE = re.compile(
    r"""(?:configureStore|createStore)\s*\(""",
)

# Reducer/action names inside createSlice reducers block:
# reducers: { increment(state) { ... }, decrement: (state) => ... }
_REDUX_REDUCER_RE = re.compile(
    r"""reducers\s*:\s*\{([^}]+)\}""",
    re.DOTALL,
)

# Individual reducer key names within the reducers block.
_REDUX_ACTION_NAME_RE = re.compile(
    r"""(\w+)\s*[:(]""",
)

# useSelector usage
_REDUX_SELECTOR_RE = re.compile(
    r"""useSelector\s*\(\s*(?:\(\s*\w+\s*\)\s*=>|function)\s*(\w+)""",
)

# Named selector functions: export const selectFoo = ...
_REDUX_NAMED_SELECTOR_RE = re.compile(
    r"""(?:export\s+)?(?:const|function)\s+(select\w+)""",
)

# ---------------------------------------------------------------------------
# Zustand patterns
# ---------------------------------------------------------------------------

# const useStore = create((set) => ...)
_ZUSTAND_CREATE_RE = re.compile(
    r"""(?:const|let|var)\s+(\w+)\s*=\s*create\s*[(<]""",
)

# Zustand import confirmation
_ZUSTAND_IMPORT_RE = re.compile(
    r"""(?:from\s+["']zustand["']|require\s*\(\s*["']zustand["']\s*\))""",
)

# ---------------------------------------------------------------------------
# Pinia patterns
# ---------------------------------------------------------------------------

# defineStore('storeName', ...)
_PINIA_DEFINE_STORE_RE = re.compile(
    r"""defineStore\s*\(\s*["'](\w+)["']""",
)

# ---------------------------------------------------------------------------
# React Context patterns
# ---------------------------------------------------------------------------

# const FooContext = createContext(...)
_REACT_CREATE_CONTEXT_RE = re.compile(
    r"""(?:const|let|var)\s+(\w+)\s*=\s*(?:React\.)?createContext\s*[(<]""",
)

# useContext(FooContext)
_REACT_USE_CONTEXT_RE = re.compile(
    r"""useContext\s*\(\s*(\w+)\s*\)""",
)

# ---------------------------------------------------------------------------
# Vuex patterns
# ---------------------------------------------------------------------------

# Vuex.Store / createStore with vuex import
_VUEX_STORE_RE = re.compile(
    r"""(?:new\s+Vuex\.Store|createStore)\s*\(""",
)

_VUEX_IMPORT_RE = re.compile(
    r"""(?:from\s+["']vuex["']|require\s*\(\s*["']vuex["']\s*\))""",
)

# ---------------------------------------------------------------------------
# MobX patterns
# ---------------------------------------------------------------------------

_MOBX_OBSERVABLE_RE = re.compile(
    r"""(?:makeObservable|makeAutoObservable|observable)\s*\(""",
)

_MOBX_IMPORT_RE = re.compile(
    r"""(?:from\s+["']mobx["']|require\s*\(\s*["']mobx["']\s*\))""",
)

# Class name preceding makeObservable/makeAutoObservable.
_MOBX_CLASS_RE = re.compile(
    r"""class\s+(\w+)[\s\S]{0,500}?(?:makeObservable|makeAutoObservable)\s*\(""",
)


def analyze_state_management(
    inventory: InventoryResult,
    profile: StackProfile,
    workdir: Path | None = None,
) -> list[StateMgmtSurface]:
    """Discover state management patterns across the repository.

    Examines JS/TS source files for Redux slices/stores, Zustand stores,
    Pinia stores, React Context providers, Vuex stores, and MobX observables.

    Args:
        inventory: The scanned file inventory.
        profile: Detection results identifying which stacks are present.
        workdir: Repository working directory for reading file contents.

    Returns:
        A list of ``StateMgmtSurface`` objects, one per discovered store
        or state management instance.
    """
    if workdir is None:
        logger.debug("state_mgmt_skipped", reason="no_workdir")
        return []

    surfaces: list[StateMgmtSurface] = []

    for entry in inventory.files:
        if entry.extension not in _ALL_EXTENSIONS:
            continue

        content = _read_file_safe(workdir / entry.path)
        if content is None:
            continue

        # Redux: createSlice
        for match in _REDUX_CREATE_SLICE_RE.finditer(content):
            store_name = match.group(1)
            actions = _extract_redux_actions(content, match.start())
            selectors = _extract_redux_selectors(content)
            surfaces.append(
                StateMgmtSurface(
                    name=f"redux:{store_name}",
                    store_name=store_name,
                    pattern="redux",
                    actions=actions,
                    selectors=selectors,
                    source_refs=[
                        SourceRef(
                            file_path=entry.path,
                            start_line=_line_number(content, match.start()),
                        )
                    ],
                )
            )

        # Redux: configureStore/createStore (only if no createSlice found in file)
        if not _REDUX_CREATE_SLICE_RE.search(content):
            for match in _REDUX_CONFIGURE_STORE_RE.finditer(content):
                # Confirm redux import
                if "redux" not in content.lower():
                    continue
                surfaces.append(
                    StateMgmtSurface(
                        name=f"redux:store:{entry.path}",
                        store_name="root",
                        pattern="redux",
                        source_refs=[
                            SourceRef(
                                file_path=entry.path,
                                start_line=_line_number(content, match.start()),
                            )
                        ],
                    )
                )
                break  # One store per file for configureStore

        # Zustand: create() with zustand import
        if _ZUSTAND_IMPORT_RE.search(content):
            for match in _ZUSTAND_CREATE_RE.finditer(content):
                store_name = match.group(1)
                surfaces.append(
                    StateMgmtSurface(
                        name=f"zustand:{store_name}",
                        store_name=store_name,
                        pattern="zustand",
                        source_refs=[
                            SourceRef(
                                file_path=entry.path,
                                start_line=_line_number(content, match.start()),
                            )
                        ],
                    )
                )

        # Pinia: defineStore
        for match in _PINIA_DEFINE_STORE_RE.finditer(content):
            store_name = match.group(1)
            surfaces.append(
                StateMgmtSurface(
                    name=f"pinia:{store_name}",
                    store_name=store_name,
                    pattern="pinia",
                    source_refs=[
                        SourceRef(
                            file_path=entry.path,
                            start_line=_line_number(content, match.start()),
                        )
                    ],
                )
            )

        # React Context: createContext
        for match in _REACT_CREATE_CONTEXT_RE.finditer(content):
            context_name = match.group(1)
            surfaces.append(
                StateMgmtSurface(
                    name=f"context:{context_name}",
                    store_name=context_name,
                    pattern="context",
                    source_refs=[
                        SourceRef(
                            file_path=entry.path,
                            start_line=_line_number(content, match.start()),
                        )
                    ],
                )
            )

        # Vuex: createStore with vuex import
        if _VUEX_IMPORT_RE.search(content):
            for match in _VUEX_STORE_RE.finditer(content):
                surfaces.append(
                    StateMgmtSurface(
                        name=f"vuex:store:{entry.path}",
                        store_name="root",
                        pattern="vuex",
                        source_refs=[
                            SourceRef(
                                file_path=entry.path,
                                start_line=_line_number(content, match.start()),
                            )
                        ],
                    )
                )
                break  # One vuex store per file

        # MobX: observable/makeObservable/makeAutoObservable
        if _MOBX_IMPORT_RE.search(content):
            for match in _MOBX_CLASS_RE.finditer(content):
                class_name = match.group(1)
                surfaces.append(
                    StateMgmtSurface(
                        name=f"mobx:{class_name}",
                        store_name=class_name,
                        pattern="mobx",
                        source_refs=[
                            SourceRef(
                                file_path=entry.path,
                                start_line=_line_number(content, match.start()),
                            )
                        ],
                    )
                )

            # Fallback: standalone observable() without class wrapper
            if not _MOBX_CLASS_RE.search(content):
                for match in _MOBX_OBSERVABLE_RE.finditer(content):
                    surfaces.append(
                        StateMgmtSurface(
                            name=f"mobx:observable:{entry.path}",
                            store_name="observable",
                            pattern="mobx",
                            source_refs=[
                                SourceRef(
                                    file_path=entry.path,
                                    start_line=_line_number(
                                        content, match.start()
                                    ),
                                )
                            ],
                        )
                    )
                    break  # One per file for standalone observables

    logger.info("state_mgmt_analysis_complete", total_surfaces=len(surfaces))
    return surfaces


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_redux_actions(content: str, slice_offset: int) -> list[str]:
    """Extract action names from a createSlice reducers block.

    Searches for the ``reducers: { ... }`` block following the createSlice
    call and extracts the key names as action identifiers.

    Args:
        content: The full file content.
        slice_offset: Character offset of the createSlice call.

    Returns:
        A list of action name strings.
    """
    # Search the region after the createSlice call for a reducers block.
    region = content[slice_offset : slice_offset + 5000]
    reducer_match = _REDUX_REDUCER_RE.search(region)
    if reducer_match is None:
        return []

    reducers_block = reducer_match.group(1)
    actions: list[str] = []
    for action_match in _REDUX_ACTION_NAME_RE.finditer(reducers_block):
        name = action_match.group(1)
        # Filter out common non-action keywords.
        if name not in {"state", "action", "payload", "return", "const", "let", "var"}:
            actions.append(name)
    return actions


def _extract_redux_selectors(content: str) -> list[str]:
    """Extract named selector functions from file content.

    Looks for exported functions or constants matching the ``select*``
    naming convention commonly used in Redux Toolkit.

    Args:
        content: The full file content.

    Returns:
        A list of selector function names.
    """
    selectors: list[str] = []
    for match in _REDUX_NAMED_SELECTOR_RE.finditer(content):
        name = match.group(1)
        if name not in selectors:
            selectors.append(name)
    return selectors


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
                "state_mgmt_file_too_large",
                path=str(file_path),
                size=len(content),
            )
            return None
        return content
    except OSError:
        logger.debug("state_mgmt_file_read_failed", path=str(file_path))
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
