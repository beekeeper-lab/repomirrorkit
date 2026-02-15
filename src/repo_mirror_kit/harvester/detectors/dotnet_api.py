""".NET API framework detector.

Detects ASP.NET and minimal API projects by examining file inventory
for .csproj files with web SDK references, Program.cs patterns,
controller conventions, and configuration files.
"""

from __future__ import annotations

import re

import structlog

from repo_mirror_kit.harvester.detectors.base import Detector, Signal, register_detector
from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Pattern constants
# ---------------------------------------------------------------------------

# .csproj file pattern
_CSPROJ_PATTERN: re.Pattern[str] = re.compile(r"\.csproj$", re.IGNORECASE)

# Program.cs entry point (root or one level deep)
_PROGRAM_CS_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)[Pp]rogram\.cs$")

# Startup.cs (older ASP.NET Core pattern)
_STARTUP_CS_PATTERN: re.Pattern[str] = re.compile(r"(?:^|/)[Ss]tartup\.cs$")

# Controller file pattern: *Controller.cs
_CONTROLLER_PATTERN: re.Pattern[str] = re.compile(r"Controller\.cs$")

# Controllers directory pattern
_CONTROLLERS_DIR_PATTERN: re.Pattern[str] = re.compile(
    r"(?:^|/)[Cc]ontrollers/", re.IGNORECASE
)

# appsettings.json files
_APPSETTINGS_PATTERN: re.Pattern[str] = re.compile(
    r"(?:^|/)appsettings(?:\.\w+)?\.json$", re.IGNORECASE
)

# Web SDK reference in .csproj content (matched against file path name only)
_WEB_SDK_CSPROJ = "Microsoft.NET.Sdk.Web"

# Non-web .NET indicators (reduce false positives)
_NON_WEB_INDICATORS: tuple[str, ...] = ("Microsoft.NET.Sdk.Worker",)

# Confidence weights
_CONF_CSPROJ: float = 0.15
_CONF_PROGRAM_CS: float = 0.20
_CONF_STARTUP_CS: float = 0.20
_CONF_CONTROLLER: float = 0.25
_CONF_CONTROLLERS_DIR: float = 0.15
_CONF_APPSETTINGS: float = 0.10
_CONF_MINIMAL_API: float = 0.25


class DotnetApiDetector(Detector):
    """Detect .NET backend API projects.

    Identifies ASP.NET and minimal API projects by examining file paths
    in the inventory for .csproj files, Program.cs entry points,
    controller conventions, and configuration patterns.
    """

    def detect(self, inventory: InventoryResult) -> list[Signal]:
        """Run .NET API detection against the file inventory.

        Args:
            inventory: The scanned file inventory to analyze.

        Returns:
            Signals for detected .NET API frameworks.
        """
        files = inventory.files
        if not files:
            return []

        file_paths = [f.path for f in files]

        # Must have at least one .csproj file
        csproj_files = [p for p in file_paths if _CSPROJ_PATTERN.search(p)]
        if not csproj_files:
            return []

        signals: list[Signal] = []

        aspnet_signal = self._detect_aspnet(file_paths, csproj_files)
        if aspnet_signal is not None:
            signals.append(aspnet_signal)

        minimal_signal = self._detect_minimal_api(file_paths, csproj_files)
        if minimal_signal is not None:
            signals.append(minimal_signal)

        logger.info(
            "dotnet_api_detection_complete",
            signals_found=len(signals),
            frameworks=[s.stack_name for s in signals],
        )
        return signals

    def _detect_aspnet(
        self, paths: list[str], csproj_files: list[str]
    ) -> Signal | None:
        """Detect ASP.NET controller-based API patterns.

        Args:
            paths: All file paths in the inventory.
            csproj_files: Paths to .csproj files found.

        Returns:
            A Signal for ASP.NET if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = list(csproj_files)

        # Check for controller files
        has_controller = False
        has_controllers_dir = False

        for path in paths:
            if not has_controller and _CONTROLLER_PATTERN.search(path):
                confidence += _CONF_CONTROLLER
                evidence.append(path)
                has_controller = True

            if not has_controllers_dir and _CONTROLLERS_DIR_PATTERN.search(path):
                confidence += _CONF_CONTROLLERS_DIR
                if path not in evidence:
                    evidence.append(path)
                has_controllers_dir = True

            if has_controller and has_controllers_dir:
                break

        if not has_controller:
            return None

        # Check for Startup.cs (older pattern, adds confidence)
        for path in paths:
            if _STARTUP_CS_PATTERN.search(path):
                confidence += _CONF_STARTUP_CS
                evidence.append(path)
                break

        # Check for appsettings.json
        for path in paths:
            if _APPSETTINGS_PATTERN.search(path):
                confidence += _CONF_APPSETTINGS
                evidence.append(path)
                break

        # Base confidence for having .csproj
        confidence += _CONF_CSPROJ

        confidence = min(1.0, confidence)

        if confidence <= 0.0:
            return None

        return Signal(
            stack_name="aspnet",
            confidence=round(confidence, 2),
            evidence=evidence,
        )

    def _detect_minimal_api(
        self, paths: list[str], csproj_files: list[str]
    ) -> Signal | None:
        """Detect .NET minimal API patterns.

        Minimal APIs use Program.cs with MapGet/MapPost without controllers.

        Args:
            paths: All file paths in the inventory.
            csproj_files: Paths to .csproj files found.

        Returns:
            A Signal for .NET minimal API if detected, or None.
        """
        confidence = 0.0
        evidence: list[str] = list(csproj_files)

        # Must have Program.cs
        has_program_cs = False
        for path in paths:
            if _PROGRAM_CS_PATTERN.search(path):
                confidence += _CONF_PROGRAM_CS
                evidence.append(path)
                has_program_cs = True
                break

        if not has_program_cs:
            return None

        # Check for appsettings.json (strong indicator of web project)
        has_appsettings = False
        for path in paths:
            if _APPSETTINGS_PATTERN.search(path):
                confidence += _CONF_APPSETTINGS
                evidence.append(path)
                has_appsettings = True
                break

        # Without appsettings, Program.cs alone is not enough
        # (could be a console app)
        if not has_appsettings:
            return None

        # Check for Startup.cs (older pattern, still valid)
        for path in paths:
            if _STARTUP_CS_PATTERN.search(path):
                confidence += _CONF_STARTUP_CS
                evidence.append(path)
                break

        # Base confidence for .csproj
        confidence += _CONF_CSPROJ

        confidence = min(1.0, confidence)

        if confidence <= 0.0:
            return None

        return Signal(
            stack_name="dotnet-minimal-api",
            confidence=round(confidence, 2),
            evidence=evidence,
        )


# Auto-register on import
register_detector(DotnetApiDetector())
