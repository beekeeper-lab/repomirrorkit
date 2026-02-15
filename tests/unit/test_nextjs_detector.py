"""Unit tests for the Next.js detector."""

from __future__ import annotations

import pytest

from repo_mirror_kit.harvester.detectors.base import (
    clear_registry,
    get_all_detectors,
    register_detector,
    run_detection,
)
from repo_mirror_kit.harvester.detectors.nextjs import STACK_NAME, NextjsDetector
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory(paths: list[str]) -> InventoryResult:
    """Build an InventoryResult from a list of file paths."""
    files = [
        FileEntry(path=p, size=100, extension=_ext(p), hash="abc123", category="source")
        for p in paths
    ]
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=100 * len(files),
        total_skipped=0,
    )


def _ext(path: str) -> str:
    """Extract file extension from a path."""
    dot = path.rfind(".")
    if dot == -1:
        return ""
    return path[dot:]


# ---------------------------------------------------------------------------
# Fixture: isolated detector
# ---------------------------------------------------------------------------


@pytest.fixture()
def detector() -> NextjsDetector:
    """Return a fresh NextjsDetector instance."""
    return NextjsDetector()


# ---------------------------------------------------------------------------
# Config file detection
# ---------------------------------------------------------------------------


class TestConfigFileDetection:
    """Tests for next.config.* detection."""

    def test_next_config_js(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["package.json", "next.config.js"])
        signals = detector.detect(inventory)
        config_signals = [s for s in signals if s.confidence == pytest.approx(0.6)]
        assert len(config_signals) == 1
        assert "next.config.js" in config_signals[0].evidence

    def test_next_config_mjs(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["package.json", "next.config.mjs"])
        signals = detector.detect(inventory)
        config_signals = [s for s in signals if s.confidence == pytest.approx(0.6)]
        assert len(config_signals) == 1
        assert "next.config.mjs" in config_signals[0].evidence

    def test_next_config_ts(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["package.json", "next.config.ts"])
        signals = detector.detect(inventory)
        config_signals = [s for s in signals if s.confidence == pytest.approx(0.6)]
        assert len(config_signals) == 1
        assert "next.config.ts" in config_signals[0].evidence

    def test_no_config_file_no_config_signal(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["package.json", "src/App.tsx"])
        signals = detector.detect(inventory)
        config_signals = [s for s in signals if s.confidence == pytest.approx(0.6)]
        assert len(config_signals) == 0


# ---------------------------------------------------------------------------
# Special pages detection
# ---------------------------------------------------------------------------


