"""Unit tests for the Vue.js detector."""

from __future__ import annotations

import pytest

from repo_mirror_kit.harvester.detectors.base import (
    Detector,
    clear_registry,
    get_all_detectors,
    run_detection,
)
from repo_mirror_kit.harvester.detectors.vue import VueDetector
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory(paths: list[str]) -> InventoryResult:
    """Build an InventoryResult from a list of file paths."""
    files = [
        FileEntry(
            path=p,
            size=100,
            extension="." + p.rsplit(".", 1)[-1] if "." in p.rsplit("/", 1)[-1] else "",
            hash="abc123",
            category="source",
        )
        for p in paths
    ]
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=100 * len(files),
        total_skipped=0,
    )


def _make_detector() -> VueDetector:
    """Create a fresh VueDetector instance."""
    return VueDetector()


# ---------------------------------------------------------------------------
# Interface conformance
# ---------------------------------------------------------------------------


class TestVueDetectorInterface:
    """Verify VueDetector implements the Detector interface."""

    def test_is_detector_subclass(self) -> None:
        assert issubclass(VueDetector, Detector)

    def test_instance_is_detector(self) -> None:
        detector = _make_detector()
        assert isinstance(detector, Detector)

    def test_detect_returns_list(self) -> None:
        detector = _make_detector()
        result = detector.detect(_make_inventory([]))
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# .vue file detection
# ---------------------------------------------------------------------------


class TestVueFileDetection:
    """Tests for detecting .vue single-file components."""

    def test_single_vue_file(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["src/App.vue"]))
        vue_signals = [s for s in signals if s.confidence >= 0.5]
        assert len(vue_signals) >= 1
        assert vue_signals[0].stack_name == "vue"
        assert "src/App.vue" in vue_signals[0].evidence

    def test_multiple_vue_files(self) -> None:
        detector = _make_detector()
        paths = [
            "src/App.vue",
            "src/components/Header.vue",
            "src/views/Home.vue",
        ]
        signals = detector.detect(_make_inventory(paths))
        vue_signals = [s for s in signals if s.confidence >= 0.5]
        assert len(vue_signals) >= 1
        evidence = vue_signals[0].evidence
        assert "src/App.vue" in evidence
        assert "src/components/Header.vue" in evidence
        assert "src/views/Home.vue" in evidence

    def test_no_vue_files_no_high_confidence_signal(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["src/app.js"]))
        vue_signals = [s for s in signals if s.confidence >= 0.5]
        assert len(vue_signals) == 0


# ---------------------------------------------------------------------------
# package.json detection
# ---------------------------------------------------------------------------


class TestPackageJsonDetection:
    """Tests for detecting Vue via package.json presence."""

    def test_package_json_provides_signal(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["package.json"]))
        assert len(signals) >= 1
        pkg_signals = [s for s in signals if "package.json" in s.evidence]
        assert len(pkg_signals) == 1
        assert pkg_signals[0].stack_name == "vue"

    def test_package_json_alone_below_threshold(self) -> None:
        """package.json alone should not trigger Vue detection."""
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["package.json"]))
        total_confidence = sum(s.confidence for s in signals)
        assert total_confidence < 0.3  # Below default threshold

    def test_nested_package_json_ignored(self) -> None:
        """Only root package.json counts, not nested ones."""
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["packages/foo/package.json"]))
        pkg_signals = [s for s in signals if "packages/foo/package.json" in s.evidence]
        assert len(pkg_signals) == 0


# ---------------------------------------------------------------------------
# Vite config detection
# ---------------------------------------------------------------------------


class TestViteConfigDetection:
    """Tests for detecting Vite configuration files."""

    @pytest.mark.parametrize(
        "config_file",
        [
            "vite.config.js",
            "vite.config.ts",
            "vite.config.mjs",
            "vite.config.mts",
        ],
    )
    def test_vite_config_variants(self, config_file: str) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory([config_file]))
        vite_signals = [s for s in signals if config_file in s.evidence]
        assert len(vite_signals) == 1
        assert vite_signals[0].stack_name == "vue"

    def test_nested_vite_config_ignored(self) -> None:
        """Vite config in subdirectory should not match."""
        detector = _make_detector()
        signals = detector.detect(_make_inventory(["packages/app/vite.config.ts"]))
        vite_signals = [
            s for s in signals if "packages/app/vite.config.ts" in s.evidence
        ]
        assert len(vite_signals) == 0


