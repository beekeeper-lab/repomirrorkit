"""Tests for state-machine extraction (BEAN-067)."""

from __future__ import annotations

from pathlib import Path

from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface, SourceRef
from repo_mirror_kit.harvester.analyzers.workflows import analyze_workflows
from repo_mirror_kit.harvester.inventory import FileEntry, InventoryResult


def _run(tmp_path: Path, files: dict[str, str], apis: list[ApiSurface] | None = None):  # type: ignore[no-untyped-def]
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    entries = [
        FileEntry(
            path=p,
            size=1,
            extension="." + p.rsplit(".", 1)[-1],
            hash="h",
            category="source",
        )
        for p in files
    ]
    inv = InventoryResult(
        files=entries,
        skipped=[],
        total_files=len(entries),
        total_size=1,
        total_skipped=0,
    )
    return analyze_workflows(tmp_path, inv, apis or [])


ENUM_AND_ENDPOINTS = """\
from enum import Enum

class OrderStatus(Enum):
    DRAFT = 1
    PAID = 2
    SHIPPED = 3

@app.post('/orders/<id>/pay')
def pay(id):
    o = get(id)
    if o.status == OrderStatus.DRAFT:
        o.status = OrderStatus.PAID

@app.post('/orders/<id>/ship')
def ship(id):
    o = get(id)
    if o.status == OrderStatus.PAID:
        o.status = OrderStatus.SHIPPED
"""


def test_inferred_from_enum_and_endpoints(tmp_path: Path) -> None:
    apis = [
        ApiSurface(
            name="POST /orders/<id>/pay",
            method="POST",
            path="/orders/<id>/pay",
            source_refs=[SourceRef(file_path="app.py", start_line=8)],
        ),
        ApiSurface(
            name="POST /orders/<id>/ship",
            method="POST",
            path="/orders/<id>/ship",
            source_refs=[SourceRef(file_path="app.py", start_line=14)],
        ),
    ]
    (wf,) = _run(tmp_path, {"app.py": ENUM_AND_ENDPOINTS}, apis)
    assert wf.confidence == "inferred" and wf.states == ["DRAFT", "PAID", "SHIPPED"]
    got = {(t.from_state, t.to_state, t.trigger_ref) for t in wf.transitions}
    assert got == {
        ("DRAFT", "PAID", "POST /orders/<id>/pay"),
        ("PAID", "SHIPPED", "POST /orders/<id>/ship"),
    }


def test_python_transitions_machine_is_declared(tmp_path: Path) -> None:
    code = """\
from transitions import Machine
m = Machine(model=None, states=['a', 'b', {'name': 'c'}], initial='a', transitions=[
    {'trigger': 'go', 'source': 'a', 'dest': 'b'},
    ['finish', ['a', 'b'], 'c'],
])
"""
    (wf,) = _run(tmp_path, {"m.py": code})
    assert wf.confidence == "declared" and wf.initial_state == "a"
    assert {(t.from_state, t.to_state, t.trigger) for t in wf.transitions} == {
        ("a", "b", "go"),
        ("a", "c", "finish"),
        ("b", "c", "finish"),
    }


def test_django_fsm_decorators(tmp_path: Path) -> None:
    code = """\
from django_fsm import transition
class Doc:
    @transition(field=state, source='draft', target='review')
    def submit(self): pass
    @transition(field=state, source=['review', 'draft'], target='done')
    def finish(self): pass
"""
    (wf,) = _run(tmp_path, {"doc.py": code})
    assert wf.entity_ref == "Doc" and wf.source_library == "django-fsm"
    assert len(wf.transitions) == 3 and set(wf.states) == {"draft", "review", "done"}


def test_xstate_machine_with_guard(tmp_path: Path) -> None:
    ts = """\
import { createMachine } from 'xstate';
export const m = createMachine({
  id: 'door', initial: 'closed',
  states: {
    closed: { on: { OPEN: { target: 'open', guard: 'unlocked' } } },
    open: { on: { CLOSE: 'closed' } },
  },
});
"""
    (wf,) = _run(tmp_path, {"door.ts": ts})
    assert wf.initial_state == "closed" and wf.confidence == "declared"
    assert {(t.from_state, t.to_state, t.trigger, t.guard) for t in wf.transitions} == {
        ("closed", "open", "OPEN", "unlocked"),
        ("open", "closed", "CLOSE", ""),
    }


def test_js_transition_table(tmp_path: Path) -> None:
    ts = "export const ALLOWED_TRANSITIONS = { draft: ['live'], live: ['archived'], archived: [] };"
    (wf,) = _run(tmp_path, {"t.ts": ts})
    assert {(t.from_state, t.to_state) for t in wf.transitions} == {
        ("draft", "live"),
        ("live", "archived"),
    }


def test_no_workflows(tmp_path: Path) -> None:
    assert _run(tmp_path, {"a.py": "x = 1\n"}) == []
