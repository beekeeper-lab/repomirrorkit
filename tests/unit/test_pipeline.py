"""Tests for the pipeline orchestrator."""

from __future__ import annotations

import contextlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from repo_mirror_kit.harvester.analyzers.surfaces import SurfaceCollection
from repo_mirror_kit.harvester.beans.writer import WrittenBean
from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.git_ops import CloneResult
from repo_mirror_kit.harvester.inventory import InventoryResult
from repo_mirror_kit.harvester.pipeline import (
    STAGE_NAMES,
    HarvestPipeline,
    HarvestResult,
    PipelineEvent,
    PipelineEventType,
)
from repo_mirror_kit.harvester.reports.coverage import (
    CoverageEvaluation,
    CoverageMetrics,
    FileMetrics,
    GateResult,
    MetricPair,
)
from repo_mirror_kit.harvester.reports.gaps import GapReport

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def _make_config(tmp_path: Path, *, resume: bool = False) -> HarvestConfig:
    """Build a minimal HarvestConfig pointing at tmp_path."""
    return HarvestConfig(
        repo="https://example.com/repo.git",
        out=tmp_path / "output",
        resume=resume,
        fail_on_gaps=True,
        log_level="error",
    )


def _make_clone_result(tmp_path: Path) -> CloneResult:
    """Create a dummy CloneResult."""
    repo_dir = tmp_path / "output" / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    return CloneResult(repo_dir=repo_dir, skipped_symlinks=[], normalized_files=0)


def _make_inventory() -> InventoryResult:
    return InventoryResult(
        files=[], skipped=[], total_files=0, total_size=0, total_skipped=0
    )


def _make_profile() -> StackProfile:
    return StackProfile(stacks={}, evidence={}, signals=[])


def _make_nonempty_surfaces() -> SurfaceCollection:
    """Surfaces with at least one entry so the pipeline doesn't short-circuit."""
    from repo_mirror_kit.harvester.analyzers.surfaces import (
        RouteSurface,
        SourceRef,
    )

    return SurfaceCollection(
        routes=[
            RouteSurface(
                name="home",
                path="/",
                method="GET",
                source_refs=[SourceRef(file_path="routes.py", start_line=1)],
            )
        ],
    )


def _make_beans() -> list[WrittenBean]:
    return []


def _make_evaluation() -> CoverageEvaluation:
    metrics = CoverageMetrics(
        files=FileMetrics(total=0, scanned=0, skipped=0),
        routes=MetricPair(total=0, covered=0),
        shared_components=MetricPair(total=0, covered=0),
        apis=MetricPair(total=0, covered=0),
        models=MetricPair(total=0, covered=0),
        env_vars=MetricPair(total=0, covered=0),
        auth_surfaces=MetricPair(total=0, covered=0),
        state_mgmt=MetricPair(total=0, covered=0),
        middleware=MetricPair(total=0, covered=0),
        integrations=MetricPair(total=0, covered=0),
        ui_flows=MetricPair(total=0, covered=0),
    )
    return CoverageEvaluation(
        metrics=metrics,
        gates=[GateResult(name="Routes", threshold=95.0, actual=100.0, passed=True)],
    )


def _make_gap_report() -> GapReport:
    return GapReport(entries=[])


# The patch targets for all stage modules
_P = "repo_mirror_kit.harvester.pipeline"
_CLONE = f"{_P}.clone_repository"
_SCAN = f"{_P}.scan"
_WRITE_REPORT = f"{_P}.write_report"
_RUN_DETECTION = f"{_P}.run_detection"
_ANALYZE_ROUTES = f"{_P}.analyze_routes"
_ANALYZE_COMPONENTS = f"{_P}.analyze_components"
_ANALYZE_APIS = f"{_P}.analyze_api_endpoints"
_ANALYZE_MODELS = f"{_P}.analyze_models"
_ANALYZE_AUTH = f"{_P}.analyze_auth"
_ANALYZE_CONFIG = f"{_P}.analyze_config"
_ANALYZE_CROSSCUTTING = f"{_P}.analyze_crosscutting"
_ANALYZE_STATE_MGMT = f"{_P}.analyze_state_management"
_ANALYZE_MIDDLEWARE = f"{_P}.analyze_middleware"
_ANALYZE_INTEGRATIONS = f"{_P}.analyze_integrations"
_ANALYZE_UI_FLOWS = f"{_P}.analyze_ui_flows"
_WRITE_SURFACE_MAP = f"{_P}.write_surface_map"
_BUILD_TRACEABILITY = f"{_P}.build_traceability_maps"
_WRITE_BEANS = f"{_P}.write_beans"
_COMPUTE_METRICS = f"{_P}.compute_metrics"
_EVALUATE_THRESHOLDS = f"{_P}.evaluate_thresholds"
_WRITE_COVERAGE = f"{_P}.write_coverage_reports"
_RUN_GAP_QUERIES = f"{_P}.run_all_gap_queries"
_WRITE_GAPS = f"{_P}.write_gaps_report"


