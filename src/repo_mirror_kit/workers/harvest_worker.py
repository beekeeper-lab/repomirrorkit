"""Background worker that runs the harvest pipeline in a QThread.

Bridges the pipeline's callback interface and its structured logs to Qt
signals so the main thread can update the UI without blocking. Every failure
path — including configuration errors raised before the pipeline starts —
ends in ``harvest_finished`` plus a message in the log panel, so the UI can
never be left silently waiting.
"""

from __future__ import annotations

import contextlib
import logging
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.harvest_logging import (
    register_log_handler,
    unregister_log_handler,
)
from repo_mirror_kit.harvester.pipeline import (
    HarvestPipeline,
    HarvestResult,
    PipelineEvent,
    PipelineEventType,
)
from repo_mirror_kit.harvester.providers import PROVIDERS, LlmSettings, find_key

# Human-readable labels for each pipeline stage
STAGE_LABELS: dict[str, str] = {
    "A": "Stage A: Clone & Normalize",
    "B": "Stage B: Inventory & Detection",
    "C": "Stage C: Surface Extraction",
    "C2": "Stage C2: LLM Enrichment",
    "C3": "Stage C3: Feature Clustering",
    "D": "Stage D: Traceability",
    "E": "Stage E: Bean Generation",
    "F": "Stage F: Coverage Gates",
    "G": "Stage G: Design Artifacts & Project Folder",
    "H": "Stage H: Source Cleanup",
}


class _QtLogHandler(logging.Handler):
    """Forwards formatted log records to a Qt signal (thread-safe)."""

    def __init__(self, emit: object) -> None:
        super().__init__(level=logging.INFO)
        self._emit = emit

    def emit(self, record: logging.LogRecord) -> None:
        # Logging must never raise into the pipeline.
        with contextlib.suppress(Exception):
            self._emit(self.format(record))  # type: ignore[operator]


class HarvestWorker(QThread):
    """Background worker that runs the harvest pipeline.

    Signals:
        stage_changed: A new pipeline stage started (human-readable label).
        progress_updated: Progress detail within a stage.
        log_message: A formatted structured-log line from the pipeline.
        harvest_finished: ``(success, summary)`` — always emitted exactly once.
    """

    stage_changed = Signal(str)
    progress_updated = Signal(str)
    log_message = Signal(str)
    harvest_finished = Signal(bool, str)

    def __init__(
        self,
        repo_path: Path,
        output_dir: Path | None = None,
        settings: LlmSettings | None = None,
        parent: QThread | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo_path = repo_path
        self._output_dir = output_dir
        self._settings = settings or LlmSettings()

    def _build_config(self) -> HarvestConfig:
        # The harvester accepts absolute local paths only; the GUI keeps
        # projects under a relative ``projects/`` directory.
        repo = self._repo_path.resolve()
        out = self._output_dir.resolve() if self._output_dir else None
        s = self._settings
        provider = PROVIDERS.get(s.provider)
        if s.enabled and provider is not None:
            if provider.kind == "api" and find_key(provider)[0] is None:
                self.progress_updated.emit(
                    f"No API key for {provider.label}; running without LLM enrichment. "
                    "Add one under Settings."
                )
                enabled = False
            else:
                enabled = True
        else:
            enabled = False
        kwargs: dict[str, object] = {}
        if enabled and provider is not None:
            kwargs.update(
                llm_provider=provider.id,
                llm_budget_usd=s.budget_usd,
                llm_concurrency=s.concurrency,
            )
            if s.model:
                kwargs["llm_model"] = s.model
        return HarvestConfig(
            repo=str(repo),
            out=out,
            fail_on_gaps=True,
            log_level="info",
            llm_enabled=enabled,
            **kwargs,  # type: ignore[arg-type]
        )

    def run(self) -> None:
        """Execute the harvest pipeline in a background thread."""
        handler = _QtLogHandler(self.log_message.emit)
        register_log_handler(handler)
        try:
            self.log_message.emit(f"Harvesting {self._repo_path.resolve()}")
            config = self._build_config()
            self.log_message.emit(
                "LLM enrichment: "
                + (
                    f"{config.llm_provider or config.llm_backend} / {config.llm_model}"
                    if config.llm_enabled
                    else "off (structural only)"
                )
            )
            pipeline = HarvestPipeline(callback=self._on_pipeline_event)
            result = pipeline.run(config)
        except Exception as exc:
            self.log_message.emit(traceback.format_exc())
            self.harvest_finished.emit(False, f"{type(exc).__name__}: {exc}")
            return
        finally:
            unregister_log_handler(handler)

        self.harvest_finished.emit(result.success, _format_summary(result))

    def _on_pipeline_event(self, event: PipelineEvent) -> None:
        """Bridge pipeline callback events to Qt signals (worker thread)."""
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
    """Format a HarvestResult into a human-readable summary string."""
    if result.success:
        parts = [f"{result.bean_count} beans generated"]
        if result.coverage_passed:
            parts.append("coverage gates passed")
        else:
            parts.append(f"{result.gap_count} coverage gaps")
        parts.append(f"output: {result.output_dir}")
        return ", ".join(parts)

    parts = []
    if result.error_stage:
        parts.append(f"Failed at stage {result.error_stage}")
    if result.error_message:
        parts.append(result.error_message)
    if result.gap_count > 0:
        parts.append(f"{result.gap_count} gaps")
    return ": ".join(parts) if parts else "Harvest failed"
