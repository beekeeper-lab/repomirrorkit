from __future__ import annotations

from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from repo_mirror_kit.views.main_window import MainWindow


class TestMainWindowForm:
    """Tests for the clone form UI elements."""

    def test_has_project_name_input(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window._name_input is not None
        assert window._name_input.placeholderText() == "my-project"

    def test_has_url_input(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window._url_input is not None

    def test_has_fetch_button(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window._fetch_button is not None
        assert window._fetch_button.text() == "Fetch"

    def test_has_status_label(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window._status_label is not None

    def test_has_log_area(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window._log_area is not None
        assert window._log_area.isReadOnly()

    def test_log_area_initially_hidden(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.show()
        assert window._log_area.isHidden()


class TestMainWindowValidation:
    """Tests for form validation behavior."""

    def test_empty_name_shows_error(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.show()
        window._name_input.setText("")
        window._url_input.setText("https://github.com/user/repo.git")
        window._on_fetch_clicked()
        assert not window._name_error.isHidden()
        assert window._fetch_button.isEnabled()

    def test_empty_url_shows_error(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.show()
        window._name_input.setText("my-project")
        window._url_input.setText("")
        window._on_fetch_clicked()
        assert not window._url_error.isHidden()
        assert window._fetch_button.isEnabled()

    def test_both_empty_shows_both_errors(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.show()
        window._name_input.setText("")
        window._url_input.setText("")
        window._on_fetch_clicked()
        assert not window._name_error.isHidden()
        assert not window._url_error.isHidden()

    @patch("repo_mirror_kit.views.main_window.check_git_available", return_value=False)
    def test_git_not_available_shows_error(
        self, mock_git: object, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window._name_input.setText("my-project")
        window._url_input.setText("https://github.com/user/repo.git")
        window._on_fetch_clicked()
        assert "not installed" in window._status_label.text()
        assert window._fetch_button.isEnabled()


class TestMainWindowCloneState:
    """Tests for UI state during and after clone operations."""

    def test_on_clone_finished_success(self, qapp: QApplication) -> None:
        window = MainWindow()
        window._fetch_button.setEnabled(False)
        window._on_clone_finished(True, "Clone complete")
        assert window._fetch_button.isEnabled()
        assert window._status_label.text() == "Clone complete"

    def test_on_clone_finished_failure(self, qapp: QApplication) -> None:
        window = MainWindow()
        window._fetch_button.setEnabled(False)
        window._on_clone_finished(False, "Directory already exists")
        assert window._fetch_button.isEnabled()
        assert "Directory already exists" in window._status_label.text()

    def test_on_output_received_appends_to_log(self, qapp: QApplication) -> None:
        window = MainWindow()
        window._on_output_received("Cloning into 'test'...")
        assert "Cloning into 'test'..." in window._log_area.toPlainText()

    def test_log_toggle_shows_and_hides(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.show()
        assert window._log_area.isHidden()
        window._log_toggle.setChecked(True)
        assert not window._log_area.isHidden()
        window._log_toggle.setChecked(False)
        assert window._log_area.isHidden()