def _build_patches(
    tmp_path: Path,
    surfaces: SurfaceCollection | None = None,
) -> dict[str, object]:
    """Return a dict of target -> return_value for every stage function."""
    s = surfaces if surfaces is not None else _make_nonempty_surfaces()
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = output_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    evaluation = _make_evaluation()
    gap_report = _make_gap_report()
    report_path = output_dir / "reports"
    report_path.mkdir(parents=True, exist_ok=True)

    return {
        _CLONE: _make_clone_result(tmp_path),
        _SCAN: _make_inventory(),
        _WRITE_REPORT: report_path / "inventory.json",
        _RUN_DETECTION: _make_profile(),
        _ANALYZE_ROUTES: s.routes,
        _ANALYZE_COMPONENTS: s.components,
        _ANALYZE_APIS: s.apis,
        _ANALYZE_MODELS: s.models,
        _ANALYZE_AUTH: s.auth,
        _ANALYZE_CONFIG: s.config,
        _ANALYZE_CROSSCUTTING: s.crosscutting,
        _ANALYZE_STATE_MGMT: s.state_mgmt,
        _ANALYZE_MIDDLEWARE: s.middleware,
        _ANALYZE_INTEGRATIONS: s.integrations,
        _ANALYZE_UI_FLOWS: s.ui_flows,
        _WRITE_SURFACE_MAP: (Path("/tmp/a.md"), Path("/tmp/b.json")),
        _BUILD_TRACEABILITY: [],
        _WRITE_BEANS: _make_beans(),
        _COMPUTE_METRICS: evaluation.metrics,
        _EVALUATE_THRESHOLDS: evaluation,
        _WRITE_COVERAGE: (Path("/tmp/c.json"), Path("/tmp/c.md")),
        _RUN_GAP_QUERIES: gap_report,
        _WRITE_GAPS: Path("/tmp/d.md"),
    }


def _enter_all_patches(
    stack: contextlib.ExitStack,
    return_values: dict[str, object],
    *,
    side_effects: dict[str, Exception] | None = None,
    mock_overrides: dict[str, MagicMock] | None = None,
) -> None:
    """Enter patch context managers for all stage targets via ExitStack.

    Args:
        stack: An ExitStack to enter the patches into.
        return_values: Mapping of target -> return value for normal patches.
        side_effects: Optional mapping of target -> exception for failing patches.
        mock_overrides: Optional mapping of target -> MagicMock for custom mocks.
    """
    side_effects = side_effects or {}
    mock_overrides = mock_overrides or {}
    for target, return_val in return_values.items():
        if target in mock_overrides:
            stack.enter_context(patch(target, mock_overrides[target]))
        elif target in side_effects:
            stack.enter_context(patch(target, side_effect=side_effects[target]))
        else:
            stack.enter_context(patch(target, return_value=return_val))


# -----------------------------------------------------------------------
# Tests: HarvestResult dataclass
# -----------------------------------------------------------------------


class TestHarvestResult:
    """Verify HarvestResult fields."""

    def test_success_result(self) -> None:
        r = HarvestResult(
            success=True,
            coverage_passed=True,
            bean_count=10,
            gap_count=0,
            output_dir=Path("/tmp/out"),
        )
        assert r.success is True
        assert r.coverage_passed is True
        assert r.bean_count == 10
        assert r.gap_count == 0
        assert r.error_stage is None
        assert r.error_message is None

    def test_failure_result(self) -> None:
        r = HarvestResult(
            success=False,
            coverage_passed=False,
            bean_count=0,
            gap_count=0,
            error_stage="B",
            error_message="scan failed",
        )
        assert r.success is False
        assert r.error_stage == "B"
        assert r.error_message == "scan failed"


# -----------------------------------------------------------------------
# Tests: Full pipeline flow (all stages mocked)
# -----------------------------------------------------------------------


