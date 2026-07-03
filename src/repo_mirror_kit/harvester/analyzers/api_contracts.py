"""API contract extraction for Python web frameworks (BEAN-062).

Post-processes ``ApiSurface`` objects discovered by the regex-based
``analyze_api_endpoints`` pass and populates their ``request_schema`` /
``response_schema`` fields using stdlib :mod:`ast` — no new dependencies.

Supported extraction strategies:

- **FastAPI** (``declared`` confidence): endpoint function signatures.
  Pydantic model parameters expand to their field lists; primitive-annotated
  parameters become path/query fields. ``response_model=`` decorator kwargs
  and return annotations drive the response schema.
- **Flask** (``inferred`` confidence): body access idioms
  (``request.get_json()`` aliases, ``request.json[...]``, ``request.form``,
  ``request.args``) drive the request schema; ``jsonify(...)`` calls and
  returned dict literals drive the response schema.

Schema shape (shared contract with the JS/TS pass, BEAN-063)::

    {"fields": [{"name", "type", "required", "source"}], "confidence": "..."}

Un-inferable shapes are marked ``{"unknown": True}`` — never left as a
silently empty dict. A GET/DELETE endpoint with no discovered inputs gets an
explicitly-empty declared field list instead, since "no request body" is a
real answer for those methods, not a failure to infer.

Model references are resolved within the repository only, following at most
one import hop from the endpoint's module (spec'd limit — deeper resolution
is the agentic enrichment pass's job, BEAN-068).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface

logger = structlog.get_logger()

# Methods for which an empty request schema is un-inferable rather than
# legitimately empty.
_BODY_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH"})

# Parameter names/annotations that are framework plumbing, not contract.
_SKIP_PARAM_NAMES: frozenset[str] = frozenset(
    {"self", "cls", "request", "response", "background_tasks", "db", "session"}
)
_SKIP_ANNOTATIONS: frozenset[str] = frozenset(
    {"Request", "Response", "BackgroundTasks", "Session"}
)

_PRIMITIVE_TYPES: frozenset[str] = frozenset(
    {"str", "int", "float", "bool", "bytes", "UUID", "datetime", "date", "Decimal"}
)

_FASTAPI_HTTP_METHODS: frozenset[str] = frozenset(
    {"get", "post", "put", "delete", "patch", "head", "options"}
)


def unknown_schema() -> dict[str, Any]:
    """Return the explicit could-not-infer marker."""
    return {"unknown": True}


def _fields_schema(fields: list[dict[str, Any]], confidence: str) -> dict[str, Any]:
    """Wrap extracted fields in the shared schema shape."""
    return {"fields": fields, "confidence": confidence}


def _annotation_str(node: ast.expr | None) -> str:
    """Render an annotation node back to source text ('' when absent)."""
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except ValueError:  # pragma: no cover - unparse failure is exotic
        return ""


def _is_optional_annotation(annotation: str) -> bool:
    """Whether an annotation string denotes an optional value."""
    return (
        annotation.startswith("Optional[")
        or annotation.endswith("| None")
        or annotation.startswith("None |")
    )


class _ModuleIndex:
    """Parsed-module cache + single-hop import resolution over the repo."""

    def __init__(self, workdir: Path) -> None:
        self._workdir = workdir
        self._trees: dict[Path, ast.Module | None] = {}

    def tree_for(self, path: Path) -> ast.Module | None:
        """Parse (and cache) the module at *path*; None on any failure."""
        resolved = path.resolve()
        if resolved not in self._trees:
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
                self._trees[resolved] = ast.parse(source)
            except (OSError, SyntaxError, ValueError):
                self._trees[resolved] = None
        return self._trees[resolved]

    def resolve_import(
        self, module_path: Path, class_name: str
    ) -> tuple[ast.Module, ast.ClassDef] | None:
        """Follow ``from X import class_name`` one hop from *module_path*.

        Returns the imported module's tree and the class definition, or
        None when the import target cannot be located inside the repo.
        """
        tree = self.tree_for(module_path)
        if tree is None:
            return None
        for node in tree.body:
            if not isinstance(node, ast.ImportFrom):
                continue
            if not any(alias.name == class_name for alias in node.names):
                continue
            target = self._module_file(node, module_path)
            if target is None:
                continue
            imported_tree = self.tree_for(target)
            if imported_tree is None:
                continue
            cls = _find_class(imported_tree, class_name)
            if cls is not None:
                return imported_tree, cls
        return None

    def _module_file(self, node: ast.ImportFrom, importer: Path) -> Path | None:
        """Best-effort mapping of an ImportFrom to a repo file path."""
        module = node.module or ""
        if node.level > 0:
            base = importer.parent
            for _ in range(node.level - 1):
                base = base.parent
        else:
            base = self._workdir
        parts = module.split(".") if module else []
        candidates = [
            base.joinpath(*parts).with_suffix(".py") if parts else None,
            base.joinpath(*parts, "__init__.py") if parts else None,
        ]
        # Absolute imports may also be rooted at the importer's directory
        # (common in flat repos where files import siblings by name).
        if node.level == 0 and parts:
            candidates.append(importer.parent.joinpath(*parts).with_suffix(".py"))
        for candidate in candidates:
            if candidate is not None and candidate.is_file():
                try:
                    candidate.resolve().relative_to(self._workdir.resolve())
                except ValueError:
                    continue
                return candidate
        return None


def _find_class(tree: ast.Module, name: str) -> ast.ClassDef | None:
    """Find a top-level (or nested) class definition by name."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def _expand_model_fields(
    class_name: str,
    module_path: Path,
    index: _ModuleIndex,
    source: str,
) -> list[dict[str, Any]] | None:
    """Expand a Pydantic-style model class into contract fields.

    Looks in the endpoint's own module first, then follows a single
    import hop. Any class whose body carries annotated assignments is
    accepted (covers Pydantic, dataclasses, and plain annotated classes).
    """
    tree = index.tree_for(module_path)
    cls: ast.ClassDef | None = None
    if tree is not None:
        cls = _find_class(tree, class_name)
    if cls is None:
        resolved = index.resolve_import(module_path, class_name)
        if resolved is None:
            return None
        _, cls = resolved

    fields: list[dict[str, Any]] = []
    for stmt in cls.body:
        if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
            continue
        annotation = _annotation_str(stmt.annotation)
        required = stmt.value is None and not _is_optional_annotation(annotation)
        # Pydantic idiom: `x: int = Field(...)` keeps the field required.
        if (
            isinstance(stmt.value, ast.Call)
            and isinstance(stmt.value.func, ast.Name)
            and stmt.value.func.id == "Field"
            and stmt.value.args
            and isinstance(stmt.value.args[0], ast.Constant)
            and stmt.value.args[0].value is Ellipsis
        ):
            required = True
        fields.append(
            {
                "name": stmt.target.id,
                "type": annotation or "unknown",
                "required": required,
                "source": source,
            }
        )
    return fields or None


