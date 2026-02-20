"""Unit tests for the component analyzer."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from repo_mirror_kit.harvester.analyzers.components import (
    _component_name_from_path,
    _is_in_shared_dir,
    _resolve_frameworks,
    analyze_components,
)
from repo_mirror_kit.harvester.detectors.base import StackProfile
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _file_entry(
    path: str,
    *,
    extension: str = "",
    category: str = "source",
    size: int = 100,
) -> FileEntry:
    """Create a FileEntry for testing."""
    return FileEntry(
        path=path,
        size=size,
        extension=extension or PurePosixPath(path).suffix,
        hash="abc123def456",
        category=category,
    )


def _inventory(*entries: FileEntry) -> InventoryResult:
    """Create an InventoryResult from file entries."""
    files = list(entries)
    return InventoryResult(
        files=files,
        skipped=[],
        total_files=len(files),
        total_size=sum(e.size for e in files),
        total_skipped=0,
    )


def _profile(*stack_names: str) -> StackProfile:
    """Create a StackProfile with the given stacks at full confidence."""
    return StackProfile(
        stacks=dict.fromkeys(stack_names, 1.0),
        evidence={name: [] for name in stack_names},
        signals=[],
    )


def _write_file(workdir: Path, rel_path: str, content: str) -> None:
    """Write a file relative to workdir, creating directories as needed."""
    target = workdir / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Framework resolution
# ---------------------------------------------------------------------------


class TestResolveFrameworks:
    """Tests for _resolve_frameworks."""

    def test_react_stack_maps_to_react(self) -> None:
        result = _resolve_frameworks({"react"})
        assert result == {"react"}

    def test_nextjs_stack_maps_to_react(self) -> None:
        result = _resolve_frameworks({"nextjs"})
        assert result == {"react"}

    def test_vue_stack_maps_to_vue(self) -> None:
        result = _resolve_frameworks({"vue"})
        assert result == {"vue"}

    def test_svelte_stack_maps_to_svelte(self) -> None:
        result = _resolve_frameworks({"svelte"})
        assert result == {"svelte"}

    def test_sveltekit_stack_maps_to_svelte(self) -> None:
        result = _resolve_frameworks({"sveltekit"})
        assert result == {"svelte"}

    def test_multiple_stacks(self) -> None:
        result = _resolve_frameworks({"react", "vue", "svelte"})
        assert result == {"react", "vue", "svelte"}

    def test_no_frontend_stacks_returns_empty(self) -> None:
        result = _resolve_frameworks({"fastapi", "django"})
        assert result == set()

    def test_empty_stacks_returns_empty(self) -> None:
        result = _resolve_frameworks(set())
        assert result == set()


# ---------------------------------------------------------------------------
# Shared directory detection
# ---------------------------------------------------------------------------


class TestIsInSharedDir:
    """Tests for _is_in_shared_dir."""

    def test_components_dir(self) -> None:
        assert _is_in_shared_dir("src/components/Button.tsx") is True

    def test_shared_dir(self) -> None:
        assert _is_in_shared_dir("shared/Modal.vue") is True

    def test_ui_dir(self) -> None:
        assert _is_in_shared_dir("src/ui/Card.jsx") is True

    def test_common_dir(self) -> None:
        assert _is_in_shared_dir("common/Alert.svelte") is True

    def test_lib_dir(self) -> None:
        assert _is_in_shared_dir("lib/Input.tsx") is True

    def test_nested_shared_dir(self) -> None:
        assert _is_in_shared_dir("packages/web/components/Button.tsx") is True

    def test_not_shared_dir(self) -> None:
        assert _is_in_shared_dir("src/pages/Home.tsx") is False

    def test_root_file(self) -> None:
        assert _is_in_shared_dir("App.tsx") is False

    def test_case_insensitive(self) -> None:
        assert _is_in_shared_dir("src/Components/Button.tsx") is True


# ---------------------------------------------------------------------------
# Component name derivation
# ---------------------------------------------------------------------------


class TestComponentNameFromPath:
    """Tests for _component_name_from_path."""

    def test_simple_filename(self) -> None:
        assert _component_name_from_path("components/Button.tsx") == "Button"

    def test_kebab_case(self) -> None:
        assert _component_name_from_path("components/date-picker.vue") == "DatePicker"

    def test_snake_case(self) -> None:
        assert _component_name_from_path("components/nav_bar.svelte") == "NavBar"

    def test_nested_path(self) -> None:
        assert (
            _component_name_from_path("src/components/forms/TextInput.tsx")
            == "Textinput"
        )


# ---------------------------------------------------------------------------
# React component discovery and extraction
# ---------------------------------------------------------------------------


class TestReactComponents:
    """Tests for React component discovery and prop extraction."""

    def test_discovers_react_component_in_shared_dir(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Button.tsx",
            "export function Button() { return <button>Click</button>; }",
        )
        inv = _inventory(
            _file_entry("src/components/Button.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert result[0].name == "Button"
        assert result[0].surface_type == "component"

    def test_extracts_typescript_interface_props(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Card.tsx",
            (
                "interface CardProps {\n"
                "  title: string;\n"
                "  count: number;\n"
                "  onClick: () => void;\n"
                "}\n"
                "export function Card({ title, count, onClick }: CardProps) {\n"
                "  return <div>{title}</div>;\n"
                "}\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Card.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert "title" in result[0].props
        assert "count" in result[0].props
        assert "onClick" in result[0].props

    def test_extracts_proptypes(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Alert.jsx",
            (
                "function Alert({ message, severity }) {\n"
                "  return <div>{message}</div>;\n"
                "}\n"
                "Alert.propTypes = {\n"
                "  message: PropTypes.string.isRequired,\n"
                "  severity: PropTypes.oneOf(['info', 'warning', 'error']),\n"
                "};\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Alert.jsx", extension=".jsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert "message" in result[0].props
        assert "severity" in result[0].props

    def test_extracts_callback_outputs(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Form.tsx",
            (
                "interface FormProps {\n"
                "  onSubmit: () => void;\n"
                "  onChange: (val: string) => void;\n"
                "}\n"
                "export function Form({ onSubmit, onChange }: FormProps) {\n"
                "  return <form onSubmit={onSubmit}></form>;\n"
                "}\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Form.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert "onSubmit" in result[0].outputs
        assert "onChange" in result[0].outputs

    def test_ignores_non_shared_directory(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/pages/Home.tsx",
            "export function Home() { return <div>Home</div>; }",
        )
        inv = _inventory(
            _file_entry("src/pages/Home.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 0

    def test_ignores_test_files(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Button.test.tsx",
            "test('renders', () => {});",
        )
        inv = _inventory(
            _file_entry(
                "src/components/Button.test.tsx",
                extension=".tsx",
                category="test",
            ),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 0

    def test_detects_loading_state(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/DataTable.tsx",
            (
                "export function DataTable({ isLoading }: { isLoading: boolean }) {\n"
                "  if (isLoading) return <Spinner />;\n"
                "  return <table></table>;\n"
                "}\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/DataTable.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert "loading" in result[0].states

    def test_detects_error_state(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Panel.tsx",
            (
                "export function Panel({ error }: { error?: string }) {\n"
                "  if (error) return <div>{error}</div>;\n"
                "  return <div>OK</div>;\n"
                "}\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Panel.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert "error" in result[0].states

    def test_detects_empty_state(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/List.tsx",
            (
                "export function List({ items }: { items: string[] }) {\n"
                "  if (isEmpty) return <div>No items</div>;\n"
                "  return <ul>{items.map(i => <li>{i}</li>)}</ul>;\n"
                "}\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/List.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert "empty" in result[0].states


# ---------------------------------------------------------------------------
# Vue component discovery and extraction
# ---------------------------------------------------------------------------


class TestVueComponents:
    """Tests for Vue SFC discovery and extraction."""

    def test_discovers_vue_sfc(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Modal.vue",
            (
                "<template><div>Modal</div></template>\n"
                "<script setup>\ndefineProps({ title: String })\n</script>\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Modal.vue", extension=".vue"),
        )
        result = analyze_components(inv, _profile("vue"), tmp_path)
        assert len(result) == 1
        assert result[0].name == "Modal"

    def test_extracts_define_props(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Badge.vue",
            (
                '<script setup lang="ts">\n'
                "defineProps<{\n"
                "  label: string;\n"
                "  color: string;\n"
                "}>()\n"
                "</script>\n"
                "<template><span>{{ label }}</span></template>\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Badge.vue", extension=".vue"),
        )
        result = analyze_components(inv, _profile("vue"), tmp_path)
        assert len(result) == 1
        assert "label" in result[0].props
        assert "color" in result[0].props

    def test_extracts_options_api_props_object(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Tag.vue",
            (
                "<script>\n"
                "export default {\n"
                "  props: {\n"
                "    text: String,\n"
                "    variant: { type: String, default: 'primary' },\n"
                "  },\n"
                "}\n"
                "</script>\n"
                "<template><span>{{ text }}</span></template>\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Tag.vue", extension=".vue"),
        )
        result = analyze_components(inv, _profile("vue"), tmp_path)
        assert len(result) == 1
        assert "text" in result[0].props
        assert "variant" in result[0].props

    def test_extracts_options_api_props_array(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Chip.vue",
            (
                "<script>\n"
                "export default {\n"
                "  props: ['label', 'color'],\n"
                "}\n"
                "</script>\n"
                "<template><span>{{ label }}</span></template>\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Chip.vue", extension=".vue"),
        )
        result = analyze_components(inv, _profile("vue"), tmp_path)
        assert len(result) == 1
        assert "label" in result[0].props
        assert "color" in result[0].props

    def test_extracts_define_emits(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Dialog.vue",
            (
                "<script setup>\n"
                "defineEmits(['close', 'confirm'])\n"
                "</script>\n"
                "<template><div>Dialog</div></template>\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Dialog.vue", extension=".vue"),
        )
        result = analyze_components(inv, _profile("vue"), tmp_path)
        assert len(result) == 1
        assert "close" in result[0].outputs
        assert "confirm" in result[0].outputs

    def test_extracts_options_api_emits(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Popup.vue",
            (
                "<script>\n"
                "export default {\n"
                "  emits: ['open', 'dismiss'],\n"
                "}\n"
                "</script>\n"
                "<template><div>Popup</div></template>\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Popup.vue", extension=".vue"),
        )
        result = analyze_components(inv, _profile("vue"), tmp_path)
        assert len(result) == 1
        assert "open" in result[0].outputs
        assert "dismiss" in result[0].outputs


# ---------------------------------------------------------------------------
# Svelte component discovery and extraction
# ---------------------------------------------------------------------------


class TestSvelteComponents:
    """Tests for Svelte component discovery and extraction."""

    def test_discovers_svelte_component(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Toggle.svelte",
            (
                "<script>\n"
                "  export let checked = false;\n"
                "  export let label;\n"
                "</script>\n"
                "<label>{label} <input type='checkbox' bind:checked /></label>\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Toggle.svelte", extension=".svelte"),
        )
        result = analyze_components(inv, _profile("svelte"), tmp_path)
        assert len(result) == 1
        assert result[0].name == "Toggle"

    def test_extracts_export_let_props(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Slider.svelte",
            (
                "<script>\n"
                "  export let min = 0;\n"
                "  export let max = 100;\n"
                "  export let value;\n"
                "</script>\n"
                "<input type='range' {min} {max} bind:value />\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Slider.svelte", extension=".svelte"),
        )
        result = analyze_components(inv, _profile("svelte"), tmp_path)
        assert len(result) == 1
        assert "min" in result[0].props
        assert "max" in result[0].props
        assert "value" in result[0].props

    def test_extracts_dispatch_events(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Dropdown.svelte",
            (
                "<script>\n"
                "  import { createEventDispatcher } from 'svelte';\n"
                "  const dispatch = createEventDispatcher();\n"
                "  export let options;\n"
                "  function select(opt) { dispatch('select', opt); }\n"
                "  function close() { dispatch('close'); }\n"
                "</script>\n"
                "<ul>{#each options as opt}<li on:click={() => select(opt)}>"
                "{opt}</li>{/each}</ul>\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Dropdown.svelte", extension=".svelte"),
        )
        result = analyze_components(inv, _profile("svelte"), tmp_path)
        assert len(result) == 1
        assert "select" in result[0].outputs
        assert "close" in result[0].outputs


# ---------------------------------------------------------------------------
# Usage tracking
# ---------------------------------------------------------------------------


class TestUsageTracking:
    """Tests for component usage location tracking."""

    def test_tracks_import_usage(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Button.tsx",
            "export function Button() { return <button>Click</button>; }",
        )
        _write_file(
            tmp_path,
            "src/pages/Home.tsx",
            (
                "import { Button } from '../components/Button';\n"
                "export function Home() { return <Button />; }\n"
            ),
        )
        _write_file(
            tmp_path,
            "src/pages/About.tsx",
            (
                "import { Button } from '../components/Button';\n"
                "export function About() { return <Button />; }\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Button.tsx", extension=".tsx"),
            _file_entry("src/pages/Home.tsx", extension=".tsx"),
            _file_entry("src/pages/About.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert len(result[0].usage_locations) == 2
        assert "src/pages/Home.tsx" in result[0].usage_locations
        assert "src/pages/About.tsx" in result[0].usage_locations

    def test_tracks_vue_template_tag_usage(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Badge.vue",
            (
                "<template><span>{{ label }}</span></template>\n"
                "<script setup>\ndefineProps({ label: String })\n</script>\n"
            ),
        )
        _write_file(
            tmp_path,
            "src/views/Profile.vue",
            (
                "<template><div><Badge label='new' /></div></template>\n"
                "<script setup>\nimport Badge from '../components/Badge.vue';\n"
                "</script>\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Badge.vue", extension=".vue"),
            _file_entry("src/views/Profile.vue", extension=".vue"),
        )
        result = analyze_components(inv, _profile("vue"), tmp_path)
        assert len(result) == 1
        assert "src/views/Profile.vue" in result[0].usage_locations

    def test_single_usage_not_shared(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Icon.tsx",
            "export function Icon() { return <svg></svg>; }",
        )
        _write_file(
            tmp_path,
            "src/pages/Home.tsx",
            "import { Icon } from '../components/Icon';\n",
        )
        inv = _inventory(
            _file_entry("src/components/Icon.tsx", extension=".tsx"),
            _file_entry("src/pages/Home.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert len(result[0].usage_locations) == 1

    def test_no_usage_zero_locations(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Orphan.tsx",
            "export function Orphan() { return <div>unused</div>; }",
        )
        inv = _inventory(
            _file_entry("src/components/Orphan.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert result[0].usage_locations == []


# ---------------------------------------------------------------------------
# Analyzer skipping
# ---------------------------------------------------------------------------


class TestAnalyzerSkipping:
    """Tests for skipping analysis when no frontend framework detected."""

    def test_skips_when_no_frontend_stacks(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Button.tsx",
            "export function Button() { return <button />; }",
        )
        inv = _inventory(
            _file_entry("src/components/Button.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("fastapi"), tmp_path)
        assert result == []

    def test_skips_with_empty_profile(self, tmp_path: Path) -> None:
        inv = _inventory()
        result = analyze_components(inv, _profile(), tmp_path)
        assert result == []

    def test_runs_only_for_detected_framework(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Button.tsx",
            "export function Button() { return <button />; }",
        )
        _write_file(
            tmp_path,
            "src/components/Modal.vue",
            "<template><div>Modal</div></template>",
        )
        inv = _inventory(
            _file_entry("src/components/Button.tsx", extension=".tsx"),
            _file_entry("src/components/Modal.vue", extension=".vue"),
        )
        # Only React detected, not Vue.
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert result[0].name == "Button"


# ---------------------------------------------------------------------------
# Surface data model
# ---------------------------------------------------------------------------


class TestSurfaceOutput:
    """Tests for the ComponentSurface output format."""

    def test_surface_has_source_ref(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Btn.tsx",
            "export function Btn() { return <button />; }",
        )
        inv = _inventory(
            _file_entry("src/components/Btn.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert len(result[0].source_refs) == 1
        assert result[0].source_refs[0].file_path == "src/components/Btn.tsx"

    def test_surface_serializes_to_dict(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Tag.vue",
            (
                "<script setup>\n"
                "defineProps({ label: String })\n"
                "defineEmits(['click'])\n"
                "</script>\n"
                "<template><span>{{ label }}</span></template>\n"
            ),
        )
        inv = _inventory(
            _file_entry("src/components/Tag.vue", extension=".vue"),
        )
        result = analyze_components(inv, _profile("vue"), tmp_path)
        assert len(result) == 1
        d = result[0].to_dict()
        assert d["name"] == "Tag"
        assert d["surface_type"] == "component"
        assert "label" in d["props"]
        assert "click" in d["outputs"]

    def test_nextjs_triggers_react_analysis(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Nav.tsx",
            "export function Nav() { return <nav />; }",
        )
        inv = _inventory(
            _file_entry("src/components/Nav.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("nextjs"), tmp_path)
        assert len(result) == 1
        assert result[0].name == "Nav"

    def test_sveltekit_triggers_svelte_analysis(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Header.svelte",
            "<script>\n  export let title;\n</script>\n<h1>{title}</h1>\n",
        )
        inv = _inventory(
            _file_entry("src/components/Header.svelte", extension=".svelte"),
        )
        result = analyze_components(inv, _profile("sveltekit"), tmp_path)
        assert len(result) == 1
        assert result[0].name == "Header"
        assert "title" in result[0].props


# ---------------------------------------------------------------------------
# Multiple components
# ---------------------------------------------------------------------------


class TestMultipleComponents:
    """Tests for discovering multiple components at once."""

    def test_discovers_multiple_components(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Button.tsx",
            "export function Button() { return <button />; }",
        )
        _write_file(
            tmp_path,
            "src/components/Input.tsx",
            (
                "interface InputProps { value: string; onChange: () => void; }\n"
                "export function Input(props: InputProps) { return <input />; }\n"
            ),
        )
        _write_file(
            tmp_path,
            "src/components/Card.tsx",
            "export function Card() { return <div />; }",
        )
        inv = _inventory(
            _file_entry("src/components/Button.tsx", extension=".tsx"),
            _file_entry("src/components/Input.tsx", extension=".tsx"),
            _file_entry("src/components/Card.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 3
        names = {s.name for s in result}
        assert names == {"Button", "Input", "Card"}

    def test_mixed_frameworks(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/Button.tsx",
            "export function Button() { return <button />; }",
        )
        _write_file(
            tmp_path,
            "src/components/Modal.vue",
            "<template><div>Modal</div></template>",
        )
        inv = _inventory(
            _file_entry("src/components/Button.tsx", extension=".tsx"),
            _file_entry("src/components/Modal.vue", extension=".vue"),
        )
        result = analyze_components(inv, _profile("react", "vue"), tmp_path)
        assert len(result) == 2
        names = {s.name for s in result}
        assert names == {"Button", "Modal"}


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_inventory(self, tmp_path: Path) -> None:
        inv = _inventory()
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert result == []

    def test_unreadable_file(self, tmp_path: Path) -> None:
        # File in inventory but not on disk.
        inv = _inventory(
            _file_entry("src/components/Ghost.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert result[0].name == "Ghost"
        assert result[0].props == []

    def test_kebab_case_filename(self, tmp_path: Path) -> None:
        _write_file(
            tmp_path,
            "src/components/date-picker.tsx",
            "export function DatePicker() { return <div />; }",
        )
        inv = _inventory(
            _file_entry("src/components/date-picker.tsx", extension=".tsx"),
        )
        result = analyze_components(inv, _profile("react"), tmp_path)
        assert len(result) == 1
        assert result[0].name == "DatePicker"
