"""Business-rule mining from declarative sources (BEAN-065).

Rules *are* the requirements: validation constraints, data invariants and
permission checks. This pass reads what earlier analyzers already extracted —
API request-field constraints (zod / class-validator / Pydantic), screen field
validation, model constraints (NOT NULL / UNIQUE / length / PK), and auth
requirements — and restates each as a framework-neutral
:class:`BusinessRuleSurface` linked to the surface it protects.

Imperative logic buried in function bodies is out of scope (agentic
enrichment's job); everything emitted here is ``declared`` or ``inferred``
from a declaration, never guessed.
"""

from __future__ import annotations

import re

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    BusinessRuleSurface,
    ModelSurface,
    ScreenSurface,
    SourceRef,
    SurfaceCollection,
)

logger = structlog.get_logger()

_NUMERIC = {"number", "integer", "int", "float", "decimal", "bigint"}


def _is_numeric(field_type: str) -> bool:
    return field_type.lower().strip() in _NUMERIC or field_type.lower().startswith(
        ("int", "float", "number", "decimal")
    )


def neutral_rule(raw: str, field_type: str = "") -> str | None:
    """Translate one library/HTML constraint into a neutral phrase.

    Returns None for tokens that carry no constraint (``IsString()``,
    ``optional``) — those are type information, not rules.
    """
    text = raw.strip().lstrip(".@")
    numeric = _is_numeric(field_type)

    def arg(pattern: str) -> str | None:
        m = re.search(pattern, text)
        return m.group(1).strip().strip("'\"") if m else None

    low = text.lower()
    # key=value forms (HTML attrs, pydantic kwargs)
    kv = re.match(r"^(\w+)=(.*)$", text)
    if kv:
        key, val = kv.group(1).lower(), kv.group(2).strip().strip("'\"")
        table = {
            "minlength": f"minimum length {val}",
            "min_length": f"minimum length {val}",
            "maxlength": f"maximum length {val}",
            "max_length": f"maximum length {val}",
            "min": f"minimum value {val}",
            "max": f"maximum value {val}",
            "ge": f"minimum value {val}",
            "gt": f"greater than {val}",
            "le": f"maximum value {val}",
            "lt": f"less than {val}",
            "pattern": f"must match pattern {val}",
            "regex": f"must match pattern {val}",
            "multiple_of": f"must be a multiple of {val}",
            "min_items": f"at least {val} items",
            "max_items": f"at most {val} items",
            "step": f"step {val}",
        }
        return table.get(key)
    if low in ("required", "isnotempty()", "nonempty()", "notnull", "not_null"):
        return "required"
    if low.startswith(("min(", "minlength(")):
        n = arg(r"\(([^)]*)\)")
        if low.startswith("minlength(") or (
            not numeric and field_type.lower() in ("string", "str", "")
        ):
            return (
                f"minimum length {n}"
                if low.startswith("minlength(") or field_type
                else f"minimum {n}"
            )
        return f"minimum value {n}"
    if low.startswith(("max(", "maxlength(")):
        n = arg(r"\(([^)]*)\)")
        if low.startswith("maxlength(") or (
            not numeric and field_type.lower() in ("string", "str")
        ):
            return f"maximum length {n}"
        return f"maximum value {n}"
    if low.startswith("length("):
        n = arg(r"\(([^)]*)\)")
        return f"length {n}"
    if low.startswith("email") or low.startswith("isemail"):
        return "must be a valid email address"
    if low.startswith(("url(", "isurl")):
        return "must be a valid URL"
    if low.startswith(("uuid(", "isuuid")):
        return "must be a UUID"
    if low.startswith(("int(", "isint")):
        return "must be an integer"
    if low.startswith(("positive(", "ispositive")):
        return "must be positive"
    if low.startswith(("nonnegative(", "isnotnegative")):
        return "must not be negative"
    if low.startswith(("regex(", "matches(")):
        return f"must match pattern {arg(r'\\(([^)]*)\\)')}"
    if low.startswith("isenum("):
        return f"must be one of enum {arg(r'\\(([^)]*)\\)')}"
    if low.startswith(("startswith(", "endswith(", "includes(")):
        return f"must satisfy {text}"
    if low.startswith("custom") or low.startswith("validate"):
        return "custom validation function"
    return None


