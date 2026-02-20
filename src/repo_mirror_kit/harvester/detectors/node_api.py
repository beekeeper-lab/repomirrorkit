"""Node.js API framework detector.

Detects Express, Fastify, and NestJS backend projects by examining
file inventory for framework-specific dependency manifests, file
naming patterns, and directory structures.
"""

from __future__ import annotations

import re

import structlog

from repo_mirror_kit.harvester.detectors.base import Detector, Signal, register_detector
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Pattern constants
# ---------------------------------------------------------------------------

_PACKAGE_JSON = "package.json"

# Express patterns in file paths
_EXPRESS_ROUTE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:^|/)routes?/.*\.[jt]sx?$"),
    re.compile(r"(?:^|/)middleware/.*\.[jt]sx?$"),
)
_EXPRESS_ENTRY_PATTERN: re.Pattern[str] = re.compile(
    r"(?:^|/)(?:app|server|express)\.[jt]sx?$"
)

# Fastify patterns in file paths
_FASTIFY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:^|/)plugins?/.*\.[jt]sx?$"),
    re.compile(r"(?:^|/)fastify\.[jt]sx?$"),
)

# NestJS patterns in file paths
_NESTJS_FILE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\.module\.ts$"),
    re.compile(r"\.controller\.ts$"),
    re.compile(r"\.service\.ts$"),
    re.compile(r"\.guard\.ts$"),
    re.compile(r"\.interceptor\.ts$"),
    re.compile(r"\.decorator\.ts$"),
)
_NEST_CLI_JSON = "nest-cli.json"

# Frontend-only indicators (reduce confidence for API detection)
_FRONTEND_INDICATORS: tuple[str, ...] = (
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "nuxt.config.js",
    "nuxt.config.ts",
    "gatsby-config.js",
    "gatsby-config.ts",
    "angular.json",
    ".angular-cli.json",
    "vue.config.js",
    "vite.config.ts",
    "vite.config.js",
)

# Confidence weights
_CONF_PACKAGE_JSON: float = 0.15
_CONF_EXPRESS_ENTRY: float = 0.25
_CONF_EXPRESS_ROUTES: float = 0.30
_CONF_FASTIFY_PLUGINS: float = 0.30
_CONF_NESTJS_CLI: float = 0.50
_CONF_NESTJS_MODULE: float = 0.25
_CONF_NESTJS_CONTROLLER: float = 0.20
_CONF_FRONTEND_PENALTY: float = 0.20


