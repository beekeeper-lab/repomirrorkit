"""Svelte and SvelteKit project detector.

Identifies Svelte projects by examining file extensions, configuration
files, and directory structure patterns in the repository inventory.
"""

from __future__ import annotations

from pathlib import PurePosixPath

import structlog

from repo_mirror_kit.harvester.detectors.base import Detector, Signal, register_detector
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

_SVELTE_CONFIGS: frozenset[str] = frozenset({"svelte.config.js", "svelte.config.ts"})

_SVELTEKIT_ROUTE_FILES: frozenset[str] = frozenset(
    {
        "+page.svelte",
        "+layout.svelte",
        "+error.svelte",
        "+page.server.ts",
        "+page.server.js",
        "+server.ts",
        "+server.js",
    }
)

_MAX_EVIDENCE_FILES: int = 5


class SvelteDetector(Detector):
    """Detect Svelte and SvelteKit projects from file inventory.

    Detection strategy:
    - ``.svelte`` files indicate a Svelte project (high confidence).
    - ``svelte.config.js`` or ``svelte.config.ts`` indicates Svelte and
      SvelteKit usage.
    - SvelteKit file-based routing patterns (``+page.svelte`` in a
      ``routes/`` directory) indicate SvelteKit.
    - ``package.json`` is included as supporting evidence when present.
    """

    def detect(self, inventory: InventoryResult) -> list[Signal]:
        """Scan inventory for Svelte and SvelteKit indicators.

        Args:
            inventory: The scanned file inventory to analyze.

        Returns:
            A list of signals for detected Svelte/SvelteKit stacks.
        """
        svelte_files: list[str] = []
        svelte_config: str | None = None
        has_package_json = False
        sveltekit_routes: list[str] = []

        for entry in inventory.files:
            filename = PurePosixPath(entry.path).name

            if entry.extension == ".svelte":
                svelte_files.append(entry.path)

            if filename in _SVELTE_CONFIGS:
                svelte_config = entry.path

            if filename == "package.json" and "/" not in entry.path:
                has_package_json = True

            if filename in _SVELTEKIT_ROUTE_FILES:
                parts = PurePosixPath(entry.path).parts
                if "routes" in parts:
                    sveltekit_routes.append(entry.path)

        signals = self._build_svelte_signals(
            svelte_files, svelte_config, has_package_json, sveltekit_routes
        )

        logger.debug(
            "svelte_detection_complete",
            svelte_file_count=len(svelte_files),
            has_config=svelte_config is not None,
            sveltekit_route_count=len(sveltekit_routes),
            signal_count=len(signals),
        )

        return signals

    def _build_svelte_signals(
        self,
        svelte_files: list[str],
        svelte_config: str | None,
        has_package_json: bool,
        sveltekit_routes: list[str],
    ) -> list[Signal]:
        """Build detection signals from collected evidence.

        Args:
            svelte_files: Paths of discovered ``.svelte`` files.
            svelte_config: Path of the Svelte config file, if found.
            has_package_json: Whether a root ``package.json`` was found.
            sveltekit_routes: Paths of SvelteKit routing files.

        Returns:
            Signals for the ``svelte`` and ``sveltekit`` stacks.
        """
        signals: list[Signal] = []

        has_svelte_evidence = bool(svelte_files) or svelte_config is not None

        if has_svelte_evidence:
            signals.append(
                self._svelte_signal(svelte_files, svelte_config, has_package_json)
            )

        has_sveltekit_evidence = svelte_config is not None or bool(sveltekit_routes)
        if has_sveltekit_evidence:
            signals.append(self._sveltekit_signal(svelte_config, sveltekit_routes))

        return signals

    def _svelte_signal(
        self,
        svelte_files: list[str],
        svelte_config: str | None,
        has_package_json: bool,
    ) -> Signal:
        """Build the main Svelte stack signal.

        Args:
            svelte_files: Paths of ``.svelte`` files.
            svelte_config: Path of the config file, if found.
            has_package_json: Whether ``package.json`` exists at root.

        Returns:
            A Signal for the ``svelte`` stack.
        """
        confidence = 0.0
        evidence: list[str] = []

        if svelte_files:
            confidence += 0.8
            evidence.extend(svelte_files[:_MAX_EVIDENCE_FILES])

        if svelte_config is not None:
            confidence += 0.15
            if svelte_config not in evidence:
                evidence.append(svelte_config)

        if has_package_json:
            evidence.append("package.json")

        return Signal(
            stack_name="svelte",
            confidence=min(1.0, confidence),
            evidence=evidence,
        )

    def _sveltekit_signal(
        self,
        svelte_config: str | None,
        sveltekit_routes: list[str],
    ) -> Signal:
        """Build the SvelteKit stack signal.

        Args:
            svelte_config: Path of the config file, if found.
            sveltekit_routes: Paths of SvelteKit routing files.

        Returns:
            A Signal for the ``sveltekit`` stack.
        """
        confidence = 0.0
        evidence: list[str] = []

        if svelte_config is not None:
            confidence += 0.6
            evidence.append(svelte_config)

        if sveltekit_routes:
            confidence += 0.3
            evidence.extend(sveltekit_routes[:_MAX_EVIDENCE_FILES])

        return Signal(
            stack_name="sveltekit",
            confidence=min(1.0, confidence),
            evidence=evidence,
        )


_detector = SvelteDetector()
register_detector(_detector)
