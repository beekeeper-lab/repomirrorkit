"""Feature clustering (Stage C3) and build manifest (BEAN-069).

A hundred disjoint per-surface beans are not a spec. This module groups
surfaces into **features** — vertical slices such as "Order management = these
screens, endpoints, models, rules and workflow" — and emits:

- ``features/FEAT-###-<slug>.md`` — a feature-level spec linking member beans
- ``build-manifest.json`` — a machine-readable DAG of features and beans with
  ``depends_on`` edges and a topologically sorted ``build_order``

Clustering is fully deterministic (no LLM, no randomness): same input →
byte-identical manifest. Surfaces are grouped by *resource affinity* (the
noun an endpoint, model, screen or workflow is about), then merged through
explicit cross-references (screen → API calls, field → model bindings,
workflow → triggering API, rule → protected surface, seed data → model).
Cross-cutting surfaces (config, dependencies, build, auth, middleware, …) form
a ``Platform`` feature that everything else depends on; leftovers go to
``Miscellaneous``.

Dependency edges never form cycles: each edge is added only if it does not
close one, in sorted order, so the result is reproducible.
"""

from __future__ import annotations

import heapq
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
    SeedDataSurface,
    Surface,
    SurfaceCollection,
    WorkflowSurface,
)
from repo_mirror_kit.harvester.beans.templates import derive_confidence_and_gaps
from repo_mirror_kit.harvester.beans.writer import WrittenBean

logger = structlog.get_logger()

MANIFEST_SCHEMA_VERSION = "1.0"
MANIFEST_FILENAME = "build-manifest.json"
FEATURES_DIRNAME = "features"