class NodeApiDetector(Detector):
    """Detect Node.js backend API frameworks.

    Identifies Express, Fastify, and NestJS projects by examining
    file paths in the inventory for framework-specific naming
    conventions, directory structures, and configuration files.
    """

    def detect(self, inventory: InventoryResult) -> list[Signal]:
        """Run Node API framework detection against the file inventory.

        Args:
            inventory: The scanned file inventory to analyze.

        Returns:
            Signals for detected Node.js API frameworks.
        """
        files = inventory.files
        if not files:
            return []

        file_paths = [f.path for f in files]
        has_package_json = any(self._is_root_package_json(f) for f in files)

        if not has_package_json:
            return []

        signals: list[Signal] = []
        has_frontend = self._has_frontend_indicators(file_paths)

        express_signal = self._detect_express(file_paths, has_frontend)
        if express_signal is not None:
            signals.append(express_signal)

        fastify_signal = self._detect_fastify(file_paths, has_frontend)
        if fastify_signal is not None:
            signals.append(fastify_signal)

        nestjs_signal = self._detect_nestjs(file_paths, has_frontend)
        if nestjs_signal is not None:
            signals.append(nestjs_signal)

        logger.info(
            "node_api_detection_complete",
            signals_found=len(signals),
            frameworks=[s.stack_name for s in signals],
        )
        return signals

    def _is_root_package_json(self, entry: FileEntry) -> bool:
        """Check if file is a root-level package.json."""
        return entry.path == _PACKAGE_JSON

    def _has_frontend_indicators(self, paths: list[str]) -> bool:
        """Check if the project has frontend framework indicators."""
        path_set = set(paths)
        return any(indicator in path_set for indicator in _FRONTEND_INDICATORS)

    def _detect_express(self, paths: list[str], has_frontend: bool) -> Signal | None:
        """Detect Express.js framework patterns.

        Args:
            paths: All file paths in the inventory.
            has_frontend: Whether frontend indicators were found.

        Returns:
            A Signal for Express if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = [_PACKAGE_JSON]

        # Check for Express entry point files
        for path in paths:
            if _EXPRESS_ENTRY_PATTERN.search(path):
                confidence += _CONF_EXPRESS_ENTRY
                evidence.append(path)
                break

        # Check for route/middleware directories
        route_found = False
        for path in paths:
            if route_found:
                break
            for pattern in _EXPRESS_ROUTE_PATTERNS:
                if pattern.search(path):
                    confidence += _CONF_EXPRESS_ROUTES
                    evidence.append(path)
                    route_found = True
                    break

        if confidence == 0.0:
            return None

        # Add base package.json confidence
        confidence += _CONF_PACKAGE_JSON

        if has_frontend:
            confidence = max(0.0, confidence - _CONF_FRONTEND_PENALTY)

        confidence = min(1.0, confidence)

        if confidence <= 0.0:
            return None

        return Signal(
            stack_name="express",
            confidence=round(confidence, 2),
            evidence=evidence,
        )

    def _detect_fastify(self, paths: list[str], has_frontend: bool) -> Signal | None:
        """Detect Fastify framework patterns.

        Args:
            paths: All file paths in the inventory.
            has_frontend: Whether frontend indicators were found.

        Returns:
            A Signal for Fastify if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = [_PACKAGE_JSON]

        # Check for Fastify-specific patterns
        plugin_found = False
        for path in paths:
            if plugin_found:
                break
            for pattern in _FASTIFY_PATTERNS:
                if pattern.search(path):
                    confidence += _CONF_FASTIFY_PLUGINS
                    evidence.append(path)
                    plugin_found = True
                    break

        if confidence == 0.0:
            return None

        confidence += _CONF_PACKAGE_JSON

        if has_frontend:
            confidence = max(0.0, confidence - _CONF_FRONTEND_PENALTY)

        confidence = min(1.0, confidence)

        if confidence <= 0.0:
            return None

        return Signal(
            stack_name="fastify",
            confidence=round(confidence, 2),
            evidence=evidence,
        )

    def _detect_nestjs(self, paths: list[str], has_frontend: bool) -> Signal | None:
        """Detect NestJS framework patterns.

        Args:
            paths: All file paths in the inventory.
            has_frontend: Whether frontend indicators were found.

        Returns:
            A Signal for NestJS if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = [_PACKAGE_JSON]

        path_set = set(paths)

        # nest-cli.json is a very strong signal
        if _NEST_CLI_JSON in path_set:
            confidence += _CONF_NESTJS_CLI
            evidence.append(_NEST_CLI_JSON)

        # Check for NestJS file naming conventions
        has_module = False
        has_controller = False
        for path in paths:
            for pattern in _NESTJS_FILE_PATTERNS:
                if pattern.search(path):
                    if not has_module and path.endswith(".module.ts"):
                        confidence += _CONF_NESTJS_MODULE
                        evidence.append(path)
                        has_module = True
                    elif not has_controller and path.endswith(".controller.ts"):
                        confidence += _CONF_NESTJS_CONTROLLER
                        evidence.append(path)
                        has_controller = True
                    break

        if confidence == 0.0:
            return None

        confidence += _CONF_PACKAGE_JSON

        if has_frontend:
            confidence = max(0.0, confidence - _CONF_FRONTEND_PENALTY)

        confidence = min(1.0, confidence)

        if confidence <= 0.0:
            return None

        return Signal(
            stack_name="nestjs",
            confidence=round(confidence, 2),
            evidence=evidence,
        )


# Auto-register on import
register_detector(NodeApiDetector())
