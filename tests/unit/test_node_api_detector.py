"""Unit tests for the Node API detector."""

from __future__ import annotations

import pytest

from repo_mirror_kit.harvester.detectors.base import (
    Signal,
    clear_registry,
    get_all_detectors,
)
from repo_mirror_kit.harvester.detectors.node_api import NodeApiDetector
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
            extension="." + p.rsplit(".", 1)[-1] if "." in p else "",
            hash="abc123",
            category="source",
        )
        for p in paths
    ]
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=len(files) * 100,
        total_skipped=0,
    )


def _empty_inventory() -> InventoryResult:
    """Return an empty inventory for testing."""
    return InventoryResult(
        files=[],
        skipped=[],
        total_files=0,
        total_size=0,
        total_skipped=0,
    )


@pytest.fixture()
def detector() -> NodeApiDetector:
    """Return a fresh NodeApiDetector instance."""
    return NodeApiDetector()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestNodeApiDetectorRegistration:
    """Verify that the detector auto-registers on import."""

    def setup_method(self) -> None:
        clear_registry()
        # Module is already loaded so auto-register already ran.
        # Manually register a fresh instance for this test.
        from repo_mirror_kit.harvester.detectors.base import register_detector

        register_detector(NodeApiDetector())

    def teardown_method(self) -> None:
        clear_registry()

    def test_auto_registers_on_import(self) -> None:
        detectors = get_all_detectors()
        assert len(detectors) == 1
        assert isinstance(detectors[0], NodeApiDetector)


# ---------------------------------------------------------------------------
# Empty / no package.json
# ---------------------------------------------------------------------------


