"""API contract extraction for JS/TS web frameworks (BEAN-063).

Counterpart of :mod:`api_contracts` (Python). Post-processes ``ApiSurface``
objects found by the regex pass and populates ``request_schema`` /
``response_schema`` using tree-sitter (:mod:`repo_mirror_kit.harvester.parsing`).

Supported handler shapes:

- **Next.js App Router** — ``export function GET(request)`` /
  ``export const POST = async (request) => ...``
- **Express / Fastify** — ``app.post('/x', (req, res) => ...)``
- **NestJS** — controller methods with ``@Body()`` / ``@Query()`` / ``@Param()``

Request evidence (in decreasing confidence): NestJS DTO classes and typed
body annotations (``declared``), zod ``z.object`` schemas (``declared``),
body/query/param access idioms (``inferred``). Response evidence: payloads
passed to ``NextResponse.json`` / ``res.json`` / ``res.status(n).json`` /
``reply.send`` / returned from Nest methods, with status codes.

Schema shape is shared with the Python pass::

    {"fields": [{"name","type","required","source"[, "rules"]}],
     "confidence": "...", ["is_array": True], ["status": 201],
     ["errors": [{"status": 400, "message": "..."}]]}

Un-inferable shapes get ``{"unknown": True}``. Resolution follows at most one
relative import hop, mirroring the Python pass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface
from repo_mirror_kit.harvester.parsing import ParsedSource, parse_source
from repo_mirror_kit.harvester.parsing.treesitter import language_for_path

logger = structlog.get_logger()

_JS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts")
_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})
_VERBS = frozenset({"get", "post", "put", "delete", "patch", "head", "options", "all"})
_FUNC_TYPES = (
    "arrow_function",
    "function_expression",
    "function",
    "function_declaration",
)
_PRIMITIVES = {
    "string": "string",
    "number": "number",
    "boolean": "boolean",
    "bigint": "integer",
    "Date": "string",
    "any": "unknown",
    "unknown": "unknown",
}
_ZOD_TYPES = {
    "string": "string",
    "number": "number",
    "boolean": "boolean",
    "bigint": "integer",
    "date": "string",
    "array": "array",
    "object": "object",
    "enum": "string",
    "nativeEnum": "string",
    "literal": "string",
    "any": "unknown",
    "unknown": "unknown",
}
_BODY_SOURCES = ("body",)


def _unknown() -> dict[str, Any]:
    return {"unknown": True}


def _schema(
    fields: list[dict[str, Any]], confidence: str, **extra: Any
) -> dict[str, Any]:
    out: dict[str, Any] = {"fields": fields, "confidence": confidence}
    out.update({k: v for k, v in extra.items() if v})
    return out


# ---------------------------------------------------------------------------
# Module access (parse cache + one relative-import hop)
# ---------------------------------------------------------------------------


class _Modules:
    def __init__(self, workdir: Path) -> None:
        self._workdir = workdir
        self._cache: dict[Path, ParsedSource | None] = {}

    def get(self, path: Path) -> ParsedSource | None:
        if path not in self._cache:
            parsed: ParsedSource | None = None
            if language_for_path(path.name) and path.is_file():
                try:
                    parsed = parse_source(path.name, path.read_bytes())
                except OSError:
                    parsed = None
            self._cache[path] = parsed
        return self._cache[path]

    def resolve_import(
        self, ps: ParsedSource, importer: Path, name: str
    ) -> tuple[ParsedSource, Path] | None:
        """Find the module that provides *name* via a relative import."""
        for imp in ps.find_all("import_statement"):
            if name not in ps.text(imp):
                continue
            src = imp.child_by_field_name("source")
            spec = ps.string_value(src) if src is not None else None
            if not spec or not spec.startswith("."):
                continue
            base = (importer.parent / spec).resolve()
            candidates = [base.with_suffix(ext) for ext in _JS_EXTS]
            candidates += [base / f"index{ext}" for ext in _JS_EXTS]
            if base.suffix in _JS_EXTS:
                candidates.insert(0, base)
            for cand in candidates:
                module = self.get(cand)
                if module is not None:
                    return module, cand
        return None


# ---------------------------------------------------------------------------
# Type resolution -> fields
# ---------------------------------------------------------------------------


def _strip_type(text: str) -> str:
    return text.lstrip(":").strip()


def _type_name(ps: ParsedSource, node: Any) -> str:
    return _strip_type(ps.text(node)) if node is not None else "unknown"


def _simple_type(raw: str) -> str:
    raw = raw.strip()
    if raw.endswith("[]") or raw.startswith("Array<"):
        return "array"
    if "|" in raw:
        parts = [
            p.strip() for p in raw.split("|") if p.strip() not in ("null", "undefined")
        ]
        if len(parts) == 1:
            return _simple_type(parts[0])
        if all(p.startswith(("'", '"')) for p in parts):
            return "string"
        return raw
    return _PRIMITIVES.get(raw, raw)


def _decorator_names(ps: ParsedSource, node: Any) -> list[str]:
    rules: list[str] = []
    for child in node.children:
        if child.type == "decorator":
            rules.append(ps.text(child).lstrip("@").strip())
    return rules


def _fields_from_members(
    ps: ParsedSource, body: Any, source: str
) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for member in body.children:
        if member.type not in ("property_signature", "public_field_definition"):
            continue
        name_node = member.child_by_field_name("name")
        if name_node is None:
            continue
        optional = any(c.type == "?" for c in member.children)
        type_node = member.child_by_field_name("type")
        has_default = member.child_by_field_name("value") is not None
        field: dict[str, Any] = {
            "name": ps.text(name_node),
            "type": _simple_type(_type_name(ps, type_node)),
            "required": not optional and not has_default,
            "source": source,
        }
        rules = _decorator_names(ps, member)
        if rules:
            field["rules"] = rules
            if any(r.startswith("IsOptional") for r in rules):
                field["required"] = False
        fields.append(field)
    return fields


def _find_type_decl(ps: ParsedSource, name: str) -> Any | None:
    for node in ps.find_all(
        "interface_declaration", "type_alias_declaration", "class_declaration"
    ):
        n = node.child_by_field_name("name")
        if n is not None and ps.text(n) == name:
            return node
    return None


def _unwrap_type(raw: str) -> tuple[str, bool]:
    """Strip ``Promise<>``/``Array<>``/``[]`` wrappers → (inner, is_array)."""
    raw = raw.strip()
    is_array = False
    changed = True
    while changed:
        changed = False
        if raw.startswith("Promise<") and raw.endswith(">"):
            raw, changed = raw[8:-1].strip(), True
        elif raw.startswith("Array<") and raw.endswith(">"):
            raw, changed, is_array = raw[6:-1].strip(), True, True
        elif raw.endswith("[]"):
            raw, changed, is_array = raw[:-2].strip(), True, True
    return raw, is_array


def _resolve_type_fields(
    mods: _Modules,
    ps: ParsedSource,
    path: Path,
    raw_type: str,
    source: str,
    depth: int = 0,
) -> tuple[list[dict[str, Any]] | None, bool]:
    """Resolve a type expression to (fields, is_array); (None, arr) if opaque."""
    inner, is_array = _unwrap_type(raw_type)
    if not inner.isidentifier():
        return None, is_array
    decl = _find_type_decl(ps, inner)
    mod_ps = ps
    if decl is None and depth == 0:
        hop = mods.resolve_import(ps, path, inner)
        if hop is not None:
            mod_ps, _ = hop
            decl = _find_type_decl(mod_ps, inner)
    if decl is None:
        return None, is_array
    body = decl.child_by_field_name("body")
    if decl.type == "type_alias_declaration":
        value = decl.child_by_field_name("value")
        body = value if value is not None and value.type == "object_type" else None
    if body is None:
        return None, is_array
    return _fields_from_members(mod_ps, body, source), is_array


# ---------------------------------------------------------------------------
# zod schemas
# ---------------------------------------------------------------------------


def _zod_chain(ps: ParsedSource, node: Any) -> tuple[str, list[str]]:
    """Return (base zod type, chained method names) for ``z.string().min(1)``."""
    methods: list[str] = []
    current = node
    base = "unknown"
    while current is not None and current.type == "call_expression":
        fn = current.child_by_field_name("function")
        if fn is None or fn.type != "member_expression":
            break
        prop = fn.child_by_field_name("property")
        obj = fn.child_by_field_name("object")
        pname = ps.text(prop) if prop is not None else ""
        if (
            obj is not None
            and obj.type == "identifier"
            and ps.text(obj) in ("z", "zod")
        ):
            base = pname
            break
        methods.append(ps.text(current)[ps.text(current).find("." + pname) :][:60])
        current = obj
    return base, list(reversed(methods))


def _zod_object_fields(ps: ParsedSource, obj_call: Any) -> list[dict[str, Any]] | None:
    args = obj_call.child_by_field_name("arguments")
    if args is None:
        return None
    shape = next((c for c in args.children if c.type == "object"), None)
    if shape is None:
        return None
    fields: list[dict[str, Any]] = []
    for pair in shape.children:
        if pair.type != "pair":
            continue
        key = pair.child_by_field_name("key")
        value = pair.child_by_field_name("value")
        if key is None or value is None:
            continue
        base, chain = _zod_chain(ps, value)
        chain_text = " ".join(chain)
        required = not any(
            m in chain_text for m in (".optional(", ".nullish(", ".default(")
        )
        rules = [c.strip() for c in chain if c.strip()]
        field: dict[str, Any] = {
            "name": ps.text(key).strip("'\""),
            "type": _ZOD_TYPES.get(base, base),
            "required": required,
            "source": "body",
        }
        if rules:
            field["rules"] = rules
        fields.append(field)
    return fields


def zod_schemas(ps: ParsedSource) -> dict[str, list[dict[str, Any]]]:
    schemas: dict[str, list[dict[str, Any]]] = {}
    for decl in ps.find_all("variable_declarator"):
        name = decl.child_by_field_name("name")
        value = decl.child_by_field_name("value")
        if name is None or value is None or "z.object" not in ps.text(value)[:200]:
            continue
        # Find the z.object(...) call at the root of the chain.
        call = next(
            (
                n
                for n in ps.walk(value)
                if n.type == "call_expression"
                and (fn := n.child_by_field_name("function")) is not None
                and ps.text(fn) in ("z.object", "zod.object")
            ),
            None,
        )
        if call is None:
            continue
        fields = _zod_object_fields(ps, call)
        if fields is not None:
            schemas[ps.text(name)] = fields
    return schemas


# ---------------------------------------------------------------------------
# Handler location
# ---------------------------------------------------------------------------


def _enclosing_function(ps: ParsedSource, line: int, verb: str) -> Any | None:
    """Locate the handler node for a surface sourced at *line*."""
    best: Any | None = None
    # Next.js App Router named exports.
    for node in ps.walk():
        if node.type == "function_declaration":
            n = node.child_by_field_name("name")
            if n is not None and ps.text(n) == verb.upper():
                return node
        elif node.type == "variable_declarator":
            n = node.child_by_field_name("name")
            v = node.child_by_field_name("value")
            if (
                n is not None
                and ps.text(n) == verb.upper()
                and v is not None
                and v.type in _FUNC_TYPES
            ):
                return v
    # Express/Fastify: call expression on the surface line with a function arg.
    for node in ps.find_all("call_expression"):
        if ps.line_of(node) != line:
            continue
        fn = node.child_by_field_name("function")
        if fn is None or fn.type != "member_expression":
            continue
        prop = fn.child_by_field_name("property")
        if prop is None or ps.text(prop).lower() not in _VERBS:
            continue
        args = node.child_by_field_name("arguments")
        funcs = [a for a in (args.children if args else []) if a.type in _FUNC_TYPES]
        if funcs:
            return funcs[-1]
        # Handler factory: app.post('/x', transition([...], 'paid')) where
        # `function transition(...) { return (req, res) => {...} }`.
        factories = [
            a for a in (args.children if args else []) if a.type == "call_expression"
        ]
        if factories:
            callee = factories[-1].child_by_field_name("function")
            target = ps.text(callee) if callee is not None else ""
            for decl in ps.find_all("function_declaration"):
                n = decl.child_by_field_name("name")
                if n is not None and ps.text(n) == target:
                    for ret in ps.find_all("return_statement", node=decl):
                        for c in ret.children:
                            if c.type in _FUNC_TYPES:
                                return c
        idents = [a for a in (args.children if args else []) if a.type == "identifier"]
        if idents:
            target = ps.text(idents[-1])
            for decl in ps.find_all("function_declaration"):
                n = decl.child_by_field_name("name")
                if n is not None and ps.text(n) == target:
                    return decl
    # NestJS method_definition whose preceding decorator sits on *line*.
    for cls_body in ps.find_all("class_body"):
        pending: list[Any] = []
        for child in cls_body.children:
            if child.type == "decorator":
                pending.append(child)
            elif child.type == "method_definition":
                if any(
                    ps.line_of(d) == line or ps.line_of(child) == line for d in pending
                ):
                    best = child
                pending = []
    return best


# ---------------------------------------------------------------------------
# Handler analysis
# ---------------------------------------------------------------------------


class _Handler:
    def __init__(
        self, mods: _Modules, ps: ParsedSource, path: Path, node: Any, method: str
    ) -> None:
        self.mods, self.ps, self.path, self.node, self.method = (
            mods,
            ps,
            path,
            node,
            method,
        )
        self.body_aliases: set[str] = set()
        self.request: dict[str, dict[str, Any]] = {}
        self.confidence = "inferred"
        self.zod = zod_schemas(ps)
        self.declared_body: list[dict[str, Any]] | None = None
        self.responses: list[dict[str, Any]] = []

    # -- request ---------------------------------------------------------
    def _add(
        self, name: str, source: str, required: bool, type_: str = "unknown"
    ) -> None:
        key = f"{source}:{name}"
        existing = self.request.get(key)
        if existing is None or (required and not existing["required"]):
            self.request[key] = {
                "name": name,
                "type": type_,
                "required": required,
                "source": source,
            }

    def _unwrap(self, node: Any) -> Any:
        """Strip await / parentheses / casts / non-null wrappers."""
        while node is not None:
            if node.type == "await_expression":
                node = node.children[-1]
            elif node.type == "parenthesized_expression":
                node = node.children[1]
            elif node.type in (
                "as_expression",
                "non_null_expression",
                "satisfies_expression",
            ):
                node = node.children[0]
            else:
                break
        return node

    def _is_body_expr(self, node: Any) -> bool:
        node = self._unwrap(node)
        if node is None:
            return False
        text = self.ps.text(node).replace(" ", "")
        if node.type == "identifier":
            return text in self.body_aliases
        if node.type == "member_expression":
            return text in ("req.body", "request.body", "ctx.request.body")
        if node.type == "call_expression":
            return text in ("req.json()", "request.json()", "req.body.json()")
        return False

    def _cast_type(self, node: Any) -> str | None:
        """Type name from ``expr as T`` wrappers."""
        while node is not None and node.type in (
            "await_expression",
            "parenthesized_expression",
        ):
            node = (
                node.children[-1]
                if node.type == "await_expression"
                else node.children[1]
            )
        if node is not None and node.type == "as_expression":
            return _type_name(self.ps, node.children[-1])
        return None

    def _collect_patterns(self, pattern: Any, source: str) -> None:
        ps = self.ps
        for child in pattern.children:
            if child.type == "shorthand_property_identifier_pattern":
                self._add(ps.text(child), source, True)
            elif child.type == "object_assignment_pattern":
                left = child.child_by_field_name("left")
                if left is not None:
                    self._add(ps.text(left), source, False)
            elif child.type == "pair_pattern":
                key = child.child_by_field_name("key")
                value = child.child_by_field_name("value")
                if key is not None:
                    optional = value is not None and value.type == "assignment_pattern"
                    self._add(ps.text(key).strip("'\""), source, not optional)

    def analyze(self) -> None:
        ps = self.ps
        node = self.node
        # Pass 1: parameters (Nest decorators / Next params typing).
        params = node.child_by_field_name("parameters")
        if params is not None:
            self._analyze_params(params)
        body = node.child_by_field_name("body") or node
        # Pass 2: aliases for the request body.
        for decl in ps.find_all("variable_declarator", node=body):
            name = decl.child_by_field_name("name")
            value = decl.child_by_field_name("value")
            if name is None or value is None:
                continue
            ann = decl.child_by_field_name("type")
            if self._is_body_expr(value):
                declared = (
                    _type_name(ps, ann) if ann is not None else self._cast_type(value)
                )
                if declared and declared != "unknown":
                    fields, _ = _resolve_type_fields(
                        self.mods, ps, self.path, declared, "body"
                    )
                    if fields is not None:
                        self.declared_body = fields
                if name.type == "identifier":
                    self.body_aliases.add(ps.text(name))
                elif name.type == "object_pattern":
                    self._collect_patterns(name, "body")
            elif name.type == "object_pattern":
                text = ps.text(value)
                if text in ("req.query", "request.query"):
                    self._collect_patterns(name, "query")
                elif text in ("req.params", "request.params"):
                    self._collect_patterns(name, "path")
        # Pass 3: member / subscript / call idioms.
        for n in ps.walk(body):
            if n.type == "member_expression":
                text = ps.text(n)
                obj = n.child_by_field_name("object")
                prop = n.child_by_field_name("property")
                if obj is None or prop is None:
                    continue
                obj_t, prop_t = ps.text(obj), ps.text(prop)
                if obj_t in self.body_aliases or obj_t in ("req.body", "request.body"):
                    optional = "?." in text
                    self._add(prop_t, "body", not optional)
                elif obj_t in ("req.query", "request.query"):
                    self._add(prop_t, "query", False)
                elif obj_t in ("req.params", "request.params", "params"):
                    self._add(prop_t, "path", True)
            elif n.type == "subscript_expression":
                obj = n.child_by_field_name("object")
                idx = n.child_by_field_name("index")
                key = ps.string_value(idx) if idx is not None else None
                if obj is not None and key:
                    obj_t = ps.text(obj)
                    if obj_t in self.body_aliases or obj_t in (
                        "req.body",
                        "request.body",
                    ):
                        self._add(key, "body", True)
                    elif obj_t in ("req.query", "request.query"):
                        self._add(key, "query", False)
            elif n.type == "call_expression":
                self._analyze_call(n)

    def _analyze_params(self, params: Any) -> None:
        ps = self.ps
        for p in params.children:
            if p.type not in ("required_parameter", "optional_parameter"):
                continue
            decorators = _decorator_names(ps, p)
            pattern = p.child_by_field_name("pattern")
            ann = p.child_by_field_name("type")
            raw_t = _type_name(ps, ann) if ann is not None else "unknown"
            for deco in decorators:
                dname = deco.split("(")[0]
                arg = deco[deco.find("(") + 1 : deco.rfind(")")].strip("'\" ")
                pname = ps.text(pattern) if pattern is not None else ""
                if dname == "Body":
                    if arg:
                        self._add(arg, "body", True, _simple_type(raw_t))
                    else:
                        fields, _ = _resolve_type_fields(
                            self.mods, ps, self.path, raw_t, "body"
                        )
                        if fields is not None:
                            self.declared_body = fields
                        else:
                            self.request.setdefault(
                                "body:*",
                                {
                                    "name": pname,
                                    "type": raw_t,
                                    "required": True,
                                    "source": "body",
                                },
                            )
                elif dname == "Query":
                    if arg:
                        self._add(arg, "query", False, _simple_type(raw_t))
                    else:
                        fields, _ = _resolve_type_fields(
                            self.mods, ps, self.path, raw_t, "query"
                        )
                        for f in fields or []:
                            self._add(f["name"], "query", f["required"], f["type"])
                elif dname == "Param":
                    self._add(arg or pname, "path", True, _simple_type(raw_t))
            # Next.js second param: { params }: { params: { id: string } }
            if (
                pattern is not None
                and pattern.type == "object_pattern"
                and "params" in ps.text(pattern)
            ):
                if ann is not None:
                    for sig in ps.find_all("property_signature", node=ann):
                        owner = sig.child_by_field_name("name")
                        if owner is not None and ps.text(owner) == "params":
                            inner = sig.child_by_field_name("type")
                            if inner is not None:
                                for f in ps.find_all("property_signature", node=inner):
                                    if f == sig:
                                        continue
                                    nm = f.child_by_field_name("name")
                                    tp = f.child_by_field_name("type")
                                    if nm is not None:
                                        self._add(
                                            ps.text(nm),
                                            "path",
                                            True,
                                            _simple_type(_type_name(ps, tp)),
                                        )

    def _analyze_call(self, call: Any) -> None:
        ps = self.ps
        fn = call.child_by_field_name("function")
        args = call.child_by_field_name("arguments")
        if fn is None or args is None:
            return
        fn_t = ps.text(fn)
        arg_nodes = [a for a in args.children if a.type not in ("(", ")", ",")]
        # zod: schema.parse(body) / schema.safeParse(body)
        if fn.type == "member_expression":
            obj = fn.child_by_field_name("object")
            prop = fn.child_by_field_name("property")
            pname = ps.text(prop) if prop is not None else ""
            oname = ps.text(obj) if obj is not None else ""
            if pname in ("parse", "safeParse", "parseAsync") and oname in self.zod:
                if arg_nodes and (
                    self._is_body_expr(arg_nodes[0])
                    or arg_nodes[0].type == "identifier"
                ):
                    self.declared_body = self.zod[oname]
                    self.confidence = "declared"
            # searchParams.get('x') / formData.get('x')
            if pname == "get" and arg_nodes:
                key = ps.string_value(arg_nodes[0])
                if key and "searchParams" in oname:
                    self._add(key, "query", False)
                elif key and "formData" in oname.lower():
                    self._add(key, "body", False)
        # Response emitters
        self._maybe_response(call, fn_t, arg_nodes)

    # -- response --------------------------------------------------------
    def _maybe_response(self, call: Any, fn_t: str, args: list[Any]) -> None:
        ps = self.ps
        compact = fn_t.replace(" ", "")
        status: int | None = None
        payload: Any | None = None
        is_emit = False
        if compact in (
            "NextResponse.json",
            "Response.json",
            "res.json",
            "res.send",
            "reply.send",
            "ctx.json",
        ):
            is_emit = True
        elif compact.endswith((".json", ".send")) and (
            "status(" in compact or "code(" in compact
        ):
            is_emit = True
        if not is_emit or not args:
            return
        payload = args[0]
        # status from chain: res.status(201).json(...)
        fn = call.child_by_field_name("function")
        chain = fn.child_by_field_name("object") if fn is not None else None
        if chain is not None and chain.type == "call_expression":
            cfn = chain.child_by_field_name("function")
            if cfn is not None and ps.text(cfn).endswith((".status", ".code")):
                cargs = chain.child_by_field_name("arguments")
                nums = [
                    c for c in (cargs.children if cargs else []) if c.type == "number"
                ]
                if nums:
                    status = int(ps.text(nums[0]))
        # status from options object: NextResponse.json(x, { status: 201 })
        if len(args) > 1 and args[1].type == "object":
            for pair in args[1].children:
                if pair.type == "pair":
                    k = pair.child_by_field_name("key")
                    v = pair.child_by_field_name("value")
                    if (
                        k is not None
                        and v is not None
                        and ps.text(k) == "status"
                        and v.type == "number"
                    ):
                        status = int(ps.text(v))
        self.responses.append(
            {"payload": payload, "status": status or 200, "node": call}
        )

    def _payload_fields(
        self, payload: Any, depth: int = 0
    ) -> tuple[list[dict[str, Any]] | str | None, bool]:
        """(fields | type-name | None, is_array) for a response payload."""
        ps = self.ps
        if payload is None or depth > 3:
            return None, False
        t = payload.type
        if t == "object":
            return self._object_fields(payload), False
        if t == "array":
            for el in payload.children:
                if el.type == "object":
                    return self._object_fields(el), True
            return None, True
        if t == "identifier":
            return self._identifier_payload(ps.text(payload), depth)
        if t == "call_expression":
            fn = payload.child_by_field_name("function")
            if fn is not None and fn.type == "member_expression":
                prop = fn.child_by_field_name("property")
                if prop is not None and ps.text(prop) in ("map", "flatMap"):
                    args = payload.child_by_field_name("arguments")
                    for a in args.children if args else []:
                        if a.type in _FUNC_TYPES:
                            fields, _ = self._function_return(a, depth)
                            return fields, True
                    return None, True
                if prop is not None and ps.text(prop) in (
                    "findMany",
                    "findAll",
                    "find",
                    "all",
                    "toArray",
                ):
                    return None, True
        if t == "await_expression":
            return self._payload_fields(payload.children[-1], depth + 1)
        if t in ("as_expression", "parenthesized_expression", "satisfies_expression"):
            inner = (
                payload.children[0]
                if t != "parenthesized_expression"
                else payload.children[1]
            )
            cast = (
                _type_name(ps, payload.children[-1]) if t == "as_expression" else None
            )
            if cast:
                fields, arr = _resolve_type_fields(
                    self.mods, ps, self.path, cast, "body"
                )
                if fields is not None:
                    return fields, arr
            return self._payload_fields(inner, depth + 1)
        return None, False

    def _function_return(
        self, fn: Any, depth: int
    ) -> tuple[list[dict[str, Any]] | str | None, bool]:
        body = fn.child_by_field_name("body")
        if body is None:
            return None, False
        if body.type in ("parenthesized_expression", "object"):
            return self._payload_fields(
                body.children[1] if body.type == "parenthesized_expression" else body,
                depth + 1,
            )
        for ret in self.ps.find_all("return_statement", node=body):
            for c in ret.children:
                if c.type not in ("return", ";"):
                    return self._payload_fields(c, depth + 1)
        return None, False

    def _object_fields(self, obj: Any) -> list[dict[str, Any]]:
        ps = self.ps
        fields: list[dict[str, Any]] = []
        for child in obj.children:
            if child.type == "pair":
                k = child.child_by_field_name("key")
                v = child.child_by_field_name("value")
                if k is None:
                    continue
                fields.append(
                    {
                        "name": ps.text(k).strip("'\""),
                        "type": self._value_type(v),
                        "required": True,
                        "source": "body",
                    }
                )
            elif child.type == "shorthand_property_identifier":
                fields.append(
                    {
                        "name": ps.text(child),
                        "type": "unknown",
                        "required": True,
                        "source": "body",
                    }
                )
        return fields

    def _value_type(self, v: Any | None) -> str:
        if v is None:
            return "unknown"
        return {
            "string": "string",
            "template_string": "string",
            "number": "number",
            "true": "boolean",
            "false": "boolean",
            "array": "array",
            "object": "object",
            "null": "null",
        }.get(v.type, "unknown")

    def _identifier_payload(
        self, name: str, depth: int
    ) -> tuple[list[dict[str, Any]] | str | None, bool]:
        ps = self.ps
        for decl in ps.find_all("variable_declarator"):
            n = decl.child_by_field_name("name")
            if n is None or ps.text(n) != name:
                continue
            ann = decl.child_by_field_name("type")
            if ann is not None:
                raw = _type_name(ps, ann)
                fields, arr = _resolve_type_fields(
                    self.mods, ps, self.path, raw, "body"
                )
                if fields is not None:
                    return fields, arr
                inner, arr2 = _unwrap_type(raw)
                if inner:
                    return inner, arr2
            value = decl.child_by_field_name("value")
            if value is not None and value != self.node:
                return self._payload_fields(value, depth + 1)
        return None, False

    def response_schema(self) -> dict[str, Any] | None:
        ok = [r for r in self.responses if int(r["status"]) < 400]
        errs = [r for r in self.responses if int(r["status"]) >= 400]
        errors: list[dict[str, Any]] = []
        for e in errs:
            entry: dict[str, Any] = {"status": int(e["status"])}
            if e["payload"] is not None and e["payload"].type == "object":
                msg = self._error_message(e["payload"])
                if msg:
                    entry["message"] = msg
            if entry not in errors:
                errors.append(entry)
        # Nest-style: return value of the method itself.
        schema: dict[str, Any] | None = None
        for r in ok:
            fields, arr = self._payload_fields(r["payload"])
            if isinstance(fields, list) and fields:
                schema = _schema(
                    fields,
                    "inferred",
                    is_array=arr,
                    status=int(r["status"]),
                    errors=errors,
                )
                break
            if isinstance(fields, str):
                schema = {
                    "type": fields,
                    "confidence": "inferred",
                    "is_array": arr,
                    "status": int(r["status"]),
                }
                if errors:
                    schema["errors"] = errors
                break
        if schema is None:
            schema = self._nest_return(errors)
        if schema is None and ok:
            first = ok[0]
            schema = {
                "type": "unknown",
                "confidence": "inferred",
                "status": int(first["status"]),
            }
            if errors:
                schema["errors"] = errors
            return schema
        return schema

    def _error_message(self, obj: Any) -> str | None:
        ps = self.ps
        for child in obj.children:
            if child.type == "pair":
                k = child.child_by_field_name("key")
                v = child.child_by_field_name("value")
                if (
                    k is not None
                    and v is not None
                    and ps.text(k) in ("error", "message")
                ):
                    return ps.string_value(v)
        return None

    def _nest_return(self, errors: list[dict[str, Any]]) -> dict[str, Any] | None:
        ps = self.ps
        node = self.node
        if node.type != "method_definition":
            # Express/Next handlers returning plain objects (rare); scan returns.
            return None
        ret_type = node.child_by_field_name("return_type")
        if ret_type is not None:
            raw = _type_name(ps, ret_type)
            fields, arr = _resolve_type_fields(self.mods, ps, self.path, raw, "body")
            if fields is not None:
                return _schema(fields, "declared", is_array=arr, errors=errors)
            inner, arr = _unwrap_type(raw)
            if inner and inner not in ("void", "any", "unknown"):
                return {"type": inner, "confidence": "declared", "is_array": arr}
        body = node.child_by_field_name("body")
        if body is not None:
            for r in ps.find_all("return_statement", node=body):
                for c in r.children:
                    if c.type in ("return", ";"):
                        continue
                    fields_or_t, arr = self._payload_fields(c)
                    if isinstance(fields_or_t, list) and fields_or_t:
                        return _schema(
                            fields_or_t, "inferred", is_array=arr, errors=errors
                        )
                    if isinstance(fields_or_t, str):
                        return {
                            "type": fields_or_t,
                            "confidence": "inferred",
                            "is_array": arr,
                        }
        return None

    def request_schema(self) -> dict[str, Any]:
        opaque = self.request.pop("body:*", None)
        extracted = list(self.request.values())
        if self.declared_body is not None:
            declared_names = {f["name"] for f in self.declared_body}
            rest = [
                f
                for f in extracted
                if not (f["source"] == "body" and f["name"] in declared_names)
            ]
            return _schema(_dedupe(list(self.declared_body) + rest), "declared")
        if opaque is not None and not extracted:
            return _unknown()
        return _schema(extracted, self.confidence)


def _dedupe(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for f in fields:
        key = (f["source"], f["name"])
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def populate_js_api_contracts(surfaces: list[ApiSurface], workdir: Path) -> int:
    """Populate request/response schemas on JS/TS-sourced API surfaces.

    Mutates surfaces in place; Python surfaces are ignored. Returns the number
    of surfaces with at least one extracted side.
    """
    mods = _Modules(workdir)
    populated = 0
    for surface in surfaces:
        if not surface.source_refs:
            continue
        ref = surface.source_refs[0]
        if not ref.file_path.endswith(_JS_EXTS):
            continue
        path = workdir / ref.file_path
        ps = mods.get(path)
        line = ref.start_line or 1
        handler_node = (
            _enclosing_function(ps, line, surface.method or "GET") if ps else None
        )
        if ps is None or handler_node is None:
            _mark_unknown(surface)
            continue
        handler = _Handler(mods, ps, path, handler_node, surface.method or "GET")
        try:
            handler.analyze()
            req = handler.request_schema()
            resp = handler.response_schema()
        except Exception:
            logger.warning("js_contract_failed", surface=surface.name, exc_info=True)
            _mark_unknown(surface)
            continue

        got = False
        if req.get("unknown"):
            surface.request_schema = req
        elif req.get("fields"):
            surface.request_schema = req
            got = True
        elif surface.method in _BODY_METHODS:
            surface.request_schema = _unknown()
        else:
            surface.request_schema = _schema([], req.get("confidence", "inferred"))
        if resp is not None:
            surface.response_schema = resp
            got = True
        elif not surface.response_schema:
            surface.response_schema = _unknown()
        if got:
            populated += 1
    logger.info(
        "api_contracts_js", surfaces_total=len(surfaces), surfaces_populated=populated
    )
    return populated


def _mark_unknown(surface: ApiSurface) -> None:
    if not surface.request_schema and surface.method in _BODY_METHODS:
        surface.request_schema = _unknown()
    if not surface.response_schema:
        surface.response_schema = _unknown()
