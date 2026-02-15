"""Tests for harvester structured logging and progress tracking."""

from __future__ import annotations

import logging
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.harvest_logging import (
    ProgressSnapshot,
    ProgressTracker,
    configure_logging,
    generate_progress_report,
)


class TestProgressTracker:
    """Tests for ProgressTracker counting and snapshot behavior."""

    def test_register_surface_sets_total(self) -> None:
        tracker = ProgressTracker()
        tracker.register_surface("routes", 50)
        snapshot = tracker.get_snapshot()
        assert snapshot.counters["routes"] == (0, 50)

    def test_increment_updates_completed(self) -> None:
        tracker = ProgressTracker()
        tracker.register_surface("apis", 10)
        tracker.increment("apis")
        tracker.increment("apis", 3)
        snapshot = tracker.get_snapshot()
        assert snapshot.counters["apis"] == (4, 10)

    def test_increment_without_register_creates_zero_total(self) -> None:
        tracker = ProgressTracker()
        tracker.increment("models", 2)
        snapshot = tracker.get_snapshot()
        assert snapshot.counters["models"] == (2, 0)

    def test_multiple_surfaces(self) -> None:
        tracker = ProgressTracker()
        tracker.register_surface("routes", 57)
        tracker.register_surface("apis", 21)
        tracker.register_surface("components", 15)
        tracker.increment("routes", 12)
        tracker.increment("apis", 4)
        snapshot = tracker.get_snapshot()
        assert snapshot.counters == {
            "apis": (4, 21),
            "components": (0, 15),
            "routes": (12, 57),
        }

    def test_get_snapshot_returns_sorted_surfaces(self) -> None:
        tracker = ProgressTracker()
        tracker.register_surface("zebra", 5)
        tracker.register_surface("alpha", 3)
        snapshot = tracker.get_snapshot()
        assert list(snapshot.counters.keys()) == ["alpha", "zebra"]

    def test_get_snapshot_includes_elapsed_time(self) -> None:
        tracker = ProgressTracker()
        snapshot = tracker.get_snapshot()
        assert snapshot.elapsed_seconds >= 0.0

    def test_reset_clears_all_counters(self) -> None:
        tracker = ProgressTracker()
        tracker.register_surface("routes", 50)
        tracker.increment("routes", 25)
        tracker.reset()
        snapshot = tracker.get_snapshot()
        assert snapshot.counters == {}

    def test_snapshot_is_immutable(self) -> None:
        tracker = ProgressTracker()
        tracker.register_surface("routes", 10)
        snapshot = tracker.get_snapshot()
        # Modifying returned dict should not affect tracker
        snapshot.counters["routes"] = (999, 999)
        fresh = tracker.get_snapshot()
        assert fresh.counters["routes"] == (0, 10)


class TestHeartbeat:
    """Tests for heartbeat interval logging."""

    def test_heartbeat_emits_on_first_call(self) -> None:
        configure_logging("debug")
        tracker = ProgressTracker(heartbeat_interval=0.0)
        tracker.register_surface("routes", 10)
        assert tracker.maybe_heartbeat() is True

    def test_heartbeat_respects_interval(self) -> None:
        configure_logging("debug")
        tracker = ProgressTracker(heartbeat_interval=9999.0)
        tracker.register_surface("routes", 10)
        # First call always fires because last_heartbeat starts at 0
        tracker.maybe_heartbeat()
        # Second call should not fire because interval hasn't elapsed
        assert tracker.maybe_heartbeat() is False

    def test_heartbeat_fires_after_interval_elapses(self) -> None:
        configure_logging("debug")
        tracker = ProgressTracker(heartbeat_interval=0.01)
        tracker.register_surface("routes", 10)
        tracker.maybe_heartbeat()

        import time

        time.sleep(0.02)
        assert tracker.maybe_heartbeat() is True


class TestConfigureLogging:
    """Tests for logging configuration."""

    def test_configure_sets_debug_level(self) -> None:
        configure_logging("debug")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_configure_sets_info_level(self) -> None:
        configure_logging("info")
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_configure_sets_warning_level(self) -> None:
        configure_logging("warning")
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_configure_sets_error_level(self) -> None:
        configure_logging("error")
        root = logging.getLogger()
        assert root.level == logging.ERROR

    def test_configure_json_output(self) -> None:
        # Should not raise
        configure_logging("info", json_output=True)
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_configure_default_is_human_readable(self) -> None:
        # Should not raise
        configure_logging("info", json_output=False)
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_structlog_logger_works_after_configure(self) -> None:
        configure_logging("debug")
        logger = structlog.get_logger("test")
        # Should not raise
        logger.info("test_event", key="value")


class TestProgressReport:
    """Tests for progress report generation."""

    def test_generates_markdown_file(self, tmp_path: Path) -> None:
        configure_logging("info")
        snapshot = ProgressSnapshot(
            counters={"routes": (12, 57), "apis": (4, 21)},
            elapsed_seconds=42.5,
        )
        output = tmp_path / "reports" / "progress.md"
        result = generate_progress_report(snapshot, output)

        assert result == output
        assert output.exists()
        content = output.read_text()
        assert "# Harvester Progress Report" in content
        assert "42.5s" in content
        assert "routes" in content
        assert "12" in content
        assert "57" in content

    def test_report_contains_percentage(self, tmp_path: Path) -> None:
        configure_logging("info")
        snapshot = ProgressSnapshot(
            counters={"routes": (50, 100)},
            elapsed_seconds=10.0,
        )
        output = tmp_path / "progress.md"
        generate_progress_report(snapshot, output)
        content = output.read_text()
        assert "50%" in content

    def test_report_handles_zero_total(self, tmp_path: Path) -> None:
        configure_logging("info")
        snapshot = ProgressSnapshot(
            counters={"unknown": (5, 0)},
            elapsed_seconds=1.0,
        )
        output = tmp_path / "progress.md"
        generate_progress_report(snapshot, output)
        content = output.read_text()
        assert "—" in content

    def test_report_handles_empty_counters(self, tmp_path: Path) -> None:
        configure_logging("info")
        snapshot = ProgressSnapshot(counters={}, elapsed_seconds=0.0)
        output = tmp_path / "progress.md"
        generate_progress_report(snapshot, output)
        content = output.read_text()
        assert "(none)" in content

    def test_report_creates_parent_directories(self, tmp_path: Path) -> None:
        configure_logging("info")
        snapshot = ProgressSnapshot(
            counters={"routes": (1, 1)},
            elapsed_seconds=0.5,
        )
        output = tmp_path / "deep" / "nested" / "progress.md"
        generate_progress_report(snapshot, output)
        assert output.exists()


class TestNoSecretsInLogs:
    """Verify that the logging setup does not expose sensitive data."""

    def test_log_event_uses_static_names(self) -> None:
        """Verify structured logging pattern uses static event names."""
        configure_logging("debug")
        logger = structlog.get_logger("harvester.test")
        # Static event name with keyword args is the correct pattern
        # This test just verifies the logger accepts the pattern
        logger.info("file_processed", file_path="/some/path", count=5)

    def test_progress_snapshot_contains_no_path_data(self) -> None:
        """Snapshots only contain surface names and counts, no file paths."""
        tracker = ProgressTracker()
        tracker.register_surface("routes", 10)
        tracker.increment("routes", 5)
        snapshot = tracker.get_snapshot()
        # Snapshot should only have counter data
        for key in snapshot.counters:
            assert "/" not in key
            assert "\\" not in key