def _rule(
    kind: str,
    expression: str,
    applies_to: list[str],
    library: str,
    confidence: str,
    refs: list[SourceRef],
    subject: str,
) -> BusinessRuleSurface:
    return BusinessRuleSurface(
        name=f"{subject}: {expression}",
        rule_kind=kind,
        expression=f"{subject}: {expression}",
        applies_to=applies_to,
        source_library=library,
        confidence=confidence,
        source_refs=list(refs),
    )


def _api_rules(api: ApiSurface) -> list[BusinessRuleSurface]:
    out: list[BusinessRuleSurface] = []
    schema = api.request_schema or {}
    confidence = str(schema.get("confidence") or "inferred")
    for f in schema.get("fields", []):
        subject = (
            f"{api.method} {api.path} {f.get('source', 'body')} field '{f['name']}'"
        )
        if f.get("required") and f.get("source") in ("body", "path"):
            out.append(
                _rule(
                    "validation",
                    "required",
                    [api.name],
                    "contract",
                    confidence,
                    api.source_refs,
                    subject,
                )
            )
        for raw in f.get("rules", []):
            phrase = neutral_rule(raw, str(f.get("type", "")))
            if phrase and phrase != "required":
                out.append(
                    _rule(
                        "validation",
                        phrase,
                        [api.name],
                        "validation-library",
                        "declared",
                        api.source_refs,
                        subject,
                    )
                )
    if api.auth:
        out.append(
            _rule(
                "permission",
                "authentication required",
                [api.name],
                "route-auth",
                "declared",
                api.source_refs,
                f"{api.method} {api.path}",
            )
        )
    return out


def _screen_rules(screen: ScreenSurface) -> list[BusinessRuleSurface]:
    out: list[BusinessRuleSurface] = []
    for f in screen.fields:
        subject = f"screen {screen.screen_name} field '{f.name}'"
        seen: set[str] = set()
        for raw in f.validation:
            phrase = neutral_rule(raw, f.input_type)
            if phrase and phrase not in seen:
                seen.add(phrase)
                out.append(
                    _rule(
                        "validation",
                        phrase,
                        [screen.name],
                        "form-validation",
                        "declared",
                        screen.source_refs,
                        subject,
                    )
                )
        if f.required and "required" not in seen:
            out.append(
                _rule(
                    "validation",
                    "required",
                    [screen.name],
                    "form-validation",
                    "declared",
                    screen.source_refs,
                    subject,
                )
            )
        if (
            f.input_type in ("email", "url", "tel")
            and f"must be a valid {f.input_type}" not in seen
        ):
            out.append(
                _rule(
                    "validation",
                    f"input type {f.input_type}",
                    [screen.name],
                    "form-validation",
                    "declared",
                    screen.source_refs,
                    subject,
                )
            )
    return out


def _model_rules(model: ModelSurface) -> list[BusinessRuleSurface]:
    out: list[BusinessRuleSurface] = []
    for f in model.fields:
        subject = f"{model.name}.{f.name}"
        for c in f.constraints:
            if c == "primary_key":
                phrase = "primary key (unique, identifies the record)"
            elif c == "not_null":
                phrase = "required (cannot be null)"
            elif c == "unique":
                phrase = "must be unique"
            else:
                phrase = neutral_rule(c, f.field_type) or ""
                if not phrase:
                    continue
            out.append(
                _rule(
                    "invariant",
                    phrase,
                    [model.name],
                    "data-model",
                    "declared",
                    model.source_refs,
                    subject,
                )
            )
    return out


def analyze_business_rules(surfaces: SurfaceCollection) -> list[BusinessRuleSurface]:
    """Mine business rules from already-extracted surfaces.

    Args:
        surfaces: Collection with APIs, models and screens populated.

    Returns:
        Deduplicated rules, each linked to at least one existing surface.
    """
    rules: list[BusinessRuleSurface] = []
    for api in surfaces.apis:
        rules.extend(_api_rules(api))
    for screen in surfaces.screens:
        rules.extend(_screen_rules(screen))
    for model in surfaces.models:
        rules.extend(_model_rules(model))

    seen: set[tuple[str, str]] = set()
    unique: list[BusinessRuleSurface] = []
    for rule in rules:
        key = (rule.rule_kind, rule.expression)
        if key in seen:
            continue
        seen.add(key)
        unique.append(rule)
    logger.info(
        "business_rules_mined",
        total=len(unique),
        kinds=sorted({r.rule_kind for r in unique}),
    )
    return unique
