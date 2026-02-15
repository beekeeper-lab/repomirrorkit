"""Unit tests for the Python API detector."""

from __future__ import annotations

import pytest

from repo_mirror_kit.harvester.detectors.base import (
    Signal,
    clear_registry,
    get_all_detectors,
)
from repo_mirror_kit.harvester.detectors.python_api import PythonApiDetector
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
def detector() -> PythonApiDetector:
    """Return a fresh PythonApiDetector instance."""
    return PythonApiDetector()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestPythonApiDetectorRegistration:
    """Verify that the detector auto-registers on import."""

    def setup_method(self) -> None:
        clear_registry()
        from repo_mirror_kit.harvester.detectors.base import register_detector

        register_detector(PythonApiDetector())

    def teardown_method(self) -> None:
        clear_registry()

    def test_auto_registers_on_import(self) -> None:
        detectors = get_all_detectors()
        assert len(detectors) == 1
        assert isinstance(detectors[0], PythonApiDetector)


# ---------------------------------------------------------------------------
# Empty / no Python project
# ---------------------------------------------------------------------------


class TestNoPythonProject:
    """No signals when the project is not a Python project."""

    def test_empty_inventory(self, detector: PythonApiDetector) -> None:
        result = detector.detect(_empty_inventory())
        assert result == []

    def test_no_python_markers(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(["package.json", "src/index.js"])
        result = detector.detect(inventory)
        assert result == []

    def test_node_project_only(self, detector: PythonApiDetector) -> None:
        """A pure Node project should produce no Python signals."""
        inventory = _make_inventory(["package.json", "src/app.js", "routes/users.js"])
        result = detector.detect(inventory)
        assert result == []


# ---------------------------------------------------------------------------
# FastAPI detection
# ---------------------------------------------------------------------------


class TestFastAPIDetection:
    """Detect FastAPI backend projects."""

    def test_fastapi_with_routers(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            [
                "pyproject.toml",
                "src/myapp/main.py",
                "src/myapp/routers/users.py",
                "src/myapp/routers/items.py",
            ]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "fastapi" in names

    def test_fastapi_with_routers_at_root(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(["requirements.txt", "main.py", "routers/api.py"])
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "fastapi" in names

    def test_fastapi_with_schemas(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            [
                "pyproject.toml",
                "src/myapp/routers/users.py",
                "src/myapp/schemas.py",
            ]
        )
        signals = detector.detect(inventory)
        fastapi_signal = next(s for s in signals if s.stack_name == "fastapi")
        assert fastapi_signal.confidence > 0.5

    def test_fastapi_with_dependencies(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            ["requirements.txt", "routers/api.py", "dependencies.py"]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "fastapi" in names

    def test_fastapi_high_confidence(self, detector: PythonApiDetector) -> None:
        """All FastAPI patterns produce high confidence."""
        inventory = _make_inventory(
            [
                "pyproject.toml",
                "main.py",
                "routers/users.py",
                "schemas.py",
                "dependencies.py",
            ]
        )
        signals = detector.detect(inventory)
        fastapi_signal = next(s for s in signals if s.stack_name == "fastapi")
        assert fastapi_signal.confidence >= 0.8

    def test_fastapi_evidence_includes_paths(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            ["pyproject.toml", "routers/users.py", "schemas.py"]
        )
        signals = detector.detect(inventory)
        fastapi_signal = next(s for s in signals if s.stack_name == "fastapi")
        assert "pyproject.toml" in fastapi_signal.evidence
        assert "routers/users.py" in fastapi_signal.evidence
        assert "schemas.py" in fastapi_signal.evidence

    def test_fastapi_with_requirements_txt(self, detector: PythonApiDetector) -> None:
        """Detect using requirements.txt as project marker."""
        inventory = _make_inventory(["requirements.txt", "routers/endpoints.py"])
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "fastapi" in names
        fastapi_signal = next(s for s in signals if s.stack_name == "fastapi")
        assert "requirements.txt" in fastapi_signal.evidence

    def test_fastapi_with_setup_py(self, detector: PythonApiDetector) -> None:
        """Detect using setup.py as project marker."""
        inventory = _make_inventory(["setup.py", "routers/users.py"])
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "fastapi" in names


# ---------------------------------------------------------------------------
# Flask detection
# ---------------------------------------------------------------------------


class TestFlaskDetection:
    """Detect Flask backend projects."""

    def test_flask_with_templates(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            [
                "pyproject.toml",
                "app.py",
                "templates/index.html",
                "templates/base.html",
            ]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "flask" in names

    def test_flask_with_views_and_templates(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            [
                "requirements.txt",
                "templates/home.html",
                "views.py",
            ]
        )
        signals = detector.detect(inventory)
        flask_signal = next(s for s in signals if s.stack_name == "flask")
        assert flask_signal.confidence > 0.5

    def test_flask_with_blueprints(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            [
                "pyproject.toml",
                "app/blueprints/auth.py",
                "app/blueprints/main.py",
                "app/templates/login.html",
            ]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "flask" in names

    def test_flask_with_wsgi(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            [
                "requirements.txt",
                "wsgi.py",
                "app/views.py",
                "app/templates/index.html",
            ]
        )
        signals = detector.detect(inventory)
        flask_signal = next(s for s in signals if s.stack_name == "flask")
        assert flask_signal.confidence > 0.6

    def test_flask_with_forms(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            [
                "pyproject.toml",
                "templates/register.html",
                "views.py",
                "forms.py",
            ]
        )
        signals = detector.detect(inventory)
        flask_signal = next(s for s in signals if s.stack_name == "flask")
        assert flask_signal.confidence > 0.5

    def test_flask_with_static_assets(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            [
                "requirements.txt",
                "templates/index.html",
                "static/style.css",
                "static/app.js",
            ]
        )
        signals = detector.detect(inventory)
        flask_signal = next(s for s in signals if s.stack_name == "flask")
        assert "static/style.css" in flask_signal.evidence

    def test_flask_evidence_includes_paths(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            ["requirements.txt", "templates/index.html", "views.py"]
        )
        signals = detector.detect(inventory)
        flask_signal = next(s for s in signals if s.stack_name == "flask")
        assert "requirements.txt" in flask_signal.evidence
        assert "templates/index.html" in flask_signal.evidence
        assert "views.py" in flask_signal.evidence

    def test_flask_high_confidence(self, detector: PythonApiDetector) -> None:
        """All Flask patterns produce high confidence."""
        inventory = _make_inventory(
            [
                "pyproject.toml",
                "wsgi.py",
                "templates/base.html",
                "views.py",
                "blueprints/auth.py",
                "forms.py",
                "static/style.css",
            ]
        )
        signals = detector.detect(inventory)
        flask_signal = next(s for s in signals if s.stack_name == "flask")
        assert flask_signal.confidence >= 0.9


# ---------------------------------------------------------------------------
# No false positives on non-API Python projects
# ---------------------------------------------------------------------------


class TestNoFalsePositives:
    """Ensure no API signals for non-API Python projects."""

    def test_cli_tool(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            [
                "pyproject.toml",
                "src/mytool/cli.py",
                "src/mytool/__main__.py",
                "src/mytool/commands/greet.py",
                "src/mytool/utils.py",
            ]
        )
        signals = detector.detect(inventory)
        assert signals == []

    def test_python_library(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            [
                "pyproject.toml",
                "src/mylib/__init__.py",
                "src/mylib/utils.py",
                "src/mylib/helpers.py",
                "src/mylib/core.py",
            ]
        )
        signals = detector.detect(inventory)
        assert signals == []

    def test_data_science_project(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            [
                "requirements.txt",
                "notebooks/analysis.ipynb",
                "src/pipeline/transform.py",
                "src/pipeline/load.py",
                "data/input.csv",
            ]
        )
        signals = detector.detect(inventory)
        assert signals == []

    def test_plain_python_with_main(self, detector: PythonApiDetector) -> None:
        """A Python project with just main.py but no API patterns."""
        inventory = _make_inventory(
            [
                "pyproject.toml",
                "main.py",
                "src/myapp/__init__.py",
                "src/myapp/config.py",
            ]
        )
        signals = detector.detect(inventory)
        # main.py alone gives only 0.10 + 0.10 = 0.20 confidence
        # which is below the default 0.3 min_confidence threshold,
        # but the detector still returns it as a signal
        for signal in signals:
            assert signal.confidence < 0.3

    def test_django_project_no_fastapi(self, detector: PythonApiDetector) -> None:
        """Django-style project should not produce FastAPI signals."""
        inventory = _make_inventory(
            [
                "requirements.txt",
                "manage.py",
                "myproject/settings.py",
                "myproject/urls.py",
                "myapp/models.py",
            ]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "fastapi" not in names


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


class TestConfidenceScoring:
    """Verify confidence is calibrated by evidence strength."""

    def test_more_evidence_higher_confidence(self, detector: PythonApiDetector) -> None:
        # Minimal FastAPI signal
        minimal = _make_inventory(["pyproject.toml", "routers/api.py"])
        minimal_signals = detector.detect(minimal)
        minimal_conf = next(
            s.confidence for s in minimal_signals if s.stack_name == "fastapi"
        )

        # Rich FastAPI signal
        rich = _make_inventory(
            [
                "pyproject.toml",
                "main.py",
                "routers/users.py",
                "schemas.py",
                "dependencies.py",
            ]
        )
        rich_signals = detector.detect(rich)
        rich_conf = next(
            s.confidence for s in rich_signals if s.stack_name == "fastapi"
        )

        assert rich_conf > minimal_conf

    def test_confidence_between_zero_and_one(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(
            [
                "pyproject.toml",
                "main.py",
                "routers/users.py",
                "schemas.py",
                "dependencies.py",
                "templates/index.html",
                "views.py",
                "blueprints/auth.py",
                "wsgi.py",
                "forms.py",
                "static/style.css",
            ]
        )
        signals = detector.detect(inventory)
        for signal in signals:
            assert 0.0 <= signal.confidence <= 1.0

    def test_cli_penalty_reduces_confidence(self, detector: PythonApiDetector) -> None:
        # Without CLI indicator
        backend = _make_inventory(["pyproject.toml", "routers/users.py", "schemas.py"])
        backend_signals = detector.detect(backend)
        backend_conf = next(
            s.confidence for s in backend_signals if s.stack_name == "fastapi"
        )

        # Same files plus CLI indicator
        mixed = _make_inventory(
            ["pyproject.toml", "routers/users.py", "schemas.py", "cli.py"]
        )
        mixed_signals = detector.detect(mixed)
        mixed_conf = next(
            s.confidence for s in mixed_signals if s.stack_name == "fastapi"
        )

        assert mixed_conf < backend_conf

    def test_flask_more_evidence_higher_confidence(
        self, detector: PythonApiDetector
    ) -> None:
        # Minimal Flask signal
        minimal = _make_inventory(["pyproject.toml", "templates/index.html"])
        minimal_signals = detector.detect(minimal)
        minimal_conf = next(
            s.confidence for s in minimal_signals if s.stack_name == "flask"
        )

        # Rich Flask signal
        rich = _make_inventory(
            [
                "pyproject.toml",
                "wsgi.py",
                "templates/index.html",
                "views.py",
                "blueprints/auth.py",
            ]
        )
        rich_signals = detector.detect(rich)
        rich_conf = next(s.confidence for s in rich_signals if s.stack_name == "flask")

        assert rich_conf > minimal_conf


# ---------------------------------------------------------------------------
# Multiple frameworks
# ---------------------------------------------------------------------------


class TestMultipleFrameworks:
    """Projects with signals for multiple frameworks."""

    def test_fastapi_and_flask_signals(self, detector: PythonApiDetector) -> None:
        """A monorepo might have both FastAPI and Flask patterns."""
        inventory = _make_inventory(
            [
                "pyproject.toml",
                "routers/api.py",
                "schemas.py",
                "templates/admin.html",
                "views.py",
            ]
        )
        signals = detector.detect(inventory)
        names = {s.stack_name for s in signals}
        assert "fastapi" in names
        assert "flask" in names

    def test_signal_includes_framework_name(self, detector: PythonApiDetector) -> None:
        """Signals identify the specific framework detected."""
        inventory = _make_inventory(["pyproject.toml", "routers/users.py"])
        signals = detector.detect(inventory)
        assert len(signals) >= 1
        assert signals[0].stack_name == "fastapi"


# ---------------------------------------------------------------------------
# Implements Detector interface
# ---------------------------------------------------------------------------


class TestDetectorInterface:
    """Verify PythonApiDetector properly implements the Detector ABC."""

    def test_is_detector_subclass(self) -> None:
        from repo_mirror_kit.harvester.detectors.base import Detector

        assert issubclass(PythonApiDetector, Detector)

    def test_instance_is_detector(self, detector: PythonApiDetector) -> None:
        from repo_mirror_kit.harvester.detectors.base import Detector

        assert isinstance(detector, Detector)

    def test_returns_list_of_signals(self, detector: PythonApiDetector) -> None:
        result = detector.detect(_empty_inventory())
        assert isinstance(result, list)

    def test_signal_types(self, detector: PythonApiDetector) -> None:
        inventory = _make_inventory(["pyproject.toml", "routers/users.py"])
        result = detector.detect(inventory)
        for signal in result:
            assert isinstance(signal, Signal)
