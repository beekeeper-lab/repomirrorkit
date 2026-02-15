"""Detector framework: base class, signal model, registry, and aggregation.

Provides the pluggable detector architecture for identifying technology
stacks in a repository.  Individual detectors implement the ``Detector``
ABC, register themselves via ``register_detector()``, and contribute
``Signal`` instances that are aggregated into a ``StackProfile``.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field

import structlog

from repo_mirror_kit.harvester.inventory import InventoryResult

logger = structlog.get_logger()

DEFAULT_MIN_CONFIDENCE: float = 0.3
"""Minimum combined confidence for a stack to appear in the profile."""


@dataclass
class Signal:
    """A single detection signal for a technology stack.

    Args:
        stack_name: Identifier for the detected stack (e.g. "react", "fastapi").
        confidence: Confidence level between 0.0 and 1.0 inclusive.
        evidence: Repository-relative file paths that triggered detection.
    """

    stack_name: str
    confidence: float
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            msg = f"confidence must be between 0.0 and 1.0, got {self.confidence}"
            raise ValueError(msg)


@dataclass
class StackProfile:
    """Aggregated detection results for a repository.

    Args:
        stacks: Mapping of stack name to combined confidence score.
        evidence: Mapping of stack name to list of evidence file paths.
        signals: All raw signals collected from detectors.
    """

    stacks: dict[str, float] = field(default_factory=dict)
    evidence: dict[str, list[str]] = field(default_factory=dict)
    signals: list[Signal] = field(default_factory=list)


class Detector(abc.ABC):
    """Abstract base class for technology-stack detectors.

    Subclasses implement ``detect()`` to examine the file inventory and
    return zero or more ``Signal`` instances indicating which stacks were
    found and with what confidence.
    """

    @abc.abstractmethod
    def detect(self, inventory: InventoryResult) -> list[Signal]:
        """Run detection against a file inventory.

        Args:
            inventory: The scanned file inventory to analyze.

        Returns:
            A list of signals for detected stacks. May be empty.
        """


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_registry: list[Detector] = []


def register_detector(detector: Detector) -> None:
    """Register a detector instance for use in detection runs.

    Args:
        detector: A concrete ``Detector`` implementation to register.
    """
    _registry.append(detector)
    logger.debug("detector_registered", detector=type(detector).__name__)


def get_all_detectors() -> list[Detector]:
    """Return all currently registered detectors.

    Returns:
        A list of registered ``Detector`` instances.
    """
    return list(_registry)


def clear_registry() -> None:
    """Remove all registered detectors.

    Intended for test isolation. Production code should not normally
    call this.
    """
    _registry.clear()


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def run_detection(
    inventory: InventoryResult,
    *,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> StackProfile:
    """Run all registered detectors and aggregate results.

    Each detector produces zero or more ``Signal`` instances. Signals
    for the same stack name are combined by summing confidences (capped
    at 1.0). Stacks whose combined confidence falls below
    ``min_confidence`` are excluded from the final profile.

    Args:
        inventory: The file inventory to analyze.
        min_confidence: Minimum combined confidence to include a stack.

    Returns:
        A ``StackProfile`` with detected stacks above the threshold.
    """
    all_signals: list[Signal] = []

    for detector in _registry:
        name = type(detector).__name__
        logger.info("detector_running", detector=name)
        signals = detector.detect(inventory)
        logger.info(
            "detector_complete",
            detector=name,
            signal_count=len(signals),
        )
        all_signals.extend(signals)

    # Aggregate by stack name
    combined_confidence: dict[str, float] = {}
    combined_evidence: dict[str, list[str]] = {}

    for signal in all_signals:
        stack = signal.stack_name
        prev = combined_confidence.get(stack, 0.0)
        combined_confidence[stack] = min(1.0, prev + signal.confidence)

        if stack not in combined_evidence:
            combined_evidence[stack] = []
        for path in signal.evidence:
            if path not in combined_evidence[stack]:
                combined_evidence[stack].append(path)

    # Filter by threshold
    filtered_stacks: dict[str, float] = {}
    filtered_evidence: dict[str, list[str]] = {}

    for stack, confidence in combined_confidence.items():
        if confidence >= min_confidence:
            filtered_stacks[stack] = confidence
            filtered_evidence[stack] = combined_evidence.get(stack, [])

    logger.info(
        "detection_complete",
        total_signals=len(all_signals),
        stacks_detected=len(filtered_stacks),
        stacks=list(filtered_stacks.keys()),
    )

    return StackProfile(
        stacks=filtered_stacks,
        evidence=filtered_evidence,
        signals=all_signals,
    )
