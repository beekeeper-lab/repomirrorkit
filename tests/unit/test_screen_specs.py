"""Tests for screen spec YAML + navigation map (BEAN-073)."""

from __future__ import annotations

import re
from pathlib import Path

import jsonschema
import yaml

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ScreenAction,
    ScreenField,
    ScreenSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.generator.screen_specs import (
    SCREEN_SCHEMA,
    generate_screen_specs,
    navigation_mermaid,
)


def _screens() -> list[ScreenSurface]:
    form = ScreenSurface(
        name="UserForm",
        screen_name="UserForm",
        route_ref="/users/new",
        framework="react",
        source_refs=[SourceRef(file_path="a/UserForm.tsx")],
        fields=[
            ScreenField(
                name="name",
                label="Name",
                required=True,
                validation=["required", "minLength=2"],
                bound_api_field="POST /api/users#name",
                bound_model_field="User.name",
                mapping_confidence="name-match",
            ),
            ScreenField(name="nick", gap="no matching API request field"),
        ],
        actions=[
            ScreenAction(
                trigger="submit", api_ref="POST /api/users", navigation_target="/users"
            )
        ],
        navigation_targets=["/users", "/help"],
    )
    users = ScreenSurface(
        name="Users",
        screen_name="Users",
        route_ref="/users",
        framework="react",
        source_refs=[SourceRef(file_path="a/Users.tsx")],
        navigation_targets=["/users/new"],
    )
    return [users, form]  # unsorted on purpose


def test_one_valid_yaml_per_screen_with_bindings_and_gaps(tmp_path: Path) -> None:
    files = generate_screen_specs(
        SurfaceCollection(screens=_screens()), tmp_path, "demo"
    )
    names = sorted(p.name for p in files)
    assert names == ["README.md", "navigation-map.md", "userform.yaml", "users.yaml"]
    spec = yaml.safe_load((tmp_path / "screens" / "userform.yaml").read_text())
    jsonschema.validate(spec, SCREEN_SCHEMA)
    by = {f["name"]: f for f in spec["fields"]}
    assert by["name"]["binds_to"] == {
        "api": "POST /api/users#name",
        "model": "User.name",
        "confidence": "name-match",
    }
    assert by["nick"]["binds_to"]["model"] is None and by["nick"]["gap"]
    assert spec["gaps"] == ["field 'nick': no matching API request field"]
    assert spec["actions"][0]["navigates_to"] == "/users"


def test_yaml_is_deterministic_and_safe_loadable(tmp_path: Path) -> None:
    first = tmp_path / "a"
    second = tmp_path / "b"
    generate_screen_specs(SurfaceCollection(screens=_screens()), first, "demo")
    generate_screen_specs(
        SurfaceCollection(screens=list(reversed(_screens()))), second, "demo"
    )
    for name in ("userform.yaml", "users.yaml", "navigation-map.md"):
        assert (first / "screens" / name).read_text() == (
            second / "screens" / name
        ).read_text()


def _validate_mermaid(text: str) -> tuple[set[str], set[tuple[str, str]]]:
    """Tiny syntax check for the flowchart subset we emit."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert lines[0] == "flowchart TD"
    nodes: set[str] = set()
    edges: set[tuple[str, str]] = set()
    for ln in lines[1:]:
        edge = re.fullmatch(r"\s{4}(\w+) --> (\w+)", ln)
        node = re.fullmatch(r'\s{4}(\w+)(\(\[".*"\]\)|\[".*"\]|\[/".*"/\])', ln)
        assert edge or node, f"bad mermaid line: {ln!r}"
        if edge:
            edges.add((edge.group(1), edge.group(2)))
        else:
            assert node is not None
            nodes.add(node.group(1))
    assert all(a in nodes and b in nodes for a, b in edges), "edge to undeclared node"
    return nodes, edges


def test_navigation_map_edges_match_navigation_targets() -> None:
    screens = _screens()
    nodes, edges = _validate_mermaid(navigation_mermaid(screens))
    # S1=Users, S2=UserForm (list order). Users -> UserForm; UserForm -> Users + /help external.
    assert ("S1", "S2") in edges and ("S2", "S1") in edges
    external = [e for e in edges if e[1].startswith("X")]
    assert len(external) == 1 and external[0][0] == "S2"
    assert len(nodes) == 3


def test_dynamic_route_matching() -> None:
    a = ScreenSurface(
        name="List",
        screen_name="List",
        route_ref="/items",
        navigation_targets=["/items/:param"],
    )
    b = ScreenSurface(name="Detail", screen_name="Detail", route_ref="/items/[id]")
    _nodes, edges = _validate_mermaid(navigation_mermaid([a, b]))
    assert edges == {("S1", "S2")}


def test_no_screens_writes_nothing(tmp_path: Path) -> None:
    assert generate_screen_specs(SurfaceCollection(), tmp_path, "demo") == []
    assert not (tmp_path / "screens").exists()
