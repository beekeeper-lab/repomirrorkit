"""Unit tests for the .NET API detector."""

from __future__ import annotations

import pytest

from repo_mirror_kit.harvester.detectors.base import (
    Signal,
    clear_registry,
    get_all_detectors,
)
from repo_mirror_kit.harvester.detectors.dotnet_api import DotnetApiDetector
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
def detector() -> DotnetApiDetector:
    """Return a fresh DotnetApiDetector instance."""
    return DotnetApiDetector()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestDotnetApiDetectorRegistration:
    """Verify that the detector auto-registers on import."""

    def setup_method(self) -> None:
        clear_registry()
        from repo_mirror_kit.harvester.detectors.base import register_detector

        register_detector(DotnetApiDetector())

    def teardown_method(self) -> None:
        clear_registry()

    def test_auto_registers_on_import(self) -> None:
        detectors = get_all_detectors()
        assert len(detectors) == 1
        assert isinstance(detectors[0], DotnetApiDetector)


# ---------------------------------------------------------------------------
# Empty / no .csproj
# ---------------------------------------------------------------------------


class TestNoDotnetProject:
    """No signals when the project is not a .NET project."""

    def test_empty_inventory(self, detector: DotnetApiDetector) -> None:
        result = detector.detect(_empty_inventory())
        assert result == []

    def test_no_csproj(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(["src/main.py", "requirements.txt"])
        result = detector.detect(inventory)
        assert result == []

    def test_python_project(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(
            ["pyproject.toml", "src/app.py", "tests/test_app.py"]
        )
        result = detector.detect(inventory)
        assert result == []

    def test_node_project(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(["package.json", "src/app.js", "src/routes/api.js"])
        result = detector.detect(inventory)
        assert result == []


# ---------------------------------------------------------------------------
# ASP.NET controller-based detection
# ---------------------------------------------------------------------------


class TestAspNetDetection:
    """Detect ASP.NET controller-based API projects."""

    def test_aspnet_with_controllers(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(
            [
                "MyApp.csproj",
                "Controllers/WeatherController.cs",
                "Program.cs",
            ]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "aspnet" in names

    def test_aspnet_with_controllers_dir(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(
            [
                "MyApp.csproj",
                "Controllers/UsersController.cs",
                "Controllers/OrdersController.cs",
                "appsettings.json",
            ]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "aspnet" in names

    def test_aspnet_with_startup_cs(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(
            [
                "MyApp.csproj",
                "Controllers/ApiController.cs",
                "Startup.cs",
                "appsettings.json",
            ]
        )
        signals = detector.detect(inventory)
        aspnet_signal = next(s for s in signals if s.stack_name == "aspnet")
        # Startup.cs adds extra confidence
        assert aspnet_signal.confidence > 0.5

    def test_aspnet_evidence_includes_paths(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(
            [
                "MyApp.csproj",
                "Controllers/WeatherController.cs",
                "appsettings.json",
            ]
        )
        signals = detector.detect(inventory)
        aspnet_signal = next(s for s in signals if s.stack_name == "aspnet")
        assert "MyApp.csproj" in aspnet_signal.evidence
        assert "Controllers/WeatherController.cs" in aspnet_signal.evidence

    def test_aspnet_nested_csproj(self, detector: DotnetApiDetector) -> None:
        """A .csproj in a subdirectory should still be detected."""
        inventory = _make_inventory(
            [
                "src/WebApi/WebApi.csproj",
                "src/WebApi/Controllers/UserController.cs",
                "src/WebApi/appsettings.json",
            ]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "aspnet" in names

    def test_aspnet_high_confidence_full_project(
        self, detector: DotnetApiDetector
    ) -> None:
        inventory = _make_inventory(
            [
                "MyApp.csproj",
                "Controllers/WeatherController.cs",
                "Controllers/UsersController.cs",
                "Startup.cs",
                "Program.cs",
                "appsettings.json",
                "appsettings.Development.json",
            ]
        )
        signals = detector.detect(inventory)
        aspnet_signal = next(s for s in signals if s.stack_name == "aspnet")
        assert aspnet_signal.confidence >= 0.7


# ---------------------------------------------------------------------------
# Minimal API detection
# ---------------------------------------------------------------------------


class TestMinimalApiDetection:
    """Detect .NET minimal API projects."""

    def test_minimal_api_basic(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(
            [
                "MyApp.csproj",
                "Program.cs",
                "appsettings.json",
            ]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "dotnet-minimal-api" in names

    def test_minimal_api_with_startup(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(
            [
                "MyApp.csproj",
                "Program.cs",
                "Startup.cs",
                "appsettings.json",
            ]
        )
        signals = detector.detect(inventory)
        minimal_signal = next(
            s for s in signals if s.stack_name == "dotnet-minimal-api"
        )
        assert minimal_signal.confidence > 0.4

    def test_minimal_api_evidence_includes_paths(
        self, detector: DotnetApiDetector
    ) -> None:
        inventory = _make_inventory(
            [
                "MyApp.csproj",
                "Program.cs",
                "appsettings.json",
            ]
        )
        signals = detector.detect(inventory)
        minimal_signal = next(
            s for s in signals if s.stack_name == "dotnet-minimal-api"
        )
        assert "MyApp.csproj" in minimal_signal.evidence
        assert "Program.cs" in minimal_signal.evidence
        assert "appsettings.json" in minimal_signal.evidence

    def test_minimal_api_nested_paths(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(
            [
                "src/Api/Api.csproj",
                "src/Api/Program.cs",
                "src/Api/appsettings.json",
            ]
        )
        signals = detector.detect(inventory)
        names = [s.stack_name for s in signals]
        assert "dotnet-minimal-api" in names


# ---------------------------------------------------------------------------
# No false positives on non-web .NET projects
# ---------------------------------------------------------------------------


class TestNonWebDotnetNoFalsePositives:
    """Ensure no API signals for non-web .NET projects."""

    def test_console_app(self, detector: DotnetApiDetector) -> None:
        """Console app with just Program.cs but no appsettings or controllers."""
        inventory = _make_inventory(
            [
                "MyConsoleApp.csproj",
                "Program.cs",
            ]
        )
        signals = detector.detect(inventory)
        assert signals == []

    def test_class_library(self, detector: DotnetApiDetector) -> None:
        """Class library with no entry point or controllers."""
        inventory = _make_inventory(
            [
                "MyLib.csproj",
                "src/StringHelper.cs",
                "src/MathUtils.cs",
            ]
        )
        signals = detector.detect(inventory)
        assert signals == []

    def test_unit_test_project(self, detector: DotnetApiDetector) -> None:
        """Test project should not be detected as web API."""
        inventory = _make_inventory(
            [
                "MyApp.Tests.csproj",
                "UserServiceTests.cs",
                "OrderServiceTests.cs",
            ]
        )
        signals = detector.detect(inventory)
        assert signals == []

    def test_wpf_app(self, detector: DotnetApiDetector) -> None:
        """WPF desktop app should not trigger API detection."""
        inventory = _make_inventory(
            [
                "MyWpfApp.csproj",
                "App.xaml.cs",
                "MainWindow.xaml.cs",
                "Program.cs",
            ]
        )
        signals = detector.detect(inventory)
        assert signals == []


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------


class TestConfidenceScoring:
    """Verify confidence is calibrated by evidence strength."""

    def test_more_evidence_higher_confidence(self, detector: DotnetApiDetector) -> None:
        # Minimal ASP.NET signal
        minimal = _make_inventory(
            [
                "MyApp.csproj",
                "Controllers/HomeController.cs",
            ]
        )
        minimal_signals = detector.detect(minimal)
        minimal_conf = next(
            s.confidence for s in minimal_signals if s.stack_name == "aspnet"
        )

        # Rich ASP.NET signal
        rich = _make_inventory(
            [
                "MyApp.csproj",
                "Controllers/HomeController.cs",
                "Startup.cs",
                "appsettings.json",
            ]
        )
        rich_signals = detector.detect(rich)
        rich_conf = next(s.confidence for s in rich_signals if s.stack_name == "aspnet")

        assert rich_conf > minimal_conf

    def test_confidence_between_zero_and_one(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(
            [
                "MyApp.csproj",
                "Controllers/WeatherController.cs",
                "Controllers/UsersController.cs",
                "Startup.cs",
                "Program.cs",
                "appsettings.json",
                "appsettings.Development.json",
                "appsettings.Production.json",
            ]
        )
        signals = detector.detect(inventory)
        for signal in signals:
            assert 0.0 <= signal.confidence <= 1.0

    def test_minimal_api_confidence_grows_with_evidence(
        self, detector: DotnetApiDetector
    ) -> None:
        # Basic minimal API
        basic = _make_inventory(
            [
                "MyApp.csproj",
                "Program.cs",
                "appsettings.json",
            ]
        )
        basic_signals = detector.detect(basic)
        basic_conf = next(
            s.confidence for s in basic_signals if s.stack_name == "dotnet-minimal-api"
        )

        # With Startup.cs (extra evidence)
        richer = _make_inventory(
            [
                "MyApp.csproj",
                "Program.cs",
                "Startup.cs",
                "appsettings.json",
            ]
        )
        richer_signals = detector.detect(richer)
        richer_conf = next(
            s.confidence for s in richer_signals if s.stack_name == "dotnet-minimal-api"
        )

        assert richer_conf > basic_conf


# ---------------------------------------------------------------------------
# Both ASP.NET and minimal API signals
# ---------------------------------------------------------------------------


class TestBothSignals:
    """A project with both controllers and Program.cs can emit both signals."""

    def test_aspnet_and_minimal_api(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(
            [
                "MyApp.csproj",
                "Controllers/WeatherController.cs",
                "Program.cs",
                "appsettings.json",
            ]
        )
        signals = detector.detect(inventory)
        names = {s.stack_name for s in signals}
        assert "aspnet" in names
        assert "dotnet-minimal-api" in names


# ---------------------------------------------------------------------------
# Implements Detector interface
# ---------------------------------------------------------------------------


class TestDetectorInterface:
    """Verify DotnetApiDetector properly implements the Detector ABC."""

    def test_is_detector_subclass(self) -> None:
        from repo_mirror_kit.harvester.detectors.base import Detector

        assert issubclass(DotnetApiDetector, Detector)

    def test_instance_is_detector(self, detector: DotnetApiDetector) -> None:
        from repo_mirror_kit.harvester.detectors.base import Detector

        assert isinstance(detector, Detector)

    def test_returns_list_of_signals(self, detector: DotnetApiDetector) -> None:
        result = detector.detect(_empty_inventory())
        assert isinstance(result, list)

    def test_signal_types(self, detector: DotnetApiDetector) -> None:
        inventory = _make_inventory(
            [
                "MyApp.csproj",
                "Controllers/ApiController.cs",
                "Program.cs",
                "appsettings.json",
            ]
        )
        result = detector.detect(inventory)
        for signal in result:
            assert isinstance(signal, Signal)
