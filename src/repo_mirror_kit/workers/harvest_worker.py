"""Background worker that runs the harvest pipeline in a QThread.

Bridges the pipeline's callback interface to Qt signals so the main
thread can update the UI without blocking.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.pipeline import (
    HarvestPipeline,
    HarvestResult,
    PipelineEvent,
    PipelineEventType,
)

# Human-readable labels for each pipeline stage
STAGE_LABELS: dict[str, str] = {
    "A": "Stage A: Clone & Normalize",
    "B": "Stage B: Inventory & Detection",
    "C": "Stage C: Surface Extraction",
    "D": "Stage D: Traceability",
    "E": "Stage E: Bean Generation",
    "F": "Stage F: Coverage Gates",
}


class HarvestWorker(QThread):
    """Background worker that runs the harvest pipeline.

    Emits Qt signals for stage transitions, progress updates, and
    completion so the main thread can update the UI safely.

    Signals:
        stage_changed: Emitted when a new pipeline stage starts.
            Argument is a human-readable stage label.
        progress_updated: Emitted for progress events within a stage.
            Argument is a human-readable progress message.
        harvest_finished: Emitted when the pipeline completes.
            Arguments are (success: bool, summary: str).
    """

    stage_changed = Signal(str)
    progress_updated = Signal(str)
    harvest_finished = Signal(bool, str)

    def __init__(
        self,
        repo_path: Path,
        output_dir: Path | None = None,
        parent: QThread | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo_path = repo_path
        self._output_dir = output_dir

    def run(self) -> None:
        """Execute the harvest pipeline in a background thread."""
        config = HarvestConfig(
            repo=str(self._repo_path),
            out=self._output_dir,
            fail_on_gaps=True,
            log_level="info",
        )

        pipeline = HarvestPipeline(callback=self._on_pipeline_event)

        try:
            result = pipeline.run(config)
        except Exception as exc:
            self.harvest_finished.emit(False, f"Unexpected error: {exc}")
            return

        summary = _format_summary(result)
        self.harvest_finished.emit(result.success, summary)

    def _on_pipeline_event(self, event: PipelineEvent) -> None:
        """Bridge pipeline callback events to Qt signals.

        Called from the worker thread. Signals are marshalled to the
        main thread by Qt's event loop.
        """
        if event.event_type == PipelineEventType.STAGE_START:
            label = STAGE_LABELS.get(event.stage, f"Stage {event.stage}")
            self.stage_changed.emit(label)
        elif event.event_type == PipelineEventType.PROGRESS_UPDATE:
            self.progress_updated.emit(event.message)
        elif event.event_type == PipelineEventType.STAGE_COMPLETE:
            self.progress_updated.emit(f"[{event.stage}] {event.message}")
        elif event.event_type == PipelineEventType.STAGE_ERROR:
            self.progress_updated.emit(f"[{event.stage}] ERROR: {event.message}")


def _format_summary(result: HarvestResult) -> str:
    """Format a HarvestResult into a human-readable summary string.

    Args:
        result: The pipeline result to format.

    Returns:
        A summary string suitable for display in the status label.
    """
    if result.success:
        parts = [f"{result.bean_count} beans generated"]
        if result.coverage_passed:
            parts.append("coverage gates passed")
        else:
            parts.append(f"{result.gap_count} coverage gaps")
        return ", ".join(parts)

    parts = []
    if result.error_stage:
        parts.append(f"Failed at stage {result.error_stage}")
    if result.error_message:
        parts.append(result.error_message)
    if result.gap_count > 0:
        parts.append(f"{result.gap_count} gaps")
    return ": ".join(parts) if parts else "Harvest failed"
