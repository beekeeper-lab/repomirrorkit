"""React technology stack detector.

Identifies React projects by examining package.json dependencies,
JSX/TSX file presence, React import patterns in source files, and
common React file naming conventions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath

import structlog

from repo_mirror_kit.harvester.detectors.base import Detector, Signal
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

_REACT_IMPORT_RE = re.compile(
    r"import\s+React\b"
    r"|from\s+['\"]react['\"]"
    r"|require\s*\(\s*['\"]react['\"]\s*\)"
    r"|import\s+\{[^}]*\}\s+from\s+['\"]react['\"]"
)

_COMMON_REACT_FILENAMES: frozenset[str] = frozenset(
    {"App.jsx", "App.tsx", "index.jsx", "index.tsx"}
)

_JSX_TSX_EXTENSIONS: frozenset[str] = frozenset({".jsx", ".tsx"})

_IMPORT_SCAN_EXTENSIONS: frozenset[str] = frozenset({".js", ".jsx", ".ts", ".tsx"})

_MAX_EVIDENCE_ITEMS = 10
_MAX_FILES_TO_SCAN = 50


class ReactDetector(Detector):
    """Detect React projects from repository file inventory.

    Detection signals and their confidence weights:

    - ``react`` in package.json dependencies/devDependencies: 0.4
    - ``.jsx``/``.tsx`` files present: 0.3
    - React import patterns in source files: 0.2
    - Common React file patterns (App.jsx, App.tsx, etc.): 0.1

    Multiple signals are additive, capped at 1.0.

    Args:
        workdir: Path to the repository working directory.  Required for
            package.json content analysis and import pattern detection.
            When ``None``, only file-path-based detection is available.
    """

    STACK_NAME = "react"

    _CONFIDENCE_PKG_JSON_REACT = 0.4
    _CONFIDENCE_JSX_TSX_FILES = 0.3
    _CONFIDENCE_IMPORT_PATTERNS = 0.2
    _CONFIDENCE_COMMON_FILES = 0.1

    def __init__(self, workdir: Path | None = None) -> None:
        self._workdir = workdir

    def detect(self, inventory: InventoryResult) -> list[Signal]:
        """Run React detection against the file inventory.

        Args:
            inventory: The scanned file inventory to analyze.

        Returns:
            A list containing a single React signal if detected, or empty.
        """
        evidence: list[str] = []
        confidence = 0.0

        pkg_conf, pkg_ev = self._check_package_json(inventory)
        confidence += pkg_conf
        evidence.extend(pkg_ev)

        jsx_conf, jsx_ev = self._check_jsx_tsx_files(inventory)
        confidence += jsx_conf
        evidence.extend(jsx_ev)

        imp_conf, imp_ev = self._check_import_patterns(inventory)
        confidence += imp_conf
        evidence.extend(imp_ev)

        pat_conf, pat_ev = self._check_common_patterns(inventory)
        confidence += pat_conf
        evidence.extend(pat_ev)

        if confidence <= 0.0:
            return []

        unique_evidence = _deduplicate(evidence)

        signal = Signal(
            stack_name=self.STACK_NAME,
            confidence=min(1.0, confidence),
            evidence=unique_evidence[:_MAX_EVIDENCE_ITEMS],
        )

        logger.info(
            "react_detected",
            confidence=signal.confidence,
            evidence_count=len(signal.evidence),
        )

        return [signal]

    def _check_package_json(
        self, inventory: InventoryResult
    ) -> tuple[float, list[str]]:
        """Check package.json files for a react dependency."""
        if self._workdir is None:
            return 0.0, []

        pkg_files = [
            f for f in inventory.files if PurePosixPath(f.path).name == "package.json"
        ]
        if not pkg_files:
            return 0.0, []

        for entry in pkg_files:
            file_path = self._workdir / entry.path
            try:
                content = file_path.read_text(encoding="utf-8")
                data = json.loads(content)
            except (OSError, json.JSONDecodeError, TypeError):
                logger.debug("package_json_read_failed", path=entry.path)
                continue

            deps = data.get("dependencies", {})
            dev_deps = data.get("devDependencies", {})

            if isinstance(deps, dict) and "react" in deps:
                return self._CONFIDENCE_PKG_JSON_REACT, [entry.path]
            if isinstance(dev_deps, dict) and "react" in dev_deps:
                return self._CONFIDENCE_PKG_JSON_REACT, [entry.path]

        return 0.0, []

    def _check_jsx_tsx_files(
        self, inventory: InventoryResult
    ) -> tuple[float, list[str]]:
        """Check for presence of .jsx/.tsx files."""
        jsx_tsx = [
            f.path for f in inventory.files if f.extension in _JSX_TSX_EXTENSIONS
        ]
        if not jsx_tsx:
            return 0.0, []
        return self._CONFIDENCE_JSX_TSX_FILES, jsx_tsx[:_MAX_EVIDENCE_ITEMS]

    def _check_import_patterns(
        self, inventory: InventoryResult
    ) -> tuple[float, list[str]]:
        """Check source files for React import patterns."""
        if self._workdir is None:
            return 0.0, []

        scannable = [
            f
            for f in inventory.files
            if f.extension in _IMPORT_SCAN_EXTENSIONS and f.category == "source"
        ][:_MAX_FILES_TO_SCAN]

        matches: list[str] = []
        for entry in scannable:
            file_path = self._workdir / entry.path
            try:
                content = file_path.read_text(encoding="utf-8")
            except OSError:
                continue
            if _REACT_IMPORT_RE.search(content):
                matches.append(entry.path)

        if not matches:
            return 0.0, []
        return self._CONFIDENCE_IMPORT_PATTERNS, matches[:_MAX_EVIDENCE_ITEMS]

    def _check_common_patterns(
        self, inventory: InventoryResult
    ) -> tuple[float, list[str]]:
        """Check for common React file naming patterns."""
        matches = [
            f.path
            for f in inventory.files
            if PurePosixPath(f.path).name in _COMMON_REACT_FILENAMES
        ]
        if not matches:
            return 0.0, []
        return self._CONFIDENCE_COMMON_FILES, matches[:_MAX_EVIDENCE_ITEMS]


def _deduplicate(items: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
