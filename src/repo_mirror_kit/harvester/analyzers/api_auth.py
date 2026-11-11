"""Handler-level authentication detection (found by the parity eval, 2026-11).

Decorator/middleware auth is caught by the route analyzers. Many apps instead
check credentials *inside* the handler (or a helper it calls): read an
``X-API-Key`` / ``Authorization`` header, compare it, and answer 401/403. This
pass finds that pattern in Python (``ast``) and JS/TS (tree-sitter), marks the
affected :class:`ApiSurface` ``auth="required"`` and emits one
:class:`AuthSurface` per credential mechanism describing it — including the
configuration variable the expected value is read from, when visible.

A handler counts as protected only when BOTH hold within the handler plus the
helpers it calls (two hops): a credential read AND a 401/403 outcome. Reading a
header alone (e.g. for logging) never marks an endpoint protected.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.api_contracts_js import (
    _enclosing_function,
    _Modules,
)
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    AuthSurface,
    SourceRef,
)
from repo_mirror_kit.harvester.parsing import ParsedSource

logger = structlog.get_logger()

_CRED_RE = re.compile(
    r"(api[-_]?key|authorization|auth[-_]?token|access[-_]?token|x-token|bearer)", re.I
)
_MAX_HOPS = 2
_ENV_PY_RE = re.compile(r"environ(?:\.get)?\s*[\(\[]\s*['\"]([A-Za-z0-9_]+)['\"]")
_ENV_JS_RE = re.compile(
    r"process\.env\.([A-Za-z0-9_]+)|process\.env\[['\"]([A-Za-z0-9_]+)['\"]\]"
)


def _display(header: str) -> str:
    """Header name exactly as the source spells it (casing is part of the contract)."""
    return header


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------


def _py_funcs(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        n.name: n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _py_scan(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    funcs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    depth: int = 0,
    seen: frozenset[str] = frozenset(),
) -> tuple[set[str], bool]:
    """(credential headers read, saw 401/403) over func + helpers."""
    headers: set[str] = set()
    denied = False
    for node in ast.walk(func):
        # request.headers.get("X-API-Key") / request.headers["X-API-Key"]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = ast.unparse(node.func.value)
            if (
                node.func.attr in ("get", "get_all")
                and owner.endswith("headers")
                and node.args
            ):
                a0 = node.args[0]
                if (
                    isinstance(a0, ast.Constant)
                    and isinstance(a0.value, str)
                    and _CRED_RE.search(a0.value)
                ):
                    headers.add(a0.value)
        if isinstance(node, ast.Subscript) and ast.unparse(node.value).endswith(
            "headers"
        ):
            idx = node.slice
            if (
                isinstance(idx, ast.Constant)
                and isinstance(idx.value, str)
                and _CRED_RE.search(idx.value)
            ):
                headers.add(idx.value)
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "authorization"
            and "request" in ast.unparse(node.value)
        ):
            headers.add("Authorization")
        # 401/403: abort(401) or ..., 401 / ..., 403
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "abort"
        ):
            if (
                node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value in (401, 403)
            ):
                denied = True
        if isinstance(node, ast.Tuple) and len(node.elts) > 1:
            code = node.elts[1]
            if isinstance(code, ast.Constant) and code.value in (401, 403):
                denied = True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in funcs
            and depth < _MAX_HOPS
            and node.func.id not in seen
        ):
            h, d = _py_scan(
                funcs[node.func.id], funcs, depth + 1, seen | {node.func.id}
            )
            headers |= h
            denied = denied or d
    return headers, denied


def _py_expected_config(
    tree: ast.Module, funcs: dict[str, Any], used: set[str]
) -> str | None:
    """Env var the compared constant is initialised from, e.g. ``API_KEY``."""
    names = (
        {n.id for f in used for n in ast.walk(funcs[f]) if isinstance(n, ast.Name)}
        if used
        else set()
    )
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in names:
                m = _ENV_PY_RE.search(ast.unparse(node.value))
                if m:
                    return m.group(1)
    return None


# ---------------------------------------------------------------------------
# JS / TS
# ---------------------------------------------------------------------------


def _js_helpers(ps: ParsedSource) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for n in ps.find_all("function_declaration"):
        name = n.child_by_field_name("name")
        if name is not None:
            out[ps.text(name)] = n
    for d in ps.find_all("variable_declarator"):
        name = d.child_by_field_name("name")
        val = d.child_by_field_name("value")
        if (
            name is not None
            and val is not None
            and val.type in ("arrow_function", "function_expression")
        ):
            out[ps.text(name)] = val
    return out


def _js_scan(
    ps: ParsedSource,
    node: Any,
    helpers: dict[str, Any],
    depth: int = 0,
    seen: frozenset[str] = frozenset(),
) -> tuple[set[str], bool]:
    headers: set[str] = set()
    denied = False
    for n in ps.walk(node):
        if n.type == "call_expression":
            fn = n.child_by_field_name("function")
            args = n.child_by_field_name("arguments")
            fn_t = ps.text(fn) if fn is not None else ""
            arg_nodes = [
                a
                for a in (args.children if args else [])
                if a.type not in ("(", ")", ",")
            ]
            if (
                fn_t.split(".")[-1] in ("get", "header")
                and arg_nodes
                and re.match(r"^(req|request|ctx)", fn_t)
            ):
                key = ps.string_value(arg_nodes[0])
                if key and _CRED_RE.search(key):
                    headers.add(key)
            if (
                re.search(r"\.(status|code|sendStatus)$", fn_t)
                and arg_nodes
                and arg_nodes[0].type == "number"
            ):
                if ps.text(arg_nodes[0]) in ("401", "403"):
                    denied = True
            if fn.type == "identifier" if fn is not None else False:
                name = fn_t
                if (
                    name in helpers
                    and depth < _MAX_HOPS
                    and name not in seen
                    and helpers[name] != node
                ):
                    h, d = _js_scan(
                        ps, helpers[name], helpers, depth + 1, seen | {name}
                    )
                    headers |= h
                    denied = denied or d
        elif n.type == "subscript_expression":
            obj = n.child_by_field_name("object")
            idx = n.child_by_field_name("index")
            if obj is not None and ps.text(obj).endswith("headers") and idx is not None:
                key = ps.string_value(idx)
                if key and _CRED_RE.search(key):
                    headers.add(key)
        elif n.type == "member_expression":
            obj = n.child_by_field_name("object")
            prop = n.child_by_field_name("property")
            if (
                obj is not None
                and prop is not None
                and ps.text(obj).endswith("headers")
                and _CRED_RE.search(ps.text(prop))
            ):
                headers.add(ps.text(prop))
    return headers, denied


def _js_expected_config(
    ps: ParsedSource, node: Any, helpers: dict[str, Any]
) -> str | None:
    idents = {ps.text(i) for i in ps.find_all("identifier", node=node)}
    for h in helpers.values():
        idents |= {ps.text(i) for i in ps.find_all("identifier", node=h)}
    for d in ps.find_all("variable_declarator"):
        name = d.child_by_field_name("name")
        val = d.child_by_field_name("value")
        if name is not None and val is not None and ps.text(name) in idents:
            m = _ENV_JS_RE.search(ps.text(val))
            if m:
                return m.group(1) or m.group(2)
    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def refine_api_auth(apis: list[ApiSurface], workdir: Path) -> list[AuthSurface]:
    """Mark handler-protected APIs and return the auth surfaces describing them."""
    mods = _Modules(workdir)
    py_trees: dict[str, ast.Module | None] = {}
    mechanisms: dict[str, AuthSurface] = {}

    def register(
        api: ApiSurface, header: str, config: str | None, ref: SourceRef
    ) -> None:
        label = _display(header)
        api.auth = f"required (header {label})"
        surface = mechanisms.get(label)
        if surface is None:
            rules = [
                f"Requests must send the `{label}` header; a missing or wrong value is answered 401/403."
            ]
            if config:
                rules.append(
                    f"The expected credential is read from configuration variable `{config}`."
                )
            surface = AuthSurface(
                name=f"Header credential: {label}",
                rules=rules,
                source_refs=[ref],
            )
            mechanisms[label] = surface
        if api.name not in surface.protected_endpoints:
            surface.protected_endpoints.append(api.name)

    for api in apis:
        if not api.source_refs:
            continue
        ref = api.source_refs[0]
        line = ref.start_line or 1
        if ref.file_path.endswith(".py"):
            if ref.file_path not in py_trees:
                try:
                    py_trees[ref.file_path] = ast.parse(
                        (workdir / ref.file_path).read_text(
                            encoding="utf-8", errors="replace"
                        )
                    )
                except (OSError, SyntaxError):
                    py_trees[ref.file_path] = None
            tree = py_trees[ref.file_path]
            if tree is None:
                continue
            funcs = _py_funcs(tree)
            handler = next(
                (
                    f
                    for f in funcs.values()
                    if any(d.lineno == line for d in f.decorator_list)
                ),
                None,
            )
            if handler is None:
                continue
            headers, denied = _py_scan(handler, funcs)
            if headers and denied:
                used = {handler.name} | {
                    c.func.id
                    for c in ast.walk(handler)
                    if isinstance(c, ast.Call)
                    and isinstance(c.func, ast.Name)
                    and c.func.id in funcs
                }
                register(
                    api, sorted(headers)[0], _py_expected_config(tree, funcs, used), ref
                )
        elif ref.file_path.endswith((".js", ".ts", ".mjs", ".cjs", ".jsx", ".tsx")):
            ps = mods.get(workdir / ref.file_path)
            if ps is None:
                continue
            handler_node = _enclosing_function(ps, line, api.method or "GET")
            if handler_node is None:
                continue
            helpers = _js_helpers(ps)
            headers, denied = _js_scan(ps, handler_node, helpers)
            if headers and denied:
                register(
                    api,
                    sorted(headers)[0],
                    _js_expected_config(ps, handler_node, helpers),
                    ref,
                )
    logger.info(
        "api_auth_refined",
        protected=sum(len(m.protected_endpoints) for m in mechanisms.values()),
    )
    return list(mechanisms.values())