# ---------------------------------------------------------------------------
# Vue Router detection
# ---------------------------------------------------------------------------


class TestVueRouterDetection:
    """Tests for detecting Vue Router configuration."""

    @pytest.mark.parametrize(
        "router_path",
        [
            "router/index.js",
            "router/index.ts",
            "src/router/index.js",
            "src/router/index.ts",
        ],
    )
    def test_vue_router_paths(self, router_path: str) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory([router_path]))
        router_signals = [s for s in signals if router_path in s.evidence]
        assert len(router_signals) == 1
        assert router_signals[0].stack_name == "vue"


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


class TestConfidenceScoring:
    """Tests for confidence accumulation across signals."""

    def test_vue_files_have_highest_confidence(self) -> None:
        detector = _make_detector()
        signals = detector.detect(
            _make_inventory(["src/App.vue", "package.json", "vite.config.ts"])
        )
        vue_file_signal = [s for s in signals if "src/App.vue" in s.evidence]
        other_signals = [s for s in signals if "src/App.vue" not in s.evidence]
        assert len(vue_file_signal) == 1
        for other in other_signals:
            assert vue_file_signal[0].confidence > other.confidence

    def test_full_vue_project_high_confidence(self) -> None:
        """A full Vue project should accumulate near-maximum confidence."""
        detector = _make_detector()
        paths = [
            "package.json",
            "vite.config.ts",
            "src/App.vue",
            "src/router/index.ts",
            "src/components/Nav.vue",
        ]
        signals = detector.detect(_make_inventory(paths))
        total = sum(s.confidence for s in signals)
        assert total >= 0.9

    def test_empty_inventory_no_signals(self) -> None:
        detector = _make_detector()
        signals = detector.detect(_make_inventory([]))
        assert signals == []


# ---------------------------------------------------------------------------
# False positive prevention
# ---------------------------------------------------------------------------


class TestFalsePositivePrevention:
    """Ensure non-Vue projects do not trigger Vue detection."""

    def test_react_project_no_detection(self) -> None:
        """A typical React project should not be detected as Vue."""
        detector = _make_detector()
        paths = [
            "package.json",
            "src/App.tsx",
            "src/index.tsx",
            "src/components/Header.tsx",
            "vite.config.ts",
        ]
        signals = detector.detect(_make_inventory(paths))
        total = sum(s.confidence for s in signals)
        assert total < 0.3  # Below default threshold

    def test_svelte_project_no_detection(self) -> None:
        """A typical Svelte project should not be detected as Vue."""
        detector = _make_detector()
        paths = [
            "package.json",
            "src/App.svelte",
            "src/routes/+page.svelte",
            "vite.config.js",
        ]
        signals = detector.detect(_make_inventory(paths))
        total = sum(s.confidence for s in signals)
        assert total < 0.3  # Below default threshold

    def test_plain_node_project_no_detection(self) -> None:
        """A plain Node.js project should not be detected as Vue."""
        detector = _make_detector()
        paths = [
            "package.json",
            "src/index.js",
            "src/server.js",
        ]
        signals = detector.detect(_make_inventory(paths))
        total = sum(s.confidence for s in signals)
        assert total < 0.3


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------


class TestVueDetectorRegistration:
    """Verify the VueDetector registers itself on module import."""

    def setup_method(self) -> None:
        clear_registry()
        # Re-register by creating and registering a new instance.
        # The module-level registration happens at import time.

    def teardown_method(self) -> None:
        clear_registry()

    def test_detector_in_registry_after_import(self) -> None:
        """Importing vue module should register the detector."""
        # Clear and re-import to test registration.
        clear_registry()
        from repo_mirror_kit.harvester.detectors import vue as vue_mod

        vue_mod._create_and_register()
        detectors = get_all_detectors()
        vue_detectors = [d for d in detectors if isinstance(d, VueDetector)]
        assert len(vue_detectors) >= 1

    def test_run_detection_includes_vue(self) -> None:
        """VueDetector should work through run_detection pipeline."""
        clear_registry()
        from repo_mirror_kit.harvester.detectors import vue as vue_mod

        vue_mod._create_and_register()

        inventory = _make_inventory(
            ["package.json", "src/App.vue", "src/components/Nav.vue"]
        )
        profile = run_detection(inventory)
        assert "vue" in profile.stacks
        assert profile.stacks["vue"] >= 0.3