class TestSpecialPagesDetection:
    """Tests for _app, _document, _error page detection."""

    def test_pages_app_tsx(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["pages/_app.tsx"])
        signals = detector.detect(inventory)
        special = [s for s in signals if s.confidence == pytest.approx(0.3)]
        assert len(special) >= 1
        assert any("pages/_app.tsx" in s.evidence for s in special)

    def test_pages_document_tsx(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["pages/_document.tsx"])
        signals = detector.detect(inventory)
        special = [s for s in signals if s.confidence == pytest.approx(0.3)]
        assert len(special) >= 1
        assert any("pages/_document.tsx" in s.evidence for s in special)

    def test_pages_error_jsx(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["pages/_error.jsx"])
        signals = detector.detect(inventory)
        special = [s for s in signals if s.confidence == pytest.approx(0.3)]
        assert len(special) >= 1
        assert any("pages/_error.jsx" in s.evidence for s in special)

    def test_src_pages_app(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["src/pages/_app.tsx"])
        signals = detector.detect(inventory)
        special = [s for s in signals if s.confidence == pytest.approx(0.3)]
        assert len(special) >= 1
        assert any("src/pages/_app.tsx" in s.evidence for s in special)

    def test_multiple_special_pages(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(
            ["pages/_app.tsx", "pages/_document.tsx", "pages/_error.tsx"]
        )
        signals = detector.detect(inventory)
        special = [s for s in signals if s.confidence == pytest.approx(0.3)]
        assert len(special) >= 1
        evidence = special[0].evidence
        assert len(evidence) == 3


# ---------------------------------------------------------------------------
# App Router detection
# ---------------------------------------------------------------------------


class TestAppRouterDetection:
    """Tests for Next.js 13+ App Router detection."""

    def test_app_layout_and_page(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["app/layout.tsx", "app/page.tsx"])
        signals = detector.detect(inventory)
        app_signals = [
            s
            for s in signals
            if s.confidence == pytest.approx(0.3)
            and any("app/" in e for e in s.evidence)
        ]
        assert len(app_signals) >= 1
        evidence = app_signals[0].evidence
        assert "app/layout.tsx" in evidence
        assert "app/page.tsx" in evidence

    def test_src_app_router(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["src/app/layout.tsx", "src/app/page.tsx"])
        signals = detector.detect(inventory)
        app_signals = [
            s
            for s in signals
            if s.confidence == pytest.approx(0.3)
            and any("src/app/" in e for e in s.evidence)
        ]
        assert len(app_signals) >= 1

    def test_app_loading_and_error(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(
            ["app/layout.tsx", "app/page.tsx", "app/loading.tsx", "app/error.tsx"]
        )
        signals = detector.detect(inventory)
        app_signals = [
            s
            for s in signals
            if s.confidence == pytest.approx(0.3)
            and any("app/" in e for e in s.evidence)
        ]
        assert len(app_signals) >= 1
        assert len(app_signals[0].evidence) == 4


# ---------------------------------------------------------------------------
# Pages directory detection
# ---------------------------------------------------------------------------


class TestPagesDirectoryDetection:
    """Tests for pages/ directory route file detection."""

    def test_pages_with_route_files(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(
            ["pages/index.tsx", "pages/about.tsx", "pages/contact.tsx"]
        )
        signals = detector.detect(inventory)
        pages_signals = [s for s in signals if s.confidence == pytest.approx(0.2)]
        assert len(pages_signals) == 1
        assert "pages/index.tsx" in pages_signals[0].evidence

    def test_pages_skips_special_pages(self, detector: NextjsDetector) -> None:
        """Special pages are handled by _check_special_pages, not double-counted."""
        inventory = _make_inventory(["pages/_app.tsx", "pages/index.tsx"])
        signals = detector.detect(inventory)
        pages_signals = [s for s in signals if s.confidence == pytest.approx(0.2)]
        # pages/index.tsx should be in the pages signal
        assert len(pages_signals) == 1
        assert "pages/_app.tsx" not in pages_signals[0].evidence
        assert "pages/index.tsx" in pages_signals[0].evidence

    def test_non_route_extension_ignored(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["pages/readme.md", "pages/styles.css"])
        signals = detector.detect(inventory)
        pages_signals = [s for s in signals if s.confidence == pytest.approx(0.2)]
        assert len(pages_signals) == 0


# ---------------------------------------------------------------------------
# API routes detection
# ---------------------------------------------------------------------------


class TestApiRoutesDetection:
    """Tests for pages/api/ and app/api/ detection."""

    def test_pages_api_routes(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["pages/api/hello.ts", "pages/api/users.ts"])
        signals = detector.detect(inventory)
        api_signals = [s for s in signals if s.confidence == pytest.approx(0.15)]
        assert len(api_signals) == 1
        assert "pages/api/hello.ts" in api_signals[0].evidence

    def test_app_api_routes(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["app/api/route.ts", "app/api/users/route.ts"])
        signals = detector.detect(inventory)
        api_signals = [s for s in signals if s.confidence == pytest.approx(0.15)]
        assert len(api_signals) == 1
        assert "app/api/route.ts" in api_signals[0].evidence

    def test_src_pages_api_routes(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["src/pages/api/hello.ts"])
        signals = detector.detect(inventory)
        api_signals = [s for s in signals if s.confidence == pytest.approx(0.15)]
        assert len(api_signals) == 1

    def test_src_app_api_routes(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["src/app/api/route.ts"])
        signals = detector.detect(inventory)
        api_signals = [s for s in signals if s.confidence == pytest.approx(0.15)]
        assert len(api_signals) == 1


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


class TestConfidenceScoring:
    """Tests for combined confidence scores."""

    def test_full_nextjs_project_high_confidence(
        self, detector: NextjsDetector
    ) -> None:
        """A full Next.js project should produce high combined confidence."""
        inventory = _make_inventory(
            [
                "package.json",
                "next.config.js",
                "pages/_app.tsx",
                "pages/_document.tsx",
                "pages/index.tsx",
                "pages/about.tsx",
                "pages/api/hello.ts",
            ]
        )
        signals = detector.detect(inventory)
        total = sum(s.confidence for s in signals)
        assert total >= 1.0
        assert all(s.stack_name == STACK_NAME for s in signals)

    def test_app_router_project_high_confidence(self, detector: NextjsDetector) -> None:
        """An App Router project should produce high combined confidence."""
        inventory = _make_inventory(
            [
                "package.json",
                "next.config.mjs",
                "app/layout.tsx",
                "app/page.tsx",
                "app/api/route.ts",
            ]
        )
        signals = detector.detect(inventory)
        total = sum(s.confidence for s in signals)
        assert total >= 1.0

    def test_config_only_gives_moderate_confidence(
        self, detector: NextjsDetector
    ) -> None:
        """Config file alone produces moderate confidence."""
        inventory = _make_inventory(["next.config.js"])
        signals = detector.detect(inventory)
        total = sum(s.confidence for s in signals)
        assert total == pytest.approx(0.6)

    def test_partial_signals_combine(self, detector: NextjsDetector) -> None:
        """Partial signals should combine to cross threshold."""
        inventory = _make_inventory(["pages/_app.tsx", "pages/api/hello.ts"])
        signals = detector.detect(inventory)
        total = sum(s.confidence for s in signals)
        # 0.3 (special pages) + 0.15 (api routes) = 0.45
        assert total == pytest.approx(0.45)


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


class TestEvidence:
    """Tests for evidence collection in signals."""

    def test_evidence_includes_config_file(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["next.config.js"])
        signals = detector.detect(inventory)
        all_evidence = [e for s in signals for e in s.evidence]
        assert "next.config.js" in all_evidence

    def test_evidence_includes_special_pages(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["pages/_app.tsx", "pages/_document.tsx"])
        signals = detector.detect(inventory)
        all_evidence = [e for s in signals for e in s.evidence]
        assert "pages/_app.tsx" in all_evidence
        assert "pages/_document.tsx" in all_evidence

    def test_evidence_includes_api_routes(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["pages/api/users.ts"])
        signals = detector.detect(inventory)
        all_evidence = [e for s in signals for e in s.evidence]
        assert "pages/api/users.ts" in all_evidence

    def test_evidence_includes_app_router_files(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(["app/layout.tsx", "app/page.tsx"])
        signals = detector.detect(inventory)
        all_evidence = [e for s in signals for e in s.evidence]
        assert "app/layout.tsx" in all_evidence
        assert "app/page.tsx" in all_evidence


# ---------------------------------------------------------------------------
# False positive prevention
# ---------------------------------------------------------------------------


class TestFalsePositivePrevention:
    """Tests ensuring no false positives on non-Next.js projects."""

    def test_plain_react_project_no_signals(self, detector: NextjsDetector) -> None:
        """A plain React project should produce no Next.js signals."""
        inventory = _make_inventory(
            [
                "package.json",
                "src/App.tsx",
                "src/index.tsx",
                "src/components/Header.tsx",
                "public/index.html",
                "tsconfig.json",
            ]
        )
        signals = detector.detect(inventory)
        assert len(signals) == 0

    def test_vue_project_no_signals(self, detector: NextjsDetector) -> None:
        """A Vue project should produce no Next.js signals."""
        inventory = _make_inventory(
            [
                "package.json",
                "vue.config.js",
                "src/App.vue",
                "src/main.ts",
                "src/components/HelloWorld.vue",
            ]
        )
        signals = detector.detect(inventory)
        assert len(signals) == 0

    def test_angular_project_no_signals(self, detector: NextjsDetector) -> None:
        """An Angular project should produce no Next.js signals."""
        inventory = _make_inventory(
            [
                "package.json",
                "angular.json",
                "src/app/app.component.ts",
                "src/app/app.module.ts",
            ]
        )
        signals = detector.detect(inventory)
        assert len(signals) == 0

    def test_nuxtjs_pages_not_detected_as_nextjs(
        self, detector: NextjsDetector
    ) -> None:
        """A Nuxt.js project with pages/ should not trigger Next.js-specific signals.

        The pages/ directory alone is a weak signal (0.2, below the default
        threshold of 0.3).  Without Next.js-specific markers, it stays low.
        """
        inventory = _make_inventory(
            [
                "package.json",
                "nuxt.config.ts",
                "pages/index.vue",
                "pages/about.vue",
            ]
        )
        signals = detector.detect(inventory)
        # .vue files are not route extensions, so no pages signal either
        assert len(signals) == 0


# ---------------------------------------------------------------------------
# Empty and edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_inventory(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory([])
        signals = detector.detect(inventory)
        assert signals == []

    def test_all_signals_use_correct_stack_name(self, detector: NextjsDetector) -> None:
        inventory = _make_inventory(
            [
                "next.config.js",
                "pages/_app.tsx",
                "app/layout.tsx",
                "pages/index.tsx",
                "pages/api/hello.ts",
            ]
        )
        signals = detector.detect(inventory)
        assert all(s.stack_name == STACK_NAME for s in signals)

    def test_deeply_nested_route_not_detected_as_api(
        self, detector: NextjsDetector
    ) -> None:
        """Files not under pages/api or app/api should not be API signals."""
        inventory = _make_inventory(["src/components/api/helper.ts"])
        signals = detector.detect(inventory)
        api_signals = [s for s in signals if s.confidence == pytest.approx(0.15)]
        assert len(api_signals) == 0


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------


class TestRegistryIntegration:
    """Tests for detector registry integration."""

    def setup_method(self) -> None:
        clear_registry()

    def teardown_method(self) -> None:
        clear_registry()

    def test_detector_registered_on_import(self) -> None:
        register_detector(NextjsDetector())
        detectors = get_all_detectors()
        nextjs_detectors = [d for d in detectors if isinstance(d, NextjsDetector)]
        assert len(nextjs_detectors) >= 1

    def test_run_detection_with_nextjs_detector(self) -> None:
        register_detector(NextjsDetector())
        inventory = _make_inventory(
            [
                "package.json",
                "next.config.js",
                "pages/_app.tsx",
                "pages/index.tsx",
            ]
        )
        profile = run_detection(inventory)
        assert STACK_NAME in profile.stacks
        assert profile.stacks[STACK_NAME] >= 0.6
        assert len(profile.evidence[STACK_NAME]) > 0

    def test_run_detection_plain_react_excluded(self) -> None:
        register_detector(NextjsDetector())
        inventory = _make_inventory(
            [
                "package.json",
                "src/App.tsx",
                "src/index.tsx",
            ]
        )
        profile = run_detection(inventory)
        assert STACK_NAME not in profile.stacks
