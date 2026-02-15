"""Structured logging and progress tracking for the harvester pipeline.

Provides structlog-based logging configuration, a ProgressTracker that
maintains counters per surface type, periodic heartbeat logging, and
progress report generation.

Module is named harvest_logging to avoid shadowing the stdlib logging module.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog


@dataclass(frozen=True)
class ProgressSnapshot:
    """Immutable snapshot of progress counters at a point in time.

    Attributes:
        counters: Mapping of surface type to (completed, total) pairs.
        elapsed_seconds: Seconds elapsed since tracking started.
    """

    counters: dict[str, tuple[int, int]]
    elapsed_seconds: float


class ProgressTracker:
    """Tracks progress counters per surface type.

    Thread-safe. Designed for both CLI (log output) and GUI (queryable state)
    consumption.

    Args:
        heartbeat_interval: Seconds between automatic heartbeat log emissions.
    """

    def __init__(self, heartbeat_interval: float = 30.0) -> None:
        self._lock = threading.Lock()
        self._completed: dict[str, int] = {}
        self._totals: dict[str, int] = {}
        self._start_time: float = time.monotonic()
        self._heartbeat_interval = heartbeat_interval
        self._last_heartbeat: float = 0.0
        self._logger: structlog.stdlib.BoundLogger = structlog.get_logger(
            "harvester.progress"
        )

    def register_surface(self, surface_type: str, total: int) -> None:
        """Register a surface type with its expected total count.

        Args:
            surface_type: Name of the surface type (e.g., "routes", "apis").
            total: Expected total number of items for this surface.
        """
        with self._lock:
            self._totals[surface_type] = total
            if surface_type not in self._completed:
                self._completed[surface_type] = 0

    def increment(self, surface_type: str, count: int = 1) -> None:
        """Increment the completed count for a surface type.

        Args:
            surface_type: Name of the surface type to increment.
            count: Number of items to add to the completed count.
        """
        with self._lock:
            self._completed[surface_type] = self._completed.get(surface_type, 0) + count
            if surface_type not in self._totals:
                self._totals[surface_type] = 0

    def get_snapshot(self) -> ProgressSnapshot:
        """Return an immutable snapshot of current progress.

        Returns:
            A ProgressSnapshot with current counter values and elapsed time.
        """
        with self._lock:
            counters: dict[str, tuple[int, int]] = {}
            all_surfaces = set(self._completed) | set(self._totals)
            for surface in sorted(all_surfaces):
                completed = self._completed.get(surface, 0)
                total = self._totals.get(surface, 0)
                counters[surface] = (completed, total)
            elapsed = time.monotonic() - self._start_time
        return ProgressSnapshot(counters=counters, elapsed_seconds=elapsed)

    def maybe_heartbeat(self) -> bool:
        """Emit a heartbeat log if the interval has elapsed.

        Returns:
            True if a heartbeat was emitted, False otherwise.
        """
        now = time.monotonic()
        with self._lock:
            if now - self._last_heartbeat < self._heartbeat_interval:
                return False
            self._last_heartbeat = now

        snapshot = self.get_snapshot()
        parts = [f"{name}: {c}/{t}" for name, (c, t) in snapshot.counters.items()]
        summary = ", ".join(parts) if parts else "no surfaces registered"

        self._logger.info(
            "progress_heartbeat",
            summary=summary,
            elapsed_seconds=round(snapshot.elapsed_seconds, 1),
            **_snapshot_to_kwargs(snapshot),
        )
        return True

    def reset(self) -> None:
        """Reset all counters and the start time."""
        with self._lock:
            self._completed.clear()
            self._totals.clear()
            self._start_time = time.monotonic()
            self._last_heartbeat = 0.0


def _snapshot_to_kwargs(snapshot: ProgressSnapshot) -> dict[str, Any]:
    """Convert a snapshot's counters to flat keyword arguments for logging."""
    kwargs: dict[str, Any] = {}
    for name, (completed, total) in snapshot.counters.items():
        kwargs[f"{name}_completed"] = completed
        kwargs[f"{name}_total"] = total
    return kwargs


def configure_logging(
    log_level: str = "info",
    *,
    json_output: bool = False,
) -> None:
    """Configure structlog for the harvester pipeline.

    Args:
        log_level: Logging verbosity level (debug, info, warning, error).
        json_output: If True, output JSON format (production). Otherwise,
            output human-readable format (development).
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)


def generate_progress_report(
    snapshot: ProgressSnapshot,
    output_path: Path,
) -> Path:
    """Generate a Markdown progress report from a snapshot.

    Args:
        snapshot: The progress snapshot to report on.
        output_path: Path where the report will be written.

    Returns:
        The path to the written report file.
    """
    lines: list[str] = [
        "# Harvester Progress Report",
        "",
        f"Elapsed: {snapshot.elapsed_seconds:.1f}s",
        "",
        "| Surface Type | Completed | Total | Progress |",
        "|---|---|---|---|",
    ]

    for name, (completed, total) in snapshot.counters.items():
        if total > 0:
            pct = f"{completed / total * 100:.0f}%"
        else:
            pct = "—"
        lines.append(f"| {name} | {completed} | {total} | {pct} |")

    if not snapshot.counters:
        lines.append("| (none) | 0 | 0 | — |")

    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    logger: structlog.stdlib.BoundLogger = structlog.get_logger("harvester.progress")
    logger.info("progress_report_generated", path=str(output_path))

    return output_path
