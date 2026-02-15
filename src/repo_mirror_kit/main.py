from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from repo_mirror_kit.app import configure_application
from repo_mirror_kit.views.main_window import MainWindow


def main() -> None:
    """Launch the RepoMirrorKit application."""
    app = QApplication(sys.argv)
    configure_application(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
