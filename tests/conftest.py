from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication

    _HAS_QT = True
except ImportError:
    _HAS_QT = False


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Provide a QApplication instance for the test session."""
    if not _HAS_QT:
        pytest.skip("PySide6 not available")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app  # type: ignore[return-value]
