"""Unit tests for the state management analyzer."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.state_mgmt import analyze_state_management
from repo_mirror_kit.harvester.analyzers.surfaces import StateMgmtSurface
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_inventory(files: list[FileEntry]) -> InventoryResult:
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=sum(f.size for f in files),
        total_skipped=0,
    )


def _make_profile() -> StackProfile:
    return StackProfile(stacks={}, evidence={}, signals=[])


def _write_file(tmp_path: Path, rel_path: str, content: str) -> FileEntry:
    full_path = tmp_path / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    ext = ""
    dot = rel_path.rfind(".")
    if dot != -1:
        ext = rel_path[dot:]
    return FileEntry(
        path=rel_path, size=len(content), extension=ext, hash="abc123", category="source"
    )


# ---------------------------------------------------------------------------
# Empty / no matches
# ---------------------------------------------------------------------------


class TestEmptyResults:
    """Verify analyzer returns empty list when no patterns are present."""

    def test_no_state_management_patterns(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/utils.ts",
            "export function add(a: number, b: number) { return a + b; }\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert result == []

    def test_no_workdir_returns_empty(self) -> None:
        entry = FileEntry(
            path="src/store.ts", size=100, extension=".ts", hash="abc123", category="source"
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=None)

        assert result == []

    def test_non_js_ts_py_files_skipped(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/store.css",
            "body { color: red; }\n",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert result == []


# ---------------------------------------------------------------------------
# Redux patterns
# ---------------------------------------------------------------------------


class TestReduxDetection:
    """Tests for Redux createSlice, configureStore, and createStore patterns."""

    def test_create_slice_detected(self, tmp_path: Path) -> None:
        # Use arrow-function style reducers so the heuristic regex
        # (which stops at the first '}') captures both action names.
        entry = _write_file(
            tmp_path,
            "src/store/counterSlice.ts",
            """\
import { createSlice } from '@reduxjs/toolkit';

const counterSlice = createSlice({
  name: "counter",
  initialState: 0,
  reducers: {
    increment: (state) => state + 1,
    decrement: (state) => state - 1,
  },
});

export const selectCount = (state) => state.counter;
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        surface = result[0]
        assert isinstance(surface, StateMgmtSurface)
        assert surface.surface_type == "state_mgmt"
        assert surface.store_name == "counter"
        assert surface.pattern == "redux"
        assert surface.name == "redux:counter"
        assert "increment" in surface.actions
        assert "decrement" in surface.actions
        assert "selectCount" in surface.selectors

    def test_configure_store_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/store/index.ts",
            """\
import { configureStore } from '@reduxjs/toolkit';
import rootReducer from './rootReducer';

const store = configureStore({
  reducer: rootReducer,
});
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        surface = result[0]
        assert surface.pattern == "redux"
        assert surface.store_name == "root"

    def test_create_store_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/store/legacy.ts",
            """\
import { createStore } from 'redux';
import rootReducer from './reducers';

