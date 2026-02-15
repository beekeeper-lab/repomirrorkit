from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

from repo_mirror_kit.services.clone_service import CloneResult
from repo_mirror_kit.workers.clone_worker import CloneWorker


class TestCloneWorker:
    """Tests for CloneWorker signal emission."""

    @patch("repo_mirror_kit.workers.clone_worker.clone_repository")
    def test_emits_output_and_finished_on_success(
        self, mock_clone: MagicMock, qapp: QApplication, tmp_path: Path
    ) -> None:
        def fake_gen(
            url: str, project_name: str, base_dir: Path | None = None
        ) -> MagicMock:
            """Simulate a generator that yields lines then returns a result."""
            gen = MagicMock()
            gen.__next__ = MagicMock(
                side_effect=[
                    "line1",
                    "line2",
                    StopIteration(CloneResult(True, "Clone complete")),
                ]
            )
            gen.__iter__ = MagicMock(return_value=gen)
            return gen

        mock_clone.side_effect = fake_gen

        worker = CloneWorker("https://example.com/repo.git", "test", tmp_path)

        output_lines: list[str] = []
        finished_args: list[tuple[bool, str]] = []
        worker.output_received.connect(lambda line: output_lines.append(line))
        worker.clone_finished.connect(lambda s, m: finished_args.append((s, m)))

        worker.run()

        assert output_lines == ["line1", "line2"]
        assert len(finished_args) == 1
        assert finished_args[0] == (True, "Clone complete")

    @patch("repo_mirror_kit.workers.clone_worker.clone_repository")
    def test_emits_finished_on_failure(
        self, mock_clone: MagicMock, qapp: QApplication, tmp_path: Path
    ) -> None:
        def fake_gen(
            url: str, project_name: str, base_dir: Path | None = None
        ) -> MagicMock:
            gen = MagicMock()
            gen.__next__ = MagicMock(
                side_effect=[
                    StopIteration(CloneResult(False, "Directory already exists"))
                ]
            )
            gen.__iter__ = MagicMock(return_value=gen)
            return gen

        mock_clone.side_effect = fake_gen

        worker = CloneWorker("https://example.com/repo.git", "test", tmp_path)

        finished_args: list[tuple[bool, str]] = []
        worker.clone_finished.connect(lambda s, m: finished_args.append((s, m)))

        worker.run()

        assert len(finished_args) == 1
        assert finished_args[0] == (False, "Directory already exists")
