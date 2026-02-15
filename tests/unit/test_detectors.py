"""Unit tests for the detector framework."""

from __future__ import annotations

import pytest

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
from repo_mirror_kit.harvester.inventory import InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_inventory() -> InventoryResult:
    """Return an empty inventory for testing."""
    return InventoryResult(
        files=[],
        skipped=[],
        total_files=0,
        total_size=0,
        total_skipped=0,
    )


class _StubDetector(Detector):
    """A detector that returns pre-configured signals."""

    def __init__(self, signals: list[Signal] | None = None) -> None:
        self._signals = signals or []

    def detect(self, inventory: InventoryResult) -> list[Signal]:
        return list(self._signals)


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------


class TestSignal:
    """Tests for the Signal dataclass."""

    def test_create_valid_signal(self) -> None:
        signal = Signal(
            stack_name="react",
            confidence=0.8,
            evidence=["package.json"],
        )
        assert signal.stack_name == "react"
        assert signal.confidence == 0.8
        assert signal.evidence == ["package.json"]

    def test_default_evidence_is_empty_list(self) -> None:
        signal = Signal(stack_name="python", confidence=0.5)
        assert signal.evidence == []

    def test_confidence_zero_is_valid(self) -> None:
        signal = Signal(stack_name="go", confidence=0.0)
        assert signal.confidence == 0.0

    def test_confidence_one_is_valid(self) -> None:
        signal = Signal(stack_name="rust", confidence=1.0)
        assert signal.confidence == 1.0

    def test_confidence_below_zero_raises(self) -> None:
        with pytest.raises(ValueError, match=r"between 0\.0 and 1\.0"):
            Signal(stack_name="bad", confidence=-0.1)

    def test_confidence_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match=r"between 0\.0 and 1\.0"):
            Signal(stack_name="bad", confidence=1.1)

    def test_multiple_evidence_paths(self) -> None:
        signal = Signal(
            stack_name="nextjs",
            confidence=0.9,
            evidence=["next.config.js", "pages/index.tsx"],
        )
        assert len(signal.evidence) == 2


# ---------------------------------------------------------------------------
# StackProfile dataclass
# ---------------------------------------------------------------------------


class TestStackProfile:
    """Tests for the StackProfile dataclass."""

    def test_empty_profile(self) -> None:
        profile = StackProfile()
        assert profile.stacks == {}
        assert profile.evidence == {}
        assert profile.signals == []

    def test_profile_with_data(self) -> None:
        profile = StackProfile(
            stacks={"react": 0.9},
            evidence={"react": ["package.json"]},
            signals=[
                Signal(stack_name="react", confidence=0.9, evidence=["package.json"])
            ],
        )
        assert profile.stacks["react"] == 0.9
        assert "package.json" in profile.evidence["react"]
        assert len(profile.signals) == 1


# ---------------------------------------------------------------------------
# Detector ABC
# ---------------------------------------------------------------------------


class TestDetectorABC:
    """Tests for the Detector abstract base class."""

    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError):
            Detector()  # type: ignore[abstract]

    def test_subclass_must_implement_detect(self) -> None:
        class IncompleteDetector(Detector):
            pass

        with pytest.raises(TypeError):
            IncompleteDetector()  # type: ignore[abstract]

    def test_concrete_subclass_works(self) -> None:
        detector = _StubDetector()
        result = detector.detect(_empty_inventory())
        assert result == []


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    """Tests for detector registration and retrieval."""

    def setup_method(self) -> None:
        clear_registry()

    def teardown_method(self) -> None:
        clear_registry()

    def test_empty_registry(self) -> None:
        assert get_all_detectors() == []

    def test_register_single_detector(self) -> None:
        detector = _StubDetector()
        register_detector(detector)
        assert get_all_detectors() == [detector]

    def test_register_multiple_detectors(self) -> None:
        d1 = _StubDetector()
        d2 = _StubDetector()
        register_detector(d1)
        register_detector(d2)
        detectors = get_all_detectors()
        assert len(detectors) == 2
        assert d1 in detectors
        assert d2 in detectors

    def test_get_all_returns_copy(self) -> None:
        detector = _StubDetector()
        register_detector(detector)
        result = get_all_detectors()
        result.clear()
        assert len(get_all_detectors()) == 1

    def test_clear_registry(self) -> None:
        register_detector(_StubDetector())
        register_detector(_StubDetector())
        clear_registry()
        assert get_all_detectors() == []


# ---------------------------------------------------------------------------
# run_detection
# ---------------------------------------------------------------------------


