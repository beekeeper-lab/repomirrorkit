"""Detector framework for identifying technology stacks in repositories."""

from __future__ import annotations

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
