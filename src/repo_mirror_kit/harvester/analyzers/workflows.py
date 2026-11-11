"""Entity state-machine extraction (BEAN-067).

Captures entity lifecycles — state sets and legal transitions — from:

**Declared** (highest confidence)
- Python ``transitions.Machine(states=[...], transitions=[...])``
- Python ``django-fsm`` ``@transition(field=..., source=..., target=...)``
- Explicit transition tables: a dict named ``*TRANSITIONS*`` / ``*WORKFLOW*`` /
  ``*ALLOWED*`` mapping a state to its reachable states (Python and JS/TS)
- XState ``createMachine({ initial, states: { s: { on: { EVT: 'target' } } } })``

**Inferred**
- A status-like enum (``*Status`` / ``*State`` / ``*Stage`` / ``*Phase``) plus
  functions that assign one of its members to an attribute. Source states come
  from comparisons against the same enum in the function; each transition is
  linked to the API surface that performs it (the endpoint itself, or an
  endpoint that calls the function).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    SourceRef,
    WorkflowSurface,
    WorkflowTransition,
)
from repo_mirror_kit.harvester.inventory import InventoryResult
from repo_mirror_kit.harvester.parsing import ParsedSource, parse_source

logger = structlog.get_logger()

_STATUS_ENUM_RE = re.compile(r"(Status|State|Stage|Phase|Step)$")
_TABLE_NAME_RE = re.compile(r"(TRANSITION|WORKFLOW|ALLOWED|STATE_MACHINE|FLOW)", re.I)
_ENUM_BASES = {"Enum", "StrEnum", "IntEnum", "IntFlag", "Flag"}
_SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "dist", "build", "__pycache__"}
_MAX_BYTES = 500_000


def _read(path: Path) -> str | None:
    try:
        if path.stat().st_size > _MAX_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------


def _str_or_attr(node: ast.expr | None) -> str | None:
    """State name from ``'draft'`` or ``Status.DRAFT``."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def _state_list(node: ast.expr | None) -> list[str]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [s for e in node.elts if (s := _str_or_attr(e))]
    single = _str_or_attr(node)
    return [single] if single else []


def _enum_classes(tree: ast.Module) -> dict[str, list[str]]:
    enums: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = {
            b.id
            if isinstance(b, ast.Name)
            else b.attr
            if isinstance(b, ast.Attribute)
            else ""
            for b in node.bases
        }
        if not bases & _ENUM_BASES:
            continue
        members = [
            t.id
            for st in node.body
            if isinstance(st, ast.Assign)
            for t in st.targets
            if isinstance(t, ast.Name) and not t.id.startswith("_")
        ]
        if members:
            enums[node.name] = members
    return enums


def _py_machine_calls(tree: ast.Module, rel: str) -> list[WorkflowSurface]:
    out: list[WorkflowSurface] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        fname = (
            fn.id
            if isinstance(fn, ast.Name)
            else fn.attr
            if isinstance(fn, ast.Attribute)
            else ""
        )
        if fname not in ("Machine", "GraphMachine", "HierarchicalMachine"):
            continue
        kw = {k.arg: k.value for k in node.keywords if k.arg}
        if "states" not in kw or "transitions" not in kw:
            continue
        states: list[str] = []
        st = kw["states"]
        if isinstance(st, (ast.List, ast.Tuple)):
            for e in st.elts:
                if isinstance(e, ast.Dict):
                    for k, v in zip(e.keys, e.values, strict=False):
                        if isinstance(k, ast.Constant) and k.value == "name":
                            nm = _str_or_attr(v)
                            if nm:
                                states.append(nm)
                elif (nm := _str_or_attr(e)) is not None:
                    states.append(nm)
        transitions: list[WorkflowTransition] = []
        tr = kw["transitions"]
        for e in tr.elts if isinstance(tr, (ast.List, ast.Tuple)) else []:
            trigger = src = dest = guard = ""
            sources: list[str] = []
            if isinstance(e, ast.Dict):
                d = {
                    k.value: v
                    for k, v in zip(e.keys, e.values, strict=False)
                    if isinstance(k, ast.Constant)
                }
                trigger = _str_or_attr(d.get("trigger")) or ""
                sources = _state_list(d.get("source")) or ["*"]
                dest = _str_or_attr(d.get("dest")) or ""
                cond = d.get("conditions")
                guard = ", ".join(_state_list(cond)) if cond else ""
            elif isinstance(e, (ast.List, ast.Tuple)) and len(e.elts) >= 3:
                trigger = _str_or_attr(e.elts[0]) or ""
                sources = _state_list(e.elts[1]) or ["*"]
                dest = _str_or_attr(e.elts[2]) or ""
            for src in sources:
                if dest:
                    transitions.append(
                        WorkflowTransition(
                            from_state=src, to_state=dest, trigger=trigger, guard=guard
                        )
                    )
                    if dest not in states:
                        states.append(dest)
        if transitions:
            initial = _str_or_attr(kw.get("initial")) or ""
            out.append(
                WorkflowSurface(
                    name=f"{rel.rsplit('/', 1)[-1].removesuffix('.py')} state machine",
                    entity_ref=(_str_or_attr(node.args[0]) if node.args else None)
                    or "",
                    states=states,
                    initial_state=initial,
                    transitions=transitions,
                    confidence="declared",
                    source_library="transitions",
                    source_refs=[SourceRef(file_path=rel, start_line=node.lineno)],
                )
            )
    return out


