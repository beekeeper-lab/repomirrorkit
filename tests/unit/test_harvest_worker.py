from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

from repo_mirror_kit.harvester.pipeline import (
    HarvestResult,
    PipelineEvent,
    PipelineEventType,
)
from repo_mirror_kit.workers.harvest_worker import (
    STAGE_LABELS,
    HarvestWorker,
    _format_summary,
)


class TestHarvestWorkerSignals:
    """Tests for HarvestWorker signal emission."""

    @patch("repo_mirror_kit.workers.harvest_worker.HarvestPipeline")
    def test_emits_finished_on_success(
        self, mock_pipeline_cls: MagicMock, qapp: QApplication, tmp_path: Path
    ) -> None:
        result = HarvestResult(
            success=True,
            coverage_passed=True,
            bean_count=10,
            gap_count=0,
            output_dir=tmp_path / "out",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = result
        mock_pipeline_cls.return_value = mock_pipeline

        worker = HarvestWorker(tmp_path / "repo", tmp_path / "out")

        finished_args: list[tuple[bool, str]] = []
        worker.harvest_finished.connect(lambda s, m: finished_args.append((s, m)))

        worker.run()

        assert len(finished_args) == 1
        assert finished_args[0][0] is True
        assert "10 beans" in finished_args[0][1]

    @patch("repo_mirror_kit.workers.harvest_worker.HarvestPipeline")
    def test_emits_finished_on_failure(
        self, mock_pipeline_cls: MagicMock, qapp: QApplication, tmp_path: Path
    ) -> None:
        result = HarvestResult(
            success=False,
            coverage_passed=False,
            bean_count=0,
            gap_count=5,
            error_stage="C",
            error_message="Analysis failed",
            output_dir=tmp_path / "out",
        )
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = result
        mock_pipeline_cls.return_value = mock_pipeline

        worker = HarvestWorker(tmp_path / "repo", tmp_path / "out")

        finished_args: list[tuple[bool, str]] = []
        worker.harvest_finished.connect(lambda s, m: finished_args.append((s, m)))

        worker.run()

        assert len(finished_args) == 1
        assert finished_args[0][0] is False
        assert "stage C" in finished_args[0][1]

    @patch("repo_mirror_kit.workers.harvest_worker.HarvestPipeline")
    def test_emits_finished_on_exception(
        self, mock_pipeline_cls: MagicMock, qapp: QApplication, tmp_path: Path
    ) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.run.side_effect = RuntimeError("boom")
        mock_pipeline_cls.return_value = mock_pipeline

        worker = HarvestWorker(tmp_path / "repo", tmp_path / "out")

        finished_args: list[tuple[bool, str]] = []
        worker.harvest_finished.connect(lambda s, m: finished_args.append((s, m)))

        worker.run()

        assert len(finished_args) == 1
        assert finished_args[0][0] is False
        assert "boom" in finished_args[0][1]

    @patch("repo_mirror_kit.workers.harvest_worker.HarvestPipeline")
    def test_bridges_stage_start_to_stage_changed(
        self, mock_pipeline_cls: MagicMock, qapp: QApplication, tmp_path: Path
    ) -> None:
        """Pipeline STAGE_START events should emit stage_changed signal."""

        def fake_run(config: object) -> HarvestResult:
            callback = (
                mock_pipeline_cls.call_args[1].get("callback")
                or mock_pipeline_cls.call_args[0][0]
                if mock_pipeline_cls.call_args[0]
                else None
            )
            if callback is None:
                callback = mock_pipeline_cls.return_value._callback
            return HarvestResult(
                success=True, coverage_passed=True, bean_count=0, gap_count=0
            )

        # Capture the callback when HarvestPipeline is constructed
        captured_callback: list[object] = []

        def capture_pipeline(callback: object = None) -> MagicMock:
            captured_callback.append(callback)
            pipeline = MagicMock()
            pipeline.run.side_effect = lambda config: _run_with_events(
                callback,
                config,  # type: ignore[arg-type]
            )
            return pipeline

        def _run_with_events(callback: object, config: object) -> HarvestResult:
            if callable(callback):
                callback(
                    PipelineEvent(
                        event_type=PipelineEventType.STAGE_START,
                        stage="B",
                        message="Scanning inventory",
                    )
                )
            return HarvestResult(
                success=True, coverage_passed=True, bean_count=0, gap_count=0
            )

        mock_pipeline_cls.side_effect = capture_pipeline

        worker = HarvestWorker(tmp_path / "repo", tmp_path / "out")

        stage_labels: list[str] = []
        worker.stage_changed.connect(lambda label: stage_labels.append(label))

        worker.run()

        assert len(stage_labels) == 1
        assert stage_labels[0] == STAGE_LABELS["B"]

    @patch("repo_mirror_kit.workers.harvest_worker.HarvestPipeline")
    def test_bridges_progress_update_to_progress_updated(
        self, mock_pipeline_cls: MagicMock, qapp: QApplication, tmp_path: Path
    ) -> None:
        """Pipeline PROGRESS_UPDATE events should emit progress_updated signal."""

        def capture_pipeline(callback: object = None) -> MagicMock:
            pipeline = MagicMock()
            pipeline.run.side_effect = lambda config: _run_with_events(
                callback,
                config,  # type: ignore[arg-type]
            )
            return pipeline

        def _run_with_events(callback: object, config: object) -> HarvestResult:
            if callable(callback):
                callback(
                    PipelineEvent(
                        event_type=PipelineEventType.PROGRESS_UPDATE,
                        stage="C",
                        message="Routes: 42 found",
                    )
                )
            return HarvestResult(
                success=True, coverage_passed=True, bean_count=0, gap_count=0
            )

        mock_pipeline_cls.side_effect = capture_pipeline

        worker = HarvestWorker(tmp_path / "repo", tmp_path / "out")

        messages: list[str] = []
        worker.progress_updated.connect(lambda msg: messages.append(msg))

        worker.run()

        assert len(messages) == 1
        assert messages[0] == "Routes: 42 found"

    @patch("repo_mirror_kit.workers.harvest_worker.HarvestPipeline")
    def test_bridges_stage_complete_to_progress_updated(
        self, mock_pipeline_cls: MagicMock, qapp: QApplication, tmp_path: Path
    ) -> None:
        """Pipeline STAGE_COMPLETE events should emit progress_updated."""

        def capture_pipeline(callback: object = None) -> MagicMock:
            pipeline = MagicMock()
            pipeline.run.side_effect = lambda config: _run_with_events(
                callback,
                config,  # type: ignore[arg-type]
            )
            return pipeline

        def _run_with_events(callback: object, config: object) -> HarvestResult:
            if callable(callback):
                callback(
                    PipelineEvent(
                        event_type=PipelineEventType.STAGE_COMPLETE,
                        stage="B",
                        message="Inventory complete",
                    )
                )
            return HarvestResult(
                success=True, coverage_passed=True, bean_count=0, gap_count=0
            )

        mock_pipeline_cls.side_effect = capture_pipeline

        worker = HarvestWorker(tmp_path / "repo", tmp_path / "out")

        messages: list[str] = []
        worker.progress_updated.connect(lambda msg: messages.append(msg))

        worker.run()

        assert len(messages) == 1
        assert "[B] Inventory complete" in messages[0]

    @patch("repo_mirror_kit.workers.harvest_worker.HarvestPipeline")
    def test_bridges_stage_error_to_progress_updated(
        self, mock_pipeline_cls: MagicMock, qapp: QApplication, tmp_path: Path
    ) -> None:
        """Pipeline STAGE_ERROR events should emit progress_updated with ERROR prefix."""

        def capture_pipeline(callback: object = None) -> MagicMock:
            pipeline = MagicMock()
            pipeline.run.side_effect = lambda config: _run_with_events(
                callback,
                config,  # type: ignore[arg-type]
            )
            return pipeline

        def _run_with_events(callback: object, config: object) -> HarvestResult:
            if callable(callback):
                callback(
                    PipelineEvent(
                        event_type=PipelineEventType.STAGE_ERROR,
                        stage="C",
                        message="Stage C failed: boom",
                    )
                )
            return HarvestResult(
                success=False,
                coverage_passed=False,
                bean_count=0,
                gap_count=0,
                error_stage="C",
                error_message="boom",
            )

        mock_pipeline_cls.side_effect = capture_pipeline

        worker = HarvestWorker(tmp_path / "repo", tmp_path / "out")

        messages: list[str] = []
        worker.progress_updated.connect(lambda msg: messages.append(msg))

        worker.run()

        assert len(messages) == 1
        assert "ERROR" in messages[0]
        assert "[C]" in messages[0]


class TestFormatSummary:
    """Tests for _format_summary helper."""

    def test_success_with_coverage_passed(self) -> None:
        result = HarvestResult(
            success=True, coverage_passed=True, bean_count=42, gap_count=0
        )
        summary = _format_summary(result)
        assert "42 beans" in summary
        assert "coverage gates passed" in summary

    def test_success_with_gaps(self) -> None:
        result = HarvestResult(
            success=True, coverage_passed=False, bean_count=10, gap_count=5
        )
        summary = _format_summary(result)
        assert "10 beans" in summary
        assert "5 coverage gaps" in summary

    def test_failure_with_stage_and_message(self) -> None:
        result = HarvestResult(
            success=False,
            coverage_passed=False,
            bean_count=0,
            gap_count=3,
            error_stage="B",
            error_message="Detection failed",
        )
        summary = _format_summary(result)
        assert "stage B" in summary
        assert "Detection failed" in summary
        assert "3 gaps" in summary

    def test_failure_minimal(self) -> None:
        result = HarvestResult(
            success=False, coverage_passed=False, bean_count=0, gap_count=0
        )
        summary = _format_summary(result)
        assert "failed" in summary.lower()
