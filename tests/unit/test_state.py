"""Unit tests for harvester state management."""

from __future__ import annotations

import json
from pathlib import Path

from repo_mirror_kit.harvester.state import (
    PipelineState,
    StageState,
    StageStatus,
    StateManager,
)


class TestStateManagerSaveLoad:
    """Tests for saving and loading pipeline state."""

    def test_save_creates_state_file(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A", "B", "C"])

        assert mgr.state_file.exists()

    def test_save_writes_valid_json(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A", "B"])

        data = json.loads(mgr.state_file.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert "stages" in data
        assert "bean_count" in data
        assert "last_checkpoint" in data

    def test_state_json_includes_stage_name_and_status(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A", "B"])

        data = json.loads(mgr.state_file.read_text(encoding="utf-8"))
        stages = data["stages"]
        assert len(stages) == 2
        assert stages[0]["name"] == "A"
        assert stages[0]["status"] == "pending"
        assert stages[1]["name"] == "B"

    def test_state_json_includes_bean_count(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A"])
        mgr.state.bean_count = 5
        mgr.save()

        data = json.loads(mgr.state_file.read_text(encoding="utf-8"))
        assert data["bean_count"] == 5

    def test_state_json_includes_timestamp(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A"])

        data = json.loads(mgr.state_file.read_text(encoding="utf-8"))
        assert data["last_checkpoint"] is not None
        assert data["started_at"] is not None

    def test_load_restores_saved_state(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A", "B", "C"])
        mgr.complete_stage("A")
        mgr.state.bean_count = 15
        mgr.save()

        mgr2 = StateManager(tmp_path)
        loaded = mgr2.load()

        assert loaded is True
        assert mgr2.is_stage_done("A")
        assert not mgr2.is_stage_done("B")
        assert mgr2.get_bean_count() == 15

    def test_load_round_trip_preserves_all_fields(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A", "B"])
        mgr.complete_stage("A")
        mgr.state.bean_count = 20
        mgr.save()

        mgr2 = StateManager(tmp_path)
        mgr2.load()

        assert len(mgr2.state.stages) == 2
        assert mgr2.state.stages[0].name == "A"
        assert mgr2.state.stages[0].status == StageStatus.DONE
        assert mgr2.state.stages[0].completed_at is not None
        assert mgr2.state.stages[1].name == "B"
        assert mgr2.state.stages[1].status == StageStatus.PENDING
        assert mgr2.state.bean_count == 20
        assert mgr2.state.started_at is not None

    def test_save_creates_state_directory(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "deep" / "nested"
        mgr = StateManager(output_dir)
        mgr.initialize(["A"])

        assert (output_dir / "state").is_dir()
        assert (output_dir / "state" / "stages").is_dir()

    def test_save_uses_atomic_write(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A"])

        # The tmp file should not remain after save
        tmp_file = mgr.state_file.with_suffix(".tmp")
        assert not tmp_file.exists()
        assert mgr.state_file.exists()


class TestStateManagerResume:
    """Tests for resume skip logic."""

    def test_resume_skips_completed_stages(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A", "B", "C"])
        mgr.complete_stage("A")
        mgr.complete_stage("B")

        mgr2 = StateManager(tmp_path)
        mgr2.load()

        assert mgr2.is_stage_done("A")
        assert mgr2.is_stage_done("B")
        assert not mgr2.is_stage_done("C")

    def test_get_pending_stages_returns_only_pending(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A", "B", "C", "D"])
        mgr.complete_stage("A")
        mgr.complete_stage("B")

        mgr2 = StateManager(tmp_path)
        mgr2.load()

        assert mgr2.get_pending_stages() == ["C", "D"]

    def test_get_completed_stages_returns_only_done(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A", "B", "C"])
        mgr.complete_stage("A")

        mgr2 = StateManager(tmp_path)
        mgr2.load()

        assert mgr2.get_completed_stages() == ["A"]

    def test_resume_continues_from_last_bean_count(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A"])
        for i in range(1, 26):
            mgr.record_bean(i)
        mgr.save()

        mgr2 = StateManager(tmp_path)
        mgr2.load()

        assert mgr2.get_bean_count() == 25
        assert mgr2.should_skip_bean(1)
        assert mgr2.should_skip_bean(25)
        assert not mgr2.should_skip_bean(26)

    def test_should_skip_bean_returns_true_for_completed(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A"])
        mgr.state.bean_count = 10

        assert mgr.should_skip_bean(1)
        assert mgr.should_skip_bean(5)
        assert mgr.should_skip_bean(10)

    def test_should_skip_bean_returns_false_for_new(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A"])
        mgr.state.bean_count = 10

        assert not mgr.should_skip_bean(11)
        assert not mgr.should_skip_bean(20)

    def test_completed_beans_not_overwritten_on_resume(self, tmp_path: Path) -> None:
        """Verify that should_skip_bean prevents overwriting completed work."""
        mgr = StateManager(tmp_path)
        mgr.initialize(["A"])

        # Simulate first run: generate 15 beans
        for i in range(1, 16):
            mgr.record_bean(i)
        mgr.save()

        # Simulate resume
        mgr2 = StateManager(tmp_path)
        mgr2.load()

        # Beans 1-15 should be skipped (never overwritten)
        processed: list[int] = []
        for i in range(1, 30):
            if not mgr2.should_skip_bean(i):
                processed.append(i)
                mgr2.record_bean(i)

        # Only beans 16-29 should be processed
        assert processed == list(range(16, 30))

    def test_is_stage_done_returns_false_for_unknown_stage(
        self, tmp_path: Path
    ) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A", "B"])

        assert not mgr.is_stage_done("Z")


class TestStateManagerCheckpoint:
    """Tests for checkpoint behavior."""

    def test_checkpoint_after_stage_completion(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A", "B"])

        # Modify the file after initialize to detect save
        initial_data = mgr.state_file.read_text(encoding="utf-8")
        mgr.complete_stage("A")
        updated_data = mgr.state_file.read_text(encoding="utf-8")

        assert initial_data != updated_data
        data = json.loads(updated_data)
        assert data["stages"][0]["status"] == "done"

    def test_checkpoint_every_n_beans_default(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A"])

        assert mgr.checkpoint_interval == 10

        # Record beans 1-9, no checkpoint at each
        for i in range(1, 10):
            mgr.record_bean(i)

        data_at_9 = json.loads(mgr.state_file.read_text(encoding="utf-8"))
        # After initialize, bean_count was 0 in the saved file
        # record_bean only saves at intervals
        assert data_at_9["bean_count"] == 0

        # Record bean 10, checkpoint should fire
        mgr.record_bean(10)
        data_at_10 = json.loads(mgr.state_file.read_text(encoding="utf-8"))
        assert data_at_10["bean_count"] == 10

    def test_checkpoint_with_custom_interval(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path, checkpoint_interval=5)
        mgr.initialize(["A"])

        assert mgr.checkpoint_interval == 5

        for i in range(1, 5):
            mgr.record_bean(i)

        data_at_4 = json.loads(mgr.state_file.read_text(encoding="utf-8"))
        assert data_at_4["bean_count"] == 0

        mgr.record_bean(5)
        data_at_5 = json.loads(mgr.state_file.read_text(encoding="utf-8"))
        assert data_at_5["bean_count"] == 5

    def test_checkpoint_at_20_beans(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A"])

        for i in range(1, 21):
            mgr.record_bean(i)

        data = json.loads(mgr.state_file.read_text(encoding="utf-8"))
        assert data["bean_count"] == 20

    def test_finalize_saves_state(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        mgr.initialize(["A"])
        mgr.state.bean_count = 7
        mgr.finalize()

        data = json.loads(mgr.state_file.read_text(encoding="utf-8"))
        assert data["bean_count"] == 7


class TestStateManagerCorruptState:
    """Tests for corrupt or missing state file handling."""

    def test_missing_state_file_returns_false(self, tmp_path: Path) -> None:
        mgr = StateManager(tmp_path)
        loaded = mgr.load()

        assert loaded is False
        assert mgr.get_bean_count() == 0
        assert mgr.state.stages == []

    def test_empty_file_starts_fresh(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "state.json").write_text("", encoding="utf-8")

        mgr = StateManager(tmp_path)
        loaded = mgr.load()

        assert loaded is False
        assert mgr.get_bean_count() == 0

    def test_invalid_json_starts_fresh(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "state.json").write_text("{not valid json!!!", encoding="utf-8")

        mgr = StateManager(tmp_path)
        loaded = mgr.load()

        assert loaded is False
        assert mgr.get_bean_count() == 0

    def test_json_array_instead_of_object_starts_fresh(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "state.json").write_text("[1, 2, 3]", encoding="utf-8")

        mgr = StateManager(tmp_path)
        loaded = mgr.load()

        assert loaded is False

    def test_missing_stages_key_starts_fresh(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "state.json").write_text('{"bean_count": 5}', encoding="utf-8")

        mgr = StateManager(tmp_path)
        loaded = mgr.load()

        assert loaded is False

    def test_corrupt_stage_data_starts_fresh(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)
        bad_data = {
            "stages": [{"name": "A", "status": "INVALID_STATUS"}],
            "bean_count": 5,
        }
        (state_dir / "state.json").write_text(json.dumps(bad_data), encoding="utf-8")

        mgr = StateManager(tmp_path)
        loaded = mgr.load()

        assert loaded is False
        assert mgr.get_bean_count() == 0

    def test_non_integer_bean_count_starts_fresh(self, tmp_path: Path) -> None:
        state_dir = tmp_path / "state"
        state_dir.mkdir(parents=True)
        bad_data = {
            "stages": [],
            "bean_count": "not_a_number",
        }
        (state_dir / "state.json").write_text(json.dumps(bad_data), encoding="utf-8")

        mgr = StateManager(tmp_path)
        loaded = mgr.load()

        assert loaded is False


class TestStageState:
    """Tests for the StageState dataclass."""

    def test_to_dict_returns_correct_structure(self) -> None:
        stage = StageState(
            name="A", status=StageStatus.DONE, completed_at="2026-01-01T00:00:00+00:00"
        )
        result = stage.to_dict()

        assert result == {
            "name": "A",
            "status": "done",
            "completed_at": "2026-01-01T00:00:00+00:00",
        }

    def test_from_dict_round_trip(self) -> None:
        original = StageState(name="B", status=StageStatus.PENDING)
        data = original.to_dict()
        restored = StageState.from_dict(data)

        assert restored.name == original.name
        assert restored.status == original.status
        assert restored.completed_at == original.completed_at

    def test_default_status_is_pending(self) -> None:
        stage = StageState(name="X")
        assert stage.status == StageStatus.PENDING
        assert stage.completed_at is None


class TestPipelineState:
    """Tests for the PipelineState dataclass."""

    def test_to_dict_and_from_dict_round_trip(self) -> None:
        original = PipelineState(
            stages=[
                StageState(
                    name="A",
                    status=StageStatus.DONE,
                    completed_at="2026-01-01T00:00:00+00:00",
                ),
                StageState(name="B", status=StageStatus.PENDING),
            ],
            bean_count=42,
            last_checkpoint="2026-01-01T01:00:00+00:00",
            started_at="2026-01-01T00:00:00+00:00",
        )
        data = original.to_dict()
        restored = PipelineState.from_dict(data)

        assert len(restored.stages) == 2
        assert restored.stages[0].name == "A"
        assert restored.stages[0].status == StageStatus.DONE
        assert restored.bean_count == 42
        assert restored.started_at == "2026-01-01T00:00:00+00:00"

    def test_default_state_is_empty(self) -> None:
        state = PipelineState()
        assert state.stages == []
        assert state.bean_count == 0
        assert state.last_checkpoint is None
        assert state.started_at is None