def _py_fsm_decorators(tree: ast.Module, rel: str) -> list[WorkflowSurface]:
    by_class: dict[str, WorkflowSurface] = {}
    for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        for fn in cls.body:
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in fn.decorator_list:
                if not (
                    isinstance(deco, ast.Call)
                    and (
                        (
                            isinstance(deco.func, ast.Name)
                            and deco.func.id == "transition"
                        )
                        or (
                            isinstance(deco.func, ast.Attribute)
                            and deco.func.attr == "transition"
                        )
                    )
                ):
                    continue
                kw = {k.arg: k.value for k in deco.keywords if k.arg}
                sources = _state_list(kw.get("source")) or ["*"]
                target = _str_or_attr(kw.get("target"))
                if not target:
                    continue
                wf = by_class.setdefault(
                    cls.name,
                    WorkflowSurface(
                        name=f"{cls.name} lifecycle",
                        entity_ref=cls.name,
                        confidence="declared",
                        source_library="django-fsm",
                        source_refs=[SourceRef(file_path=rel, start_line=cls.lineno)],
                    ),
                )
                guard = ""
                if "conditions" in kw:
                    guard = ", ".join(_state_list(kw["conditions"]))
                for s in sources:
                    wf.transitions.append(
                        WorkflowTransition(
                            from_state=s, to_state=target, trigger=fn.name, guard=guard
                        )
                    )
                    for st in (s, target):
                        if st != "*" and st not in wf.states:
                            wf.states.append(st)
    return list(by_class.values())


def _py_tables(
    tree: ast.Module, rel: str, enums: dict[str, list[str]]
) -> list[WorkflowSurface]:
    out: list[WorkflowSurface] = []
    for node in tree.body:
        target_name = ""
        value: ast.expr | None = None
        if (
            isinstance(node, ast.Assign)
            and node.targets
            and isinstance(node.targets[0], ast.Name)
        ):
            target_name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name, value = node.target.id, node.value
        if (
            not target_name
            or not _TABLE_NAME_RE.search(target_name)
            or not isinstance(value, ast.Dict)
        ):
            continue
        transitions: list[WorkflowTransition] = []
        states: list[str] = []
        ok = True
        for k, v in zip(value.keys, value.values, strict=False):
            src = _str_or_attr(k)
            dests = _state_list(v)
            if src is None or (
                not dests and not isinstance(v, (ast.List, ast.Tuple, ast.Set))
            ):
                ok = False
                break
            if src not in states:
                states.append(src)
            for d in dests:
                transitions.append(WorkflowTransition(from_state=src, to_state=d))
                if d not in states:
                    states.append(d)
        if ok and transitions:
            entity = target_name
            for enum_name, members in enums.items():
                if set(states) <= set(members):
                    entity = enum_name
                    break
            out.append(
                WorkflowSurface(
                    name=f"{entity} transition table",
                    entity_ref=entity,
                    states=states,
                    transitions=transitions,
                    confidence="declared",
                    source_library="transition-table",
                    source_refs=[SourceRef(file_path=rel, start_line=node.lineno)],
                )
            )
    return out


