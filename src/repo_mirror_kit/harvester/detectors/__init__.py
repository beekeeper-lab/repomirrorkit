"""Detector framework for identifying technology stacks in repositories."""

from __future__ import annotations

# BEAN-062: concrete detector modules self-register on import. Importing
# them here guarantees the registry is populated for any pipeline run —
# previously nothing in src/ imported them, so production pipeline runs
# executed with an EMPTY registry and detection always returned no stacks.
from repo_mirror_kit.harvester.detectors import data as _data  # noqa: F401
from repo_mirror_kit.harvester.detectors import dotnet_api as _dotnet_api  # noqa: F401
from repo_mirror_kit.harvester.detectors import nextjs as _nextjs  # noqa: F401
from repo_mirror_kit.harvester.detectors import node_api as _node_api  # noqa: F401
from repo_mirror_kit.harvester.detectors import python_api as _python_api  # noqa: F401
from repo_mirror_kit.harvester.detectors import react as _react  # noqa: F401
from repo_mirror_kit.harvester.detectors import svelte as _svelte  # noqa: F401
from repo_mirror_kit.harvester.detectors import vue as _vue  # noqa: F401
from repo_mirror_kit.harvester.detectors.base import (
    DEFAULT_MIN_CONFIDENCE,
    Detector,
    Signal,
    StackProfile,
    clear_registry,
    get_all_detectors,
    register_detector,
    run_detection,
)

__all__ = [
    "DEFAULT_MIN_CONFIDENCE",
    "Detector",
    "Signal",
    "StackProfile",
    "clear_registry",
    "get_all_detectors",
    "register_detector",
    "run_detection",
]
