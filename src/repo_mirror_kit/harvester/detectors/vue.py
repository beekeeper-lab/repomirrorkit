"""Vue.js project detector.

Identifies Vue.js projects by examining file inventory for Vue-specific
signals: ``.vue`` single-file components, Vite configuration, Vue Router
conventions, and ``package.json`` presence.
"""

from __future__ import annotations

from repo_mirror_kit.harvester.detectors.base import Detector, Signal, register_detector
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# Confidence weights for each signal type.
_VUE_FILE_CONFIDENCE: float = 0.7
_VITE_CONFIG_CONFIDENCE: float = 0.1
_VUE_ROUTER_CONFIDENCE: float = 0.1
_PACKAGE_JSON_CONFIDENCE: float = 0.05

_STACK_NAME: str = "vue"

_VITE_CONFIG_STEMS: frozenset[str] = frozenset(
    {
        "vite.config.js",
        "vite.config.ts",
        "vite.config.mjs",
        "vite.config.mts",
    }
)

_VUE_ROUTER_PATHS: frozenset[str] = frozenset(
    {
        "router/index.js",
        "router/index.ts",
        "src/router/index.js",
        "src/router/index.ts",
    }
)


class VueDetector(Detector):
    """Detect Vue.js projects from file inventory signals.

    Detection relies on four signal types, each contributing independent
    confidence:

    - ``.vue`` files (single-file components) — strongest signal, unique
      to Vue.
    - ``vite.config.*`` — supporting signal for modern Vue tooling.
    - ``router/index.{js,ts}`` — conventional Vue Router entry point.
    - ``package.json`` — weak prerequisite indicating a JS/TS project.

    Confidence values are tuned so that ``.vue`` files alone exceed the
    default detection threshold (0.3), while non-Vue JS projects (React,
    Svelte) that share ``package.json`` and Vite config stay below it.
    """

    def detect(self, inventory: InventoryResult) -> list[Signal]:
        """Scan inventory for Vue.js indicators.

        Args:
            inventory: The scanned file inventory to analyze.

        Returns:
            A list of signals. Empty if no Vue indicators found.
        """
        signals: list[Signal] = []

        vue_signal = self._check_vue_files(inventory.files)
        if vue_signal is not None:
            signals.append(vue_signal)

        vite_signal = self._check_vite_config(inventory.files)
        if vite_signal is not None:
            signals.append(vite_signal)

        router_signal = self._check_vue_router(inventory.files)
        if router_signal is not None:
            signals.append(router_signal)

        pkg_signal = self._check_package_json(inventory.files)
        if pkg_signal is not None:
            signals.append(pkg_signal)

        return signals

    def _check_vue_files(self, files: list[FileEntry]) -> Signal | None:
        """Check for .vue single-file components."""
        evidence = [f.path for f in files if f.extension == ".vue"]
        if not evidence:
            return None
        return Signal(
            stack_name=_STACK_NAME,
            confidence=_VUE_FILE_CONFIDENCE,
            evidence=evidence,
        )

    def _check_vite_config(self, files: list[FileEntry]) -> Signal | None:
        """Check for Vite configuration files."""
        evidence = [f.path for f in files if _is_vite_config(f.path)]
        if not evidence:
            return None
        return Signal(
            stack_name=_STACK_NAME,
            confidence=_VITE_CONFIG_CONFIDENCE,
            evidence=evidence,
        )

    def _check_vue_router(self, files: list[FileEntry]) -> Signal | None:
        """Check for Vue Router configuration files."""
        evidence = [f.path for f in files if f.path in _VUE_ROUTER_PATHS]
        if not evidence:
            return None
        return Signal(
            stack_name=_STACK_NAME,
            confidence=_VUE_ROUTER_CONFIDENCE,
            evidence=evidence,
        )

    def _check_package_json(self, files: list[FileEntry]) -> Signal | None:
        """Check for package.json as a JS ecosystem indicator."""
        evidence = [f.path for f in files if _is_root_package_json(f.path)]
        if not evidence:
            return None
        return Signal(
            stack_name=_STACK_NAME,
            confidence=_PACKAGE_JSON_CONFIDENCE,
            evidence=evidence,
        )


def _is_vite_config(path: str) -> bool:
    """Check if a path is a root-level Vite config file."""
    # Match only root-level config (no directory separators before filename).
    parts = path.split("/")
    return len(parts) == 1 and path in _VITE_CONFIG_STEMS


def _is_root_package_json(path: str) -> bool:
    """Check if a path is the root package.json."""
    return path == "package.json"


def _create_and_register() -> None:
    """Create and register the Vue detector instance."""
    register_detector(VueDetector())


_create_and_register()
