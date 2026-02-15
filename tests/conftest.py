from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication

    @pytest.fixture(scope="session")
    def qapp() -> QApplication:
        """Provide a QApplication instance for the test session."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

except ImportError:
    pass
