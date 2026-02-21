"""Pipeline orchestrator for the requirements harvester.

Sequences Stages A through F (with optional C2 for LLM enrichment),
manages checkpoints, handles errors, and provides a callback interface
for progress reporting. Both the CLI and GUI entry points delegate to
``HarvestPipeline.run()``.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers import (
    SurfaceCollection,
    analyze_api_endpoints,
    analyze_auth,
    analyze_components,
    analyze_config,
    analyze_crosscutting,
    analyze_dependencies,
    analyze_integrations,
    analyze_middleware,
    analyze_models,
    analyze_routes,
    analyze_state_management,
    analyze_ui_flows,
)
from repo_mirror_kit.harvester.beans.writer import WrittenBean, write_beans
from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.detectors.base import StackProfile, run_detection
from repo_mirror_kit.harvester.git_ops import CloneResult, clone_repository
from repo_mirror_kit.harvester.harvest_logging import configure_logging
from repo_mirror_kit.harvester.inventory import InventoryResult, scan, write_report
from repo_mirror_kit.harvester.reports.coverage import (
    CoverageEvaluation,
    compute_metrics,
    evaluate_thresholds,
    write_coverage_reports,
)
from repo_mirror_kit.harvester.reports.gaps import (
    GapReport,
    run_all_gap_queries,
    write_gaps_report,
)
from repo_mirror_kit.harvester.reports.surface_map import write_surface_map
from repo_mirror_kit.harvester.reports.traceability import build_traceability_maps
from repo_mirror_kit.harvester.state import StateManager

logger = structlog.get_logger()

# Ordered stage names matching the spec
STAGE_NAMES: list[str] = ["A", "B", "C", "C2", "D", "E", "F"]


class PipelineEventType(StrEnum):
    """Types of events emitted by the pipeline."""

    STAGE_START = "stage_start"
    STAGE_COMPLETE = "stage_complete"
    STAGE_ERROR = "stage_error"
    PROGRESS_UPDATE = "progress_update"


@dataclass(frozen=True)
class PipelineEvent:
    """An event emitted during pipeline execution.

    Attributes:
        event_type: The type of event.
        stage: The stage this event relates to.
        message: Human-readable description.
        detail: Optional additional data.
    """

    event_type: PipelineEventType
    stage: str
    message: str
    detail: dict[str, object] = field(default_factory=dict)


# Type alias for the callback signature
PipelineCallback = Callable[[PipelineEvent], None]


class PipelineError(Exception):
    """Raised when a pipeline stage fails.

    Attributes:
        stage: The stage that failed.
    """

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(f"Stage {stage} failed: {message}")


@dataclass(frozen=True)
class HarvestResult:
    """Result of a complete pipeline run.

    Attributes:
        success: Whether the pipeline completed without errors.
        coverage_passed: Whether all coverage gates passed.
        bean_count: Number of beans generated.
        gap_count: Number of coverage gaps found.
        error_stage: Stage where an error occurred, if any.
        error_message: Error description, if any.
        output_dir: Path to the output directory.
    """

    success: bool
    coverage_passed: bool
    bean_count: int
    gap_count: int
    error_stage: str | None = None
    error_message: str | None = None
    output_dir: Path | None = None


class HarvestPipeline:
    """Orchestrates the harvester pipeline stages A through F.

    Sequences stage execution, manages checkpointing via StateManager,
    supports resume from the last incomplete stage, and emits progress
    events through an optional callback.
    """

    def __init__(
        self,
        callback: PipelineCallback | None = None,
    ) -> None:
        self._callback = callback

    def run(self, config: HarvestConfig) -> HarvestResult:
        """Execute the full pipeline.

        Args:
            config: Harvest configuration.

        Returns:
            A HarvestResult summarizing the outcome.
        """
        configure_logging(config.log_level)

        output_dir = config.out or Path(tempfile.mkdtemp(prefix="harvest-"))
        output_dir.mkdir(parents=True, exist_ok=True)

        state = StateManager(output_dir)

        if config.resume:
            loaded = state.load()
            if loaded:
                logger.info(
                    "pipeline_resuming",
                    completed=state.get_completed_stages(),
                    pending=state.get_pending_stages(),
                )
            else:
                logger.info("pipeline_no_prior_state_starting_fresh")
                state.initialize(STAGE_NAMES)
        else:
            state.initialize(STAGE_NAMES)

        logger.info("pipeline_starting", output_dir=str(output_dir))

        # Mutable containers for stage outputs shared across stages
        clone_result: CloneResult | None = None
        inventory_result: InventoryResult | None = None
        profile: StackProfile | None = None
        surfaces: SurfaceCollection | None = None
        beans: list[WrittenBean] = []
        evaluation: CoverageEvaluation | None = None
        gap_report: GapReport | None = None

        try:
            # --- Stage A: Clone & Normalize ---
            if not state.is_stage_done("A"):
                self._emit(PipelineEventType.STAGE_START, "A", "Cloning repository")
                try:
                    clone_result = self._run_stage_a(config, output_dir)
                except Exception as exc:
                    return self._handle_stage_error("A", exc, state, output_dir)
                state.complete_stage("A")
                self._emit(
                    PipelineEventType.STAGE_COMPLETE,
                    "A",
                    "Clone complete",
                )
            else:
                logger.info("stage_skipped_resume", stage="A")
                # Reconstruct workdir for resumed runs
                clone_result = CloneResult(
                    repo_dir=output_dir / "repo",
                    skipped_symlinks=[],
                    normalized_files=0,
                )

            workdir = clone_result.repo_dir

            # --- Stage B: Inventory + Detection ---
            if not state.is_stage_done("B"):
                self._emit(
                    PipelineEventType.STAGE_START,
                    "B",
                    "Scanning inventory and detecting frameworks",
                )
                try:
                    inventory_result, profile = self._run_stage_b(
                        config, workdir, output_dir
                    )
                except Exception as exc:
                    return self._handle_stage_error("B", exc, state, output_dir)
                state.complete_stage("B")
                self._emit(
                    PipelineEventType.STAGE_COMPLETE,
                    "B",
                    "Inventory and detection complete",
                    {
                        "files": inventory_result.total_files,
                        "stacks": list(profile.stacks.keys()),
                    },
                )
            else:
                logger.info("stage_skipped_resume", stage="B")
                # On resume, re-run inventory and detection since results are
                # needed by later stages and are fast to recompute
                inventory_result, profile = self._run_stage_b(
                    config, workdir, output_dir
                )

            # --- Stage C: Surface Extraction ---
            if not state.is_stage_done("C"):
                self._emit(
                    PipelineEventType.STAGE_START,
                    "C",
                    "Extracting surfaces",
                )
                try:
                    surfaces = self._run_stage_c(
                        workdir, inventory_result, profile, output_dir
                    )
                except Exception as exc:
                    return self._handle_stage_error("C", exc, state, output_dir)
                state.complete_stage("C")
                self._emit(
                    PipelineEventType.STAGE_COMPLETE,
                    "C",
                    "Surface extraction complete",
                    {"total_surfaces": len(surfaces)},
                )
            else:
                logger.info("stage_skipped_resume", stage="C")
                surfaces = self._run_stage_c(
                    workdir, inventory_result, profile, output_dir
                )

            # Handle empty repository gracefully
            if len(surfaces) == 0:
                logger.info("pipeline_empty_repo_no_surfaces")
                state.finalize()
                return HarvestResult(
                    success=True,
                    coverage_passed=True,
                    bean_count=0,
                    gap_count=0,
                    output_dir=output_dir,
                )

            # --- Stage C2: LLM Enrichment (optional) ---
            if not state.is_stage_done("C2"):
                self._emit(
                    PipelineEventType.STAGE_START,
                    "C2",
                    "Enriching surfaces with LLM",
                )
                try:
                    surfaces = self._run_stage_c2(surfaces, config, workdir)
                except Exception as exc:
                    return self._handle_stage_error("C2", exc, state, output_dir)
                state.complete_stage("C2")
                self._emit(
                    PipelineEventType.STAGE_COMPLETE,
                    "C2",
                    "LLM enrichment complete",
                )
            else:
                logger.info("stage_skipped_resume", stage="C2")

            # --- Stage D: Traceability ---
            if not state.is_stage_done("D"):
                self._emit(
                    PipelineEventType.STAGE_START,
                    "D",
                    "Building traceability maps",
                )
                try:
                    self._run_stage_d(surfaces, output_dir)
                except Exception as exc:
                    return self._handle_stage_error("D", exc, state, output_dir)
                state.complete_stage("D")
                self._emit(
                    PipelineEventType.STAGE_COMPLETE,
                    "D",
                    "Traceability complete",
                )
            else:
                logger.info("stage_skipped_resume", stage="D")

            # --- Stage E: Bean Generation ---
            if not state.is_stage_done("E"):
                self._emit(
                    PipelineEventType.STAGE_START,
                    "E",
                    "Generating beans",
                )
                try:
                    beans = self._run_stage_e(surfaces, output_dir, state)
                except Exception as exc:
                    return self._handle_stage_error("E", exc, state, output_dir)
                state.complete_stage("E")
                self._emit(
                    PipelineEventType.STAGE_COMPLETE,
                    "E",
                    "Bean generation complete",
                    {"bean_count": len(beans)},
                )
            else:
                logger.info("stage_skipped_resume", stage="E")
                beans = write_beans(surfaces, output_dir, state)

            # --- Stage F: Coverage Gates ---
            if not state.is_stage_done("F"):
                self._emit(
                    PipelineEventType.STAGE_START,
                    "F",
                    "Evaluating coverage gates",
                )
                try:
                    evaluation, gap_report = self._run_stage_f(
                        surfaces, beans, inventory_result, output_dir
                    )
                except Exception as exc:
                    return self._handle_stage_error("F", exc, state, output_dir)
                state.complete_stage("F")
                self._emit(
                    PipelineEventType.STAGE_COMPLETE,
                    "F",
                    "Coverage gates complete",
                    {
                        "all_passed": evaluation.all_passed,
                        "gap_count": gap_report.total_gaps,
                    },
                )
            else:
                logger.info("stage_skipped_resume", stage="F")
                evaluation, gap_report = self._run_stage_f(
                    surfaces, beans, inventory_result, output_dir
                )

        except Exception as exc:
            logger.error("pipeline_unexpected_error", error=str(exc))
            state.finalize()
            return HarvestResult(
                success=False,
                coverage_passed=False,
                bean_count=len(beans),
                gap_count=0,
                error_stage="unknown",
                error_message=str(exc),
                output_dir=output_dir,
            )

        state.finalize()

        logger.info(
            "pipeline_complete",
            bean_count=len(beans),
            gap_count=gap_report.total_gaps,
            coverage_passed=evaluation.all_passed,
        )

        return HarvestResult(
            success=True,
            coverage_passed=evaluation.all_passed,
            bean_count=len(beans),
            gap_count=gap_report.total_gaps,
            output_dir=output_dir,
        )

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _run_stage_a(
        self,
        config: HarvestConfig,
        output_dir: Path,
    ) -> CloneResult:
        """Stage A: clone repository and normalize."""
        repo_dir = output_dir / "repo"
        return clone_repository(config.repo, config.ref, repo_dir)

    def _run_stage_b(
        self,
        config: HarvestConfig,
        workdir: Path,
        output_dir: Path,
    ) -> tuple[InventoryResult, StackProfile]:
        """Stage B: inventory scan and framework detection."""
        inventory_result = scan(workdir, config)
        write_report(output_dir, inventory_result)

        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "B",
            f"Inventory: {inventory_result.total_files} files",
        )

        profile = run_detection(inventory_result)

        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "B",
            f"Detected: {list(profile.stacks.keys())}",
        )

        return inventory_result, profile

    def _run_stage_c(
        self,
        workdir: Path,
        inventory: InventoryResult,
        profile: StackProfile,
        output_dir: Path,
    ) -> SurfaceCollection:
        """Stage C: extract all surfaces from the repository.

        Iterates the full worklist deterministically. Each analyzer runs
        against the full inventory — no early exit.
        """
        routes = analyze_routes(inventory, profile, workdir)
        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "C",
            f"Routes: {len(routes)} found",
        )

        components = analyze_components(inventory, profile, workdir)
        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "C",
            f"Components: {len(components)} found",
        )

        apis = analyze_api_endpoints(workdir, inventory, profile)
        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "C",
            f"APIs: {len(apis)} found",
        )

        models = analyze_models(workdir, inventory, profile)
        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "C",
            f"Models: {len(models)} found",
        )

        auth = analyze_auth(inventory, profile, workdir)
        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "C",
            f"Auth: {len(auth)} found",
        )

        config_surfaces = analyze_config(inventory, profile, workdir)
        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "C",
            f"Config: {len(config_surfaces)} found",
        )

        crosscutting = analyze_crosscutting(inventory, workdir)
        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "C",
            f"Crosscutting: {len(crosscutting)} found",
        )

        state_mgmt = analyze_state_management(inventory, profile, workdir)
        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "C",
            f"State management: {len(state_mgmt)} found",
        )

        middleware = analyze_middleware(inventory, profile, workdir)
        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "C",
            f"Middleware: {len(middleware)} found",
        )

        integrations = analyze_integrations(inventory, profile, workdir)
        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "C",
            f"Integrations: {len(integrations)} found",
        )

        ui_flows = analyze_ui_flows(inventory, profile, workdir)
        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "C",
            f"UI flows: {len(ui_flows)} found",
        )

        dependencies = analyze_dependencies(inventory, profile, workdir)
        self._emit(
            PipelineEventType.PROGRESS_UPDATE,
            "C",
            f"Dependencies: {len(dependencies)} found",
        )

        surfaces = SurfaceCollection(
            routes=routes,
            components=components,
            apis=apis,
            models=models,
            auth=auth,
            config=config_surfaces,
            crosscutting=crosscutting,
            state_mgmt=state_mgmt,
            middleware=middleware,
            integrations=integrations,
            ui_flows=ui_flows,
            dependencies=dependencies,
        )

        write_surface_map(output_dir, surfaces, profile)

        return surfaces

    def _run_stage_c2(
        self,
        surfaces: SurfaceCollection,
        config: HarvestConfig,
        workdir: Path,
    ) -> SurfaceCollection:
        """Stage C2: enrich surfaces with LLM-generated behavioral data."""
        from repo_mirror_kit.harvester.llm import enrich_surfaces

        return enrich_surfaces(surfaces, config, workdir, self._callback)

    def _run_stage_d(
        self,
        surfaces: SurfaceCollection,
        output_dir: Path,
    ) -> list[Path]:
        """Stage D: build traceability maps."""
        return build_traceability_maps(surfaces, output_dir)

    def _run_stage_e(
        self,
        surfaces: SurfaceCollection,
        output_dir: Path,
        state: StateManager,
    ) -> list[WrittenBean]:
        """Stage E: generate bean files."""
        return write_beans(surfaces, output_dir, state)

    def _run_stage_f(
        self,
        surfaces: SurfaceCollection,
        beans: list[WrittenBean],
        inventory: InventoryResult,
        output_dir: Path,
    ) -> tuple[CoverageEvaluation, GapReport]:
        """Stage F: coverage gates and gap analysis."""
        metrics = compute_metrics(surfaces, beans, inventory)
        evaluation = evaluate_thresholds(metrics)
        write_coverage_reports(output_dir, evaluation)

        gap_report = run_all_gap_queries(surfaces, beans)
        write_gaps_report(output_dir, gap_report)

        return evaluation, gap_report

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: PipelineEventType,
        stage: str,
        message: str,
        detail: dict[str, object] | None = None,
    ) -> None:
        """Emit a pipeline event to the callback if one is registered."""
        event = PipelineEvent(
            event_type=event_type,
            stage=stage,
            message=message,
            detail=detail or {},
        )
        logger.info(
            event_type.value,
            stage=stage,
            message=message,
            **{k: v for k, v in event.detail.items() if v is not None},
        )
        if self._callback is not None:
            self._callback(event)

    def _handle_stage_error(
        self,
        stage: str,
        exc: Exception,
        state: StateManager,
        output_dir: Path,
    ) -> HarvestResult:
        """Handle an error in a pipeline stage.

        Logs the error, emits a stage_error event, saves state for
        resume, and returns a failure result.
        """
        error_msg = str(exc)
        logger.error("stage_failed", stage=stage, error=error_msg)
        self._emit(
            PipelineEventType.STAGE_ERROR,
            stage,
            f"Stage {stage} failed: {error_msg}",
            {"error": error_msg},
        )
        state.finalize()
        return HarvestResult(
            success=False,
            coverage_passed=False,
            bean_count=0,
            gap_count=0,
            error_stage=stage,
            error_message=error_msg,
            output_dir=output_dir,
        )