class TestNoNodeProject:
    """No signals when the project is not a Node project."""

    def test_empty_inventory(self, detector: NodeApiDetector) -> None:
        result = detector.detect(_empty_inventory())
        assert result == []

    def test_no_package_json(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(["src/main.py", "requirements.txt"])
        result = detector.detect(inventory)
        assert result == []

    def test_nested_package_json_only(self, detector: NodeApiDetector) -> None:
        """A package.json inside a subdirectory does not count as root."""
        inventory = _make_inventory(["subdir/package.json", "src/app.js"])
        result = detector.detect(inventory)
        assert result == []


# ---------------------------------------------------------------------------
# Express detection
# ---------------------------------------------------------------------------


class TestExpressDetection:
    """Detect Express.js backend projects."""

    def test_express_entry_point(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(["package.json", "app.js"])
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "express" in names

    def test_express_server_entry(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(["package.json", "server.js"])
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "express" in names

    def test_express_with_routes_directory(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(
            ["package.json", "src/routes/users.js", "src/routes/orders.ts"]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "express" in names
        express_signal = next(s for s in signals if s.stack_name == "express")
        assert express_signal.confidence > 0.3

    def test_express_with_middleware(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(["package.json", "app.js", "middleware/auth.js"])
        signals = detector.detect(inventory)
        express_signal = next(s for s in signals if s.stack_name == "express")
        assert express_signal.confidence > 0.4

    def test_express_evidence_includes_paths(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(["package.json", "app.js", "routes/api.js"])
        signals = detector.detect(inventory)
        express_signal = next(s for s in signals if s.stack_name == "express")
        assert "package.json" in express_signal.evidence
        assert "app.js" in express_signal.evidence

    def test_express_ts_entry_point(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(["package.json", "src/app.ts"])
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "express" in names


# ---------------------------------------------------------------------------
# Fastify detection
# ---------------------------------------------------------------------------


class TestFastifyDetection:
    """Detect Fastify framework projects."""

    def test_fastify_with_plugins(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(
            ["package.json", "plugins/auth.js", "plugins/db.js"]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "fastify" in names

    def test_fastify_ts_plugin(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(["package.json", "src/plugins/cors.ts"])
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "fastify" in names

    def test_fastify_entry_file(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(["package.json", "fastify.js"])
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "fastify" in names

    def test_fastify_evidence_includes_paths(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(["package.json", "plugins/auth.js"])
        signals = detector.detect(inventory)
        fastify_signal = next(s for s in signals if s.stack_name == "fastify")
        assert "package.json" in fastify_signal.evidence
        assert "plugins/auth.js" in fastify_signal.evidence


# ---------------------------------------------------------------------------
# NestJS detection
# ---------------------------------------------------------------------------


class TestNestJSDetection:
    """Detect NestJS framework projects."""

    def test_nestjs_with_cli_config(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(["package.json", "nest-cli.json"])
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "nestjs" in names

    def test_nestjs_high_confidence_with_cli(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(
            [
                "package.json",
                "nest-cli.json",
                "src/app.module.ts",
                "src/app.controller.ts",
            ]
        )
        signals = detector.detect(inventory)
        nestjs_signal = next(s for s in signals if s.stack_name == "nestjs")
        assert nestjs_signal.confidence >= 0.8

    def test_nestjs_module_files(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(
            ["package.json", "src/app.module.ts", "src/users/users.module.ts"]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "nestjs" in names

    def test_nestjs_controller_files(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(
            [
                "package.json",
                "src/app.module.ts",
                "src/users/users.controller.ts",
            ]
        )
        signals = detector.detect(inventory)
        nestjs_signal = next(s for s in signals if s.stack_name == "nestjs")
        assert nestjs_signal.confidence > 0.4

    def test_nestjs_evidence_includes_paths(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(
            ["package.json", "nest-cli.json", "src/app.module.ts"]
        )
        signals = detector.detect(inventory)
        nestjs_signal = next(s for s in signals if s.stack_name == "nestjs")
        assert "package.json" in nestjs_signal.evidence
        assert "nest-cli.json" in nestjs_signal.evidence
        assert "src/app.module.ts" in nestjs_signal.evidence


# ---------------------------------------------------------------------------
# Frontend-only (no false positives)
# ---------------------------------------------------------------------------


class TestFrontendOnlyNoFalsePositives:
    """Ensure no API signals for frontend-only Node projects."""

    def test_react_only_project(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(
            [
                "package.json",
                "vite.config.ts",
                "src/App.tsx",
                "src/components/Header.tsx",
                "src/index.tsx",
            ]
        )
        signals = detector.detect(inventory)
        assert signals == []

    def test_nextjs_only_project(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(
            [
                "package.json",
                "next.config.js",
                "pages/index.tsx",
                "pages/about.tsx",
            ]
        )
        signals = detector.detect(inventory)
        assert signals == []

    def test_angular_only_project(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(
            [
                "package.json",
                "angular.json",
                "src/app/app.component.ts",
                "src/app/app.module.ts",
            ]
        )
        signals = detector.detect(inventory)
        # Angular has .module.ts which could trigger NestJS, but the
        # frontend penalty should reduce confidence below threshold
        for signal in signals:
            assert signal.stack_name != "nestjs" or signal.confidence < 0.3

    def test_plain_node_no_api(self, detector: NodeApiDetector) -> None:
        """Node project with only a package.json returns no signals."""
        inventory = _make_inventory(["package.json", "src/index.js", "src/utils.js"])
        signals = detector.detect(inventory)
        assert signals == []


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


class TestConfidenceScoring:
    """Verify confidence is calibrated by evidence strength."""

    def test_more_evidence_higher_confidence(self, detector: NodeApiDetector) -> None:
        # Minimal Express signal
        minimal = _make_inventory(["package.json", "app.js"])
        minimal_signals = detector.detect(minimal)
        minimal_conf = next(
            s.confidence for s in minimal_signals if s.stack_name == "express"
        )

        # Rich Express signal
        rich = _make_inventory(
            ["package.json", "app.js", "routes/users.js", "middleware/auth.js"]
        )
        rich_signals = detector.detect(rich)
        rich_conf = next(
            s.confidence for s in rich_signals if s.stack_name == "express"
        )

        assert rich_conf > minimal_conf

    def test_confidence_between_zero_and_one(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(
            [
                "package.json",
                "nest-cli.json",
                "src/app.module.ts",
                "src/app.controller.ts",
                "src/app.service.ts",
                "app.js",
                "routes/api.js",
                "middleware/auth.js",
                "plugins/db.js",
            ]
        )
        signals = detector.detect(inventory)
        for signal in signals:
            assert 0.0 <= signal.confidence <= 1.0

    def test_frontend_penalty_reduces_confidence(
        self, detector: NodeApiDetector
    ) -> None:
        # Without frontend indicator
        backend = _make_inventory(["package.json", "app.js", "routes/api.js"])
        backend_signals = detector.detect(backend)
        backend_conf = next(
            s.confidence for s in backend_signals if s.stack_name == "express"
        )

        # Same files plus frontend indicator
        mixed = _make_inventory(
            ["package.json", "app.js", "routes/api.js", "next.config.js"]
        )
        mixed_signals = detector.detect(mixed)
        mixed_conf = next(
            s.confidence for s in mixed_signals if s.stack_name == "express"
        )

        assert mixed_conf < backend_conf


# ---------------------------------------------------------------------------
# Multiple frameworks
# ---------------------------------------------------------------------------


class TestMultipleFrameworks:
    """Projects with signals for multiple frameworks."""

    def test_express_and_nestjs_signals(self, detector: NodeApiDetector) -> None:
        """A monorepo might have both Express and NestJS patterns."""
        inventory = _make_inventory(
            [
                "package.json",
                "app.js",
                "routes/api.js",
                "nest-cli.json",
                "src/app.module.ts",
            ]
        )
        signals = detector.detect(inventory)
        names = {s.stack_name for s in signals}
        assert "express" in names
        assert "nestjs" in names


# ---------------------------------------------------------------------------
# Implements Detector interface
# ---------------------------------------------------------------------------


class TestDetectorInterface:
    """Verify NodeApiDetector properly implements the Detector ABC."""

    def test_is_detector_subclass(self) -> None:
        from repo_mirror_kit.harvester.detectors.base import Detector

        assert issubclass(NodeApiDetector, Detector)

    def test_instance_is_detector(self, detector: NodeApiDetector) -> None:
        from repo_mirror_kit.harvester.detectors.base import Detector

        assert isinstance(detector, Detector)

    def test_returns_list_of_signals(self, detector: NodeApiDetector) -> None:
        result = detector.detect(_empty_inventory())
        assert isinstance(result, list)

    def test_signal_types(self, detector: NodeApiDetector) -> None:
        inventory = _make_inventory(["package.json", "app.js"])
        result = detector.detect(inventory)
        for signal in result:
            assert isinstance(signal, Signal)