def _function_defs(
    tree: ast.Module,
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        n.name: n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _enum_refs(node: ast.AST, enum_name: str) -> list[str]:
    return [
        n.attr
        for n in ast.walk(node)
        if isinstance(n, ast.Attribute)
        and isinstance(n.value, ast.Name)
        and n.value.id == enum_name
    ]


def _py_inferred(
    tree: ast.Module,
    rel: str,
    enums: dict[str, list[str]],
    apis: list[ApiSurface],
) -> list[WorkflowSurface]:
    status_enums = {
        n: m for n, m in enums.items() if _STATUS_ENUM_RE.search(n) and len(m) >= 2
    }
    if not status_enums:
        return []
    funcs = _function_defs(tree)
    # endpoint function name -> API names (decorator line match)
    endpoint_apis: dict[str, list[str]] = {}
    for api in apis:
        for ref in api.source_refs:
            if ref.file_path != rel or ref.start_line is None:
                continue
            for name, fn in funcs.items():
                if any(d.lineno == ref.start_line for d in fn.decorator_list):
                    endpoint_apis.setdefault(name, []).append(api.name)
    calls: dict[str, set[str]] = {
        name: {
            c.func.id
            for c in ast.walk(fn)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
        }
        for name, fn in funcs.items()
    }

    out: list[WorkflowSurface] = []
    for enum_name, members in status_enums.items():
        transitions: list[WorkflowTransition] = []
        for fname, fn in funcs.items():
            assigned: list[str] = []
            for n in ast.walk(fn):
                if isinstance(n, ast.Assign) and any(
                    isinstance(t, ast.Attribute) for t in n.targets
                ):
                    assigned.extend(_enum_refs(n.value, enum_name))
                elif (
                    isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr
                    in (
                        "update",
                        "setattr",
                        "set_status",
                        "transition_to",
                    )
                ):
                    assigned.extend(_enum_refs(n, enum_name))
            if not assigned:
                continue
            # states compared in tests/conditions of this function
            guards: list[str] = []
            for n in ast.walk(fn):
                if isinstance(n, (ast.If, ast.While, ast.Assert)):
                    guards.extend(_enum_refs(n.test, enum_name))
            sources = [g for g in dict.fromkeys(guards) if g not in assigned] or ["*"]
            refs = list(endpoint_apis.get(fname, []))
            for ep, called in calls.items():
                if fname in called:
                    refs.extend(endpoint_apis.get(ep, []))
            for target in dict.fromkeys(assigned):
                for src in sources:
                    transitions.append(
                        WorkflowTransition(
                            from_state=src,
                            to_state=target,
                            trigger=fname,
                            guard=f"current state is {src}" if src != "*" else "",
                            trigger_ref=refs[0] if refs else "",
                        )
                    )
        if transitions:
            out.append(
                WorkflowSurface(
                    name=f"{enum_name} lifecycle",
                    entity_ref=enum_name,
                    states=list(members),
                    initial_state="",
                    transitions=transitions,
                    confidence="inferred",
                    source_library="enum+assignments",
                    source_refs=[SourceRef(file_path=rel)],
                )
            )
    return out


# ---------------------------------------------------------------------------
# JS / TS
# ---------------------------------------------------------------------------


def _js_key(ps: ParsedSource, node: Any) -> str:
    return ps.text(node).strip("'\"")


def _js_array_strings(ps: ParsedSource, node: Any) -> list[str]:
    if node is None:
        return []
    if node.type == "array":
        out: list[str] = []
        for c in node.children:
            v = ps.string_value(c)
            if v is not None:
                out.append(v)
            elif c.type in ("member_expression", "identifier"):
                out.append(ps.text(c).split(".")[-1])
        return out
    v = ps.string_value(node)
    return [v] if v is not None else []


def _js_xstate(ps: ParsedSource, rel: str) -> list[WorkflowSurface]:
    out: list[WorkflowSurface] = []
    for call in ps.find_all("call_expression"):
        fn = call.child_by_field_name("function")
        if fn is None or ps.text(fn).split(".")[-1] not in ("createMachine", "Machine"):
            continue
        args = call.child_by_field_name("arguments")
        cfg = next(
            (a for a in (args.children if args else []) if a.type == "object"), None
        )
        if cfg is None:
            continue
        initial = ""
        states_obj = None
        machine_id = ""
        for pair in cfg.children:
            if pair.type != "pair":
                continue
            k = _js_key(ps, pair.child_by_field_name("key"))
            v = pair.child_by_field_name("value")
            if k == "initial" and v is not None:
                initial = ps.string_value(v) or ""
            elif k == "id" and v is not None:
                machine_id = ps.string_value(v) or ""
            elif k == "states" and v is not None and v.type == "object":
                states_obj = v
        if states_obj is None:
            continue
        states: list[str] = []
        transitions: list[WorkflowTransition] = []
        for spair in states_obj.children:
            if spair.type != "pair":
                continue
            state = _js_key(ps, spair.child_by_field_name("key"))
            states.append(state)
            sval = spair.child_by_field_name("value")
            on = None
            if sval is not None and sval.type == "object":
                for p2 in sval.children:
                    if (
                        p2.type == "pair"
                        and _js_key(ps, p2.child_by_field_name("key")) == "on"
                    ):
                        on = p2.child_by_field_name("value")
            if on is None or on.type != "object":
                continue
            for ev in on.children:
                if ev.type != "pair":
                    continue
                event = _js_key(ps, ev.child_by_field_name("key"))
                tv = ev.child_by_field_name("value")
                if tv is None:
                    continue
                target = ps.string_value(tv)
                guard = ""
                if target is None and tv.type == "object":
                    for tp in tv.children:
                        if tp.type != "pair":
                            continue
                        tk = _js_key(ps, tp.child_by_field_name("key"))
                        tval = tp.child_by_field_name("value")
                        if tk == "target" and tval is not None:
                            target = ps.string_value(tval)
                        elif tk in ("guard", "cond") and tval is not None:
                            guard = ps.string_value(tval) or ps.text(tval)[:60]
                if target:
                    transitions.append(
                        WorkflowTransition(
                            from_state=state,
                            to_state=target,
                            trigger=event,
                            guard=guard,
                        )
                    )
        if transitions:
            out.append(
                WorkflowSurface(
                    name=f"{machine_id or rel.rsplit('/', 1)[-1].split('.')[0]} state machine",
                    entity_ref=machine_id,
                    states=states,
                    initial_state=initial,
                    transitions=transitions,
                    confidence="declared",
                    source_library="xstate",
                    source_refs=[SourceRef(file_path=rel, start_line=ps.line_of(call))],
                )
            )
    return out


def _js_tables(ps: ParsedSource, rel: str) -> list[WorkflowSurface]:
    out: list[WorkflowSurface] = []
    for decl in ps.find_all("variable_declarator"):
        name = decl.child_by_field_name("name")
        value = decl.child_by_field_name("value")
        if name is None or value is None or value.type != "object":
            continue
        if not _TABLE_NAME_RE.search(ps.text(name)):
            continue
        states: list[str] = []
        transitions: list[WorkflowTransition] = []
        ok = True
        for pair in value.children:
            if pair.type != "pair":
                continue
            src = _js_key(ps, pair.child_by_field_name("key"))
            v = pair.child_by_field_name("value")
            if v is None or v.type != "array":
                ok = False
                break
            states.append(src)
            for d in _js_array_strings(ps, v):
                transitions.append(WorkflowTransition(from_state=src, to_state=d))
                if d not in states:
                    states.append(d)
        if ok and transitions:
            out.append(
                WorkflowSurface(
                    name=f"{ps.text(name)} transition table",
                    entity_ref=ps.text(name),
                    states=states,
                    transitions=transitions,
                    confidence="declared",
                    source_library="transition-table",
                    source_refs=[SourceRef(file_path=rel, start_line=ps.line_of(decl))],
                )
            )
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def analyze_workflows(
    workdir: Path,
    inventory: InventoryResult,
    apis: list[ApiSurface] | None = None,
) -> list[WorkflowSurface]:
    """Extract entity state machines (declared and inferred)."""
    apis = apis or []
    found: list[WorkflowSurface] = []
    repo_enums = _repo_enums(workdir, inventory)
    for entry in inventory.files:
        rel = entry.path
        if any(part in _SKIP_DIRS for part in rel.split("/")):
            continue
        if (
            ".test." in rel
            or ".spec." in rel
            or rel.startswith("tests/")
            or "/tests/" in rel
        ):
            continue
        if rel.endswith(".py"):
            text = _read(workdir / rel)
            if text is None:
                continue
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            enums = _enum_classes(tree)
            # Enums may be defined in another module; merge repo-wide enums lazily.
            enums = {**repo_enums, **enums}
            found.extend(_py_machine_calls(tree, rel))
            found.extend(_py_fsm_decorators(tree, rel))
            found.extend(_py_tables(tree, rel, enums))
            found.extend(_py_inferred(tree, rel, enums, apis))
        elif rel.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs")):
            text = _read(workdir / rel)
            if text is None or not (
                "createMachine" in text
                or _TABLE_NAME_RE.search(text)
                or "Machine(" in text
            ):
                continue
            ps = parse_source(rel, text)
            if ps is None:
                continue
            found.extend(_js_xstate(ps, rel))
            found.extend(_js_tables(ps, rel))
    # Dedupe identical (name, source) machines.
    seen: set[tuple[str, str]] = set()
    unique: list[WorkflowSurface] = []
    for wf in found:
        key = (wf.name, wf.source_refs[0].file_path if wf.source_refs else "")
        if key not in seen:
            seen.add(key)
            unique.append(wf)
    logger.info("workflows_analyzed", workflows=len(unique))
    return unique


def _repo_enums(workdir: Path, inventory: InventoryResult) -> dict[str, list[str]]:
    """Status-like enums defined anywhere in the repo."""
    result: dict[str, list[str]] = {}
    for entry in inventory.files:
        if not entry.path.endswith(".py") or any(
            p in _SKIP_DIRS for p in entry.path.split("/")
        ):
            continue
        text = _read(workdir / entry.path)
        if text is None or "Enum" not in text:
            continue
        try:
            result.update(_enum_classes(ast.parse(text)))
        except SyntaxError:
            continue
    return result
