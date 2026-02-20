from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from repo_mirror_kit.services.clone_service import (
    check_git_available,
    validate_git_url,
    validate_project_name,
)
from repo_mirror_kit.workers.clone_worker import CloneWorker
from repo_mirror_kit.workers.harvest_worker import HarvestWorker


class MainWindow(QMainWindow):
    """Main application window for RepoMirrorKit."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("RepoMirrorKit")
        self.setMinimumSize(600, 400)
        self._worker: CloneWorker | None = None
        self._harvest_worker: HarvestWorker | None = None
        self._clone_project_name: str | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Initialize the UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Project name field
        name_layout = QHBoxLayout()
        name_label = QLabel("Project Name:")
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("my-project")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self._name_input)
        layout.addLayout(name_layout)

        self._name_error = QLabel()
        self._name_error.setStyleSheet("color: red;")
        self._name_error.hide()
        layout.addWidget(self._name_error)

        # Git URL field
        url_layout = QHBoxLayout()
        url_label = QLabel("Git URL:")
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://github.com/user/repo.git")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self._url_input)
        layout.addLayout(url_layout)

        self._url_error = QLabel()
        self._url_error.setStyleSheet("color: red;")
        self._url_error.hide()
        layout.addWidget(self._url_error)

        # Fetch button
        self._fetch_button = QPushButton("Fetch")
        layout.addWidget(self._fetch_button)

        # Generate Requirements button (hidden until clone succeeds)
        self._harvest_button = QPushButton("Generate Requirements")
        self._harvest_button.setEnabled(False)
        self._harvest_button.hide()
        layout.addWidget(self._harvest_button)

        # Status label
        self._status_label = QLabel()
        layout.addWidget(self._status_label)

        # Log area (collapsible)
        self._log_toggle = QPushButton("Show Log")
        self._log_toggle.setCheckable(True)
        layout.addWidget(self._log_toggle)

        self._log_area = QTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.hide()
        layout.addWidget(self._log_area)

        layout.addStretch()

    def _connect_signals(self) -> None:
        """Connect UI signals to slots."""
        self._fetch_button.clicked.connect(self._on_fetch_clicked)
        self._log_toggle.toggled.connect(self._on_log_toggled)
        self._harvest_button.clicked.connect(self._on_harvest_clicked)

    @Slot()
    def _on_fetch_clicked(self) -> None:
        """Handle Fetch button click."""
        self._name_error.hide()
        self._url_error.hide()

        project_name = self._name_input.text().strip()
        git_url = self._url_input.text().strip()

        name_err = validate_project_name(project_name)
        url_err = validate_git_url(git_url)

        has_error = False
        if name_err:
            self._name_error.setText(name_err)
            self._name_error.show()
            has_error = True
        if url_err:
            self._url_error.setText(url_err)
            self._url_error.show()
            has_error = True

        if has_error:
            return

        if not check_git_available():
            self._status_label.setText("Error: git is not installed or not on PATH.")
            return

        self._fetch_button.setEnabled(False)
        self._harvest_button.setEnabled(False)
        self._status_label.setText("Cloning...")
        self._log_area.clear()
        self._log_area.show()
        self._log_toggle.setChecked(True)

        self._worker = CloneWorker(git_url, project_name)
        self._worker.output_received.connect(self._on_output_received)
        self._worker.clone_finished.connect(self._on_clone_finished)
        self._worker.start()

    @Slot(str)
    def _on_output_received(self, line: str) -> None:
        """Append a line of clone output to the log area."""
        self._log_area.append(line)

    @Slot(bool, str)
    def _on_clone_finished(self, success: bool, message: str) -> None:
        """Handle clone completion."""
        self._fetch_button.setEnabled(True)
        if success:
            self._status_label.setText("Clone complete")
            self._clone_project_name = self._name_input.text().strip()
            self._harvest_button.show()
            self._harvest_button.setEnabled(True)
        else:
            self._status_label.setText(f"Error: {message}")
        self._worker = None

    @Slot()
    def _on_harvest_clicked(self) -> None:
        """Handle Generate Requirements button click."""
        if self._clone_project_name is None:
            return

        project_dir = Path("projects") / self._clone_project_name
        output_dir = project_dir / "ai"

        self._set_harvesting_state(enabled=False)
        self._status_label.setText("Harvesting: starting pipeline...")
        self._log_area.clear()
        self._log_area.show()
        self._log_toggle.setChecked(True)

        self._harvest_worker = HarvestWorker(project_dir, output_dir)
        self._harvest_worker.stage_changed.connect(self._on_stage_changed)
        self._harvest_worker.progress_updated.connect(self._on_progress_updated)
        self._harvest_worker.harvest_finished.connect(self._on_harvest_finished)
        self._harvest_worker.start()

    @Slot(str)
    def _on_stage_changed(self, label: str) -> None:
        """Update status label when pipeline stage changes."""
        self._status_label.setText(f"Harvesting: {label}")
        self._log_area.append(f"\n--- {label} ---")

    @Slot(str)
    def _on_progress_updated(self, message: str) -> None:
        """Append progress detail to the log area."""
        self._log_area.append(message)

    @Slot(bool, str)
    def _on_harvest_finished(self, success: bool, summary: str) -> None:
        """Handle harvest completion."""
        self._set_harvesting_state(enabled=True)
        if success:
            self._status_label.setText(f"Harvest complete: {summary}")
        else:
            self._status_label.setText(f"Harvest failed: {summary}")
        self._harvest_worker = None

    @Slot(bool)
    def _on_log_toggled(self, checked: bool) -> None:
        """Toggle log area visibility."""
        self._log_area.setVisible(checked)
        self._log_toggle.setText("Hide Log" if checked else "Show Log")

    def _set_harvesting_state(self, *, enabled: bool) -> None:
        """Enable or disable UI elements during harvest.

        Args:
            enabled: True to re-enable controls, False to disable for harvest.
        """
        self._fetch_button.setEnabled(enabled)
        self._harvest_button.setEnabled(enabled)
        self._name_input.setEnabled(enabled)
        self._url_input.setEnabled(enabled)