def _endpoint_function(
    tree: ast.Module, start_line: int
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Locate the endpoint function whose decorator sits at *start_line*."""
    best: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        deco_lines = [d.lineno for d in node.decorator_list]
        if not deco_lines:
            continue
        end = node.end_lineno or node.lineno
        if min(deco_lines) <= start_line <= end:
            # Prefer the innermost (latest-starting) match.
            if best is None or min(deco_lines) >= min(
                d.lineno for d in best.decorator_list
            ):
                best = node
    return best


# ---------------------------------------------------------------------------
# FastAPI extraction (declared confidence)
# ---------------------------------------------------------------------------


def _fastapi_decorator_call(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> ast.Call | None:
    """Return the FastAPI route decorator call, if present."""
    for deco in func.decorator_list:
        if (
            isinstance(deco, ast.Call)
            and isinstance(deco.func, ast.Attribute)
            and deco.func.attr in _FASTAPI_HTTP_METHODS
        ):
            return deco
    return None


def _extract_fastapi_request(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    module_path: Path,
    index: _ModuleIndex,
) -> list[dict[str, Any]]:
    """Extract request fields from a FastAPI endpoint signature."""
    fields: list[dict[str, Any]] = []
    args = func.args
    all_args = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
    defaults_count = len(args.defaults)
    positional = list(args.posonlyargs) + list(args.args)
    defaulted = {arg.arg for arg in positional[len(positional) - defaults_count :]}
    kw_defaulted = {
        arg.arg
        for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=False)
        if default is not None
    }

    for arg in all_args:
        if arg.arg in _SKIP_PARAM_NAMES:
            continue
        annotation = _annotation_str(arg.annotation)
        if annotation in _SKIP_ANNOTATIONS:
            continue
        if not annotation:
            continue
        bare = annotation.removeprefix("Optional[").removesuffix("]")
        if bare in _PRIMITIVE_TYPES or annotation in _PRIMITIVE_TYPES:
            fields.append(
                {
                    "name": arg.arg,
                    "type": annotation,
                    "required": arg.arg not in defaulted
                    and arg.arg not in kw_defaulted
                    and not _is_optional_annotation(annotation),
                    "source": "path_or_query",
                }
            )
            continue
        expanded = _expand_model_fields(annotation, module_path, index, "body")
        if expanded is not None:
            fields.extend(expanded)
    return fields


def _extract_fastapi_response(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    module_path: Path,
    index: _ModuleIndex,
) -> list[dict[str, Any]] | str | None:
    """Extract response fields (or a bare type name) from a FastAPI endpoint.

    Returns a field list when a model resolves, a type string when only the
    name is known, or None when nothing is declared.
    """
    deco = _fastapi_decorator_call(func)
    model_name: str | None = None
    if deco is not None:
        for kw in deco.keywords:
            if kw.arg == "response_model":
                model_name = _annotation_str(kw.value)
                break
    if model_name is None and func.returns is not None:
        model_name = _annotation_str(func.returns)
    if not model_name or model_name == "None":
        return None
    inner = model_name
    if inner.startswith("list[") and inner.endswith("]"):
        inner = inner[5:-1]
    expanded = _expand_model_fields(inner, module_path, index, "body")
    if expanded is not None:
        return expanded
    return model_name


# ---------------------------------------------------------------------------
# Flask extraction (inferred confidence)
# ---------------------------------------------------------------------------


def _json_aliases(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Names bound to the parsed request body inside *func*."""
    aliases: set[str] = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        is_body = (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and value.func.attr == "get_json"
        ) or (
            isinstance(value, ast.Attribute)
            and value.attr == "json"
            and isinstance(value.value, ast.Name)
            and value.value.id == "request"
        )
        if is_body:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    aliases.add(target.id)
    return aliases


def _request_attr_source(node: ast.expr) -> str | None:
    """Map a ``request.<attr>`` expression to a contract source label."""
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "request"
    ):
        return {"json": "body", "form": "form", "args": "query"}.get(node.attr)
    return None