# surface_type → build layer (lower layers are built first).
_LAYERS: dict[str, int] = {
    "dependency": 0,
    "config": 0,
    "build_deploy": 0,
    "state_mgmt": 1,
    "crosscutting": 1,
    "middleware": 1,
    "integration": 1,
    "auth": 1,
    "model": 1,
    "seed_data": 2,
    "workflow": 2,
    "business_rule": 3,
    "api": 3,
    "general_logic": 3,
    "route": 4,
    "screen": 4,
    "component": 4,
    "ui_flow": 5,
    "test_pattern": 6,
}
_PLATFORM_TYPES = frozenset(
    {
        "dependency",
        "config",
        "build_deploy",
        "state_mgmt",
        "crosscutting",
        "middleware",
        "integration",
        "auth",
        "test_pattern",
    }
)
_SUFFIXES = (
    "management",
    "controller",
    "service",
    "repository",
    "screen",
    "details",
    "detail",
    "status",
    "state",
    "schema",
    "table",
    "model",
    "items",
    "item",
    "form",
    "list",
    "page",
    "view",
    "edit",
    "new",
    "create",
    "dto",
)
_STATIC_SEGMENTS = frozenset(
    {"api", "rest", "v1", "v2", "v3", "v4", "public", "internal"}
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Feature:
    """A vertical slice of the application."""

    id: str
    name: str
    kind: str  # "domain" | "platform" | "misc"
    key: str
    members: list[Surface] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        """Filesystem-safe slug of the feature name."""
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-") or "feature"


# ---------------------------------------------------------------------------
# Resource keys
# ---------------------------------------------------------------------------


def _singular(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(("sses", "xes", "ches", "shes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith(("ss", "us", "is")) and len(word) > 3:
        return word[:-1]
    return word


def _words(text: str) -> list[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return [w for w in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if w]


def resource_key(text: str) -> str:
    """Reduce a name to the resource noun it is about (``UserForm`` → ``user``)."""
    words = _words(text)
    while len(words) > 1 and words[-1] in _SUFFIXES:
        words.pop()
    if words and words[-1] in _SUFFIXES and len(words) == 1:
        return _singular(words[0])
    return _singular("".join(words)) if words else ""


def _path_key(path: str) -> str:
    for seg in path.split("/"):
        if not seg or seg in _STATIC_SEGMENTS or seg.startswith((":", "{", "<")):
            continue
        return resource_key(seg)
    return ""


def _stem_key(file_path: str) -> str:
    stem = Path(file_path).stem
    if stem in ("index", "page", "route", "layout"):
        stem = Path(file_path).parent.name
    return resource_key(stem)


def _primary_action_ref(screen: ScreenSurface) -> str:
    """The API call that defines a screen's purpose (writes win over reads)."""
    refs = [a.api_ref for a in screen.actions if " " in a.api_ref]
    for ref in refs:
        if ref.split(" ", 1)[0] in ("POST", "PUT", "PATCH", "DELETE"):
            return ref
    return refs[0] if refs else ""


def _surface_key(s: Surface, by_name: dict[tuple[str, str], Surface]) -> str:
    if isinstance(s, ModelSurface):
        return resource_key(s.entity_name or s.name)
    if isinstance(s, ApiSurface):
        return _path_key(s.path)
    if isinstance(s, ScreenSurface):
        primary = _primary_action_ref(s)
        if primary:
            k = _path_key(primary.split(" ", 1)[1])
            if k:
                return k
        models = [
            f.bound_model_field.split(".")[0] for f in s.fields if f.bound_model_field
        ]
        if models:
            return resource_key(max(sorted(set(models)), key=models.count))
        return resource_key(s.screen_name or s.name)
    if isinstance(s, WorkflowSurface):
        return resource_key(s.entity_ref or s.name)
    if isinstance(s, SeedDataSurface):
        if s.target_model_ref:
            return resource_key(s.target_model_ref)
        model_keys = {
            resource_key(getattr(m, "entity_name", "") or m.name)
            for (t, _), m in by_name.items()
            if t == "model"
        }
        for word in _words(s.dataset_name or s.name):
            if _singular(word) in model_keys:
                return _singular(word)
        return resource_key(s.dataset_name or s.name)
    if isinstance(s, BusinessRuleSurface):
        for target in s.applies_to:
            for (_, name), other in by_name.items():
                if name == target and other is not s:
                    return _surface_key(other, by_name)
        return ""
    if s.surface_type == "route":
        path = getattr(s, "path", "") or s.name
        return _path_key(path)
    if s.source_refs:
        return _stem_key(s.source_refs[0].file_path)
    return resource_key(s.name)


# ---------------------------------------------------------------------------
# Union-find
# ---------------------------------------------------------------------------


class _UnionFind:
    def __init__(self, n: int) -> None:
        self._p = list(range(n))

    def find(self, x: int) -> int:
        while self._p[x] != x:
            self._p[x] = self._p[self._p[x]]
            x = self._p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._p[max(ra, rb)] = min(ra, rb)  # lowest index wins: deterministic


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------


def cluster_surfaces(surfaces: SurfaceCollection) -> list[Feature]:
    """Group surfaces into features and stamp ``surface.feature_id``.

    Returns features ordered: platform first, domain features alphabetical,
    miscellaneous last. Every surface is assigned to exactly one feature.
    """
    all_surfaces = list(surfaces)
    by_name: dict[tuple[str, str], Surface] = {
        (s.surface_type, s.name): s for s in all_surfaces
    }
    api_by_ref: dict[str, int] = {}
    idx = {id(s): i for i, s in enumerate(all_surfaces)}
    for s in all_surfaces:
        if isinstance(s, ApiSurface):
            api_by_ref[f"{s.method} {s.path}"] = idx[id(s)]
            api_by_ref.setdefault(s.name, idx[id(s)])

    domain = [s for s in all_surfaces if s.surface_type not in _PLATFORM_TYPES]
    uf = _UnionFind(len(all_surfaces))
    keys: dict[int, str] = {}
    first_with_key: dict[str, int] = {}
    for s in domain:
        key = _surface_key(s, by_name)
        i = idx[id(s)]
        keys[i] = key
        if key:
            if key in first_with_key:
                uf.union(first_with_key[key], i)
            else:
                first_with_key[key] = i

    # Explicit cross-references.
    for s in domain:
        i = idx[id(s)]
        if isinstance(s, ScreenSurface):
            j = api_by_ref.get(_primary_action_ref(s))
            if j is not None:
                uf.union(i, j)
        elif isinstance(s, WorkflowSurface):
            for t in s.transitions:
                j = api_by_ref.get(t.trigger_ref)
                if j is not None:
                    uf.union(i, j)
        elif isinstance(s, BusinessRuleSurface):
            for target in s.applies_to:
                for (_, name), other in by_name.items():
                    if name == target:
                        uf.union(i, idx[id(other)])
                        break

    groups: dict[int, list[Surface]] = {}
    for s in domain:
        groups.setdefault(uf.find(idx[id(s)]), []).append(s)

    features: list[Feature] = []
    misc_members: list[Surface] = []
    for root in sorted(groups):
        members = groups[root]
        core = [
            m
            for m in members
            if m.surface_type in ("model", "api", "screen", "workflow")
        ]
        if not core:
            misc_members.extend(members)
            continue
        name = _feature_name(members, keys.get(root, ""))
        features.append(
            Feature(
                id="",
                name=name,
                kind="domain",
                key=keys.get(root) or resource_key(name),
                members=members,
            )
        )
    features.sort(key=lambda f: (f.name.lower(), f.key))

    ordered: list[Feature] = []
    platform_members = [s for s in all_surfaces if s.surface_type in _PLATFORM_TYPES]
    if platform_members:
        ordered.append(
            Feature(
                id="",
                name="Platform & Configuration",
                kind="platform",
                key="platform",
                members=platform_members,
            )
        )
    ordered.extend(features)
    if misc_members:
        ordered.append(
            Feature(
                id="",
                name="Miscellaneous",
                kind="misc",
                key="misc",
                members=misc_members,
            )
        )

    for n, feat in enumerate(ordered, start=1):
        feat.id = f"FEAT-{n:03d}"
        for m in feat.members:
            m.feature_id = feat.id
    _link_features(ordered, surfaces)
    logger.info("features_clustered", features=len(ordered), surfaces=len(all_surfaces))
    return ordered


def _feature_name(members: list[Surface], key: str) -> str:
    models = sorted(
        {m.entity_name or m.name for m in members if isinstance(m, ModelSurface)}
    )
    if models:
        base = models[0]
        spaced = " ".join(w.capitalize() for w in _words(base))
        return f"{spaced} management"
    label = key or resource_key(members[0].name) or members[0].name
    return f"{' '.join(w.capitalize() for w in _words(label))} management"


# ---------------------------------------------------------------------------
# Feature dependency edges
# ---------------------------------------------------------------------------


class _Dag:
    """Cycle-safe edge store: an edge is skipped if it would close a cycle."""

    def __init__(self) -> None:
        self.edges: dict[str, set[str]] = {}

    def _reachable(self, start: str, goal: str) -> bool:
        stack, seen = [start], set()
        while stack:
            cur = stack.pop()
            if cur == goal:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(self.edges.get(cur, ()))
        return False

    def add(self, src: str, dst: str) -> bool:
        if src == dst or self._reachable(dst, src):
            return False
        self.edges.setdefault(src, set()).add(dst)
        return True


def _link_features(features: list[Feature], surfaces: SurfaceCollection) -> None:
    feat_of: dict[tuple[str, str], str] = {
        (s.surface_type, s.name): s.feature_id for s in surfaces
    }
    model_feat = {m.entity_name or m.name: m.feature_id for m in surfaces.models}
    api_feat = {f"{a.method} {a.path}": a.feature_id for a in surfaces.apis}
    pairs: set[tuple[str, str]] = set()
    platform = next((f for f in features if f.kind == "platform"), None)
    for f in features:
        if platform is not None and f.kind != "platform":
            pairs.add((f.id, platform.id))
    for m in surfaces.models:
        for rel in m.relationship_details:
            target = model_feat.get(rel.target_model)
            if target and target != m.feature_id:
                pairs.add((m.feature_id, target))
    for s in surfaces.screens:
        for a in s.actions:
            target = api_feat.get(a.api_ref)
            if target and target != s.feature_id:
                pairs.add((s.feature_id, target))
        for fld in s.fields:
            if fld.bound_model_field:
                target = model_feat.get(fld.bound_model_field.split(".")[0])
                if target and target != s.feature_id:
                    pairs.add((s.feature_id, target))
    for w in surfaces.workflows:
        for t in w.transitions:
            target = api_feat.get(t.trigger_ref)
            if target and target != w.feature_id:
                pairs.add((w.feature_id, target))
    del feat_of
    dag = _Dag()
    for src, dst in sorted(pairs):
        dag.add(src, dst)
    for f in features:
        f.depends_on = sorted(dag.edges.get(f.id, ()))


# ---------------------------------------------------------------------------
# Bean-level graph + manifest
# ---------------------------------------------------------------------------


def _bean_edges(
    surfaces: SurfaceCollection, bean_of: dict[int, WrittenBean]
) -> dict[str, list[str]]:
    """Bean-level ``depends_on`` (cycle-safe, deterministic)."""
    all_surfaces = list(surfaces)
    by_name = {(s.surface_type, s.name): s for s in all_surfaces}
    model_by_name = {m.entity_name or m.name: m for m in surfaces.models}
    api_by_ref = {f"{a.method} {a.path}": a for a in surfaces.apis}
    models_in: dict[str, list[ModelSurface]] = {}
    for m in surfaces.models:
        models_in.setdefault(m.feature_id, []).append(m)
    auth_surfaces = list(surfaces.auth)

    wanted: set[tuple[str, str]] = set()

    def link(src: Surface, dst: Surface | None) -> None:
        if dst is None or dst is src:
            return
        a, b = bean_of.get(id(src)), bean_of.get(id(dst))
        if a is not None and b is not None:
            wanted.add((a.bean_id, b.bean_id))

    for s in all_surfaces:
        if isinstance(s, ApiSurface):
            for m in models_in.get(s.feature_id, []):
                link(s, m)
            if s.auth:
                for au in auth_surfaces:
                    link(s, au)
        elif isinstance(s, ScreenSurface):
            for a in s.actions:
                link(s, api_by_ref.get(a.api_ref))
            for f in s.fields:
                if f.bound_model_field:
                    link(s, model_by_name.get(f.bound_model_field.split(".")[0]))
        elif isinstance(s, WorkflowSurface):
            for m in models_in.get(s.feature_id, []):
                link(s, m)
            for t in s.transitions:
                link(s, api_by_ref.get(t.trigger_ref))
        elif isinstance(s, BusinessRuleSurface):
            for target in s.applies_to:
                for st in ("api", "screen", "model"):
                    link(s, by_name.get((st, target)))
        elif isinstance(s, SeedDataSurface):
            link(s, model_by_name.get(s.target_model_ref))
        elif isinstance(s, ModelSurface):
            for rel in s.relationship_details:
                link(s, model_by_name.get(rel.target_model))

    dag = _Dag()
    for src, dst in sorted(wanted):
        dag.add(src, dst)
    return {k: sorted(v) for k, v in dag.edges.items()}


def _toposort(
    nodes: list[str], edges: dict[str, list[str]], priority: dict[str, tuple[int, str]]
) -> list[str]:
    """Kahn's algorithm; dependencies first; ties broken by *priority*."""
    indegree = dict.fromkeys(nodes, 0)
    dependents: dict[str, list[str]] = {n: [] for n in nodes}
    for src, dsts in edges.items():
        for dst in dsts:
            if src in indegree and dst in indegree:
                indegree[src] += 1
                dependents[dst].append(src)
    heap = [(priority[n], n) for n in nodes if indegree[n] == 0]
    heapq.heapify(heap)
    order: list[str] = []
    while heap:
        _, node = heapq.heappop(heap)
        order.append(node)
        for dep in sorted(dependents[node]):
            indegree[dep] -= 1
            if indegree[dep] == 0:
                heapq.heappush(heap, (priority[dep], dep))
    return order


def build_manifest(
    project_name: str,
    surfaces: SurfaceCollection,
    features: list[Feature],
    beans: list[WrittenBean],
) -> dict[str, Any]:
    """Assemble the build-manifest dict (see ``MANIFEST_SCHEMA``)."""
    all_surfaces = list(surfaces)
    bean_of: dict[int, WrittenBean] = {}
    for surface, bean in zip(all_surfaces, beans, strict=False):
        bean_of[id(surface)] = bean
    edges = _bean_edges(surfaces, bean_of)

    bean_entries: list[dict[str, Any]] = []
    priority: dict[str, tuple[int, str]] = {}
    for surface, bean in zip(all_surfaces, beans, strict=False):
        confidence, gaps = derive_confidence_and_gaps(surface)
        layer = _LAYERS.get(surface.surface_type, 3)
        priority[bean.bean_id] = (layer, bean.bean_id)
        bean_entries.append(
            {
                "id": bean.bean_id,
                "type": surface.surface_type,
                "title": surface.name,
                "path": f"beans/{Path(bean.path).name}",
                "feature": surface.feature_id,
                "layer": layer,
                "depends_on": edges.get(bean.bean_id, []),
                "confidence": confidence,
                "gaps": gaps,
            }
        )
    bean_order = _toposort([b["id"] for b in bean_entries], edges, priority)

    feat_edges = {f.id: list(f.depends_on) for f in features}
    feat_priority = {
        f.id: (0 if f.kind == "platform" else 2 if f.kind == "misc" else 1, f.id)
        for f in features
    }
    feature_order = _toposort([f.id for f in features], feat_edges, feat_priority)

    beans_by_feature: dict[str, list[str]] = {}
    for b in bean_entries:
        beans_by_feature.setdefault(b["feature"], []).append(b["id"])
    feature_entries = [
        {
            "id": f.id,
            "name": f.name,
            "kind": f.kind,
            "slug": f.slug,
            "path": f"{FEATURES_DIRNAME}/{f.id}-{f.slug}.md",
            "beans": beans_by_feature.get(f.id, []),
            "depends_on": f.depends_on,
        }
        for f in features
    ]
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "project": project_name,
        "features": feature_entries,
        "beans": bean_entries,
        "build_order": {"features": feature_order, "beans": bean_order},
    }


MANIFEST_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "RepoMirrorKit build manifest",
    "type": "object",
    "required": ["schema_version", "project", "features", "beans", "build_order"],
    "properties": {
        "schema_version": {"const": MANIFEST_SCHEMA_VERSION},
        "project": {"type": "string"},
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "id",
                    "name",
                    "kind",
                    "slug",
                    "path",
                    "beans",
                    "depends_on",
                ],
                "properties": {
                    "id": {"type": "string", "pattern": "^FEAT-\\d{3}$"},
                    "name": {"type": "string"},
                    "kind": {"enum": ["domain", "platform", "misc"]},
                    "slug": {"type": "string"},
                    "path": {"type": "string"},
                    "beans": {"type": "array", "items": {"type": "string"}},
                    "depends_on": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "beans": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "id",
                    "type",
                    "title",
                    "path",
                    "feature",
                    "layer",
                    "depends_on",
                    "confidence",
                    "gaps",
                ],
                "properties": {
                    "id": {"type": "string", "pattern": "^BEAN-\\d+$"},
                    "type": {"type": "string"},
                    "title": {"type": "string"},
                    "path": {"type": "string"},
                    "feature": {"type": "string"},
                    "layer": {"type": "integer"},
                    "depends_on": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "string"},
                    "gaps": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "build_order": {
            "type": "object",
            "required": ["features", "beans"],
            "properties": {
                "features": {"type": "array", "items": {"type": "string"}},
                "beans": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Feature markdown
# ---------------------------------------------------------------------------


def _criteria(feature: Feature) -> list[str]:
    lines: list[str] = []
    for m in feature.members:
        if isinstance(m, ApiSurface):
            required = [
                f["name"]
                for f in (m.request_schema or {}).get("fields", [])
                if f.get("required") and f.get("source") == "body"
            ]
            status = (m.response_schema or {}).get("status") or (
                "201" if m.method == "POST" else "200"
            )
            req = (
                f" with required body fields {', '.join(f'`{r}`' for r in required)}"
                if required
                else ""
            )
            lines.append(
                f"- [ ] `{m.method} {m.path}` accepts requests{req} and responds `{status}`."
            )
        elif isinstance(m, ScreenSurface) and (m.fields or m.actions):
            names = ", ".join(f"`{f.name}`" for f in m.fields) or "no input fields"
            lines.append(f"- [ ] Screen **{m.screen_name}** presents {names}.")
        elif isinstance(m, BusinessRuleSurface):
            lines.append(f"- [ ] {m.expression}.")
        elif isinstance(m, WorkflowSurface):
            trans = "; ".join(
                f"{t.from_state}→{t.to_state}" for t in m.transitions[:12]
            )
            lines.append(f"- [ ] **{m.name}** allows only: {trans}.")
    return lines


def render_feature(
    feature: Feature,
    beans_by_surface: dict[int, WrittenBean],
    names: dict[str, tuple[str, str]],
) -> str:
    """Render one ``FEAT-###`` markdown file."""
    by_type: dict[str, list[Surface]] = {}
    for m in feature.members:
        by_type.setdefault(m.surface_type, []).append(m)
    counts = ", ".join(f"{len(v)} {t}" for t, v in sorted(by_type.items()))
    deps = (
        ", ".join(f"[{d}]({d}) {names.get(d, '')}".strip() for d in feature.depends_on)
        or "none"
    )
    lines = [
        "---",
        f"id: {feature.id}",
        f"name: {json.dumps(feature.name)}",
        f"kind: {feature.kind}",
        f"depends_on: {json.dumps(feature.depends_on)}",
        "---",
        f"# {feature.id}: {feature.name}",
        "",
        "## Overview",
        "",
        f"- Members: {len(feature.members)} surfaces ({counts})",
        f"- Depends on: {deps}",
        "",
    ]
    summaries = [
        (m, str(m.enrichment.get("behavioral_description", "")).strip().split("\n")[0])
        for m in feature.members
        if m.enrichment.get("behavioral_description")
    ]
    if summaries:
        lines += ["## Behavior summary", ""]
        lines += [f"- **{m.name}**: {text}" for m, text in summaries[:20]]
        lines.append("")
    lines += [
        "## Member beans",
        "",
        "| Bean | Type | Title | Confidence |",
        "|------|------|-------|-----------|",
    ]
    for m in sorted(
        feature.members,
        key=lambda s: (_LAYERS.get(s.surface_type, 3), s.surface_type, s.name),
    ):
        bean = beans_by_surface.get(id(m))
        confidence, _ = derive_confidence_and_gaps(m)
        ref = f"[{bean.bean_id}](../beans/{Path(bean.path).name})" if bean else "-"
        lines.append(f"| {ref} | {m.surface_type} | {m.name} | {confidence} |")
    criteria = _criteria(feature)
    lines += ["", "## Feature-level acceptance criteria", ""]
    lines += criteria or ["- [ ] Member bean acceptance criteria are all satisfied."]
    lines.append("")
    return "\n".join(lines)


def write_features_and_manifest(
    output_dir: Path,
    project_name: str,
    surfaces: SurfaceCollection,
    features: list[Feature],
    beans: list[WrittenBean],
) -> Path:
    """Write ``features/*.md`` and ``build-manifest.json``; return manifest path."""
    features_dir = output_dir / FEATURES_DIRNAME
    features_dir.mkdir(parents=True, exist_ok=True)
    for stale in features_dir.glob("FEAT-*.md"):
        stale.unlink()
    beans_by_surface = {id(s): b for s, b in zip(list(surfaces), beans, strict=False)}
    names = {f.id: (f.name, f.slug) for f in features}
    for f in features:
        (features_dir / f"{f.id}-{f.slug}.md").write_text(
            render_feature(f, beans_by_surface, names), encoding="utf-8"
        )
    manifest = build_manifest(project_name, surfaces, features, beans)
    path = output_dir / MANIFEST_FILENAME
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    logger.info(
        "build_manifest_written",
        features=len(features),
        beans=len(beans),
        path=str(path),
    )
    return path
