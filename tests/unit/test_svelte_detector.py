"""Unit tests for the Svelte/SvelteKit detector."""

from __future__ import annotations

from repo_mirror_kit.harvester.detectors.base import clear_registry
from repo_mirror_kit.harvester.detectors.svelte import SvelteDetector
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult


def _make_inventory(files: list[FileEntry]) -> InventoryResult:
    """Build an InventoryResult from a list of FileEntry objects."""
    total_size = sum(f.size for f in files)
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=total_size,
        total_skipped=0,
    )


def _file(path: str, *, ext: str = "", size: int = 100) -> FileEntry:
    """Create a FileEntry with sensible defaults."""
    if not ext:
        from pathlib import PurePosixPath

        ext = PurePosixPath(path).suffix
    return FileEntry(
        path=path, size=size, extension=ext, hash="abc123", category="source"
    )


class TestSvelteDetector:
    """Tests for the SvelteDetector class."""

    def setup_method(self) -> None:
        clear_registry()
        self.detector = SvelteDetector()

    def teardown_method(self) -> None:
        clear_registry()

    # -----------------------------------------------------------------
    # Basic Svelte detection
    # -----------------------------------------------------------------

    def test_detects_svelte_via_svelte_files(self) -> None:
        inventory = _make_inventory(
            [
                _file("src/App.svelte", ext=".svelte"),
                _file("src/lib/Counter.svelte", ext=".svelte"),
            ]
        )
        signals = self.detector.detect(inventory)

        svelte_signals = [s for s in signals if s.stack_name == "svelte"]
        assert len(svelte_signals) == 1
        assert svelte_signals[0].confidence >= 0.8
        assert "src/App.svelte" in svelte_signals[0].evidence

    def test_detects_svelte_via_package_json_as_evidence(self) -> None:
        """package.json appears as evidence when Svelte files are present."""
        inventory = _make_inventory(
            [
                _file("package.json", ext=".json"),
                _file("src/App.svelte", ext=".svelte"),
            ]
        )
        signals = self.detector.detect(inventory)

        svelte_signals = [s for s in signals if s.stack_name == "svelte"]
        assert len(svelte_signals) == 1
        assert "package.json" in svelte_signals[0].evidence

    def test_detects_svelte_via_config_file_js(self) -> None:
        inventory = _make_inventory(
            [
                _file("svelte.config.js", ext=".js"),
            ]
        )
        signals = self.detector.detect(inventory)

        svelte_signals = [s for s in signals if s.stack_name == "svelte"]
        assert len(svelte_signals) == 1
        assert svelte_signals[0].confidence > 0.0
        assert "svelte.config.js" in svelte_signals[0].evidence

    def test_detects_svelte_via_config_file_ts(self) -> None:
        inventory = _make_inventory(
            [
                _file("svelte.config.ts", ext=".ts"),
            ]
        )
        signals = self.detector.detect(inventory)

        svelte_signals = [s for s in signals if s.stack_name == "svelte"]
        assert len(svelte_signals) == 1
        assert "svelte.config.ts" in svelte_signals[0].evidence

    def test_svelte_files_plus_config_increases_confidence(self) -> None:
        """Having both .svelte files and a config gives higher confidence."""
        inventory_files_only = _make_inventory(
            [
                _file("src/App.svelte", ext=".svelte"),
            ]
        )
        inventory_both = _make_inventory(
            [
                _file("src/App.svelte", ext=".svelte"),
                _file("svelte.config.js", ext=".js"),
            ]
        )

        signals_files = self.detector.detect(inventory_files_only)
        signals_both = self.detector.detect(inventory_both)

        conf_files = next(
            s for s in signals_files if s.stack_name == "svelte"
        ).confidence
        conf_both = next(s for s in signals_both if s.stack_name == "svelte").confidence

        assert conf_both > conf_files

    # -----------------------------------------------------------------
    # SvelteKit detection
    # -----------------------------------------------------------------

    def test_detects_sveltekit_via_config(self) -> None:
        inventory = _make_inventory(
            [
                _file("svelte.config.js", ext=".js"),
            ]
        )
        signals = self.detector.detect(inventory)

        sveltekit_signals = [s for s in signals if s.stack_name == "sveltekit"]
        assert len(sveltekit_signals) == 1
        assert sveltekit_signals[0].confidence >= 0.5
        assert "svelte.config.js" in sveltekit_signals[0].evidence

    def test_detects_sveltekit_via_routes_directory(self) -> None:
        inventory = _make_inventory(
            [
                _file("src/routes/+page.svelte", ext=".svelte"),
                _file("src/routes/about/+page.svelte", ext=".svelte"),
            ]
        )
        signals = self.detector.detect(inventory)

        sveltekit_signals = [s for s in signals if s.stack_name == "sveltekit"]
        assert len(sveltekit_signals) == 1
        assert sveltekit_signals[0].confidence > 0.0
        assert "src/routes/+page.svelte" in sveltekit_signals[0].evidence

    def test_detects_sveltekit_via_config_and_routes(self) -> None:
        """Config + routes gives higher SvelteKit confidence."""
        inventory = _make_inventory(
            [
                _file("svelte.config.js", ext=".js"),
                _file("src/routes/+page.svelte", ext=".svelte"),
                _file("src/routes/+layout.svelte", ext=".svelte"),
            ]
        )
        signals = self.detector.detect(inventory)

        sveltekit_signals = [s for s in signals if s.stack_name == "sveltekit"]
        assert len(sveltekit_signals) == 1
        assert sveltekit_signals[0].confidence >= 0.8
        assert "svelte.config.js" in sveltekit_signals[0].evidence
        assert "src/routes/+page.svelte" in sveltekit_signals[0].evidence

    def test_sveltekit_server_routes_detected(self) -> None:
        inventory = _make_inventory(
            [
                _file("svelte.config.ts", ext=".ts"),
                _file("src/routes/api/+server.ts", ext=".ts"),
            ]
        )
        signals = self.detector.detect(inventory)

        sveltekit_signals = [s for s in signals if s.stack_name == "sveltekit"]
        assert len(sveltekit_signals) == 1
        assert "src/routes/api/+server.ts" in sveltekit_signals[0].evidence

    # -----------------------------------------------------------------
    # Full SvelteKit project
    # -----------------------------------------------------------------

    def test_full_sveltekit_project(self) -> None:
        """A realistic SvelteKit project produces both svelte and sveltekit signals."""
        inventory = _make_inventory(
            [
                _file("package.json", ext=".json"),
                _file("svelte.config.js", ext=".js"),
                _file("src/app.html", ext=".html"),
                _file("src/routes/+page.svelte", ext=".svelte"),
                _file("src/routes/+layout.svelte", ext=".svelte"),
                _file("src/routes/about/+page.svelte", ext=".svelte"),
                _file("src/lib/Counter.svelte", ext=".svelte"),
            ]
        )
        signals = self.detector.detect(inventory)

        stack_names = {s.stack_name for s in signals}
        assert "svelte" in stack_names
        assert "sveltekit" in stack_names

    # -----------------------------------------------------------------
    # No false positives
    # -----------------------------------------------------------------

    def test_no_false_positive_on_react_project(self) -> None:
        inventory = _make_inventory(
            [
                _file("package.json", ext=".json"),
                _file("src/App.tsx", ext=".tsx"),
                _file("src/index.tsx", ext=".tsx"),
                _file("src/components/Header.tsx", ext=".tsx"),
                _file("tsconfig.json", ext=".json"),
            ]
        )
        signals = self.detector.detect(inventory)

        assert len(signals) == 0

    def test_no_false_positive_on_vue_project(self) -> None:
        inventory = _make_inventory(
            [
                _file("package.json", ext=".json"),
                _file("src/App.vue", ext=".vue"),
                _file("src/components/HelloWorld.vue", ext=".vue"),
                _file("vue.config.js", ext=".js"),
            ]
        )
        signals = self.detector.detect(inventory)

        assert len(signals) == 0

    def test_no_false_positive_on_empty_inventory(self) -> None:
        inventory = _make_inventory([])
        signals = self.detector.detect(inventory)

        assert len(signals) == 0

    def test_no_false_positive_on_plain_node_project(self) -> None:
        """A Node.js project with only package.json does not trigger Svelte."""
        inventory = _make_inventory(
            [
                _file("package.json", ext=".json"),
                _file("src/index.js", ext=".js"),
                _file("src/utils.js", ext=".js"),
            ]
        )
        signals = self.detector.detect(inventory)

        assert len(signals) == 0

    # -----------------------------------------------------------------
    # Edge cases
    # -----------------------------------------------------------------

    def test_svelte_files_only_no_package_json(self) -> None:
        """Svelte detected even without package.json."""
        inventory = _make_inventory(
            [
                _file("src/App.svelte", ext=".svelte"),
            ]
        )
        signals = self.detector.detect(inventory)

        svelte_signals = [s for s in signals if s.stack_name == "svelte"]
        assert len(svelte_signals) == 1
        assert "package.json" not in svelte_signals[0].evidence

    def test_route_files_outside_routes_dir_ignored(self) -> None:
        """SvelteKit route file naming outside routes/ is not a SvelteKit signal."""
        inventory = _make_inventory(
            [
                _file("src/components/+page.svelte", ext=".svelte"),
            ]
        )
        signals = self.detector.detect(inventory)

        sveltekit_signals = [s for s in signals if s.stack_name == "sveltekit"]
        assert len(sveltekit_signals) == 0

    def test_evidence_capped(self) -> None:
        """Evidence does not grow unbounded for many .svelte files."""
        files = [_file(f"src/components/C{i}.svelte", ext=".svelte") for i in range(20)]
        inventory = _make_inventory(files)
        signals = self.detector.detect(inventory)

        svelte_signals = [s for s in signals if s.stack_name == "svelte"]
        assert len(svelte_signals) == 1
        # Evidence should be capped, not 20 entries
        assert len(svelte_signals[0].evidence) <= 6  # 5 files + possibly config

    def test_confidence_never_exceeds_one(self) -> None:
        """Confidence is capped at 1.0 even with maximum evidence."""
        inventory = _make_inventory(
            [
                _file("svelte.config.js", ext=".js"),
                _file("src/App.svelte", ext=".svelte"),
                _file("src/lib/A.svelte", ext=".svelte"),
                _file("src/lib/B.svelte", ext=".svelte"),
            ]
        )
        signals = self.detector.detect(inventory)

        for signal in signals:
            assert signal.confidence <= 1.0

    def test_nested_package_json_not_root(self) -> None:
        """package.json in subdirectories is not treated as root package.json."""
        inventory = _make_inventory(
            [
                _file("packages/ui/package.json", ext=".json"),
                _file("src/App.svelte", ext=".svelte"),
            ]
        )
        signals = self.detector.detect(inventory)

        svelte_signals = [s for s in signals if s.stack_name == "svelte"]
        assert len(svelte_signals) == 1
        assert "package.json" not in svelte_signals[0].evidence