def _extract_flask_request(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[dict[str, Any]]:
    """Infer request fields from Flask body/query access idioms."""
    aliases = _json_aliases(func)
    fields: dict[str, dict[str, Any]] = {}

    def add(name: str, source: str, required: bool) -> None:
        existing = fields.get(name)
        if existing is None or (required and not existing["required"]):
            fields[name] = {
                "name": name,
                "type": "unknown",
                "required": required,
                "source": source,
            }

    for node in ast.walk(func):
        # data["key"] / request.json["key"] / request.form["key"]
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            key = node.slice.value
            if not isinstance(key, str):
                continue
            if isinstance(node.value, ast.Name) and node.value.id in aliases:
                add(key, "body", required=True)
            else:
                source = _request_attr_source(node.value)
                if source is not None:
                    add(key, source, required=True)
        # data.get("key") / request.args.get("key", default)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value
            container = node.func.value
            if isinstance(container, ast.Name) and container.id in aliases:
                add(key, "body", required=False)
            else:
                source = _request_attr_source(container)
                if source is not None:
                    add(key, source, required=False)
    return list(fields.values())


def _literal_type(node: ast.expr) -> str:
    """Best-effort JSON-ish type name for a literal expression node."""
    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, str):
            return "string"
        if value is None:
            return "null"
    if isinstance(node, (ast.List, ast.ListComp)):
        return "array"
    if isinstance(node, ast.Dict):
        return "object"
    return "unknown"


