"""Python API framework detector.

Detects FastAPI and Flask backend projects by examining file inventory
for framework-specific directory structures, file naming conventions,
and project configuration files.
"""

from __future__ import annotations

import re

import structlog

from repo_mirror_kit.harvester.detectors.base import (
    Detector,
    Signal,
    register_detector,
)
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Python project markers
# ---------------------------------------------------------------------------

_PYTHON_PROJECT_MARKERS: tuple[str, ...] = (
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "setup.cfg",
)

# ---------------------------------------------------------------------------
# FastAPI file-path patterns
# ---------------------------------------------------------------------------

_FASTAPI_ROUTERS_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)routers/[^/]+\.py$")
_FASTAPI_SCHEMAS_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)schemas\.py$")
_FASTAPI_DEPS_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)dependencies\.py$")
_FASTAPI_MAIN_PATTERN: re.Pattern[str] = re.compile(r"^(?:src/[^/]+/)?main\.py$")

# ---------------------------------------------------------------------------
# Flask file-path patterns
# ---------------------------------------------------------------------------

_FLASK_TEMPLATES_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)templates/.*\.html$")
_FLASK_VIEWS_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)views\.py$")
_FLASK_BLUEPRINTS_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)blueprints/[^/]+\.py$")
_FLASK_WSGI_PATTERN: re.Pattern[str] = re.compile(r"^wsgi\.py$")
_FLASK_FORMS_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)forms\.py$")
_FLASK_STATIC_PATTERN: re.Pattern[str] = re.compile(
    r"(?:^|/)static/.*\.(css|js|png|jpg|svg|ico|woff2?)$"
)

# ---------------------------------------------------------------------------
# Non-API Python indicators (penalty signals)
# ---------------------------------------------------------------------------

_CLI_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:^|/)cli\.py$"),
    re.compile(r"(?:^|/)__main__\.py$"),
    re.compile(r"(?:^|/)commands/[^/]+\.py$"),
)

# ---------------------------------------------------------------------------
# Confidence weights
# ---------------------------------------------------------------------------

_CONF_PYTHON_PROJECT: float = 0.10

_CONF_FASTAPI_ROUTERS: float = 0.40
_CONF_FASTAPI_SCHEMAS: float = 0.15
_CONF_FASTAPI_DEPS: float = 0.15
_CONF_FASTAPI_MAIN: float = 0.10

_CONF_FLASK_TEMPLATES: float = 0.35
_CONF_FLASK_VIEWS: float = 0.20
_CONF_FLASK_BLUEPRINTS: float = 0.25
_CONF_FLASK_WSGI: float = 0.15
_CONF_FLASK_FORMS: float = 0.10
_CONF_FLASK_STATIC: float = 0.10

_CONF_CLI_PENALTY: float = 0.15