class TestRunDetection:
    """Tests for the run_detection aggregation function."""

    def setup_method(self) -> None:
        clear_registry()

    def teardown_method(self) -> None:
        clear_registry()

    def test_empty_registry_returns_empty_profile(self) -> None:
        profile = run_detection(_empty_inventory())
        assert profile.stacks == {}
        assert profile.evidence == {}
        assert profile.signals == []

    def test_single_detector_single_signal(self) -> None:
        register_detector(
            _StubDetector(
                [Signal(stack_name="python", confidence=0.9, evidence=["setup.py"])]
            )
        )
        profile = run_detection(_empty_inventory())
        assert "python" in profile.stacks
        assert profile.stacks["python"] == 0.9
        assert profile.evidence["python"] == ["setup.py"]

    def test_single_detector_multiple_signals(self) -> None:
        register_detector(
            _StubDetector(
                [
                    Signal(stack_name="python", confidence=0.7, evidence=["setup.py"]),
                    Signal(
                        stack_name="react", confidence=0.8, evidence=["package.json"]
                    ),
                ]
            )
        )
        profile = run_detection(_empty_inventory())
        assert len(profile.stacks) == 2
        assert profile.stacks["python"] == 0.7
        assert profile.stacks["react"] == 0.8

    def test_multiple_detectors_same_stack_combine_confidence(self) -> None:
        register_detector(
            _StubDetector(
                [Signal(stack_name="react", confidence=0.4, evidence=["package.json"])]
            )
        )
        register_detector(
            _StubDetector(
                [Signal(stack_name="react", confidence=0.3, evidence=["src/App.tsx"])]
            )
        )
        profile = run_detection(_empty_inventory())
        assert profile.stacks["react"] == pytest.approx(0.7)
        assert "package.json" in profile.evidence["react"]
        assert "src/App.tsx" in profile.evidence["react"]

    def test_combined_confidence_capped_at_one(self) -> None:
        register_detector(
            _StubDetector(
                [Signal(stack_name="python", confidence=0.8, evidence=["a.py"])]
            )
        )
        register_detector(
            _StubDetector(
                [Signal(stack_name="python", confidence=0.6, evidence=["b.py"])]
            )
        )
        profile = run_detection(_empty_inventory())
        assert profile.stacks["python"] == 1.0

    def test_below_threshold_excluded(self) -> None:
        register_detector(
            _StubDetector(
                [Signal(stack_name="obscure", confidence=0.2, evidence=["x.txt"])]
            )
        )
        profile = run_detection(_empty_inventory())
        assert "obscure" not in profile.stacks
        assert "obscure" not in profile.evidence

    def test_at_threshold_included(self) -> None:
        register_detector(
            _StubDetector(
                [
                    Signal(
                        stack_name="edge",
                        confidence=DEFAULT_MIN_CONFIDENCE,
                        evidence=["edge.cfg"],
                    )
                ]
            )
        )
        profile = run_detection(_empty_inventory())
        assert "edge" in profile.stacks

    def test_custom_min_confidence(self) -> None:
        register_detector(
            _StubDetector(
                [Signal(stack_name="low", confidence=0.1, evidence=["l.txt"])]
            )
        )
        # With default threshold 0.3, excluded
        profile_default = run_detection(_empty_inventory())
        assert "low" not in profile_default.stacks

        # With lower threshold, included
        profile_low = run_detection(_empty_inventory(), min_confidence=0.05)
        assert "low" in profile_low.stacks

    def test_signals_preserved_in_profile(self) -> None:
        signals = [
            Signal(stack_name="python", confidence=0.5, evidence=["a.py"]),
            Signal(stack_name="react", confidence=0.1, evidence=["b.js"]),
        ]
        register_detector(_StubDetector(signals))
        profile = run_detection(_empty_inventory())
        assert len(profile.signals) == 2

    def test_duplicate_evidence_deduplicated(self) -> None:
        register_detector(
            _StubDetector(
                [Signal(stack_name="go", confidence=0.5, evidence=["go.mod"])]
            )
        )
        register_detector(
            _StubDetector(
                [Signal(stack_name="go", confidence=0.3, evidence=["go.mod"])]
            )
        )
        profile = run_detection(_empty_inventory())
        assert profile.evidence["go"].count("go.mod") == 1

    def test_detector_returning_no_signals(self) -> None:
        register_detector(_StubDetector([]))
        register_detector(
            _StubDetector(
                [Signal(stack_name="rust", confidence=0.9, evidence=["Cargo.toml"])]
            )
        )
        profile = run_detection(_empty_inventory())
        assert len(profile.stacks) == 1
        assert "rust" in profile.stacks