def _dict_fields(node: ast.Dict) -> list[dict[str, Any]]:
    """Turn a dict literal into response contract fields."""
    fields: list[dict[str, Any]] = []
    for key, value in zip(node.keys, node.values, strict=False):
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            fields.append(
                {
                    "name": key.value,
                    "type": _literal_type(value),
                    "required": True,
                    "source": "body",
                }
            )
    return fields


def _response_payload_fields(node: ast.expr) -> list[dict[str, Any]]:
    """Extract fields from a jsonify(...)/returned-literal payload node."""
    if isinstance(node, ast.Dict):
        return _dict_fields(node)
    if isinstance(node, ast.ListComp) and isinstance(node.elt, ast.Dict):
        return _dict_fields(node.elt)
    if isinstance(node, ast.List) and node.elts and isinstance(node.elts[0], ast.Dict):
        return _dict_fields(node.elts[0])
    return []


def _extract_flask_response(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[dict[str, Any]]:
    """Infer response fields from jsonify calls and returned literals."""
    fields: dict[str, dict[str, Any]] = {}
    for node in ast.walk(func):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        value: ast.expr = node.value
        # `return jsonify(...), 201` tuples
        if isinstance(value, ast.Tuple) and value.elts:
            value = value.elts[0]
        payload: ast.expr | None = None
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "jsonify"
        ):
            if value.args:
                payload = value.args[0]
            elif value.keywords:
                for kw in value.keywords:
                    if kw.arg is not None:
                        fields.setdefault(
                            kw.arg,
                            {
                                "name": kw.arg,
                                "type": _literal_type(kw.value),
                                "required": True,
                                "source": "body",
                            },
                        )
        elif isinstance(value, (ast.Dict, ast.List, ast.ListComp)):
            payload = value
        if payload is not None:
            for field in _response_payload_fields(payload):
                fields.setdefault(field["name"], field)
    return list(fields.values())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def populate_python_api_contracts(
    surfaces: list[ApiSurface],
    workdir: Path,
) -> int:
    """Populate request/response schemas on Python-sourced API surfaces.

    Mutates the given surfaces in place. Non-Python surfaces are left
    untouched (the JS/TS pass is BEAN-063). Returns the number of surfaces
    whose contracts were populated (fields extracted on either side).

    Args:
        surfaces: API surfaces from ``analyze_api_endpoints``.
        workdir: Root of the cloned repository.
    """
    index = _ModuleIndex(workdir)
    populated = 0

    for surface in surfaces:
        if not surface.source_refs:
            continue
        ref = surface.source_refs[0]
        if not ref.file_path.endswith(".py"):
            continue
        module_path = workdir / ref.file_path
        tree = index.tree_for(module_path)
        start_line = ref.start_line if ref.start_line is not None else 1
        func = _endpoint_function(tree, start_line) if tree is not None else None
        if func is None:
            _mark_unknown(surface)
            continue

        if _fastapi_decorator_call(func) is not None:
            request_fields = _extract_fastapi_request(func, module_path, index)
            response = _extract_fastapi_response(func, module_path, index)
            confidence = "declared"
        else:
            request_fields = _extract_flask_request(func)
            response = _extract_flask_response(func)
            confidence = "inferred"

        got_any = False
        if request_fields:
            surface.request_schema = _fields_schema(request_fields, confidence)
            got_any = True
        elif surface.method in _BODY_METHODS:
            surface.request_schema = unknown_schema()
        else:
            surface.request_schema = _fields_schema([], confidence)

        if isinstance(response, list) and response:
            surface.response_schema = _fields_schema(response, confidence)
            got_any = True
        elif isinstance(response, str):
            # Model name known but not resolvable — keep the type hint.
            surface.response_schema = {"type": response, "confidence": confidence}
            got_any = True
        elif not surface.response_schema:
            surface.response_schema = unknown_schema()

        if got_any:
            populated += 1

    logger.info(
        "api_contracts_python",
        surfaces_total=len(surfaces),
        surfaces_populated=populated,
    )
    return populated


def _mark_unknown(surface: ApiSurface) -> None:
    """Stamp explicit unknown markers on an unresolvable Python surface."""
    if not surface.request_schema and surface.method in _BODY_METHODS:
        surface.request_schema = unknown_schema()
    if not surface.response_schema:
        surface.response_schema = unknown_schema()
