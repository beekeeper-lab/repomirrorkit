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
import re
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

_SERIALIZER_METHODS = frozenset({"to_dict", "as_dict", "serialize", "to_json", "dict"})

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

    def serializer_dict(self, method: str) -> ast.Dict | None:
        """First ``def <method>(...): return {...}`` dict literal anywhere in the repo."""
        if not hasattr(self, "_serializers"):
            self._serializers: dict[str, ast.Dict] = {}
            skip = {".git", "node_modules", ".venv", "venv", "__pycache__", "tests"}
            for path in sorted(self._workdir.rglob("*.py"))[:400]:
                if any(part in skip for part in path.relative_to(self._workdir).parts):
                    continue
                tree = self.tree_for(path)
                if tree is None:
                    continue
                for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
                    for fn in cls.body:
                        if (
                            isinstance(fn, ast.FunctionDef)
                            and fn.name in _SERIALIZER_METHODS
                        ):
                            for ret in (
                                r for r in ast.walk(fn) if isinstance(r, ast.Return)
                            ):
                                if isinstance(ret.value, ast.Dict):
                                    self._serializers.setdefault(fn.name, ret.value)
        return self._serializers.get(method)

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


_PYDANTIC_CONSTRAINTS: frozenset[str] = frozenset(
    {
        "min_length",
        "max_length",
        "ge",
        "gt",
        "le",
        "lt",
        "pattern",
        "regex",
        "multiple_of",
        "min_items",
        "max_items",
    }
)


def _pydantic_rules(stmt: ast.AnnAssign) -> list[str]:
    """Constraint kwargs of ``x: int = Field(ge=1)`` as ``"ge=1"`` strings."""
    rules: list[str] = []
    value = stmt.value
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "Field"
    ):
        for kw in value.keywords:
            if kw.arg in _PYDANTIC_CONSTRAINTS:
                rules.append(f"{kw.arg}={ast.unparse(kw.value)}")
    annotation = _annotation_str(stmt.annotation)
    if "EmailStr" in annotation:
        rules.append("email")
    return rules


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
        entry: dict[str, Any] = {
            "name": stmt.target.id,
            "type": annotation or "unknown",
            "required": required,
            "source": source,
        }
        rules = _pydantic_rules(stmt)
        if rules:
            entry["rules"] = rules
        fields.append(entry)
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


def _module_is_flask(tree: ast.Module | None) -> bool:
    """True when the module imports flask and not fastapi.

    Disambiguates Flask 2.0 ``@app.get`` shorthand from FastAPI decorators.
    """
    if tree is None:
        return False
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.add((node.module or "").split(".")[0])
        elif isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
    return "flask" in names and "fastapi" not in names


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


def _serializer_fields(
    tree: ast.Module | None, node: ast.expr, index: _ModuleIndex | None = None
) -> list[dict[str, Any]]:
    """Fields of ``obj.to_dict()`` from a serializer method returning a dict literal.

    Looks in the handler's module first, then anywhere in the repo (the model
    usually lives in another module). Types are unknown; keys are the contract.
    """
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _SERIALIZER_METHODS
    ):
        return []
    if tree is not None:
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            for fn in cls.body:
                if isinstance(fn, ast.FunctionDef) and fn.name == node.func.attr:
                    for ret in (r for r in ast.walk(fn) if isinstance(r, ast.Return)):
                        if isinstance(ret.value, ast.Dict):
                            return _dict_fields(ret.value)
    if index is not None:
        found = index.serializer_dict(node.func.attr)
        if found is not None:
            return _dict_fields(found)
    return []


def _response_payload_fields(
    node: ast.expr,
    tree: ast.Module | None = None,
    index: _ModuleIndex | None = None,
) -> list[dict[str, Any]]:
    """Extract fields from a jsonify(...)/returned-literal payload node."""
    serial = _serializer_fields(tree, node, index)
    if serial:
        return serial
    if isinstance(node, ast.Dict):
        return _dict_fields(node)
    if isinstance(node, ast.ListComp):
        inner = _serializer_fields(tree, node.elt, index)
        if inner:
            return inner
    if isinstance(node, ast.ListComp) and isinstance(node.elt, ast.Dict):
        return _dict_fields(node.elt)
    if isinstance(node, ast.List) and node.elts and isinstance(node.elts[0], ast.Dict):
        return _dict_fields(node.elts[0])
    return []


