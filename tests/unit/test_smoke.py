from __future__ import annotations

from PySide6.QtWidgets import QApplication

from repo_mirror_kit.views.main_window import MainWindow


def test_main_window_creates_without_crashing(qapp: QApplication) -> None:
    """Verify that MainWindow can be instantiated."""
    window = MainWindow()
    assert window.windowTitle() == "RepoMirrorKit"


def test_main_window_has_central_widget(qapp: QApplication) -> None:
    """Verify that MainWindow has a central widget with a layout."""
    window = MainWindow()
    central = window.centralWidget()
    assert central is not None
    assert central.layout() is not None
