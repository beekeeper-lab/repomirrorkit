"""API contract extraction for ASP.NET Core (controllers + minimal APIs).

Third member of the contract-extraction family (Python: BEAN-062, JS/TS:
BEAN-063). Uses tree-sitter C#. Evidence:

- ``[FromBody]`` / implicit complex-type parameters → request body fields
  expanded from the DTO class / record (``[Required]``, ``required``
  modifier, DataAnnotations → ``rules``)
- ``[FromQuery]`` / ``[FromRoute]`` / simple parameters → query / path fields
- Return type (``ActionResult<T>``, ``Task<T>``, ``List<T>``) → response
  fields; ``Ok`` / ``Created`` / ``NoContent`` / ``NotFound`` / ``BadRequest``
  helper calls → status codes and error responses

Schema shape matches the other contract extractors.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import ApiSurface
from repo_mirror_kit.harvester.parsing import ParsedSource, parse_source

logger = structlog.get_logger()

_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})
_TYPE_MAP = {
    "string": "string",
    "int": "integer",
    "long": "integer",
    "short": "integer",
    "float": "number",
    "double": "number",
    "decimal": "number",
    "bool": "boolean",
    "DateTime": "string",
    "DateTimeOffset": "string",
    "Guid": "string",
    "object": "object",
}
_STATUS_CALLS = {
    "Ok": 200,
    "Created": 201,
    "CreatedAtAction": 201,
    "CreatedAtRoute": 201,
    "Accepted": 202,
    "NoContent": 204,
    "BadRequest": 400,
    "Unauthorized": 401,
    "Forbid": 403,
    "NotFound": 404,
    "Conflict": 409,
    "UnprocessableEntity": 422,
}
_RESULTS = {f"Results.{k}": v for k, v in _STATUS_CALLS.items()}


def _unknown() -> dict[str, Any]:
    return {"unknown": True}


def _type_text(ps: ParsedSource, node: Any | None) -> str:
    return ps.text(node).strip() if node is not None else "unknown"


def _unwrap(raw: str) -> tuple[str, bool]:
    raw = raw.strip()
    is_array = False
    changed = True
    while changed:
        changed = False
        m = re.match(
            r"^(?:Task|ValueTask|ActionResult|ActionResult|Nullable)<(.+)>$", raw
        )
        if m:
            raw, changed = m.group(1).strip(), True
            continue
        m = re.match(
            r"^(?:List|IList|IEnumerable|ICollection|IReadOnlyList|IReadOnlyCollection|HashSet)<(.+)>$",
            raw,
        )
        if m:
            raw, changed, is_array = m.group(1).strip(), True, True
            continue
        if raw.endswith("[]"):
            raw, changed, is_array = raw[:-2], True, True
        if raw.endswith("?"):
            raw, changed = raw[:-1], True
    return raw, is_array


def _simple_type(raw: str) -> str:
    inner, arr = _unwrap(raw)
    if arr:
        return "array"
    return _TYPE_MAP.get(inner, inner)


def _attr_rules(ps: ParsedSource, node: Any) -> tuple[list[str], bool]:
    """(rules, has_required) from attribute lists attached to *node*."""
    rules: list[str] = []
    required = False
    for attr in ps.find_all("attribute", node=node):
        # Only attributes belonging to this node (not nested members).
        parent = attr.parent
        while parent is not None and parent.type != "attribute_list":
            parent = parent.parent
        if parent is None or parent.parent != node:
            continue
        name_node = attr.children[0] if attr.children else None
        name = ps.text(name_node) if name_node is not None else ""
        args = ps.text(attr)[len(name) :].strip("() ")
        if name == "Required":
            required = True
        elif name == "StringLength":
            nums = re.findall(r"\d+", args)
            if nums:
                rules.append(f"max_length={nums[0]}")
            m = re.search(r"MinimumLength\s*=\s*(\d+)", args)
            if m:
                rules.append(f"min_length={m.group(1)}")
        elif name in ("MaxLength", "MinLength"):
            rules.append(f"{name[:3].lower()}_length={args}")
        elif name == "Range":
            parts = [p.strip() for p in args.split(",")[:2]]
            if len(parts) == 2:
                rules.extend([f"min={parts[0]}", f"max={parts[1]}"])
        elif name == "EmailAddress":
            rules.append("email")
        elif name == "Url":
            rules.append("url(")
        elif name == "RegularExpression":
            rules.append(f"pattern={args}")
    return rules, required


class _Types:
    """Repo-wide index of C# DTO types."""

    def __init__(self, workdir: Path, files: list[str]) -> None:
        self._decls: dict[str, tuple[ParsedSource, Any]] = {}
        for rel in files:
            if not rel.endswith(".cs"):
                continue
            try:
                text = (workdir / rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if len(text) > 400_000:
                continue
            ps = parse_source(rel, text)
            if ps is None:
                continue
            for node in ps.find_all(
                "class_declaration",
                "record_declaration",
                "struct_declaration",
                "record_struct_declaration",
            ):
                name = node.child_by_field_name("name")
                if name is not None:
                    self._decls.setdefault(ps.text(name), (ps, node))

    def fields(
        self, raw_type: str, source: str
    ) -> tuple[list[dict[str, Any]] | None, bool]:
        inner, is_array = _unwrap(raw_type)
        entry = self._decls.get(inner)
        if entry is None:
            return None, is_array
        ps, decl = entry
        fields: list[dict[str, Any]] = []
        for param in ps.find_all("parameter", node=decl):
            if param.parent is None or param.parent.parent != decl:
                continue
            name = param.child_by_field_name("name")
            ptype = param.child_by_field_name("type")
            if name is None:
                continue
            rules, required = _attr_rules(ps, param)
            fields.append(
                {
                    "name": ps.text(name),
                    "type": _simple_type(_type_text(ps, ptype)),
                    "required": required,
                    "source": source,
                    **({"rules": rules} if rules else {}),
                }
            )
        for prop in ps.find_all("property_declaration", node=decl):
            name = prop.child_by_field_name("name")
            ptype = prop.child_by_field_name("type")
            if name is None:
                continue
            rules, required = _attr_rules(ps, prop)
            if any(
                ps.text(m) == "required" for m in prop.children if m.type == "modifier"
            ):
                required = True
            fields.append(
                {
                    "name": ps.text(name),
                    "type": _simple_type(_type_text(ps, ptype)),
                    "required": required,
                    "source": source,
                    **({"rules": rules} if rules else {}),
                }
            )
        return fields or None, is_array


def _locate(ps: ParsedSource, line: int) -> Any | None:
    """Handler node for a surface sourced at *line*.

    The regex pass can report the blank line just before the HTTP attribute,
    so an attribute on ``line`` or ``line + 1`` identifies the method.
    """
    methods = ps.find_all("method_declaration", "local_function_statement")
    for want in (line, line + 1):
        for m in methods:
            if any(ps.line_of(a) == want for a in ps.find_all("attribute", node=m)):
                return m
    for call in ps.find_all("invocation_expression"):
        if abs(ps.line_of(call) - line) <= 1 and re.search(
            r"\.Map(Get|Post|Put|Delete|Patch)\b", ps.text(call)[:80]
        ):
            lam = next(
                iter(
                    ps.find_all(
                        "lambda_expression", "anonymous_method_expression", node=call
                    )
                ),
                None,
            )
            if lam is not None:
                return lam
    return None


def _route_params(path: str) -> set[str]:
    return set(re.findall(r"\{(\w+)(?:[:?][^}]*)?\}", path))


def _status_calls(ps: ParsedSource, node: Any) -> list[tuple[int, Any | None]]:
    out: list[tuple[int, Any | None]] = []
    for inv in ps.find_all("invocation_expression", node=node):
        fn = inv.child_by_field_name("function") or (
            inv.children[0] if inv.children else None
        )
        name = ps.text(fn) if fn is not None else ""
        code = _STATUS_CALLS.get(name) or _RESULTS.get(name)
        if code is None:
            continue
        args = inv.child_by_field_name("arguments")
        arg_nodes = [a for a in (args.children if args else []) if a.type == "argument"]
        out.append((code, arg_nodes[-1].children[-1] if arg_nodes else None))
    return out


def populate_dotnet_api_contracts(
    surfaces: list[ApiSurface], workdir: Path, files: list[str]
) -> int:
    """Populate schemas on ``.cs``-sourced API surfaces; return count populated."""
    cs_surfaces = [
        s
        for s in surfaces
        if s.source_refs and s.source_refs[0].file_path.endswith(".cs")
    ]
    if not cs_surfaces:
        return 0
    types = _Types(workdir, files)
    populated = 0
    cache: dict[str, ParsedSource | None] = {}
    for surface in cs_surfaces:
        ref = surface.source_refs[0]
        if ref.file_path not in cache:
            try:
                cache[ref.file_path] = parse_source(
                    ref.file_path, (workdir / ref.file_path).read_bytes()
                )
            except OSError:
                cache[ref.file_path] = None
        ps = cache[ref.file_path]
        handler = _locate(ps, ref.start_line or 1) if ps else None
        if ps is None or handler is None:
            surface.request_schema = surface.request_schema or (
                _unknown() if surface.method in _BODY_METHODS else {}
            )
            surface.response_schema = surface.response_schema or _unknown()
            continue
        try:
            req, resp = _analyze(ps, handler, surface, types)
        except Exception:
            logger.warning(
                "dotnet_contract_failed", surface=surface.name, exc_info=True
            )
            surface.response_schema = surface.response_schema or _unknown()
            continue
        surface.request_schema = req
        surface.response_schema = resp
        if req.get("fields") or resp.get("fields") or "type" in resp:
            populated += 1
    logger.info(
        "api_contracts_dotnet",
        surfaces_total=len(cs_surfaces),
        surfaces_populated=populated,
    )
    return populated


def _analyze(
    ps: ParsedSource, handler: Any, surface: ApiSurface, types: _Types
) -> tuple[dict[str, Any], dict[str, Any]]:
    path_params = _route_params(surface.path)
    params = next(
        (
            c
            for c in handler.children
            if c.type in ("parameter_list", "implicit_parameter_list")
        ),
        None,
    )
    fields: list[dict[str, Any]] = []
    opaque_body = False
    for p in params.children if params is not None else []:
        if p.type != "parameter":
            continue
        name_n = p.child_by_field_name("name")
        type_n = p.child_by_field_name("type")
        if name_n is None:
            continue
        pname, ptype = ps.text(name_n), _type_text(ps, type_n)
        attrs = " ".join(ps.text(a) for a in ps.find_all("attribute", node=p))
        inner, _ = _unwrap(ptype)
        is_complex = inner not in _TYPE_MAP and inner not in (
            "CancellationToken",
            "HttpContext",
            "HttpRequest",
        )
        if inner in ("CancellationToken", "HttpContext", "HttpRequest", "ILogger"):
            continue
        if "FromBody" in attrs or (
            is_complex and surface.method in _BODY_METHODS and "From" not in attrs
        ):
            found, _ = types.fields(ptype, "body")
            if found is not None:
                fields.extend(found)
            else:
                opaque_body = True
        elif "FromQuery" in attrs:
            fields.append(
                {
                    "name": pname,
                    "type": _simple_type(ptype),
                    "required": not ptype.endswith("?"),
                    "source": "query",
                }
            )
        elif "FromRoute" in attrs or pname in path_params:
            fields.append(
                {
                    "name": pname,
                    "type": _simple_type(ptype),
                    "required": True,
                    "source": "path",
                }
            )
        elif not is_complex:
            fields.append(
                {
                    "name": pname,
                    "type": _simple_type(ptype),
                    "required": False,
                    "source": "query",
                }
            )
    if opaque_body and not any(f["source"] == "body" for f in fields):
        req: dict[str, Any] = _unknown()
    else:
        req = {"fields": fields, "confidence": "declared"}

    # Response: declared return type first, then status helper calls.
    ret = handler.child_by_field_name("returns") or handler.child_by_field_name("type")
    ret_text = (
        _type_text(ps, ret)
        if ret is not None and handler.type == "method_declaration"
        else ""
    )
    calls = _status_calls(ps, handler)
    ok = [(c, a) for c, a in calls if c < 400]
    errors = []
    for code, _arg in calls:
        if code >= 400 and {"status": code} not in errors:
            errors.append({"status": code})
    resp: dict[str, Any] = {}
    if ret_text and not re.match(
        r"^(Task<)?(IActionResult|ActionResult|IResult|void|Task)>?$", ret_text
    ):
        found, arr = types.fields(ret_text, "body")
        inner, _ = _unwrap(ret_text)
        if found is not None:
            resp = {"fields": found, "confidence": "declared", "is_array": arr}
        elif inner and inner not in ("void", "IActionResult", "IResult"):
            resp = {
                "type": _simple_type(ret_text),
                "confidence": "declared",
                "is_array": arr,
            }
    if not resp:
        for _code, arg in ok:
            if arg is None:
                continue
            created = next(
                iter(ps.find_all("object_creation_expression", node=arg)), None
            ) or (arg if arg.type == "object_creation_expression" else None)
            if created is not None:
                tn = created.child_by_field_name("type")
                found, arr = types.fields(_type_text(ps, tn), "body")
                if found is not None:
                    resp = {"fields": found, "confidence": "inferred", "is_array": arr}
                    break
    if ok and "status" not in resp and resp:
        resp["status"] = ok[0][0]
    if not resp:
        resp = {"type": "unknown", "confidence": "inferred"} if ok else _unknown()
        if ok:
            resp["status"] = ok[0][0]
    if errors and not resp.get("unknown"):
        resp["errors"] = errors
    return req, {k: v for k, v in resp.items() if v or k == "unknown"}