class TestFullPipelineFlow:
    """Verify end-to-end pipeline execution with mocked stages."""

    def test_runs_all_stages_in_order(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        rv = _build_patches(tmp_path)

        with contextlib.ExitStack() as stack:
            _enter_all_patches(stack, rv)
            pipeline = HarvestPipeline()
            result = pipeline.run(config)

        assert result.success is True
        assert result.coverage_passed is True
        assert result.error_stage is None

    def test_returns_bean_and_gap_counts(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        beans = [
            WrittenBean(
                bean_number=1,
                bean_id="BEAN-001",
                slug="home",
                surface_type="route",
                title="home",
                path=Path("/tmp/b.md"),
            )
        ]
        gap_report = GapReport(entries=[])
        rv = _build_patches(tmp_path)
        rv[_WRITE_BEANS] = beans
        rv[_RUN_GAP_QUERIES] = gap_report

        with contextlib.ExitStack() as stack:
            _enter_all_patches(stack, rv)
            pipeline = HarvestPipeline()
            result = pipeline.run(config)

        assert result.bean_count == 1
        assert result.gap_count == 0

    def test_empty_repo_returns_success_with_zero_beans(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        empty_surfaces = SurfaceCollection()
        rv = _build_patches(tmp_path, surfaces=empty_surfaces)
        # Override analyzer returns with empty lists
        for target in [
            _ANALYZE_ROUTES, _ANALYZE_COMPONENTS, _ANALYZE_APIS, _ANALYZE_MODELS,
            _ANALYZE_AUTH, _ANALYZE_CONFIG, _ANALYZE_CROSSCUTTING,
            _ANALYZE_STATE_MGMT, _ANALYZE_MIDDLEWARE, _ANALYZE_INTEGRATIONS,
            _ANALYZE_UI_FLOWS,
        ]:
            rv[target] = []

        with contextlib.ExitStack() as stack:
            _enter_all_patches(stack, rv)
            pipeline = HarvestPipeline()
            result = pipeline.run(config)

        assert result.success is True
        assert result.bean_count == 0
        assert result.coverage_passed is True


# -----------------------------------------------------------------------
# Tests: Error handling
# -----------------------------------------------------------------------


class TestPipelineErrorHandling:
    """Verify error handling for each stage."""

    @pytest.mark.parametrize(
        "failing_stage",
        [s for s in STAGE_NAMES if s != "C2"],
    )
    def test_error_in_stage_returns_failure(
        self, tmp_path: Path, failing_stage: str
    ) -> None:
        config = _make_config(tmp_path)
        rv = _build_patches(tmp_path)

        # Map stage to the patch target to make fail
        stage_to_target = {
            "A": _CLONE,
            "B": _SCAN,
            "C": _ANALYZE_ROUTES,
            "D": _BUILD_TRACEABILITY,
            "E": _WRITE_BEANS,
            "F": _COMPUTE_METRICS,
        }

        target = stage_to_target[failing_stage]

        with contextlib.ExitStack() as stack:
            _enter_all_patches(
                stack, rv, side_effects={target: RuntimeError("boom")}
            )
            pipeline = HarvestPipeline()
            result = pipeline.run(config)

        assert result.success is False
        assert result.error_stage == failing_stage
        assert result.error_message is not None
        assert "boom" in result.error_message

    def test_error_leaves_state_for_resume(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        rv = _build_patches(tmp_path)

        # Make stage B fail so A is checkpointed
        with contextlib.ExitStack() as stack:
            _enter_all_patches(
                stack, rv, side_effects={_SCAN: RuntimeError("disk full")}
            )
            pipeline = HarvestPipeline()
            result = pipeline.run(config)

        assert result.success is False
        assert result.error_stage == "B"

        # State file should exist for resume
        state_file = config.out / "state" / "state.json"  # type: ignore[operator]
        assert state_file.exists()


# -----------------------------------------------------------------------
# Tests: Resume logic
# -----------------------------------------------------------------------


class TestPipelineResume:
    """Verify resume skips completed stages."""

    def test_resume_skips_completed_stage_a(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        rv = _build_patches(tmp_path)

        # First run: fail at stage B so A is checkpointed
        with contextlib.ExitStack() as stack:
            _enter_all_patches(
                stack, rv, side_effects={_SCAN: RuntimeError("fail")}
            )
            pipeline = HarvestPipeline()
            pipeline.run(config)

        # Second run: resume — clone should NOT be called
        resume_config = _make_config(tmp_path, resume=True)
        clone_mock = MagicMock(return_value=rv[_CLONE])

        with contextlib.ExitStack() as stack:
            _enter_all_patches(stack, rv, mock_overrides={_CLONE: clone_mock})
            pipeline = HarvestPipeline()
            result = pipeline.run(resume_config)

        # Clone should not have been called on resume
        clone_mock.assert_not_called()
        assert result.success is True

    def test_resume_with_no_prior_state_starts_fresh(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path, resume=True)
        rv = _build_patches(tmp_path)
        clone_mock = MagicMock(return_value=rv[_CLONE])

        with contextlib.ExitStack() as stack:
            _enter_all_patches(stack, rv, mock_overrides={_CLONE: clone_mock})
            pipeline = HarvestPipeline()
            result = pipeline.run(config)

        # With no prior state, clone should be called
        clone_mock.assert_called_once()
        assert result.success is True


# -----------------------------------------------------------------------
# Tests: Callback events
# -----------------------------------------------------------------------


class TestPipelineCallbacks:
    """Verify that the pipeline emits correct callback events."""

    def test_callback_fires_stage_start_and_complete(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        rv = _build_patches(tmp_path)
        events: list[PipelineEvent] = []

        with contextlib.ExitStack() as stack:
            _enter_all_patches(stack, rv)
            pipeline = HarvestPipeline(callback=events.append)
            pipeline.run(config)

        # Expect stage_start and stage_complete for each of 7 stages
        start_events = [
            e for e in events if e.event_type == PipelineEventType.STAGE_START
        ]
        complete_events = [
            e for e in events if e.event_type == PipelineEventType.STAGE_COMPLETE
        ]
        assert len(start_events) == 7
        assert len(complete_events) == 7

        # Stages should be in order
        start_stages = [e.stage for e in start_events]
        assert start_stages == STAGE_NAMES

    def test_callback_fires_stage_error_on_failure(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        rv = _build_patches(tmp_path)
        events: list[PipelineEvent] = []

        with contextlib.ExitStack() as stack:
            _enter_all_patches(
                stack, rv,
                side_effects={_ANALYZE_ROUTES: RuntimeError("extractor crash")},
            )
            pipeline = HarvestPipeline(callback=events.append)
            pipeline.run(config)

        error_events = [
            e for e in events if e.event_type == PipelineEventType.STAGE_ERROR
        ]
        assert len(error_events) == 1
        assert error_events[0].stage == "C"
        assert "extractor crash" in error_events[0].message

    def test_callback_fires_progress_update(self, tmp_path: Path) -> None:
        config = _make_config(tmp_path)
        rv = _build_patches(tmp_path)
        events: list[PipelineEvent] = []

        with contextlib.ExitStack() as stack:
            _enter_all_patches(stack, rv)
            pipeline = HarvestPipeline(callback=events.append)
            pipeline.run(config)

        progress_events = [
            e for e in events if e.event_type == PipelineEventType.PROGRESS_UPDATE
        ]
        # Expect progress updates during stage B and C
        assert len(progress_events) > 0
        stage_b_progress = [e for e in progress_events if e.stage == "B"]
        stage_c_progress = [e for e in progress_events if e.stage == "C"]
        assert len(stage_b_progress) >= 1
        assert len(stage_c_progress) >= 1


# -----------------------------------------------------------------------
# Tests: PipelineEvent and PipelineEventType
# -----------------------------------------------------------------------


class TestPipelineEventType:
    """Verify PipelineEventType enum values."""

    def test_event_types(self) -> None:
        assert PipelineEventType.STAGE_START.value == "stage_start"
        assert PipelineEventType.STAGE_COMPLETE.value == "stage_complete"
        assert PipelineEventType.STAGE_ERROR.value == "stage_error"
        assert PipelineEventType.PROGRESS_UPDATE.value == "progress_update"


class TestPipelineEvent:
    """Verify PipelineEvent dataclass."""

    def test_event_fields(self) -> None:
        event = PipelineEvent(
            event_type=PipelineEventType.STAGE_START,
            stage="A",
            message="Starting clone",
            detail={"url": "https://example.com"},
        )
        assert event.event_type == PipelineEventType.STAGE_START
        assert event.stage == "A"
        assert event.message == "Starting clone"
        assert event.detail == {"url": "https://example.com"}

    def test_event_default_detail(self) -> None:
        event = PipelineEvent(
            event_type=PipelineEventType.STAGE_START,
            stage="A",
            message="test",
        )
        assert event.detail == {}


# -----------------------------------------------------------------------
# Tests: Stage names
# -----------------------------------------------------------------------


class TestStageNames:
    """Verify stage ordering constant."""

    def test_stage_names_order(self) -> None:
        assert STAGE_NAMES == ["A", "B", "C", "C2", "D", "E", "F"]
