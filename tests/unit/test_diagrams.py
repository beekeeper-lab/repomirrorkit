"""Tests for Mermaid state/sequence diagrams (BEAN-075)."""

from __future__ import annotations

import re
from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    ModelSurface,
    ScreenAction,
    ScreenSurface,
    SurfaceCollection,
    WorkflowSurface,
    WorkflowTransition,
)
from repo_mirror_kit.harvester.generator.diagrams import (
    MAX_SEQUENCE_DIAGRAMS,
    generate_diagrams,
    state_diagram,
    traced_sequence,
)


def _wf() -> WorkflowSurface:
    return WorkflowSurface(
        name="Order lifecycle",
        states=["DRAFT", "PAID", "SHIPPED", "cancelled order"],
        initial_state="DRAFT",
        transitions=[
            WorkflowTransition(
                "DRAFT", "PAID", trigger="pay", guard="has payment: card"
            ),
            WorkflowTransition("PAID", "SHIPPED", trigger="ship"),
            WorkflowTransition("*", "cancelled order", trigger="cancel"),
        ],
    )


def _check_state(text: str) -> tuple[set[str], set[tuple[str, str]]]:
    lines = text.splitlines()
    assert lines[0] == "stateDiagram-v2"
    ids: dict[str, str] = {}
    edges: set[tuple[str, str]] = set()
    for ln in lines[1:]:
        m = re.fullmatch(r'    state "([^"]+)" as (S\d+)', ln)
        e = re.fullmatch(r"    (S\d+|\[\*\]) --> (S\d+)(?:: .+)?", ln)
        assert m or e, f"bad line {ln!r}"
        if m:
            ids[m.group(2)] = m.group(1)
        else:
            assert e is not None
            edges.add((ids.get(e.group(1), e.group(1)), ids[e.group(2)]))
    return set(ids.values()), edges


def test_state_diagram_matches_workflow() -> None:
    states, edges = _check_state(state_diagram(_wf()))
    assert states == {"DRAFT", "PAID", "SHIPPED", "cancelled order"}
    assert (
        ("[*]", "DRAFT") in edges
        and ("DRAFT", "PAID") in edges
        and ("PAID", "SHIPPED") in edges
    )
    # wildcard source fans out from every other state
    assert {
        ("DRAFT", "cancelled order"),
        ("PAID", "cancelled order"),
        ("SHIPPED", "cancelled order"),
    } <= edges


def test_guard_colon_is_sanitized() -> None:
    assert "has payment - card" in state_diagram(_wf())


def _check_sequence(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    assert lines[0] == "sequenceDiagram"
    declared: set[str] = set()
    messages: list[tuple[str, str]] = []
    for ln in lines[1:]:
        d = re.fullmatch(r"    (?:actor|participant) (P\d+) as .+", ln)
        m = re.fullmatch(r"    (P\d+)(?:->>|-->>)(P\d+): .+", ln)
        assert d or m, f"bad line {ln!r}"
        if d:
            declared.add(d.group(1))
        else:
            assert m is not None
            assert m.group(1) in declared and m.group(2) in declared
            messages.append((m.group(1), m.group(2)))
    return messages


def test_traced_flow_sequence_keeps_hop_order() -> None:
    api = ApiSurface(name="POST /x", method="POST", path="/x")
    api.enrichment = {
        "traced_flow": [
            {"hop": "Form", "note": "submit"},
            {"hop": "POST /x", "note": "validates"},
            {"hop": "OrderService", "note": "creates order"},
        ]
    }
    diagram = traced_sequence(api)
    assert diagram is not None
    msgs = _check_sequence(diagram)
    assert msgs == [("P1", "P2"), ("P2", "P3"), ("P3", "P4")]
    assert (
        diagram.index("submit")
        < diagram.index("validates")
        < diagram.index("creates order")
    )


def test_structural_sequence_and_cap_reporting(tmp_path: Path) -> None:
    api = ApiSurface(name="POST /api/users", method="POST", path="/api/users")
    model = ModelSurface(name="User", entity_name="User")
    screens = [
        ScreenSurface(
            name=f"Form{i}",
            screen_name=f"Form{i}",
            actions=[
                ScreenAction(
                    trigger="submit",
                    api_ref="POST /api/users",
                    navigation_target="/users",
                )
            ],
        )
        for i in range(MAX_SEQUENCE_DIAGRAMS + 3)
    ]
    coll = SurfaceCollection(
        apis=[api], models=[model], screens=screens, workflows=[_wf()]
    )
    files = generate_diagrams(coll, tmp_path)
    names = {p.name for p in files}
    assert "state-order-lifecycle.md" in names
    seq = [p for p in files if p.name.startswith("sequence-")]
    assert len(seq) == MAX_SEQUENCE_DIAGRAMS
    readme = (tmp_path / "diagrams" / "README.md").read_text()
    assert "skipped (cap 25): 3" in readme
    body = seq[0].read_text()
    _check_sequence(body.split("```mermaid\n")[1].split("\n```")[0])


def test_nothing_to_draw(tmp_path: Path) -> None:
    assert generate_diagrams(SurfaceCollection(), tmp_path) == []
