"""Harvester run state tracking.

Provides StateManager for saving and loading pipeline progress to
``state/state.json``, supporting checkpoint and resume workflows.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_DIR = "state"
_STATE_FILE = "state.json"
_STAGES_DIR = "stages"
_DEFAULT_CHECKPOINT_INTERVAL = 10


class StageStatus(StrEnum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    DONE = "done"


@dataclass
class StageState:
    """Tracks the status of a single pipeline stage.

    Args:
        name: Identifier for the pipeline stage (e.g. "A", "B").
        status: Current status of the stage.
        completed_at: ISO-format timestamp when the stage completed.
    """

    name: str
    status: StageStatus = StageStatus.PENDING
    completed_at: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Serialize to a plain dict for JSON output."""
        return {
            "name": self.name,
            "status": self.status.value,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | None]) -> StageState:
        """Deserialize from a plain dict.

        Args:
            data: Dictionary with name, status, and completed_at keys.

        Returns:
            A StageState instance.
        """
        return cls(
            name=str(data["name"]),
            status=StageStatus(str(data["status"])),
            completed_at=data.get("completed_at"),
        )


@dataclass
class PipelineState:
    """Full pipeline state persisted to state.json.

    Args:
        stages: Ordered list of stage states.
        bean_count: Number of beans generated so far.
        last_checkpoint: ISO-format timestamp of the last checkpoint.
        started_at: ISO-format timestamp when the pipeline run started.
    """

    stages: list[StageState] = field(default_factory=list)
    bean_count: int = 0
    last_checkpoint: str | None = None
    started_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to a plain dict for JSON output."""
        return {
            "stages": [s.to_dict() for s in self.stages],
            "bean_count": self.bean_count,
            "last_checkpoint": self.last_checkpoint,
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PipelineState:
        """Deserialize from a plain dict.

        Args:
            data: Dictionary matching the state.json schema.

        Returns:
            A PipelineState instance.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If field values are invalid.
        """
        raw_stages = data.get("stages")
        if not isinstance(raw_stages, list):
            msg = "stages must be a list"
            raise ValueError(msg)

        stages = [StageState.from_dict(s) for s in raw_stages]
        bean_count = data.get("bean_count", 0)
        if not isinstance(bean_count, int):
            msg = "bean_count must be an int"
            raise ValueError(msg)

        last_cp = data.get("last_checkpoint")
        started = data.get("started_at")

        return cls(
            stages=stages,
            bean_count=bean_count,
            last_checkpoint=str(last_cp) if last_cp is not None else None,
            started_at=str(started) if started is not None else None,
        )


class StateManager:
    """Manage pipeline progress persistence for checkpoint and resume.

    Saves and loads pipeline state to ``<output_dir>/state/state.json``.
    Supports checkpointing after each stage and every N beans during
    bean generation.

    Args:
        output_dir: Root output directory (e.g. the cloned repo's ``ai/``).
        checkpoint_interval: Save state every N beans during generation.
    """

    def __init__(
        self,
        output_dir: Path,
        checkpoint_interval: int = _DEFAULT_CHECKPOINT_INTERVAL,
    ) -> None:
        self._output_dir = output_dir
        self._checkpoint_interval = checkpoint_interval
        self._state_dir = output_dir / _STATE_DIR
        self._state_file = self._state_dir / _STATE_FILE
        self._stages_dir = self._state_dir / _STAGES_DIR
        self._state = PipelineState()

    @property
    def state(self) -> PipelineState:
        """Return the current pipeline state."""
        return self._state

    @property
    def state_file(self) -> Path:
        """Return the path to the state JSON file."""
        return self._state_file

    @property
    def checkpoint_interval(self) -> int:
        """Return the configured checkpoint interval."""
        return self._checkpoint_interval

    def initialize(self, stage_names: list[str]) -> None:
        """Set up a fresh pipeline state with the given stages.

        Creates the state directory structure and initializes all stages
        to pending.

        Args:
            stage_names: Ordered list of stage identifiers.
        """
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._stages_dir.mkdir(parents=True, exist_ok=True)
        self._state = PipelineState(
            stages=[StageState(name=name) for name in stage_names],
            bean_count=0,
            last_checkpoint=None,
            started_at=_now_iso(),
        )
        self.save()

    def save(self) -> None:
        """Persist current state to state.json."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state.last_checkpoint = _now_iso()
        data = self._state.to_dict()
        tmp_file = self._state_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        tmp_file.replace(self._state_file)
        logger.debug("state_saved", extra={"path": str(self._state_file)})

    def load(self) -> bool:
        """Load state from state.json if it exists and is valid.

        Returns:
            True if state was loaded successfully, False if the file is
            missing or corrupt (state is reset to empty in that case).
        """
        if not self._state_file.exists():
            logger.info(
                "state_file_not_found",
                extra={"path": str(self._state_file)},
            )
            self._state = PipelineState()
            return False

        try:
            raw = self._state_file.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                msg = "state.json root must be an object"
                raise ValueError(msg)
            self._state = PipelineState.from_dict(data)
            logger.info("state_loaded", extra={"path": str(self._state_file)})
            return True
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            logger.warning(
                "state_corrupt_starting_fresh",
                extra={"path": str(self._state_file), "error": str(exc)},
            )
            self._state = PipelineState()
            return False

    def is_stage_done(self, stage_name: str) -> bool:
        """Check whether a stage is marked as done.

        Args:
            stage_name: The stage identifier to check.

        Returns:
            True if the stage exists and has status DONE.
        """
        for stage in self._state.stages:
            if stage.name == stage_name:
                return stage.status == StageStatus.DONE
        return False

    def complete_stage(self, stage_name: str) -> None:
        """Mark a stage as done and checkpoint.

        Args:
            stage_name: The stage identifier to mark complete.
        """
        for stage in self._state.stages:
            if stage.name == stage_name:
                stage.status = StageStatus.DONE
                stage.completed_at = _now_iso()
                break
        self.save()

    def get_bean_count(self) -> int:
        """Return the number of beans recorded in state."""
        return self._state.bean_count

    def record_bean(self, bean_number: int) -> None:
        """Record a bean and checkpoint if the interval is reached.

        Updates the bean count and saves state every
        ``checkpoint_interval`` beans.

        Args:
            bean_number: The 1-based bean number just completed.
        """
        self._state.bean_count = bean_number
        if bean_number % self._checkpoint_interval == 0:
            self.save()

    def should_skip_bean(self, bean_number: int) -> bool:
        """Check whether a bean should be skipped on resume.

        A bean is skipped if its number is at or below the last
        checkpointed bean count.

        Args:
            bean_number: The 1-based bean number to check.

        Returns:
            True if this bean was already completed.
        """
        return bean_number <= self._state.bean_count

    def finalize(self) -> None:
        """Save final state after the pipeline completes."""
        self.save()

    def get_pending_stages(self) -> list[str]:
        """Return names of stages that are not yet done.

        Returns:
            List of stage names with status PENDING.
        """
        return [s.name for s in self._state.stages if s.status == StageStatus.PENDING]

    def get_completed_stages(self) -> list[str]:
        """Return names of stages that are done.

        Returns:
            List of stage names with status DONE.
        """
        return [s.name for s in self._state.stages if s.status == StageStatus.DONE]


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(tz=UTC).isoformat()