const store = createStore(rootReducer);
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        surface = result[0]
        assert surface.pattern == "redux"
        assert surface.store_name == "root"

    def test_create_slice_with_no_reducers_block(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/store/apiSlice.ts",
            """\
import { createSlice } from '@reduxjs/toolkit';

const apiSlice = createSlice({
  name: "api",
  initialState: {},
});
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        assert result[0].store_name == "api"
        assert result[0].actions == []

    def test_configure_store_skipped_when_create_slice_present(self, tmp_path: Path) -> None:
        """configureStore is not double-counted when createSlice is also in the file."""
        entry = _write_file(
            tmp_path,
            "src/store/combined.ts",
            """\
import { createSlice, configureStore } from '@reduxjs/toolkit';

const counterSlice = createSlice({
  name: "counter",
  initialState: { value: 0 },
  reducers: {},
});

const store = configureStore({
  reducer: { counter: counterSlice.reducer },
});
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        # Only the createSlice surface, not the configureStore surface.
        assert len(result) == 1
        assert result[0].store_name == "counter"

    def test_source_refs_populated(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/store/slice.ts",
            """\
import { createSlice } from '@reduxjs/toolkit';

const slice = createSlice({
  name: "todos",
  initialState: [],
  reducers: {},
});
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        assert len(result[0].source_refs) == 1
        assert result[0].source_refs[0].file_path == "src/store/slice.ts"
        assert result[0].source_refs[0].start_line is not None
        assert result[0].source_refs[0].start_line > 0


# ---------------------------------------------------------------------------
# Zustand patterns
# ---------------------------------------------------------------------------


class TestZustandDetection:
    """Tests for Zustand create() pattern detection."""

    def test_zustand_create_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/store/useCounterStore.ts",
            """\
import { create } from 'zustand';

const useCounterStore = create((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 })),
}));
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        surface = result[0]
        assert isinstance(surface, StateMgmtSurface)
        assert surface.surface_type == "state_mgmt"
        assert surface.store_name == "useCounterStore"
        assert surface.pattern == "zustand"
        assert surface.name == "zustand:useCounterStore"

    def test_zustand_requires_import(self, tmp_path: Path) -> None:
        """create() without zustand import should not match."""
        entry = _write_file(
            tmp_path,
            "src/utils/factory.ts",
            """\
const useStore = create((set) => ({
  value: 0,
}));
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert result == []

    def test_zustand_with_type_params(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/store/typed.ts",
            """\
import { create } from 'zustand';

interface BearState {
  bears: number;
}

const useBearStore = create<BearState>((set) => ({
  bears: 0,
}));
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        assert result[0].store_name == "useBearStore"
        assert result[0].pattern == "zustand"


# ---------------------------------------------------------------------------
# React Context patterns
# ---------------------------------------------------------------------------


class TestReactContextDetection:
    """Tests for React.createContext and useContext patterns."""

    def test_create_context_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/contexts/ThemeContext.tsx",
            """\
import React from 'react';

const ThemeContext = React.createContext({
  theme: 'light',
  toggleTheme: () => {},
});

export default ThemeContext;
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        surface = result[0]
        assert isinstance(surface, StateMgmtSurface)
        assert surface.surface_type == "state_mgmt"
        assert surface.store_name == "ThemeContext"
        assert surface.pattern == "context"
        assert surface.name == "context:ThemeContext"

    def test_create_context_without_react_prefix(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/contexts/AuthContext.tsx",
            """\
import { createContext } from 'react';

const AuthContext = createContext(null);
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        assert result[0].store_name == "AuthContext"
        assert result[0].pattern == "context"

    def test_create_context_with_type_param(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/contexts/UserContext.tsx",
            """\
import { createContext } from 'react';

const UserContext = createContext<User | null>(null);
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        assert result[0].store_name == "UserContext"


# ---------------------------------------------------------------------------
# Pinia patterns
# ---------------------------------------------------------------------------


class TestPiniaDetection:
    """Tests for Pinia defineStore pattern detection."""

    def test_define_store_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/stores/counter.ts",
            """\
import { defineStore } from 'pinia';

export const useCounterStore = defineStore('counter', {
  state: () => ({ count: 0 }),
  actions: {
    increment() {
      this.count++;
    },
  },
});
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        surface = result[0]
        assert isinstance(surface, StateMgmtSurface)
        assert surface.surface_type == "state_mgmt"
        assert surface.store_name == "counter"
        assert surface.pattern == "pinia"
        assert surface.name == "pinia:counter"

    def test_multiple_pinia_stores_in_directory(self, tmp_path: Path) -> None:
        entry1 = _write_file(
            tmp_path,
            "src/stores/counter.ts",
            "export const useCounterStore = defineStore('counter', {});\n",
        )
        entry2 = _write_file(
            tmp_path,
            "src/stores/user.ts",
            "export const useUserStore = defineStore('user', {});\n",
        )
        inventory = _make_inventory([entry1, entry2])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 2
        names = {s.store_name for s in result}
        assert names == {"counter", "user"}


# ---------------------------------------------------------------------------
# Vuex patterns
# ---------------------------------------------------------------------------


class TestVuexDetection:
    """Tests for Vuex store detection."""

    def test_vuex_create_store_detected(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/store/index.ts",
            """\
import { createStore } from 'vuex';

const store = createStore({
  state: { count: 0 },
});
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        surface = result[0]
        assert surface.pattern == "vuex"
        assert surface.store_name == "root"

    def test_vuex_requires_import(self, tmp_path: Path) -> None:
        """createStore without vuex import should not match as vuex."""
        entry = _write_file(
            tmp_path,
            "src/store/index.ts",
            """\
import { createStore } from 'some-other-lib';

const store = createStore({});
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        # Should not detect as vuex (no vuex import).
        vuex_surfaces = [s for s in result if s.pattern == "vuex"]
        assert vuex_surfaces == []


# ---------------------------------------------------------------------------
# MobX patterns
# ---------------------------------------------------------------------------


class TestMobxDetection:
    """Tests for MobX observable pattern detection."""

    def test_mobx_class_with_make_auto_observable(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/store/TodoStore.ts",
            """\
import { makeAutoObservable } from 'mobx';

class TodoStore {
  todos = [];

  constructor() {
    makeAutoObservable(this);
  }
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        surface = result[0]
        assert surface.pattern == "mobx"
        assert surface.store_name == "TodoStore"
        assert surface.name == "mobx:TodoStore"

    def test_mobx_standalone_observable_fallback(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/store/state.ts",
            """\
import { observable } from 'mobx';

const appState = observable({
  count: 0,
});
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 1
        surface = result[0]
        assert surface.pattern == "mobx"
        assert surface.store_name == "observable"

    def test_mobx_requires_import(self, tmp_path: Path) -> None:
        """makeAutoObservable without mobx import should not match."""
        entry = _write_file(
            tmp_path,
            "src/store/fake.ts",
            """\
class FakeStore {
  constructor() {
    makeAutoObservable(this);
  }
}
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert result == []


# ---------------------------------------------------------------------------
# Multiple patterns in one repository
# ---------------------------------------------------------------------------


class TestMultiplePatterns:
    """Tests for repositories using multiple state management patterns."""

    def test_redux_and_context_in_same_repo(self, tmp_path: Path) -> None:
        entry1 = _write_file(
            tmp_path,
            "src/store/counterSlice.ts",
            """\
import { createSlice } from '@reduxjs/toolkit';
const counterSlice = createSlice({
  name: "counter",
  initialState: {},
  reducers: {},
});
""",
        )
        entry2 = _write_file(
            tmp_path,
            "src/contexts/ThemeContext.tsx",
            """\
const ThemeContext = React.createContext({ theme: 'light' });
""",
        )
        inventory = _make_inventory([entry1, entry2])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        assert len(result) == 2
        patterns = {s.pattern for s in result}
        assert patterns == {"redux", "context"}

    def test_all_surfaces_have_correct_surface_type(self, tmp_path: Path) -> None:
        entry = _write_file(
            tmp_path,
            "src/store/counterSlice.ts",
            """\
import { createSlice } from '@reduxjs/toolkit';
const s = createSlice({
  name: "test",
  initialState: {},
  reducers: {},
});
""",
        )
        inventory = _make_inventory([entry])
        result = analyze_state_management(inventory, _make_profile(), workdir=tmp_path)

        for surface in result:
            assert isinstance(surface, StateMgmtSurface)
            assert surface.surface_type == "state_mgmt"
