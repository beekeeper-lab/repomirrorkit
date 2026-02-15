"""Unit tests for the React detector."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

import pytest

from repo_mirror_kit.harvester.detectors.base import (
    Detector,
    clear_registry,
    get_all_detectors,
    register_detector,
    run_detection,
)
from repo_mirror_kit.harvester.detectors.react import ReactDetector
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _file_entry(
    path: str,
    *,
    extension: str = "",
    category: str = "source",
    size: int = 100,
) -> FileEntry:
    """Create a FileEntry for testing."""
    return FileEntry(
        path=path,
        size=size,
        extension=extension or PurePosixPath(path).suffix,
        hash="abc123def456",
        category=category,
    )


def _inventory(*entries: FileEntry) -> InventoryResult:
    """Create an InventoryResult from file entries."""
    files = list(entries)
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=sum(e.size for e in files),
        total_skipped=0,
    )


def _write_package_json(
    workdir: Path,
    *,
    dependencies: dict[str, str] | None = None,
    dev_dependencies: dict[str, str] | None = None,
    sub_path: str = "package.json",
) -> None:
    """Write a package.json file to the workdir."""
    data: dict[str, object] = {}
    if dependencies is not None:
        data["dependencies"] = dependencies
    if dev_dependencies is not None:
        data["devDependencies"] = dev_dependencies
    target = workdir / sub_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# ReactDetector — interface and basic behavior
# ---------------------------------------------------------------------------


class TestReactDetectorInterface:
    """Tests for ReactDetector interface compliance."""

    def test_implements_detector_interface(self) -> None:
        detector = ReactDetector()
        assert isinstance(detector, Detector)

    def test_empty_inventory_returns_no_signals(self) -> None:
        detector = ReactDetector()
        result = detector.detect(_inventory())
        assert result == []

    def test_stack_name_is_react(self) -> None:
        assert ReactDetector.STACK_NAME == "react"


# ---------------------------------------------------------------------------
# package.json detection
# ---------------------------------------------------------------------------


class TestPackageJsonDetection:
    """Tests for React detection via package.json."""

    def test_detects_react_in_dependencies(self, tmp_path: Path) -> None:
        _write_package_json(tmp_path, dependencies={"react": "^18.2.0"})
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("package.json", extension=".json", category="config"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        assert result[0].stack_name == "react"
        assert result[0].confidence == pytest.approx(0.4)
        assert "package.json" in result[0].evidence

    def test_detects_react_in_dev_dependencies(self, tmp_path: Path) -> None:
        _write_package_json(tmp_path, dev_dependencies={"react": "^18.0.0"})
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("package.json", extension=".json", category="config"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        assert result[0].confidence == pytest.approx(0.4)
        assert "package.json" in result[0].evidence

    def test_package_json_without_react_returns_no_signal(self, tmp_path: Path) -> None:
        _write_package_json(tmp_path, dependencies={"express": "^4.18.0"})
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("package.json", extension=".json", category="config"),
        )
        result = detector.detect(inv)
        assert result == []

    def test_malformed_package_json_handled_gracefully(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("not valid json{{{", encoding="utf-8")
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("package.json", extension=".json", category="config"),
            _file_entry("src/App.jsx", extension=".jsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        # Only JSX + common patterns; package.json read fails
        assert "package.json" not in result[0].evidence

    def test_missing_package_json_file_on_disk(self, tmp_path: Path) -> None:
        # Inventory lists package.json but file doesn't exist on disk
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("package.json", extension=".json", category="config"),
        )
        result = detector.detect(inv)
        assert result == []

    def test_nested_package_json_in_monorepo(self, tmp_path: Path) -> None:
        _write_package_json(
            tmp_path,
            dependencies={"react": "^18.0.0"},
            sub_path="packages/frontend/package.json",
        )
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry(
                "packages/frontend/package.json",
                extension=".json",
                category="config",
            ),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        assert "packages/frontend/package.json" in result[0].evidence

    def test_no_workdir_skips_package_json_check(self) -> None:
        detector = ReactDetector()  # No workdir
        inv = _inventory(
            _file_entry("package.json", extension=".json", category="config"),
            _file_entry("src/App.jsx", extension=".jsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        # Only JSX (0.3) + common pattern (0.1), no package.json analysis
        assert result[0].confidence == pytest.approx(0.4)
        assert "package.json" not in result[0].evidence


# ---------------------------------------------------------------------------
# JSX/TSX file detection
# ---------------------------------------------------------------------------


class TestJsxTsxDetection:
    """Tests for React detection via .jsx/.tsx file presence."""

    def test_detects_jsx_files(self) -> None:
        detector = ReactDetector()
        inv = _inventory(
            _file_entry("src/Header.jsx", extension=".jsx"),
            _file_entry("src/Footer.jsx", extension=".jsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        assert result[0].stack_name == "react"
        assert result[0].confidence >= 0.3
        assert "src/Header.jsx" in result[0].evidence
        assert "src/Footer.jsx" in result[0].evidence

    def test_detects_tsx_files(self) -> None:
        detector = ReactDetector()
        inv = _inventory(
            _file_entry("src/Component.tsx", extension=".tsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        assert result[0].confidence >= 0.3

    def test_no_jsx_tsx_files_no_signal(self) -> None:
        detector = ReactDetector()
        inv = _inventory(
            _file_entry("src/main.py", extension=".py"),
            _file_entry("src/index.js", extension=".js"),
        )
        result = detector.detect(inv)
        assert result == []


# ---------------------------------------------------------------------------
# Import pattern detection
# ---------------------------------------------------------------------------


class TestImportPatternDetection:
    """Tests for React detection via import patterns."""

    def test_detects_import_react(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "App.jsx").write_text(
            'import React from "react";\nfunction App() { return <div>Hello</div>; }\n',
            encoding="utf-8",
        )
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("src/App.jsx", extension=".jsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        assert "src/App.jsx" in result[0].evidence
        # JSX (0.3) + import (0.2) + common file (0.1) = 0.6
        assert result[0].confidence == pytest.approx(0.6)

    def test_detects_named_import_hooks(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "Counter.tsx").write_text(
            "import { useState, useEffect } from 'react';\n"
            "export function Counter() { return <div />; }\n",
            encoding="utf-8",
        )
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("src/Counter.tsx", extension=".tsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        assert "src/Counter.tsx" in result[0].evidence

    def test_detects_require_react(self, tmp_path: Path) -> None:
        (tmp_path / "index.js").write_text(
            "const React = require('react');\n",
            encoding="utf-8",
        )
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("index.js", extension=".js"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        assert result[0].confidence == pytest.approx(0.2)

    def test_detects_from_react_import(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "utils.ts").write_text(
            'import type { ReactNode } from "react";\n',
            encoding="utf-8",
        )
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("src/utils.ts", extension=".ts"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        assert "src/utils.ts" in result[0].evidence

    def test_no_react_imports_no_import_signal(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.js").write_text(
            'import express from "express";\nconst app = express();\n',
            encoding="utf-8",
        )
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("src/main.js", extension=".js"),
        )
        result = detector.detect(inv)
        assert result == []

    def test_no_workdir_skips_import_check(self) -> None:
        detector = ReactDetector()  # No workdir
        inv = _inventory(
            _file_entry("src/utils.js", extension=".js"),
        )
        result = detector.detect(inv)
        assert result == []


# ---------------------------------------------------------------------------
# Common file pattern detection
# ---------------------------------------------------------------------------


class TestCommonFilePatterns:
    """Tests for React detection via common file patterns."""

    def test_detects_app_jsx(self) -> None:
        detector = ReactDetector()
        inv = _inventory(
            _file_entry("src/App.jsx", extension=".jsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        assert "src/App.jsx" in result[0].evidence

    def test_detects_app_tsx(self) -> None:
        detector = ReactDetector()
        inv = _inventory(
            _file_entry("src/App.tsx", extension=".tsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1

    def test_detects_index_jsx(self) -> None:
        detector = ReactDetector()
        inv = _inventory(
            _file_entry("src/index.jsx", extension=".jsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1

    def test_non_react_filenames_no_common_pattern_signal(self) -> None:
        detector = ReactDetector()
        inv = _inventory(
            _file_entry("src/utils.jsx", extension=".jsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        # Still detected via JSX extension, but only 0.3 (no common pattern bonus)
        assert result[0].confidence == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Combined signals and confidence scoring
# ---------------------------------------------------------------------------


class TestCombinedSignals:
    """Tests for confidence scoring with multiple signals."""

    def test_package_json_plus_jsx_gives_high_confidence(self, tmp_path: Path) -> None:
        _write_package_json(tmp_path, dependencies={"react": "^18.2.0"})
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("package.json", extension=".json", category="config"),
            _file_entry("src/Header.jsx", extension=".jsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        # pkg (0.4) + jsx (0.3) = 0.7
        assert result[0].confidence == pytest.approx(0.7)

    def test_all_signals_produce_maximum_confidence(self, tmp_path: Path) -> None:
        _write_package_json(tmp_path, dependencies={"react": "^18.2.0"})
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "App.tsx").write_text(
            "import React from 'react';\n"
            "export default function App() { return <div />; }\n",
            encoding="utf-8",
        )
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("package.json", extension=".json", category="config"),
            _file_entry("src/App.tsx", extension=".tsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        # pkg (0.4) + tsx (0.3) + imports (0.2) + common (0.1) = 1.0
        assert result[0].confidence == pytest.approx(1.0)

    def test_confidence_capped_at_one(self, tmp_path: Path) -> None:
        _write_package_json(tmp_path, dependencies={"react": "^18.0.0"})
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "App.tsx").write_text(
            "import React from 'react';\n",
            encoding="utf-8",
        )
        (src_dir / "index.tsx").write_text(
            "import { createRoot } from 'react';\n",
            encoding="utf-8",
        )
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("package.json", extension=".json", category="config"),
            _file_entry("src/App.tsx", extension=".tsx"),
            _file_entry("src/index.tsx", extension=".tsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        assert result[0].confidence <= 1.0

    def test_jsx_only_gives_medium_confidence(self) -> None:
        detector = ReactDetector()
        inv = _inventory(
            _file_entry("src/utils.jsx", extension=".jsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        # Only JSX (0.3), no common pattern
        assert result[0].confidence == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Evidence tracking
# ---------------------------------------------------------------------------


class TestEvidence:
    """Tests for evidence collection and deduplication."""

    def test_evidence_includes_triggering_files(self, tmp_path: Path) -> None:
        _write_package_json(tmp_path, dependencies={"react": "^18.0.0"})
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("package.json", extension=".json", category="config"),
            _file_entry("src/App.jsx", extension=".jsx"),
            _file_entry("src/Header.jsx", extension=".jsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        assert "package.json" in result[0].evidence
        assert "src/App.jsx" in result[0].evidence
        assert "src/Header.jsx" in result[0].evidence

    def test_evidence_is_deduplicated(self) -> None:
        """App.jsx appears in both JSX check and common patterns check."""
        detector = ReactDetector()
        inv = _inventory(
            _file_entry("src/App.jsx", extension=".jsx"),
        )
        result = detector.detect(inv)
        assert len(result) == 1
        # App.jsx found by both jsx check and common pattern check
        assert result[0].evidence.count("src/App.jsx") == 1


# ---------------------------------------------------------------------------
# Non-React repos (no false positives)
# ---------------------------------------------------------------------------


class TestNonReactRepos:
    """Tests ensuring no false positives for non-React repositories."""

    def test_python_only_repo(self) -> None:
        detector = ReactDetector()
        inv = _inventory(
            _file_entry("src/main.py", extension=".py"),
            _file_entry("tests/test_main.py", extension=".py", category="test"),
            _file_entry("pyproject.toml", extension=".toml", category="config"),
        )
        result = detector.detect(inv)
        assert result == []

    def test_vanilla_js_repo(self, tmp_path: Path) -> None:
        _write_package_json(tmp_path, dependencies={"express": "^4.18.0"})
        (tmp_path / "index.js").write_text(
            'import express from "express";\n', encoding="utf-8"
        )
        detector = ReactDetector(workdir=tmp_path)
        inv = _inventory(
            _file_entry("package.json", extension=".json", category="config"),
            _file_entry("index.js", extension=".js"),
        )
        result = detector.detect(inv)
        assert result == []

    def test_vue_repo(self) -> None:
        detector = ReactDetector()
        inv = _inventory(
            _file_entry("src/App.vue", extension=".vue"),
            _file_entry("package.json", extension=".json", category="config"),
        )
        result = detector.detect(inv)
        assert result == []

    def test_empty_repo(self) -> None:
        detector = ReactDetector()
        result = detector.detect(_inventory())
        assert result == []


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------


class TestReactDetectorRegistry:
    """Tests for ReactDetector integration with the detector registry."""

    def setup_method(self) -> None:
        clear_registry()

    def teardown_method(self) -> None:
        clear_registry()

    def test_registers_with_detector_registry(self) -> None:
        detector = ReactDetector()
        register_detector(detector)
        assert detector in get_all_detectors()

    def test_works_with_run_detection(self) -> None:
        detector = ReactDetector()
        register_detector(detector)
        inv = _inventory(
            _file_entry("src/App.jsx", extension=".jsx"),
        )
        profile = run_detection(inv)
        assert "react" in profile.stacks
        assert profile.stacks["react"] >= 0.3

    def test_no_react_in_run_detection_for_non_react_repo(self) -> None:
        detector = ReactDetector()
        register_detector(detector)
        inv = _inventory(
            _file_entry("src/main.py", extension=".py"),
        )
        profile = run_detection(inv)
        assert "react" not in profile.stacks
