"""Screen / form / field extraction and field→model mapping (BEAN-064).

Produces one :class:`ScreenSurface` per user-facing screen: its input fields
(name, input type, label, required, validation), the actions it exposes (API
calls, form submissions), and where it navigates. A mapping pass then chains
each field to an API request field and a model column.

Sources:

- **React / Next.js** (tree-sitter): JSX ``input/select/textarea`` (and UI-kit
  components with a ``name`` prop), label association, react-hook-form
  ``register(...)`` options, ``zodResolver(schema)`` rules, ``fetch`` /
  ``axios`` / ``useSWR`` calls, ``<Link>`` / ``router.push`` navigation.
- **HTML-like templates** (regex): ``.vue`` / ``.svelte`` / ``.html`` /
  Jinja / ERB / EJS / Handlebars / Razor — ``<form action method>`` with
  controls, ``v-model`` / ``bind:value`` bindings, anchors.

Visual styling is deliberately out of scope.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.api_contracts_js import zod_schemas
from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    ModelSurface,
    RouteSurface,
    ScreenAction,
    ScreenField,
    ScreenSurface,
    SourceRef,
)
from repo_mirror_kit.harvester.inventory import InventoryResult
from repo_mirror_kit.harvester.parsing import ParsedSource, parse_source

logger = structlog.get_logger()

_REACT_EXTS = (".tsx", ".jsx", ".js", ".ts", ".mjs")
_TEMPLATE_EXTS = (
    ".vue",
    ".svelte",
    ".html",
    ".htm",
    ".jinja",
    ".jinja2",
    ".j2",
    ".erb",
    ".ejs",
    ".hbs",
    ".cshtml",
)
_CONTROL_TAGS = {"input", "select", "textarea"}
_UI_KIT_CONTROLS = {
    "Input",
    "TextField",
    "Select",
    "Checkbox",
    "Textarea",
    "TextArea",
    "Switch",
    "Radio",
    "DatePicker",
    "NumberInput",
}
_SKIP_INPUT_TYPES = {"submit", "button", "reset", "image", "hidden"}
_HTML_VALIDATION_ATTRS = ("minLength", "maxLength", "min", "max", "pattern", "step")
_HTTP_VERBS = {"get", "post", "put", "delete", "patch"}
_MAX_FILE_BYTES = 400_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _normalize_url(raw: str) -> str:
    """Reduce a URL literal to a path template (``/api/users/:id``)."""
    url = raw.strip()
    url = re.sub(r"^https?://[^/]+", "", url)
    url = re.sub(r"\$\{[^}]*\}", ":param", url)
    url = url.split("?", 1)[0].split("#", 1)[0]
    return url or "/"


def _path_key(path: str) -> str:
    """Comparable form of a path: params collapse to ``{}``."""
    p = re.sub(r"<[^>]*>", "{}", path)
    p = re.sub(r"\{[^}]*\}", "{}", p)
    p = re.sub(r"(?<=/):[A-Za-z_][\w]*", "{}", p)
    return p.rstrip("/") or "/"


def _humanize_trigger(fn_name: str | None) -> str:
    if not fn_name:
        return "load"
    low = fn_name.lower()
    if "submit" in low or low.startswith(("create", "save", "add")):
        return f"submit ({fn_name})"
    if low.startswith(("delete", "remove")):
        return f"delete ({fn_name})"
    return fn_name


def _read(path: Path) -> str | None:
    try:
        if path.stat().st_size > _MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# React / Next.js (tree-sitter)
# ---------------------------------------------------------------------------


def _attr_map(ps: ParsedSource, element: Any) -> dict[str, Any]:
    """JSX attribute name → value node (None for bare boolean attributes)."""
    tag = element if element.type == "jsx_self_closing_element" else None
    if tag is None:
        tag = next(
            (c for c in element.children if c.type == "jsx_opening_element"), element
        )
    attrs: dict[str, Any] = {}
    for child in tag.children:
        if child.type == "jsx_attribute":
            nm = child.children[0] if child.children else None
            if nm is None:
                continue
            value = child.children[2] if len(child.children) > 2 else None
            attrs[ps.text(nm)] = value
    return attrs


def _tag_name(ps: ParsedSource, element: Any) -> str:
    tag = (
        element
        if element.type == "jsx_self_closing_element"
        else next(
            (c for c in element.children if c.type == "jsx_opening_element"), None
        )
    )
    if tag is None:
        return ""
    for c in tag.children:
        if c.type in ("identifier", "member_expression", "nested_identifier"):
            return ps.text(c)
    return ""


def _attr_text(ps: ParsedSource, value: Any) -> str | None:
    """Literal text of an attribute value (string or ``{"x"}`` / ``{3}``)."""
    if value is None:
        return None
    lit = ps.string_value(value)
    if lit is not None:
        return lit
    if value.type == "jsx_expression":
        inner = [c for c in value.children if c.type not in ("{", "}")]
        if inner:
            s = ps.string_value(inner[0])
            if s is not None:
                return s
            if inner[0].type == "number":
                return ps.text(inner[0])
            if inner[0].type == "template_string":
                return ps.text(inner[0]).strip("`")
    return None


def _bound_name(ps: ParsedSource, value: Any) -> str | None:
    """Field name from ``value={form.name}`` / ``value={email}``."""
    if value is None or value.type != "jsx_expression":
        return None
    inner = [c for c in value.children if c.type not in ("{", "}")]
    if not inner:
        return None
    node = inner[0]
    if node.type == "member_expression":
        prop = node.child_by_field_name("property")
        return ps.text(prop) if prop is not None else None
    if node.type == "identifier":
        return ps.text(node)
    return None


def _register_call(
    ps: ParsedSource, element: Any
) -> tuple[str, list[str], bool] | None:
    """Parse ``{...register("name", {required: true, minLength: 3})}``."""
    tag = (
        element
        if element.type == "jsx_self_closing_element"
        else next(
            (c for c in element.children if c.type == "jsx_opening_element"), None
        )
    )
    if tag is None:
        return None
    for child in tag.children:
        if child.type != "jsx_expression":
            continue
        spread = next((c for c in child.children if c.type == "spread_element"), None)
        call = next(
            (
                c
                for c in (spread.children if spread else [])
                if c.type == "call_expression"
            ),
            None,
        )
        if call is None:
            continue
        fn = call.child_by_field_name("function")
        if fn is None or ps.text(fn).split(".")[-1] != "register":
            continue
        args = call.child_by_field_name("arguments")
        arg_nodes = [
            a for a in (args.children if args else []) if a.type not in ("(", ")", ",")
        ]
        if not arg_nodes:
            continue
        name = ps.string_value(arg_nodes[0])
        if name is None:
            continue
        rules: list[str] = []
        required = False
        if len(arg_nodes) > 1 and arg_nodes[1].type == "object":
            for pair in arg_nodes[1].children:
                if pair.type != "pair":
                    continue
                k = pair.child_by_field_name("key")
                v = pair.child_by_field_name("value")
                if k is None or v is None:
                    continue
                kt = ps.text(k)
                vt = ps.text(v)
                if kt == "required":
                    required = vt != "false"
                    rules.append("required")
                elif kt in ("minLength", "maxLength", "min", "max", "pattern"):
                    rules.append(f"{kt}={vt}")
                elif kt == "validate":
                    rules.append("custom validate()")
        return name, rules, required
    return None


def _label_texts(ps: ParsedSource) -> tuple[dict[str, str], dict[int, str]]:
    """Map ``htmlFor`` ids → label text, and nested-control node ids → text."""
    by_for: dict[str, str] = {}
    by_node: dict[int, str] = {}
    for el in ps.find_all("jsx_element"):
        if _tag_name(ps, el) != "label":
            continue
        text = " ".join(
            ps.text(c).strip()
            for c in el.children
            if c.type == "jsx_text" and ps.text(c).strip()
        )
        attrs = _attr_map(ps, el)
        target = _attr_text(ps, attrs.get("htmlFor")) or _attr_text(
            ps, attrs.get("for")
        )
        if target:
            by_for[target] = text
        for inner in ps.walk(el):
            if inner is not el and inner.type in (
                "jsx_self_closing_element",
                "jsx_element",
            ):
                by_node[inner.id] = text
    return by_for, by_node


def _enclosing_function_name(ps: ParsedSource, node: Any) -> str | None:
    cur = node.parent
    while cur is not None:
        if cur.type == "function_declaration":
            n = cur.child_by_field_name("name")
            return ps.text(n) if n is not None else None
        if cur.type in ("arrow_function", "function_expression", "function"):
            parent = cur.parent
            if parent is not None and parent.type == "variable_declarator":
                n = parent.child_by_field_name("name")
                return ps.text(n) if n is not None else None
            if parent is not None and parent.type == "arguments":
                call = parent.parent
                fn = call.child_by_field_name("function") if call is not None else None
                if fn is not None and ps.text(fn) in ("useEffect", "useLayoutEffect"):
                    return None  # on load
        cur = cur.parent
    return None


def _call_args(call: Any) -> list[Any]:
    args = call.child_by_field_name("arguments")
    return [a for a in (args.children if args else []) if a.type not in ("(", ")", ",")]


def _url_arg(ps: ParsedSource, node: Any | None) -> str | None:
    if node is None:
        return None
    lit = ps.string_value(node)
    if lit is not None:
        return lit
    if node.type == "template_string":
        return ps.text(node).strip("`")
    return None


def _react_actions(ps: ParsedSource) -> tuple[list[ScreenAction], list[str]]:
    actions: list[ScreenAction] = []
    nav: list[str] = []
    seen_actions: set[tuple[str, str, str]] = set()

    def add_action(trigger: str, api_ref: str = "", target: str = "") -> None:
        key = (trigger, api_ref, target)
        if key not in seen_actions:
            seen_actions.add(key)
            actions.append(
                ScreenAction(trigger=trigger, api_ref=api_ref, navigation_target=target)
            )

    def add_nav(target: str) -> None:
        t = _normalize_url(target)
        if t.startswith("/") and t not in nav:
            nav.append(t)

    for call in ps.find_all("call_expression"):
        fn = call.child_by_field_name("function")
        if fn is None:
            continue
        fn_t = ps.text(fn)
        args = _call_args(call)
        trigger = _humanize_trigger(_enclosing_function_name(ps, call))
        # fetch(url, { method })
        if fn_t in ("fetch", "$fetch", "ofetch") and args:
            url = _url_arg(ps, args[0])
            if url and (url.startswith(("/", "http", "`")) or "/" in url):
                method = "GET"
                if len(args) > 1 and args[1].type == "object":
                    for pair in args[1].children:
                        if pair.type == "pair":
                            k = pair.child_by_field_name("key")
                            v = pair.child_by_field_name("value")
                            if (
                                k is not None
                                and v is not None
                                and ps.text(k) == "method"
                            ):
                                method = (ps.string_value(v) or "GET").upper()
                add_action(trigger, f"{method} {_normalize_url(url)}")
        # axios.post(url) / api.get(url) / http.delete(url)
        elif "." in fn_t and fn_t.rsplit(".", 1)[-1] in _HTTP_VERBS and args:
            owner = fn_t.rsplit(".", 1)[0]
            url = _url_arg(ps, args[0])
            if (
                url
                and url.startswith(("/", "http"))
                and owner not in ("router", "history", "map", "params")
            ):
                add_action(
                    trigger, f"{fn_t.rsplit('.', 1)[-1].upper()} {_normalize_url(url)}"
                )
        elif fn_t in ("useSWR", "useQuery", "useFetch") and args:
            url = _url_arg(ps, args[0])
            if url and url.startswith("/"):
                add_action("load", f"GET {_normalize_url(url)}")
        elif (
            fn_t.split(".")[-1] in ("push", "replace", "navigate", "redirect") and args
        ):
            if fn_t.split(".")[0] in (
                "router",
                "history",
                "navigate",
                "redirect",
                "navigator",
            ):
                url = _url_arg(ps, args[0])
                if url:
                    add_nav(url)
                    add_action(trigger, "", _normalize_url(url))
    for el in ps.find_all("jsx_element", "jsx_self_closing_element"):
        tag = _tag_name(ps, el)
        if tag in ("Link", "NavLink", "a", "RouterLink"):
            attrs = _attr_map(ps, el)
            href = _attr_text(ps, attrs.get("href")) or _attr_text(ps, attrs.get("to"))
            if href:
                add_nav(href)
    return actions, nav


def _screen_fields_react(ps: ParsedSource) -> list[ScreenField]:
    by_for, by_node = _label_texts(ps)
    zod = zod_schemas(ps)
    resolver_schema: str | None = None
    for call in ps.find_all("call_expression"):
        fn = call.child_by_field_name("function")
        if fn is not None and ps.text(fn) == "zodResolver":
            args = _call_args(call)
            if args and args[0].type == "identifier":
                resolver_schema = ps.text(args[0])
    zod_fields = {f["name"]: f for f in zod.get(resolver_schema or "", [])}

    fields: list[ScreenField] = []
    seen: set[str] = set()
    for el in ps.find_all("jsx_element", "jsx_self_closing_element"):
        tag = _tag_name(ps, el)
        if tag not in _CONTROL_TAGS and tag not in _UI_KIT_CONTROLS:
            continue
        attrs = _attr_map(ps, el)
        reg = _register_call(ps, el)
        name = _attr_text(ps, attrs.get("name"))
        validation: list[str] = []
        required = "required" in attrs
        if reg is not None:
            name = name or reg[0]
            validation.extend(reg[1])
            required = required or reg[2]
        if name is None:
            name = _bound_name(ps, attrs.get("value")) or _bound_name(
                ps, attrs.get("checked")
            )
        if name is None:
            name = _attr_text(ps, attrs.get("id"))
        if not name:
            continue
        input_type = _attr_text(ps, attrs.get("type")) or {
            "select": "select",
            "textarea": "textarea",
            "Select": "select",
            "Textarea": "textarea",
            "TextArea": "textarea",
            "Checkbox": "checkbox",
            "Switch": "checkbox",
        }.get(tag, "text")
        if input_type in _SKIP_INPUT_TYPES:
            continue
        for attr in _HTML_VALIDATION_ATTRS:
            if attr in attrs:
                validation.append(
                    f"{attr}={_attr_text(ps, attrs[attr]) or ''}".rstrip("=")
                )
        if "required" in attrs and "required" not in validation:
            validation.insert(0, "required")
        zf = zod_fields.get(name)
        if zf is not None:
            required = required or bool(zf["required"])
            validation.extend(r for r in zf.get("rules", []) if r not in validation)
            if zf["required"] and "required" not in validation:
                validation.insert(0, "required")
        ident = _attr_text(ps, attrs.get("id"))
        label = by_for.get(ident or "", "") or by_node.get(el.id, "")
        if not label:
            label = (
                _attr_text(ps, attrs.get("aria-label"))
                or _attr_text(ps, attrs.get("label"))
                or ""
            )
        if name in seen:
            continue
        seen.add(name)
        fields.append(
            ScreenField(
                name=name,
                input_type=input_type,
                label=label,
                required=required,
                validation=validation,
            )
        )
    return fields


def _component_names(ps: ParsedSource) -> list[str]:
    """Names of capitalised components defined in the file (declaration order)."""
    names: list[str] = []
    for node in ps.walk():
        if node.type == "function_declaration":
            n = node.child_by_field_name("name")
            if n is not None and ps.text(n)[:1].isupper():
                names.append(ps.text(n))
        elif node.type == "variable_declarator":
            n = node.child_by_field_name("name")
            v = node.child_by_field_name("value")
            if (
                n is not None
                and v is not None
                and v.type in ("arrow_function", "function_expression")
                and ps.text(n)[:1].isupper()
            ):
                names.append(ps.text(n))
    return names


def _used_components(ps: ParsedSource, own: list[str]) -> list[str]:
    imported: set[str] = set()
    for imp in ps.find_all("import_statement"):
        src = imp.child_by_field_name("source")
        spec = ps.string_value(src) if src is not None else None
        if spec and spec.startswith((".", "@/", "~/")):
            for ident in ps.find_all("identifier", node=imp):
                imported.add(ps.text(ident))
    used: list[str] = []
    for el in ps.find_all("jsx_element", "jsx_self_closing_element"):
        tag = _tag_name(ps, el)
        if tag in imported and tag[:1].isupper() and tag not in used and tag not in own:
            used.append(tag)
    return used


def _has_jsx(ps: ParsedSource) -> bool:
    return bool(ps.find_all("jsx_element", "jsx_self_closing_element"))


def _react_screen(ps: ParsedSource, rel: str, route_ref: str) -> ScreenSurface | None:
    if not _has_jsx(ps):
        return None
    fields = _screen_fields_react(ps)
    actions, nav = _react_actions(ps)
    names = _component_names(ps)
    uses = _used_components(ps, names)
    if not fields and not actions and not nav and not route_ref:
        return None
    default_name = None
    for exp in ps.find_all("export_statement"):
        if "default" in ps.text(exp)[:30]:
            for child in exp.children:
                n = (
                    child.child_by_field_name("name")
                    if child.type == "function_declaration"
                    else None
                )
                if n is not None:
                    default_name = ps.text(n)
            if default_name is None:
                ident = next((c for c in exp.children if c.type == "identifier"), None)
                default_name = ps.text(ident) if ident is not None else None
    screen_name = default_name or (names[0] if names else PurePosixPath(rel).stem)
    if screen_name in ("page", "index", "layout"):
        screen_name = PurePosixPath(rel).parent.name or screen_name
    return ScreenSurface(
        name=screen_name,
        screen_name=screen_name,
        route_ref=route_ref,
        framework="react",
        fields=fields,
        actions=actions,
        navigation_targets=nav,
        uses_components=uses,
        source_refs=[SourceRef(file_path=rel, start_line=1)],
    )


# ---------------------------------------------------------------------------
# HTML-like templates (regex)
# ---------------------------------------------------------------------------

_FORM_RE = re.compile(r"<form\b([^>]*)>(.*?)</form>", re.I | re.S)
_CONTROL_RE = re.compile(r"<(input|select|textarea)\b([^>]*?)/?>", re.I | re.S)
_ATTR_RE = re.compile(r"""([:@\w.\-]+)\s*(?:=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?""")
_LABEL_RE = re.compile(r"<label\b([^>]*)>(.*?)</label>", re.I | re.S)
_ANCHOR_RE = re.compile(r"<(?:a|router-link|RouterLink|NuxtLink|Link)\b([^>]*)>", re.I)
_SCRIPT_FETCH_RE = re.compile(
    r"""(?:fetch|axios(?:\.(?P<verb>get|post|put|delete|patch))?|\$http\.(?P<hv>get|post|put|delete|patch))\s*\(\s*(?P<q>['"`])(?P<url>[^'"`]+)(?P=q)(?P<rest>[^)]*)""",
    re.I,
)
_METHOD_IN_OPTS_RE = re.compile(r"""method\s*:\s*['"](\w+)['"]""", re.I)


def _attrs(raw: str) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for m in _ATTR_RE.finditer(raw):
        key = m.group(1)
        out[key] = (
            m.group(2)
            if m.group(2) is not None
            else (m.group(3) if m.group(3) is not None else m.group(4))
        )
    return out


def _strip_tags(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _template_screen(text: str, rel: str, route_ref: str) -> ScreenSurface | None:
    labels_for: dict[str, str] = {}
    for m in _LABEL_RE.finditer(text):
        a = _attrs(m.group(1))
        target = a.get("for") or a.get("htmlFor")
        if target:
            labels_for[target] = _strip_tags(m.group(2))
    fields: list[ScreenField] = []
    actions: list[ScreenAction] = []
    seen: set[str] = set()

    forms = list(_FORM_RE.finditer(text))
    regions = [(f.group(1), f.group(2)) for f in forms] or [("", text)]
    for form_attrs_raw, inner in regions:
        form_attrs = _attrs(form_attrs_raw)
        for cm in _CONTROL_RE.finditer(inner):
            tag = cm.group(1).lower()
            a = _attrs(cm.group(2))
            name = a.get("name") or a.get("id")
            model = (
                a.get("v-model")
                or a.get("v-model.trim")
                or a.get("bind:value")
                or a.get("x-model")
            )
            if not name and model:
                name = model.strip("{} ").split(".")[-1]
            if not name:
                continue
            itype = (
                a.get("type")
                or (
                    "select"
                    if tag == "select"
                    else "textarea"
                    if tag == "textarea"
                    else "text"
                )
            ).lower()
            if itype in _SKIP_INPUT_TYPES or itype == "hidden" or name in seen:
                continue
            seen.add(name)
            validation = ["required"] if "required" in a else []
            for attr in ("minlength", "maxlength", "min", "max", "pattern", "step"):
                if attr in a:
                    validation.append(f"{attr}={a[attr]}")
            fields.append(
                ScreenField(
                    name=name,
                    input_type=itype,
                    label=labels_for.get(a.get("id") or "", ""),
                    required="required" in a,
                    validation=validation,
                )
            )
        if forms and (
            form_attrs.get("action") is not None
            or "@submit" in form_attrs_raw
            or "v-on:submit" in form_attrs_raw
            or True
        ):
            method = (form_attrs.get("method") or "GET").upper()
            action = form_attrs.get("action") or ""
            if action:
                actions.append(
                    ScreenAction(
                        trigger="submit form",
                        api_ref=f"{method} {_normalize_url(action)}",
                    )
                )
            else:
                actions.append(ScreenAction(trigger="submit form"))
    for m in _SCRIPT_FETCH_RE.finditer(text):
        verb = (m.group("verb") or m.group("hv") or "").upper()
        if not verb:
            mm = _METHOD_IN_OPTS_RE.search(m.group("rest") or "")
            verb = mm.group(1).upper() if mm else "GET"
        url = m.group("url")
        if url.startswith(("/", "http")):
            ref = f"{verb} {_normalize_url(url)}"
            if not any(a.api_ref == ref for a in actions):
                actions.append(ScreenAction(trigger="script call", api_ref=ref))
    nav: list[str] = []
    for m in _ANCHOR_RE.finditer(text):
        a = _attrs(m.group(1))
        href = a.get("href") or a.get("to") or a.get(":to")
        if href and href.startswith("/") and _normalize_url(href) not in nav:
            nav.append(_normalize_url(href))
    if not fields and not actions and not nav and not route_ref:
        return None
    stem = PurePosixPath(rel).stem
    name = (
        stem
        if stem not in ("index", "page")
        else (PurePosixPath(rel).parent.name or stem)
    )
    framework = {".vue": "vue", ".svelte": "svelte"}.get(
        PurePosixPath(rel).suffix, "html-template"
    )
    return ScreenSurface(
        name=name,
        screen_name=name,
        route_ref=route_ref,
        framework=framework,
        fields=fields,
        actions=actions,
        navigation_targets=nav,
        source_refs=[SourceRef(file_path=rel, start_line=1)],
    )


# ---------------------------------------------------------------------------
# Field -> API -> model mapping
# ---------------------------------------------------------------------------


def _singular(word: str) -> str:
    w = word.lower()
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith("ses") or w.endswith("xes"):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _model_for_path(path: str, models: list[ModelSurface]) -> ModelSurface | None:
    segments = [
        s
        for s in re.split(r"/", path)
        if s and not s.startswith((":", "{", "<")) and s not in ("api", "v1", "v2")
    ]
    if not segments:
        return None
    key = _singular(_norm_name(segments[-1]))
    for model in models:
        if _singular(_norm_name(model.name)) == key:
            return model
    return None


def map_screen_fields(
    screens: list[ScreenSurface],
    apis: list[ApiSurface],
    models: list[ModelSurface],
) -> None:
    """Chain screen fields to API request fields and model columns, in place."""
    api_index = {(a.method.upper(), _path_key(a.path)): a for a in apis}
    for screen in screens:
        bound_apis: list[ApiSurface] = []
        for action in screen.actions:
            if not action.api_ref or " " not in action.api_ref:
                continue
            method, path = action.api_ref.split(" ", 1)
            api = api_index.get((method.upper(), _path_key(path)))
            if api is not None and api not in bound_apis:
                bound_apis.append(api)
        body_apis = [
            a for a in bound_apis if a.method.upper() in ("POST", "PUT", "PATCH")
        ]
        for f in screen.fields:
            norm = _norm_name(f.name)
            api_field: str | None = None
            api_for_field: ApiSurface | None = None
            for api in body_apis:
                for rf in (api.request_schema or {}).get("fields", []):
                    if (
                        rf.get("source") in ("body", None)
                        and _norm_name(str(rf.get("name", ""))) == norm
                    ):
                        api_field = str(rf["name"])
                        api_for_field = api
                        break
                if api_field:
                    break
            if api_field is None:
                f.gap = (
                    "no matching API request field"
                    if body_apis
                    else "screen has no mapped API submit action"
                )
                # Still try to locate a model column through any bound or guessed model.
            else:
                f.bound_api_field = (
                    f"{api_for_field.method} {api_for_field.path}#{api_field}"
                    if api_for_field
                    else api_field
                )
            model: ModelSurface | None = None
            if api_for_field is not None:
                model = _model_for_path(api_for_field.path, models)
            if model is None and bound_apis:
                model = _model_for_path(bound_apis[0].path, models)
            col = None
            if model is not None:
                col = next(
                    (mf for mf in model.fields if _norm_name(mf.name) == norm), None
                )
            if col is not None and model is not None:
                f.bound_model_field = f"{model.name}.{col.name}"
                f.mapping_confidence = "name-match"
                f.gap = "" if api_field else f.gap
            elif not f.gap:
                f.gap = "no matching model column"
            elif api_field:
                f.gap = "no matching model column"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def analyze_screens(
    workdir: Path,
    inventory: InventoryResult,
    routes: list[RouteSurface] | None = None,
    apis: list[ApiSurface] | None = None,
    models: list[ModelSurface] | None = None,
) -> list[ScreenSurface]:
    """Extract screens (fields, actions, navigation) and map fields to models."""
    route_by_file: dict[str, str] = {}
    for r in routes or []:
        for ref in r.source_refs:
            route_by_file.setdefault(ref.file_path, r.path)
    # Next.js file-system routes (the route analyzer may not list every page).
    screens: list[ScreenSurface] = []
    for entry in inventory.files:
        rel = entry.path
        suffix = PurePosixPath(rel).suffix.lower()
        if any(
            part in rel.split("/")
            for part in ("node_modules", "dist", "build", ".next")
        ):
            continue
        if (
            ".test." in rel
            or ".spec." in rel
            or "/__tests__/" in rel
            or "/tests/" in rel
        ):
            continue
        route_ref = route_by_file.get(rel, "")
        screen: ScreenSurface | None = None
        if suffix in (".tsx", ".jsx"):
            text = _read(workdir / rel)
            if text is None:
                continue
            ps = parse_source(rel, text)
            if ps is not None:
                screen = _react_screen(ps, rel, route_ref)
        elif suffix in _TEMPLATE_EXTS:
            text = _read(workdir / rel)
            if text is None:
                continue
            screen = _template_screen(text, rel, route_ref)
        if screen is not None:
            screens.append(screen)
    map_screen_fields(screens, apis or [], models or [])
    logger.info(
        "screens_analyzed",
        screens=len(screens),
        fields=sum(len(s.fields) for s in screens),
        mapped=sum(1 for s in screens for f in s.fields if f.bound_model_field),
    )
    return screens
