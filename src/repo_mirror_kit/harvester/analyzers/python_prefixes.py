"""Resolve Flask Blueprint / FastAPI APIRouter URL prefixes (BEAN-081).

Route decorators only show the path relative to their router. The full public
path is the router's constructor prefix plus any prefix supplied where the
router is mounted (``include_router`` / ``register_blueprint``). This pass uses
stdlib ``ast`` and matches routers by variable name across the repository.
"""

from __future__ import annotations

import ast
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface

logger = structlog.get_logger(__name__)

_ROUTER_CTORS = {"APIRouter": "prefix", "Blueprint": "url_prefix"}
_MOUNT_CALLS = {"include_router": "prefix", "register_blueprint": "url_prefix"}


def _str_kwarg(call: ast.Call, name: str) -> str | None:
    for kw in call.keywords:
        if (
            kw.arg == name
            and isinstance(kw.value, ast.Constant)
            and isinstance(kw.value.value, str)
        ):
            return kw.value.value
    return None


def _leaf_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _call_name(call: ast.Call) -> str | None:
    return _leaf_name(call.func)


def _join(*parts: str) -> str:
    joined = "/".join(p.strip("/") for p in parts if p and p.strip("/"))
    return "/" + joined


def _scan_module(tree: ast.Module) -> tuple[dict[str, str], dict[str, str]]:
    """Return (constructor prefixes, mount prefixes) keyed by router var name."""
    ctor: dict[str, str] = {}
    mount: dict[str, str] = {}
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and _call_name(node.value) in _ROUTER_CTORS
        ):
            kwarg = _ROUTER_CTORS[_call_name(node.value) or ""]
            ctor_prefix = _str_kwarg(node.value, kwarg) or ""
            for target in node.targets:
                if isinstance(target, ast.Name):
                    ctor[target.id] = ctor_prefix
        elif isinstance(node, ast.Call) and _call_name(node) in _MOUNT_CALLS:
            if not node.args:
                continue
            var = _leaf_name(node.args[0])
            var = aliases.get(var, var) if var else var
            mount_prefix = _str_kwarg(node, _MOUNT_CALLS[_call_name(node) or ""])
            if var and mount_prefix:
                mount[var] = mount_prefix
    return ctor, mount


def _decorator_receiver(tree: ast.Module, start_line: int) -> str | None:
    """Variable the route decorator at *start_line* is attached to."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for deco in node.decorator_list:
                if deco.lineno == start_line and isinstance(deco, ast.Call):
                    func = deco.func
                    if isinstance(func, ast.Attribute):
                        return _leaf_name(func.value)
    return None


def apply_python_prefixes(surfaces: list[ApiSurface], workdir: Path) -> int:
    """Prepend router/mount prefixes to Python API surface paths in place.

    Returns the number of surfaces whose path changed.
    """
    py_files = sorted(
        {
            s.source_refs[0].file_path
            for s in surfaces
            if s.source_refs and s.source_refs[0].file_path.endswith(".py")
        }
    )
    if not py_files:
        return 0

    trees: dict[str, ast.Module] = {}
    ctor_all: dict[str, str] = {}
    mount_all: dict[str, str] = {}
    # Mounts can live in files that define no routes (e.g. main.py), so scan
    # every Python file in the repo, not just those holding routes.
    for path in sorted(workdir.rglob("*.py")):
        rel = path.relative_to(workdir).as_posix()
        if any(
            part in {".git", "node_modules", ".venv", "venv"} for part in path.parts
        ):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError, ValueError):
            continue
        ctor, mount = _scan_module(tree)
        ctor_all.update(ctor)
        mount_all.update(mount)
        if rel in py_files:
            trees[rel] = tree

    changed = 0
    for surface in surfaces:
        if not surface.source_refs:
            continue
        ref = surface.source_refs[0]
        route_tree = trees.get(ref.file_path)
        if route_tree is None or ref.start_line is None:
            continue
        var = _decorator_receiver(route_tree, ref.start_line)
        if var is None or var not in ctor_all:
            continue
        prefix = _join(mount_all.get(var, ""), ctor_all[var])
        if prefix == "/":
            continue
        joined = _join(prefix, surface.path)
        if surface.path.endswith("/") and not joined.endswith("/"):
            joined += "/"
        surface.path = joined
        surface.name = f"{surface.method} {surface.path}"
        changed += 1
    logger.info("api_prefixes_applied", changed=changed)
    return changed
