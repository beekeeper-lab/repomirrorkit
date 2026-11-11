"""Resolve Flask Blueprint / FastAPI APIRouter URL prefixes (BEAN-089).

Route decorators only show the path relative to their router. The full public
path is the router's constructor prefix plus any prefix supplied where the
router is mounted (``include_router`` / ``register_blueprint``).

Routers are identified by **(defining module, variable name)**, resolved through
``from X import name [as alias]`` imports — real apps routinely name every
blueprint ``bp`` (found by the microblog real-world eval), so a bare variable
name is not an identity. Uses stdlib ``ast`` only.
"""

from __future__ import annotations

import ast
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface

logger = structlog.get_logger(__name__)

_ROUTER_CTORS = {"APIRouter": "prefix", "Blueprint": "url_prefix"}
_MOUNT_CALLS = {"include_router": "prefix", "register_blueprint": "url_prefix"}
_SKIP_PARTS = {".git", "node_modules", ".venv", "venv", "__pycache__"}

# (repo-relative module file, variable name)
RouterId = tuple[str, str]


def _str_kwarg(call: ast.Call, name: str) -> str | None:
    for kw in call.keywords:
        if (
            kw.arg == name
            and isinstance(kw.value, ast.Constant)
            and isinstance(kw.value.value, str)
        ):
            return kw.value.value
    return None


def _call_name(call: ast.Call) -> str | None:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _leaf(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _join(*parts: str) -> str:
    joined = "/".join(p.strip("/") for p in parts if p and p.strip("/"))
    return "/" + joined


class _Repo:
    """Parsed Python modules plus dotted-module → file resolution."""

    def __init__(self, workdir: Path) -> None:
        self.workdir = workdir
        self.trees: dict[str, ast.Module] = {}
        for path in sorted(workdir.rglob("*.py")):
            rel = path.relative_to(workdir)
            if any(p in _SKIP_PARTS for p in rel.parts):
                continue
            try:
                self.trees[rel.as_posix()] = ast.parse(
                    path.read_text(encoding="utf-8", errors="replace")
                )
            except (SyntaxError, OSError, ValueError):
                continue

    def module_file(self, dotted: str, importer: str, level: int) -> str | None:
        """Repo file for ``from <dotted> import ...`` seen in *importer*."""
        base_parts: list[str]
        if level:
            pkg = Path(importer).parent.parts
            base_parts = list(pkg[: len(pkg) - (level - 1)]) if level > 1 else list(pkg)
        else:
            base_parts = []
        parts = [*base_parts, *(dotted.split(".") if dotted else [])]
        candidates = [
            "/".join([*parts]) + ".py",
            "/".join([*parts, "__init__.py"]),
        ]
        # Also try under a src/ layout.
        candidates += [f"src/{c}" for c in candidates]
        for c in candidates:
            if c in self.trees:
                return c
        return None


def _imports(repo: _Repo, rel: str) -> dict[str, RouterId]:
    """local name → (module file, original name) for ``from X import name``."""
    out: dict[str, RouterId] = {}
    tree = repo.trees[rel]
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        target = repo.module_file(node.module or "", rel, node.level)
        for alias in node.names:
            local = alias.asname or alias.name
            if target is not None:
                out[local] = (target, alias.name)
            # `from pkg import submodule` → module identity for attribute access
            sub = repo.module_file(
                f"{node.module}.{alias.name}" if node.module else alias.name,
                rel,
                node.level,
            )
            if sub is not None and target is None:
                out[local] = (sub, "")
    return out


def apply_python_prefixes(surfaces: list[ApiSurface], workdir: Path) -> int:
    """Prepend router/mount prefixes to Python API surface paths in place.

    Returns the number of surfaces whose path changed.
    """
    route_files = {
        s.source_refs[0].file_path
        for s in surfaces
        if s.source_refs and s.source_refs[0].file_path.endswith(".py")
    }
    if not route_files:
        return 0
    repo = _Repo(workdir)

    ctor: dict[RouterId, str] = {}
    for rel, tree in repo.trees.items():
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and _call_name(node.value) in _ROUTER_CTORS
            ):
                prefix = (
                    _str_kwarg(node.value, _ROUTER_CTORS[_call_name(node.value) or ""])
                    or ""
                )
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        ctor[(rel, t.id)] = prefix

    imports = {rel: _imports(repo, rel) for rel in repo.trees}

    def identity(rel: str, expr: ast.expr) -> RouterId | None:
        """Resolve a router expression seen in *rel* to its defining identity."""
        if isinstance(expr, ast.Name):
            if (rel, expr.id) in ctor:
                return (rel, expr.id)
            imported = imports[rel].get(expr.id)
            if imported and imported[1] and imported in ctor:
                return imported
            if imported and imported[1]:
                # re-exported name: look for the defining module of that name
                for (f, v), _p in ctor.items():
                    if v == imported[1] and f == imported[0]:
                        return (f, v)
            return None
        if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name):
            mod = imports[rel].get(expr.value.id)
            if mod and not mod[1] and (mod[0], expr.attr) in ctor:
                return (mod[0], expr.attr)
        return None

    mounts: dict[RouterId, str] = {}
    for rel, tree in repo.trees.items():
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and _call_name(node) in _MOUNT_CALLS
                and node.args
            ):
                rid = identity(rel, node.args[0])
                mount_prefix = _str_kwarg(node, _MOUNT_CALLS[_call_name(node) or ""])
                if rid is not None and mount_prefix:
                    mounts[rid] = mount_prefix

    changed = 0
    for surface in surfaces:
        if not surface.source_refs:
            continue
        ref = surface.source_refs[0]
        route_tree = repo.trees.get(ref.file_path)
        if route_tree is None or ref.start_line is None:
            continue
        receiver: ast.expr | None = None
        for node in ast.walk(route_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for deco in node.decorator_list:
                    if (
                        deco.lineno == ref.start_line
                        and isinstance(deco, ast.Call)
                        and isinstance(deco.func, ast.Attribute)
                    ):
                        receiver = deco.func.value
        if receiver is None:
            continue
        rid = identity(ref.file_path, receiver)
        if rid is None:
            continue
        prefix = _join(mounts.get(rid, ""), ctor.get(rid, ""))
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