def _extract_flask_response(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    tree: ast.Module | None = None,
    index: _ModuleIndex | None = None,
) -> list[dict[str, Any]]:
    """Infer response fields from jsonify calls and returned literals.

    Only success responses (status < 400) contribute fields; error payloads are
    reported separately as ``errors``.
    """
    fields: dict[str, dict[str, Any]] = {}
    for node in ast.walk(func):
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        value: ast.expr = node.value
        # `return jsonify(...), 201` tuples
        if isinstance(value, ast.Tuple) and value.elts:
            if (
                len(value.elts) > 1
                and isinstance(value.elts[1], ast.Constant)
                and isinstance(value.elts[1].value, int)
                and value.elts[1].value >= 400
            ):
                continue
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
            for field in _response_payload_fields(payload, tree, index):
                fields.setdefault(field["name"], field)
    return list(fields.values())


# ---------------------------------------------------------------------------
# Imperative validation inference (Flask)
# ---------------------------------------------------------------------------

_PY_TYPE_NAMES = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
}


def _name_in(node: ast.AST, names: set[str]) -> str | None:
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id in names:
            return n.id
    return None


def _bool_terms(test: ast.expr) -> list[ast.expr]:
    if isinstance(test, ast.BoolOp):
        out: list[ast.expr] = []
        for v in test.values:
            out.extend(_bool_terms(v))
        return out
    return [test]


def _rejects(body: list[ast.stmt], funcs: dict[str, Any]) -> bool:
    """True when the block answers with a 4xx (return tuple / abort / helper)."""
    holder = ast.Module(body=body, type_ignores=[])
    return any(status >= 400 for status, _ in _collect_responses(holder, funcs))


def _infer_validation(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    tree: ast.Module,
    fields: list[dict[str, Any]],
) -> None:
    """Mine ``if bad: return 4xx`` guards for type / required / constraints."""
    aliases = _json_aliases(func)
    var_to_field: dict[str, str] = {}
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        tgt, val = node.targets[0], node.value
        if not isinstance(tgt, ast.Name):
            continue
        key: str | None = None
        if (
            isinstance(val, ast.Call)
            and isinstance(val.func, ast.Attribute)
            and val.func.attr == "get"
            and val.args
            and isinstance(val.args[0], ast.Constant)
            and isinstance(val.args[0].value, str)
            and isinstance(val.func.value, ast.Name)
            and val.func.value.id in aliases
        ):
            key = val.args[0].value
        elif (
            isinstance(val, ast.Subscript)
            and isinstance(val.value, ast.Name)
            and val.value.id in aliases
            and isinstance(val.slice, ast.Constant)
            and isinstance(val.slice.value, str)
        ):
            key = val.slice.value
        if key:
            var_to_field[tgt.id] = key
    if not var_to_field:
        return
    by_name = {f["name"]: f for f in fields if f["source"] == "body"}
    funcs = _local_functions(tree)
    names = set(var_to_field)

    def note(
        var: str,
        *,
        required: bool = False,
        type_: str | None = None,
        rule: str | None = None,
    ) -> None:
        field = by_name.get(var_to_field[var])
        if field is None:
            return
        if required:
            field["required"] = True
        if type_ and field.get("type") in (None, "unknown"):
            field["type"] = type_
        if rule:
            rules = field.setdefault("rules", [])
            if rule not in rules:
                rules.append(rule)

    for node in ast.walk(func):
        if not isinstance(node, ast.If) or not _rejects(node.body, funcs):
            continue
        for term in _bool_terms(node.test):
            # not isinstance(v, T) → required, typed
            if (
                isinstance(term, ast.UnaryOp)
                and isinstance(term.op, ast.Not)
                and isinstance(term.operand, ast.Call)
                and isinstance(term.operand.func, ast.Name)
                and term.operand.func.id == "isinstance"
                and len(term.operand.args) == 2
                and isinstance(term.operand.args[0], ast.Name)
                and term.operand.args[0].id in names
            ):
                tname = ast.unparse(term.operand.args[1])
                note(
                    term.operand.args[0].id,
                    required=True,
                    type_=_PY_TYPE_NAMES.get(tname),
                )
            # not v / v is None → required
            elif (
                isinstance(term, ast.UnaryOp)
                and isinstance(term.op, ast.Not)
                and isinstance(term.operand, ast.Name)
                and term.operand.id in names
            ):
                note(term.operand.id, required=True)
            elif (
                isinstance(term, ast.Compare)
                and len(term.ops) == 1
                and isinstance(term.comparators[0], ast.Constant)
            ):
                op, rhs, left = term.ops[0], term.comparators[0].value, term.left
                if isinstance(op, ast.Is) and rhs is None:
                    if isinstance(left, ast.Name) and left.id in names:
                        note(left.id, required=True)
                    elif isinstance(left, ast.Call):
                        # db.session.get(Model, v) is None → references Model
                        args = left.args
                        var = _name_in(left, names)
                        model = next(
                            (
                                a.id
                                for a in args
                                if isinstance(a, ast.Name)
                                and a.id not in names
                                and a.id[:1].isupper()
                            ),
                            None,
                        )
                        if var and model:
                            note(var, required=True, rule=f"references={model}")
                elif isinstance(rhs, (int, float)) and isinstance(
                    op, (ast.Lt, ast.Gt, ast.LtE, ast.GtE)
                ):
                    var = _name_in(left, names)
                    if var is None:
                        continue
                    is_len = (
                        isinstance(left, ast.Call)
                        and isinstance(left.func, ast.Name)
                        and left.func.id == "len"
                    )
                    if isinstance(op, ast.Lt):
                        note(var, rule=f"{'min_length' if is_len else 'min'}={rhs}")
                    elif isinstance(op, ast.Gt):
                        note(var, rule=f"{'max_length' if is_len else 'max'}={rhs}")
                    elif isinstance(op, ast.LtE):
                        note(var, rule=f"{'min_length' if is_len else 'min'}={rhs + 1}")
                    elif isinstance(op, ast.GtE):
                        note(var, rule=f"{'max_length' if is_len else 'max'}={rhs - 1}")


