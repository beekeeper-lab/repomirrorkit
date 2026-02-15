"""Next.js project detector.

Identifies Next.js projects by examining configuration files, directory
structure, and special page conventions.  Produces confidence-scored
signals that combine additively via the detector framework.
"""

from __future__ import annotations

from pathlib import PurePosixPath

import structlog

from repo_mirror_kit.harvester.detectors.base import (
    Detector,
    Signal,
    register_detector,
)
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

STACK_NAME = "nextjs"

# Next.js configuration file names (definitive markers).
_CONFIG_FILENAMES: frozenset[str] = frozenset(
    {"next.config.js", "next.config.mjs", "next.config.ts"}
)

# Special pages that only exist in Next.js (pages router).
_SPECIAL_PAGE_STEMS: frozenset[str] = frozenset({"_app", "_document", "_error"})

# App Router convention files.
_APP_ROUTER_STEMS: frozenset[str] = frozenset(
    {"layout", "page", "loading", "error", "not-found", "template"}
)

# Extensions used for route files.
_ROUTE_EXTENSIONS: frozenset[str] = frozenset({".js", ".jsx", ".ts", ".tsx"})

# Directories where Next.js places pages/app router.
_NEXTJS_ROOTS: tuple[str, ...] = ("", "src/")


class NextjsDetector(Detector):
    """Detect Next.js projects via config files and directory structure.

    Emits signals for:
    * ``next.config.*`` presence (high confidence).
    * Next.js special pages ``_app``, ``_document``, ``_error`` (medium).
    * App Router files ``layout``, ``page`` in ``app/`` (medium).
    * Route-like files under ``pages/`` (low).
    * API routes under ``pages/api/`` or ``app/api/`` (low-medium).
    """

    def detect(self, inventory: InventoryResult) -> list[Signal]:
        """Run Next.js detection against the file inventory.

        Args:
            inventory: The scanned file inventory to analyze.

        Returns:
            A list of signals for the ``nextjs`` stack.  May be empty.
        """
        file_paths: set[str] = {f.path for f in inventory.files}
        signals: list[Signal] = []

        config_signal = self._check_config_files(file_paths)
        if config_signal:
            signals.append(config_signal)

        special_signal = self._check_special_pages(file_paths)
        if special_signal:
            signals.append(special_signal)

        app_router_signal = self._check_app_router(file_paths)
        if app_router_signal:
            signals.append(app_router_signal)

        pages_signal = self._check_pages_directory(file_paths)
        if pages_signal:
            signals.append(pages_signal)

        api_signal = self._check_api_routes(file_paths)
        if api_signal:
            signals.append(api_signal)

        if signals:
            logger.info(
                "nextjs_detection_complete",
                signal_count=len(signals),
                total_confidence=min(1.0, sum(s.confidence for s in signals)),
            )

        return signals

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_config_files(self, paths: set[str]) -> Signal | None:
        """Check for ``next.config.*`` at the repository root.

        This is the strongest single indicator of a Next.js project.
        """
        evidence: list[str] = [p for p in sorted(paths) if p in _CONFIG_FILENAMES]
        if evidence:
            return Signal(
                stack_name=STACK_NAME,
                confidence=0.6,
                evidence=evidence,
            )
        return None

    def _check_special_pages(self, paths: set[str]) -> Signal | None:
        """Check for Next.js special pages (``_app``, ``_document``, ``_error``).

        These files are unique to Next.js's pages router and provide
        a strong signal even without ``next.config.*``.
        """
        evidence: list[str] = []
        for root in _NEXTJS_ROOTS:
            for stem in _SPECIAL_PAGE_STEMS:
                for ext in _ROUTE_EXTENSIONS:
                    candidate = f"{root}pages/{stem}{ext}"
                    if candidate in paths:
                        evidence.append(candidate)
        if evidence:
            return Signal(
                stack_name=STACK_NAME,
                confidence=0.3,
                evidence=sorted(evidence),
            )
        return None

    def _check_app_router(self, paths: set[str]) -> Signal | None:
        """Check for Next.js App Router files (``layout``, ``page``).

        The presence of ``app/layout.*`` and ``app/page.*`` at the
        repository root (or under ``src/``) is characteristic of
        Next.js 13+ App Router.
        """
        evidence: list[str] = []
        for root in _NEXTJS_ROOTS:
            for stem in _APP_ROUTER_STEMS:
                for ext in _ROUTE_EXTENSIONS:
                    candidate = f"{root}app/{stem}{ext}"
                    if candidate in paths:
                        evidence.append(candidate)
        if evidence:
            return Signal(
                stack_name=STACK_NAME,
                confidence=0.3,
                evidence=sorted(evidence),
            )
        return None

    def _check_pages_directory(self, paths: set[str]) -> Signal | None:
        """Check for route-like files under ``pages/``.

        Looks for ``.tsx``, ``.jsx``, ``.ts``, ``.js`` files directly
        under ``pages/`` (excluding special pages already counted).
        A weaker signal since other frameworks also use ``pages/``.
        """
        evidence: list[str] = []
        for p in sorted(paths):
            parts = PurePosixPath(p).parts
            if len(parts) < 2:
                continue
            # Match pages/ at root or src/pages/
            is_pages_root = parts[0] == "pages" or (
                len(parts) >= 3 and parts[0] == "src" and parts[1] == "pages"
            )
            if not is_pages_root:
                continue
            ext = PurePosixPath(p).suffix
            if ext not in _ROUTE_EXTENSIONS:
                continue
            stem = PurePosixPath(p).stem
            # Skip special pages (already handled by _check_special_pages)
            if stem in _SPECIAL_PAGE_STEMS:
                continue
            # Skip api/ routes (handled by _check_api_routes)
            if "api" in parts:
                continue
            evidence.append(p)

        if evidence:
            return Signal(
                stack_name=STACK_NAME,
                confidence=0.2,
                evidence=evidence[:10],
            )
        return None

    def _check_api_routes(self, paths: set[str]) -> Signal | None:
        """Check for API routes under ``pages/api/`` or ``app/api/``.

        The presence of API route files is a medium-strength signal
        that the project uses Next.js's built-in API routing.
        """
        evidence: list[str] = []
        for p in sorted(paths):
            parts = PurePosixPath(p).parts
            if len(parts) < 3:
                continue
            ext = PurePosixPath(p).suffix
            if ext not in _ROUTE_EXTENSIONS:
                continue
            # Match pages/api/* or app/api/* (with optional src/ prefix)
            if parts[0] in ("pages", "app") and parts[1] == "api":
                evidence.append(p)
            elif (
                len(parts) >= 4
                and parts[0] == "src"
                and parts[1] in ("pages", "app")
                and parts[2] == "api"
            ):
                evidence.append(p)

        if evidence:
            return Signal(
                stack_name=STACK_NAME,
                confidence=0.15,
                evidence=evidence[:10],
            )
        return None


# Register the detector at import time.
register_detector(NextjsDetector())
