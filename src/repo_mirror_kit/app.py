from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication


def configure_application(app: QApplication) -> None:
    """Configure the QApplication with global settings and stylesheet."""
    app.setApplicationName("RepoMirrorKit")

    stylesheet_path = Path(__file__).parent / "resources" / "styles" / "main.qss"
    if stylesheet_path.exists():
        app.setStyleSheet(stylesheet_path.read_text())