# ---------------------------------------------------------------------------
# Response status codes and error responses (Flask)
# ---------------------------------------------------------------------------

_MAX_HELPER_DEPTH = 2


def _local_functions(
    tree: ast.Module,
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        n.name: n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _dict_message(node: ast.expr | None) -> str | None:
    """``"..."`` of ``{"error": "..."}`` / ``{"message": "..."}`` literals."""
    if isinstance(node, ast.Dict):
        for k, v in zip(node.keys, node.values, strict=False):
            if (
                isinstance(k, ast.Constant)
                and k.value in ("error", "message", "detail")
                and isinstance(v, ast.Constant)
                and isinstance(v.value, str)
            ):
                return v.value
    return None


def _collect_responses(
    func: ast.AST,
    funcs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    depth: int = 0,
    seen: frozenset[str] = frozenset(),
) -> list[tuple[int, ast.expr | None]]:
    """(status, payload) for each way the handler can respond.

    Follows ``return helper(...)`` into same-module helpers (bounded depth) and
    treats ``abort(N)`` as an error response.
    """
    out: list[tuple[int, ast.expr | None]] = []
    for node in ast.walk(func):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "abort"
        ):
            if (
                node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, int)
            ):
                out.append((node.args[0].value, None))
        if not isinstance(node, ast.Return) or node.value is None:
            continue
        value = node.value
        status = 200
        if isinstance(value, ast.Tuple) and value.elts:
            if (
                len(value.elts) > 1
                and isinstance(value.elts[1], ast.Constant)
                and isinstance(value.elts[1].value, int)
            ):
                status = value.elts[1].value
            value = value.elts[0]
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            name = value.func.id
            if name in ("jsonify", "make_response"):
                out.append((status, value.args[0] if value.args else None))
            elif name in funcs and depth < _MAX_HELPER_DEPTH and name not in seen:
                inner = _collect_responses(funcs[name], funcs, depth + 1, seen | {name})
                # An explicit status on the outer tuple overrides the helper's.
                if status != 200 and isinstance(node.value, ast.Tuple):
                    inner = [(status, p) for _, p in inner]
                out.extend(inner)
        elif isinstance(value, (ast.Dict, ast.List)):
            out.append((status, value))
        elif isinstance(value, ast.Constant) and isinstance(value.value, str):
            out.append((status, None))
    return out


