# PySide6 Conventions

Non-negotiable defaults for Qt for Python (PySide6) desktop applications.
Deviations require an ADR with justification.

---

## Defaults

- **Qt binding:** PySide6 (official Qt binding, LGPL-friendly).
- **Pattern:** Model/View with signals and slots for all inter-component communication.
- **Styling:** QSS stylesheets, not inline `setStyleSheet()` calls scattered across widgets.
- **Layout:** Always use layout managers. Never use fixed pixel positioning.
- **Python version:** 3.12+ with `from __future__ import annotations`.
- **Type hints:** All public methods typed, including signal signatures.

---

## Project Structure

```
project-root/
  src/
    <package_name>/
      __init__.py
      main.py               # QApplication setup, entry point
      app.py                 # Application-level config, single-instance logic
      resources/
        styles/
          main.qss           # Global stylesheet
        icons/                # SVG preferred over PNG
        resources.qrc         # Qt resource file (optional)
      models/                 # QAbstractItemModel subclasses, data models
      views/                  # QWidget subclasses (UI only, no logic)
      delegates/              # QStyledItemDelegate subclasses
      controllers/            # Mediators between models and views
      services/               # Business logic (no Qt imports where possible)
      workers/                # QThread / QRunnable worker classes
      dialogs/                # QDialog subclasses
      widgets/                # Reusable custom widgets
  tests/
    conftest.py              # QApplication fixture
    unit/
    integration/
  pyproject.toml
```

**Rules:**
- Views never call services directly. Controllers or signals mediate.
- Services should be pure Python where possible so they remain testable without Qt.
- One widget class per file. File name matches class name in snake_case.

---

## Naming Conventions

| Element             | Convention          | Example                        |
|---------------------|---------------------|--------------------------------|
| Widget classes      | `PascalCase`        | `ProjectTreeView`              |
| Signal names        | `snake_case`        | `item_selected`                |
| Slot methods        | `_on_<signal_name>` | `_on_item_selected`            |
| QSS class selectors | `PascalCase`        | `SidebarWidget`                |
| Resource files      | `kebab-case`        | `icon-save.svg`                |
| Worker classes      | `PascalCase` + Worker | `ExportWorker`               |

---

## Signals and Slots

```python
from PySide6.QtCore import Signal, Slot, QObject


class ProjectModel(QObject):
    """Model that emits signals when project state changes."""

    project_loaded = Signal(str)   # Always document the argument meaning
    error_occurred = Signal(str)

    @Slot(str)
    def load_project(self, path: str) -> None:
        """Load a project file and emit project_loaded on success."""
        try:
            data = self._read_file(path)
            self.project_loaded.emit(data.name)
        except FileNotFoundError as exc:
            self.error_occurred.emit(str(exc))
```

```python
# In the controller or parent widget -- connect, don't subclass
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.model = ProjectModel()
        self.tree = ProjectTreeView()

        # Connect signal to slot explicitly
        self.model.project_loaded.connect(self.tree.refresh)
        self.model.error_occurred.connect(self._on_error)

    @Slot(str)
    def _on_error(self, message: str) -> None:
        QMessageBox.warning(self, "Error", message)
```

---

## Do / Don't

- **Do** use `Signal`/`Slot` for all cross-component communication.
- **Do** keep widget `__init__` methods short: call `_setup_ui()` and `_connect_signals()`.
- **Do** use `QSS` files loaded at startup for consistent theming.
- **Do** use `QIcon.fromTheme()` with SVG fallbacks for icons.
- **Don't** call `QThread.sleep()` or `time.sleep()` on the main thread.
- **Don't** update UI from a worker thread. Emit a signal and let the main thread handle it.
- **Don't** use `QDesigner` .ui files without a deliberate team decision -- they obscure control flow.
- **Don't** use `pyqtSignal` or any PyQt5/6 imports. This is a PySide6 project.

---

## Common Pitfalls

1. **Blocking the event loop.** Any operation over ~50ms must run in a `QThread` or `QThreadPool`. Symptoms: frozen UI, "(Not Responding)" in the title bar.
2. **Accessing widgets from worker threads.** Qt widgets are not thread-safe. Always emit a signal from the worker and connect it to a slot on the main thread.
3. **Forgetting `super().__init__()`** in custom widgets causes silent failures and missing functionality.
4. **Circular signal connections.** Signal A triggers slot that emits Signal B which triggers slot that emits Signal A. Use `blockSignals(True)` or redesign the flow.
5. **Orphaned widgets.** Widgets without a parent are not cleaned up by Qt's object tree. Always pass a parent or add to a layout.

---

## Checklist

- [ ] `QApplication` created exactly once, in `main.py`
- [ ] All long-running operations use `QThread` or `QThreadPool` workers
- [ ] No direct UI manipulation from worker threads
- [ ] Global QSS stylesheet loaded at startup
- [ ] All signals and slots use type-safe signatures
- [ ] Widget hierarchy uses layouts, not fixed geometry
- [ ] Custom widgets pass `parent` to `super().__init__()`
- [ ] `@Slot` decorator applied to all slot methods
- [ ] No bare `except:` in signal handlers (swallows Qt errors silently)
- [ ] Application closes cleanly: workers stopped, settings saved
