from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from repo_mirror_kit.services.clone_service import clone_repository


class CloneWorker(QThread):
    """Background worker that runs a git clone operation.

    Emits output_received for each line of git output and
    clone_finished when the operation completes.
    """

    output_received = Signal(str)
    clone_finished = Signal(bool, str)

    def __init__(
        self,
        url: str,
        project_name: str,
        base_dir: Path | None = None,
        parent: QThread | None = None,
    ) -> None:
        super().__init__(parent)
        self._url = url
        self._project_name = project_name
        self._base_dir = base_dir

    def run(self) -> None:
        """Execute the clone operation in a background thread."""
        gen = clone_repository(self._url, self._project_name, self._base_dir)
        try:
            while True:
                line = next(gen)
                self.output_received.emit(line)
        except StopIteration as exc:
            result = exc.value
            self.clone_finished.emit(result.success, result.message)