def _success_payload_fields(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
    tree: ast.Module,
    index: _ModuleIndex | None,
) -> list[dict[str, Any]]:
    """Success-response fields found through helpers the handler returns from."""
    for status, payload in _collect_responses(func, _local_functions(tree)):
        if status < 400 and payload is not None:
            fields = _response_payload_fields(payload, tree, index)
            if fields:
                return fields
    return []


_PATH_PARAM_RE = re.compile(r"<(?:(?P<conv>\w+)(?:\([^)]*\))?:)?(?P<name>\w+)>")
_CONV_TYPES = {
    "int": "integer",
    "float": "number",
    "uuid": "string",
    "path": "string",
    "string": "string",
}


def _path_param_fields(path: str) -> list[dict[str, Any]]:
    """Flask ``<int:id>`` route parameters as required path fields."""
    return [
        {
            "name": m.group("name"),
            "type": _CONV_TYPES.get(m.group("conv") or "string", "string"),
            "required": True,
            "source": "path",
        }
        for m in _PATH_PARAM_RE.finditer(path)
    ]


_BODY_ATTRS = frozenset(
    {"get_json", "json", "form", "data", "files", "values", "stream"}
)


# Calls that cannot read the request body; any OTHER unresolved call might, so
# body-less is only concluded when every call is accounted for.
_HARMLESS_CALLS = frozenset(
    {
        "jsonify",
        "abort",
        "make_response",
        "len",
        "int",
        "str",
        "float",
        "bool",
        "list",
        "dict",
        "set",
        "isinstance",
        "print",
        "redirect",
        "url_for",
        "range",
    }
)


def _reads_request_body(
    func: ast.AST,
    funcs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    depth: int = 0,
    seen: frozenset[str] = frozenset(),
) -> bool:
    """True when the handler (or a helper, 2 hops) touches the request body."""
    for n in ast.walk(func):
        if (
            isinstance(n, ast.Attribute)
            and n.attr in _BODY_ATTRS
            and isinstance(n.value, ast.Name)
            and n.value.id == "request"
        ):
            return True
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            name = n.func.id
            if name in funcs:
                if (
                    depth < _MAX_HELPER_DEPTH
                    and name not in seen
                    and _reads_request_body(
                        funcs[name], funcs, depth + 1, seen | {name}
                    )
                ):
                    return True
            elif name not in _HARMLESS_CALLS and name[:1].islower():
                return True  # unresolved callee: it might read the body
    return False


def _status_and_errors(
    func: ast.FunctionDef | ast.AsyncFunctionDef, tree: ast.Module
) -> tuple[int | None, list[dict[str, Any]]]:
    responses = _collect_responses(func, _local_functions(tree))
    success = [s for s, _ in responses if s < 400]
    errors: list[dict[str, Any]] = []
    for status, payload in responses:
        if status >= 400:
            entry: dict[str, Any] = {"status": status}
            message = _dict_message(payload)
            if message:
                entry["message"] = message
            if entry not in errors:
                errors.append(entry)
    return (success[0] if success else None), errors


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

        if not _module_is_flask(tree) and _fastapi_decorator_call(func) is not None:
            request_fields = _extract_fastapi_request(func, module_path, index)
            response = _extract_fastapi_response(func, module_path, index)
            confidence = "declared"
        else:
            request_fields = _extract_flask_request(func)
            response = _extract_flask_response(func, tree, index)
            confidence = "inferred"
            body_less = False
            flask_status, flask_errors = (
                _status_and_errors(func, tree) if tree is not None else (None, [])
            )
            if tree is not None:
                _infer_validation(func, tree, request_fields)
                if not response:
                    response = _success_payload_fields(func, tree, index)
            request_fields = [
                *_path_param_fields(surface.path),
                *[f for f in request_fields if f.get("source") != "path"],
            ]
            body_less = (
                tree is not None
                and surface.method in _BODY_METHODS
                and not _reads_request_body(func, _local_functions(tree))
            )

        got_any = False
        if request_fields:
            surface.request_schema = _fields_schema(request_fields, confidence)
            got_any = True
        elif confidence == "inferred" and body_less:
            surface.request_schema = _fields_schema([], confidence)
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

        if confidence == "inferred" and tree is not None:
            if flask_status is not None:
                surface.response_schema["status"] = flask_status
                got_any = True
            if flask_errors:
                surface.response_schema["errors"] = flask_errors
                got_any = True

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
