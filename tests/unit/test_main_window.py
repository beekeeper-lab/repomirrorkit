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
        window._name_input.setText("my-project")
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


class TestMainWindowHarvestButton:
    """Tests for the harvest button UI element and state management."""

    def test_harvest_button_exists(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert window._harvest_button is not None
        assert window._harvest_button.text() == "Generate Requirements"

    def test_harvest_button_initially_hidden_and_disabled(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.show()
        assert window._harvest_button.isHidden()
        assert not window._harvest_button.isEnabled()

    def test_harvest_button_shown_after_clone_success(self, qapp: QApplication) -> None:
        window = MainWindow()
        window.show()
        window._name_input.setText("my-project")
        window._on_clone_finished(True, "Clone complete")
        assert not window._harvest_button.isHidden()
        assert window._harvest_button.isEnabled()

    def test_harvest_button_stays_hidden_on_clone_failure(
        self, qapp: QApplication
    ) -> None:
        window = MainWindow()
        window.show()
        window._on_clone_finished(False, "Failed")
        assert window._harvest_button.isHidden()

    def test_harvest_button_disabled_before_clone(self, qapp: QApplication) -> None:
        window = MainWindow()
        assert not window._harvest_button.isEnabled()


class TestMainWindowHarvestState:
    """Tests for UI state during harvest operations."""

    def test_harvesting_disables_controls(self, qapp: QApplication) -> None:
        window = MainWindow()
        window._set_harvesting_state(enabled=False)
        assert not window._fetch_button.isEnabled()
        assert not window._harvest_button.isEnabled()
        assert not window._name_input.isEnabled()
        assert not window._url_input.isEnabled()

    def test_harvesting_re_enables_controls(self, qapp: QApplication) -> None:
        window = MainWindow()
        window._set_harvesting_state(enabled=False)
        window._set_harvesting_state(enabled=True)
        assert window._fetch_button.isEnabled()
        assert window._harvest_button.isEnabled()
        assert window._name_input.isEnabled()
        assert window._url_input.isEnabled()

    def test_on_stage_changed_updates_status(self, qapp: QApplication) -> None:
        window = MainWindow()
        window._on_stage_changed("Stage B: Inventory & Detection")
        assert "Stage B" in window._status_label.text()
        assert "Harvesting" in window._status_label.text()

    def test_on_stage_changed_appends_to_log(self, qapp: QApplication) -> None:
        window = MainWindow()
        window._on_stage_changed("Stage B: Inventory & Detection")
        text = window._log_area.toPlainText()
        assert "Stage B: Inventory & Detection" in text

    def test_on_progress_updated_appends_to_log(self, qapp: QApplication) -> None:
        window = MainWindow()
        window._on_progress_updated("Routes: 42 found")
        assert "Routes: 42 found" in window._log_area.toPlainText()

    def test_on_harvest_finished_success(self, qapp: QApplication) -> None:
        window = MainWindow()
        window._set_harvesting_state(enabled=False)
        window._on_harvest_finished(True, "10 beans generated, coverage gates passed")
        assert window._fetch_button.isEnabled()
        assert window._harvest_button.isEnabled()
        assert "Harvest complete" in window._status_label.text()
        assert "10 beans" in window._status_label.text()

    def test_on_harvest_finished_failure(self, qapp: QApplication) -> None:
        window = MainWindow()
        window._set_harvesting_state(enabled=False)
        window._on_harvest_finished(False, "Failed at stage C: Analysis failed")
        assert window._fetch_button.isEnabled()
        assert window._harvest_button.isEnabled()
        assert "Harvest failed" in window._status_label.text()
        assert "stage C" in window._status_label.text()

    def test_on_harvest_clicked_guards_no_clone(self, qapp: QApplication) -> None:
        """Clicking harvest without a completed clone should do nothing."""
        window = MainWindow()
        window._clone_project_name = None
        window._on_harvest_clicked()
        # No crash; harvest_worker should remain None
        assert window._harvest_worker is None

    def test_clone_form_disabled_during_harvest(self, qapp: QApplication) -> None:
        window = MainWindow()
        window._set_harvesting_state(enabled=False)
        assert not window._name_input.isEnabled()
        assert not window._url_input.isEnabled()