class PythonApiDetector(Detector):
    """Detect Python backend API frameworks.

    Identifies FastAPI and Flask projects by examining file paths in
    the inventory for framework-specific directory structures, file
    naming conventions, and project configuration files.
    """

    def detect(self, inventory: InventoryResult) -> list[Signal]:
        """Run Python API framework detection against the file inventory.

        Args:
            inventory: The scanned file inventory to analyze.

        Returns:
            Signals for detected Python API frameworks.
        """
        files = inventory.files
        if not files:
            return []

        file_paths = [f.path for f in files]
        path_set = set(file_paths)

        if not self._has_python_project(path_set):
            return []

        project_marker = self._get_project_marker(path_set)
        has_cli = self._has_cli_indicators(file_paths)

        signals: list[Signal] = []

        fastapi_signal = self._detect_fastapi(file_paths, project_marker, has_cli)
        if fastapi_signal is not None:
            signals.append(fastapi_signal)

        flask_signal = self._detect_flask(file_paths, project_marker, has_cli)
        if flask_signal is not None:
            signals.append(flask_signal)

        logger.info(
            "python_api_detection_complete",
            signals_found=len(signals),
            frameworks=[s.stack_name for s in signals],
        )
        return signals

    def _has_python_project(self, path_set: set[str]) -> bool:
        """Check if the project has Python project configuration files."""
        return any(marker in path_set for marker in _PYTHON_PROJECT_MARKERS)

    def _get_project_marker(self, path_set: set[str]) -> str:
        """Return the first matching Python project marker."""
        for marker in _PYTHON_PROJECT_MARKERS:
            if marker in path_set:
                return marker
        return ""

    def _has_cli_indicators(self, paths: list[str]) -> bool:
        """Check for CLI-only project indicators."""
        for path in paths:
            for pattern in _CLI_PATTERNS:
                if pattern.search(path):
                    return True
        return False

    def _detect_fastapi(
        self,
        paths: list[str],
        project_marker: str,
        has_cli: bool,
    ) -> Signal | None:
        """Detect FastAPI framework patterns.

        Args:
            paths: All file paths in the inventory.
            project_marker: The Python project marker file found.
            has_cli: Whether CLI indicators were found.

        Returns:
            A Signal for FastAPI if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = [project_marker]

        # Check for routers/ directory with .py files
        for path in paths:
            if _FASTAPI_ROUTERS_PATTERN.search(path):
                confidence += _CONF_FASTAPI_ROUTERS
                evidence.append(path)
                break

        # Check for schemas.py
        for path in paths:
            if _FASTAPI_SCHEMAS_PATTERN.search(path):
                confidence += _CONF_FASTAPI_SCHEMAS
                evidence.append(path)
                break

        # Check for dependencies.py
        for path in paths:
            if _FASTAPI_DEPS_PATTERN.search(path):
                confidence += _CONF_FASTAPI_DEPS
                evidence.append(path)
                break

        # Check for main.py at root or src level
        for path in paths:
            if _FASTAPI_MAIN_PATTERN.search(path):
                confidence += _CONF_FASTAPI_MAIN
                evidence.append(path)
                break

        if confidence == 0.0:
            return None

        # Add base Python project confidence
        confidence += _CONF_PYTHON_PROJECT

        if has_cli:
            confidence = max(0.0, confidence - _CONF_CLI_PENALTY)

        confidence = min(1.0, confidence)

        if confidence <= 0.0:
            return None

        return Signal(
            stack_name="fastapi",
            confidence=round(confidence, 2),
            evidence=evidence,
        )

    def _detect_flask(
        self,
        paths: list[str],
        project_marker: str,
        has_cli: bool,
    ) -> Signal | None:
        """Detect Flask framework patterns.

        Args:
            paths: All file paths in the inventory.
            project_marker: The Python project marker file found.
            has_cli: Whether CLI indicators were found.

        Returns:
            A Signal for Flask if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = [project_marker]

        # Check for templates/ with .html files
        for path in paths:
            if _FLASK_TEMPLATES_PATTERN.search(path):
                confidence += _CONF_FLASK_TEMPLATES
                evidence.append(path)
                break

        # Check for views.py
        for path in paths:
            if _FLASK_VIEWS_PATTERN.search(path):
                confidence += _CONF_FLASK_VIEWS
                evidence.append(path)
                break

        # Check for blueprints/ directory
        for path in paths:
            if _FLASK_BLUEPRINTS_PATTERN.search(path):
                confidence += _CONF_FLASK_BLUEPRINTS
                evidence.append(path)
                break

        # Check for wsgi.py
        for path in paths:
            if _FLASK_WSGI_PATTERN.search(path):
                confidence += _CONF_FLASK_WSGI
                evidence.append(path)
                break

        # Check for forms.py
        for path in paths:
            if _FLASK_FORMS_PATTERN.search(path):
                confidence += _CONF_FLASK_FORMS
                evidence.append(path)
                break

        # Check for static/ directory with web assets
        for path in paths:
            if _FLASK_STATIC_PATTERN.search(path):
                confidence += _CONF_FLASK_STATIC
                evidence.append(path)
                break

        if confidence == 0.0:
            return None

        # Add base Python project confidence
        confidence += _CONF_PYTHON_PROJECT

        if has_cli:
            confidence = max(0.0, confidence - _CONF_CLI_PENALTY)

        confidence = min(1.0, confidence)

        if confidence <= 0.0:
            return None

        return Signal(
            stack_name="flask",
            confidence=round(confidence, 2),
            evidence=evidence,
        )


# Auto-register on import
register_detector(PythonApiDetector())
