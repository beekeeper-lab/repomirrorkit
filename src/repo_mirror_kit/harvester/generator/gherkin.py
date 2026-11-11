"""Gherkin ``.feature`` generation per feature cluster (BEAN-074).

Beans carry acceptance criteria as prose; Gherkin is the framework-neutral,
machine-parseable form — and the parity suite for a rebuilt application: run
the same scenarios against original and rebuild and "functional replacement"
becomes a pass rate.

One ``<out>/gherkin/FEAT-###-<slug>.feature`` per feature cluster (BEAN-069).
Scenarios come from:

- LLM enrichment ``given_when_then`` triples on member beans, when present;
- API contracts (success path, missing/invalid input → rejection, auth);
- business rules (validation / invariant / permission);
- workflow transitions (allowed transition + invalid-source outline);
- screens (fields presented, submit calls the operation).

Every scenario is tagged ``@BEAN-###`` (traceability), ``@FEAT-###`` and
``@generated``; scenarios built from unknown/low-confidence data also get
``@gap``. Steps are behavior-only — HTTP operations and domain terms, never
selectors, file paths or framework calls — so they bind to any target stack.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    BusinessRuleSurface,
    ModelSurface,
    ScreenSurface,
    Surface,
    SurfaceCollection,
    WorkflowSurface,
)
from repo_mirror_kit.harvester.beans.writer import WrittenBean
from repo_mirror_kit.harvester.generator.openapi import normalize_path

logger = structlog.get_logger()

GHERKIN_DIRNAME = "gherkin"


@dataclass
class _Scenario:
    title: str
    steps: list[tuple[str, str]]  # (keyword, text)
    tags: list[str]
    examples: list[tuple[str, list[str]]] | None = None  # (column, values) for outlines
    key: str = field(default="", repr=False)


def _clean(text: str) -> str:
    """Single line, no table/placeholder/comment hazards."""
    out = re.sub(r"\s+", " ", str(text)).strip()
    out = out.replace("|", "/")
    return out


def _op(method: str, path: str) -> str:
    return f"{method.upper()} {normalize_path(path)}"


def _tags(bean: WrittenBean | None, feat: str, gap: bool = False) -> list[str]:
    tags = [f"@{bean.bean_id}"] if bean is not None else []
    tags += [f"@{feat}", "@generated"]
    if gap:
        tags.append("@gap")
    return tags


def _dedupe(scenarios: list[_Scenario]) -> list[_Scenario]:
    seen: set[str] = set()
    out: list[_Scenario] = []
    for sc in scenarios:
        key = sc.key or "|".join(f"{k}:{t.lower()}" for k, t in sc.steps)
        if key in seen:
            continue
        seen.add(key)
        out.append(sc)
    return out


# ---------------------------------------------------------------------------
# Scenario builders
# ---------------------------------------------------------------------------


def _api_scenarios(
    api: ApiSurface, bean: WrittenBean | None, feat: str
) -> list[_Scenario]:
    op = _op(api.method, api.path)
    req = api.request_schema or {}
    resp = api.response_schema or {}
    unknown = (
        not req or not resp or req.get("unknown") is True or resp.get("unknown") is True
    )
    given = "the service is running" + (
        " and the client is authenticated" if api.auth else ""
    )
    body_required = [
        f["name"]
        for f in req.get("fields", [])
        if f.get("required") and f.get("source") == "body"
    ]
    body_all = [f["name"] for f in req.get("fields", []) if f.get("source") == "body"]
    status = int(resp.get("status") or (201 if api.method == "POST" else 200))
    steps: list[tuple[str, str]] = [("Given", given)]
    if body_all:
        supplied = ", ".join(f'"{n}"' for n in (body_required or body_all))
        steps.append(("When", f"the client sends {op} with {supplied}"))
    else:
        steps.append(("When", f"the client sends {op}"))
    steps.append(("Then", f"the response status is {status}"))
    resp_fields = [f["name"] for f in resp.get("fields", [])]
    if resp_fields:
        shape = "each item" if resp.get("is_array") else "the body"
        steps.append(
            ("And", f"{shape} contains " + ", ".join(f'"{n}"' for n in resp_fields))
        )
    out = [
        _Scenario(
            title=f"{op} succeeds",
            steps=steps,
            tags=_tags(bean, feat, gap=unknown),
        )
    ]
    for name in body_required:
        out.append(
            _Scenario(
                title=f"{op} rejects a missing {name}",
                steps=[
                    ("Given", given),
                    ("When", f'the client sends {op} without "{name}"'),
                    ("Then", "the request is rejected with a client error"),
                ],
                tags=_tags(bean, feat),
            )
        )
    if api.auth:
        out.append(
            _Scenario(
                title=f"{op} requires authentication",
                steps=[
                    ("Given", "the client is not authenticated"),
                    ("When", f"the client sends {op}"),
                    ("Then", "the request is rejected as unauthorized"),
                ],
                tags=_tags(bean, feat),
            )
        )
    for err in resp.get("errors", []):
        code = err.get("status")
        if isinstance(code, int):
            out.append(
                _Scenario(
                    title=f"{op} can respond {code}",
                    steps=[
                        ("Given", given),
                        ("When", f"the client sends {op} in a way the service rejects"),
                        ("Then", f"the response status is {code}"),
                    ],
                    tags=_tags(bean, feat),
                )
            )
    return out


def _rule_scenarios(
    rule: BusinessRuleSurface, bean: WrittenBean | None, feat: str
) -> list[_Scenario]:
    expr = _clean(rule.expression)
    # "<op> body field 'x': required" is already covered by the API's own
    # "rejects a missing x" scenario — skip the near-duplicate.
    if (
        rule.rule_kind == "validation"
        and " body field '" in expr
        and expr.endswith(": required")
    ):
        return []
    if rule.rule_kind == "validation":
        return [
            _Scenario(
                title=f"Rule: {expr}",
                steps=[
                    ("Given", "the service is running"),
                    ("When", f'input violates the rule "{expr}"'),
                    ("Then", "the input is rejected with a validation error"),
                ],
                tags=_tags(bean, feat, gap=rule.confidence != "declared"),
            )
        ]
    if rule.rule_kind == "invariant":
        return [
            _Scenario(
                title=f"Invariant: {expr}",
                steps=[
                    ("Given", "the service is running"),
                    ("When", f'a change would violate "{expr}"'),
                    ("Then", "the change is rejected and stored data is unchanged"),
                ],
                tags=_tags(bean, feat),
            )
        ]
    if rule.rule_kind == "permission":
        return [
            _Scenario(
                title=f"Permission: {expr}",
                steps=[
                    ("Given", "a client without the required permission"),
                    ("When", f'the client attempts the operation guarded by "{expr}"'),
                    ("Then", "access is denied"),
                ],
                tags=_tags(bean, feat),
            )
        ]
    return []


def _workflow_scenarios(
    wf: WorkflowSurface, bean: WrittenBean | None, feat: str
) -> list[_Scenario]:
    out: list[_Scenario] = []
    entity = _clean(wf.entity_ref or wf.name)
    by_trigger: dict[str, set[str]] = {}
    for t in wf.transitions:
        by_trigger.setdefault(t.trigger or f"{t.from_state}->{t.to_state}", set()).add(
            t.from_state
        )
    for t in wf.transitions:
        how = (
            f" via {_op(*t.trigger_ref.split(' ', 1))}"
            if " " in t.trigger_ref
            else (f' via "{_clean(t.trigger)}"' if t.trigger else "")
        )
        src = "any state" if t.from_state == "*" else f'state "{_clean(t.from_state)}"'
        steps = [
            ("Given", f"a {entity} entity in {src}"),
            ("When", f'the transition to "{_clean(t.to_state)}" is requested{how}'),
            ("Then", f'the {entity} entity is in state "{_clean(t.to_state)}"'),
        ]
        if t.guard:
            steps.insert(1, ("And", f"the condition holds: {_clean(t.guard)}"))
        out.append(
            _Scenario(
                title=f"{entity}: {t.from_state} to {t.to_state}",
                steps=steps,
                tags=_tags(
                    bean, feat, gap=wf.confidence != "declared" and t.from_state == "*"
                ),
            )
        )
    # Invalid-source outlines: per trigger with explicit sources.
    for trigger, sources in sorted(by_trigger.items()):
        if "*" in sources or not wf.states:
            continue
        invalid = [s for s in wf.states if s not in sources][:6]
        if not invalid:
            continue
        target = next(
            t.to_state
            for t in wf.transitions
            if (t.trigger or f"{t.from_state}->{t.to_state}") == trigger
        )
        out.append(
            _Scenario(
                title=f"{entity}: {trigger} is rejected from other states",
                steps=[
                    ("Given", f'a {entity} entity in state "<state>"'),
                    ("When", f'the transition to "{_clean(target)}" is requested'),
                    ("Then", "the transition is rejected"),
                    ("And", 'the state remains "<state>"'),
                ],
                tags=_tags(bean, feat),
                examples=[("state", [_clean(s) for s in invalid])],
                key=f"outline:{entity}:{trigger}",
            )
        )
    return out


def _screen_scenarios(
    screen: ScreenSurface, bean: WrittenBean | None, feat: str
) -> list[_Scenario]:
    if not screen.fields and not screen.actions:
        return []
    name = _clean(screen.screen_name or screen.name)
    where = f" at {normalize_path(screen.route_ref)}" if screen.route_ref else ""
    out: list[_Scenario] = []
    if screen.fields:
        names = ", ".join(f'"{_clean(f.name)}"' for f in screen.fields)
        out.append(
            _Scenario(
                title=f"{name} screen presents its fields",
                steps=[
                    ("Given", f"a user opens the {name} screen{where}"),
                    ("Then", f"the screen presents inputs for {names}"),
                ],
                tags=_tags(bean, feat),
            )
        )
        required = [f for f in screen.fields if f.required]
        for f in required:
            out.append(
                _Scenario(
                    title=f"{name} requires {f.name}",
                    steps=[
                        ("Given", f"a user opens the {name} screen{where}"),
                        ("When", f'the user submits without "{_clean(f.name)}"'),
                        ("Then", "submission is blocked with a validation message"),
                    ],
                    tags=_tags(bean, feat),
                )
            )
    for a in screen.actions:
        if a.api_ref:
            method, _, path = a.api_ref.partition(" ")
            out.append(
                _Scenario(
                    title=f"{name} performs {_op(method, path)}",
                    steps=[
                        ("Given", f"a user opens the {name} screen{where}"),
                        (
                            "When",
                            f'the user triggers "{_clean(a.trigger)}" with valid values',
                        ),
                        ("Then", f"the operation {_op(method, path)} is invoked"),
                    ],
                    tags=_tags(bean, feat),
                )
            )
    return out


def _model_scenarios(
    model: ModelSurface, bean: WrittenBean | None, feat: str
) -> list[_Scenario]:
    out: list[_Scenario] = []
    name = _clean(model.entity_name or model.name)
    for f in model.fields:
        if "unique" in f.constraints:
            out.append(
                _Scenario(
                    title=f"{name}.{f.name} must be unique",
                    steps=[
                        ("Given", f'a {name} exists with a given "{f.name}"'),
                        ("When", f'another {name} is created with the same "{f.name}"'),
                        ("Then", "creation is rejected"),
                    ],
                    tags=_tags(bean, feat),
                )
            )
    return out


def _enrichment_scenarios(
    surface: Surface, bean: WrittenBean | None, feat: str
) -> list[_Scenario]:
    out: list[_Scenario] = []
    triples = surface.enrichment.get("given_when_then") if surface.enrichment else None
    for i, t in enumerate(triples if isinstance(triples, list) else [], start=1):
        if not isinstance(t, dict):
            continue
        g, w, th = (_clean(t.get(k, "")) for k in ("given", "when", "then"))
        if not (g and w and th):
            continue
        out.append(
            _Scenario(
                title=f"{_clean(surface.name)} (scenario {i})",
                steps=[("Given", g), ("When", w), ("Then", th)],
                tags=_tags(bean, feat),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_feature_file(feature_id: str, name: str, scenarios: list[_Scenario]) -> str:
    """Render one ``.feature`` document."""
    lines = [
        f"@{feature_id} @generated",
        f"Feature: {_clean(name)}",
        f"  Behavior of {_clean(name)} derived by RepoMirrorKit ({feature_id}).",
        "  Scenarios are tagged with the bean they trace to; @gap marks low-confidence ones.",
    ]
    for sc in scenarios:
        lines.append("")
        lines.append("  " + " ".join(sc.tags))
        kind = "Scenario Outline" if sc.examples else "Scenario"
        lines.append(f"  {kind}: {_clean(sc.title)}")
        for kw, text in sc.steps:
            lines.append(f"    {kw} {text}")
        if sc.examples:
            col, values = sc.examples[0]
            lines.append("")
            lines.append("    Examples:")
            lines.append(f"      | {col} |")
            lines.extend(f"      | {v} |" for v in values)
    return "\n".join(lines) + "\n"


def generate_gherkin(
    surfaces: SurfaceCollection,
    output_dir: Path,
    beans: list[WrittenBean] | None,
) -> list[Path]:
    """Write ``<output_dir>/gherkin/*.feature``; return created files."""
    manifest_path = output_dir / "build-manifest.json"
    if beans is None or not manifest_path.is_file():
        return []
    try:
        manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    features = {f["id"]: f for f in manifest.get("features", [])}
    all_surfaces = list(surfaces)
    bean_of = {id(s): b for s, b in zip(all_surfaces, beans, strict=False)}

    by_feature: dict[str, list[Surface]] = {}
    for s in all_surfaces:
        by_feature.setdefault(s.feature_id, []).append(s)

    root = output_dir / GHERKIN_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    for stale in root.glob("*.feature"):
        stale.unlink()
    written: list[Path] = []
    for fid in sorted(features):
        feat = features[fid]
        scenarios: list[_Scenario] = []
        for s in by_feature.get(fid, []):
            bean = bean_of.get(id(s))
            scenarios.extend(_enrichment_scenarios(s, bean, fid))
            if isinstance(s, ApiSurface):
                scenarios.extend(_api_scenarios(s, bean, fid))
            elif isinstance(s, BusinessRuleSurface):
                scenarios.extend(_rule_scenarios(s, bean, fid))
            elif isinstance(s, WorkflowSurface):
                scenarios.extend(_workflow_scenarios(s, bean, fid))
            elif isinstance(s, ScreenSurface):
                scenarios.extend(_screen_scenarios(s, bean, fid))
            elif isinstance(s, ModelSurface):
                scenarios.extend(_model_scenarios(s, bean, fid))
        scenarios = _dedupe(scenarios)
        if not scenarios:
            continue
        path = root / f"{fid}-{feat['slug']}.feature"
        path.write_text(
            render_feature_file(fid, feat["name"], scenarios), encoding="utf-8"
        )
        written.append(path)
    logger.info("gherkin_written", files=len(written), path=str(root))
    return written
