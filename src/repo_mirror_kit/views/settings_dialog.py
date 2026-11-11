"""LLM settings: which provider to use and where its API key lives.

Keys are never stored in the repository. The dialog either writes a key to the
per-user env file (``~/.config/repomirrorkit/providers.env``, mode 600) or
points at that file / the environment variable so you can manage the key
yourself. Key values are never displayed back.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from repo_mirror_kit.harvester.llm.probe import ProbeResult, probe_provider
from repo_mirror_kit.harvester.providers import (
    PROVIDERS,
    LlmSettings,
    env_file_path,
    key_status,
    remove_key,
    save_key,
    save_settings,
)


class _ProbeWorker(QThread):
    """Runs the connection test off the UI thread."""

    done = Signal(bool, str)

    def __init__(self, provider_id: str, model: str | None) -> None:
        super().__init__()
        self._provider_id = provider_id
        self._model = model

    def run(self) -> None:
        result: ProbeResult = probe_provider(self._provider_id, self._model)
        suffix = f" ({result.seconds:.1f}s)" if result.seconds else ""
        self.done.emit(result.ok, result.message + suffix)


class SettingsDialog(QDialog):
    """Edit and persist :class:`LlmSettings`; manage provider keys."""

    def __init__(self, settings: LlmSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("LLM Settings")
        self.setMinimumWidth(560)
        self._settings = settings
        self._probe: _ProbeWorker | None = None
        self._build()
        self._load()

    # -- layout ------------------------------------------------------------
    def _build(self) -> None:
        layout = QVBoxLayout(self)

        self._enabled = QCheckBox(
            "Use an LLM to enrich requirements (otherwise structural analysis only)"
        )
        layout.addWidget(self._enabled)

        form = QFormLayout()
        self._provider = QComboBox()
        for provider in PROVIDERS.values():
            self._provider.addItem(provider.label, provider.id)
        form.addRow("Provider:", self._provider)
        self._model = QLineEdit()
        form.addRow("Model:", self._model)
        self._budget = QDoubleSpinBox()
        self._budget.setRange(0.0, 500.0)
        self._budget.setDecimals(2)
        self._budget.setPrefix("$")
        self._budget.setToolTip("Estimated-spend cap. 0 disables the cap.")
        form.addRow("Spend cap:", self._budget)
        self._concurrency = QSpinBox()
        self._concurrency.setRange(1, 8)
        self._concurrency.setToolTip("Parallel Claude Code calls (claude-cli only).")
        form.addRow("Parallel calls:", self._concurrency)
        layout.addLayout(form)

        # -- key section ---------------------------------------------------
        self._key_box = QWidget()
        key_layout = QVBoxLayout(self._key_box)
        key_layout.setContentsMargins(0, 8, 0, 0)
        self._key_status = QLabel()
        self._key_status.setWordWrap(True)
        key_layout.addWidget(self._key_status)

        key_row = QHBoxLayout()
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText(
            "Paste an API key to save it (never shown again)"
        )
        self._save_key = QPushButton("Save key")
        self._remove_key = QPushButton("Remove saved key")
        key_row.addWidget(self._key_input, 1)
        key_row.addWidget(self._save_key)
        key_row.addWidget(self._remove_key)
        key_layout.addLayout(key_row)

        self._where = QLabel()
        self._where.setWordWrap(True)
        self._where.setTextInteractionFlags(
            self._where.textInteractionFlags()
            | self._where.textInteractionFlags().TextSelectableByMouse
        )
        key_layout.addWidget(self._where)
        path_row = QHBoxLayout()
        self._copy_path = QPushButton("Copy key-file path")
        self._open_dir = QPushButton("Open its folder")
        path_row.addWidget(self._copy_path)
        path_row.addWidget(self._open_dir)
        path_row.addStretch(1)
        key_layout.addLayout(path_row)
        layout.addWidget(self._key_box)

        # -- test + buttons -------------------------------------------------
        test_row = QHBoxLayout()
        self._test = QPushButton("Test connection")
        self._test_result = QLabel()
        self._test_result.setWordWrap(True)
        test_row.addWidget(self._test)
        test_row.addWidget(self._test_result, 1)
        layout.addLayout(test_row)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self._buttons)

        self._provider.currentIndexChanged.connect(self._on_provider_changed)
        self._save_key.clicked.connect(self._on_save_key)
        self._remove_key.clicked.connect(self._on_remove_key)
        self._copy_path.clicked.connect(self._on_copy_path)
        self._open_dir.clicked.connect(self._on_open_dir)
        self._test.clicked.connect(self._on_test)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

    # -- state ---------------------------------------------------------------
    def _current_id(self) -> str:
        return str(self._provider.currentData())

    def _load(self) -> None:
        s = self._settings
        self._enabled.setChecked(s.enabled)
        index = self._provider.findData(s.provider)
        self._provider.setCurrentIndex(max(index, 0))
        self._model.setText(s.model)
        self._budget.setValue(s.budget_usd)
        self._concurrency.setValue(s.concurrency)
        self._on_provider_changed()

    @Slot()
    def _on_provider_changed(self) -> None:
        provider = PROVIDERS[self._current_id()]
        self._model.setPlaceholderText(provider.default_model or "provider default")
        needs_key = provider.kind == "api"
        self._key_box.setVisible(needs_key)
        self._concurrency.setEnabled(provider.kind == "cli")
        self._test_result.clear()
        if needs_key:
            names = " / ".join(provider.env_vars)
            self._where.setText(
                f"Keys are kept outside the repository. Either export <b>{names}</b> in "
                f"your shell, or use <b>Save key</b> — it writes "
                f"<code>{env_file_path()}</code> (permissions 600). "
                f"Get a key: {provider.key_help_url}"
            )
            self._refresh_key_status()

    def _refresh_key_status(self) -> None:
        provider = PROVIDERS[self._current_id()]
        status = key_status(provider)
        text = {
            "environment": "Key status: found in your environment variables.",
            "env file": f"Key status: found in {env_file_path()}.",
            "missing": "Key status: <b>not set</b> — this provider cannot be used yet.",
        }.get(status, "")
        self._key_status.setText(text)
        self._remove_key.setEnabled(status == "env file")

    # -- slots ---------------------------------------------------------------
    @Slot()
    def _on_save_key(self) -> None:
        provider = PROVIDERS[self._current_id()]
        value = self._key_input.text()
        try:
            save_key(provider.env_vars[0], value)
        except ValueError as exc:
            self._test_result.setText(f"Not saved: {exc}")
            return
        self._key_input.clear()
        self._test_result.setText(f"Saved to {env_file_path()}")
        self._refresh_key_status()

    @Slot()
    def _on_remove_key(self) -> None:
        provider = PROVIDERS[self._current_id()]
        for name in provider.env_vars:
            remove_key(name)
        self._refresh_key_status()
        self._test_result.setText("Removed from the key file.")

    @Slot()
    def _on_copy_path(self) -> None:
        QGuiApplication.clipboard().setText(str(env_file_path()))

    @Slot()
    def _on_open_dir(self) -> None:
        folder = env_file_path().parent
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @Slot()
    def _on_test(self) -> None:
        self._test.setEnabled(False)
        self._test_result.setText("Testing...")
        self._probe = _ProbeWorker(
            self._current_id(), self._model.text().strip() or None
        )
        self._probe.done.connect(self._on_test_done)
        self._probe.start()

    @Slot(bool, str)
    def _on_test_done(self, ok: bool, message: str) -> None:
        self._test.setEnabled(True)
        self._test_result.setText(("OK: " if ok else "Failed: ") + message)

    @Slot()
    def _on_accept(self) -> None:
        self._settings.enabled = self._enabled.isChecked()
        self._settings.provider = self._current_id()
        self._settings.model = self._model.text().strip()
        self._settings.budget_usd = self._budget.value()
        self._settings.concurrency = self._concurrency.value()
        save_settings(self._settings)
        self.accept()

    def settings(self) -> LlmSettings:
        """The settings as last saved by the dialog."""
        return self._settings
