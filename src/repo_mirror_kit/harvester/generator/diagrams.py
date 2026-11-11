"""Mermaid state and sequence diagrams rendered from surface data (BEAN-075).

Diagrams are *renderings* of structured data, never hand-authored:

- ``stateDiagram-v2`` per :class:`WorkflowSurface` (states + labeled transitions)
- ``sequenceDiagram`` per key operation: LLM ``traced_flow`` hops when present
  (BEAN-068); otherwise the declared screen-action → API call chain, with the
  data layer shown only when the feature's model is known (labeled as inferred).

Sequence diagrams are capped (``MAX_SEQUENCE_DIAGRAMS``); anything skipped is
counted in ``diagrams/README.md`` — never silently truncated.
"""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    ModelSurface,
    ScreenSurface,
    Surface,
    SurfaceCollection,
    WorkflowSurface,
)

logger = structlog.get_logger()

DIAGRAMS_DIRNAME = "diagrams"
MAX_SEQUENCE_DIAGRAMS = 25


def _label(text: str) -> str:
    """Mermaid-safe single-line label."""
    out = re.sub(r"[^A-Za-z0-9 /{}._:>,()'-]+", " ", str(text))
    return re.sub(r"\s+", " ", out).strip().replace(":", " -") or "step"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "diagram"


def state_diagram(wf: WorkflowSurface) -> str:
    """``stateDiagram-v2`` for one workflow."""
    states: list[str] = []
    for s in [
        *wf.states,
        *(t.from_state for t in wf.transitions),
        *(t.to_state for t in wf.transitions),
    ]:
        if s != "*" and s not in states:
            states.append(s)
    ids = {s: f"S{i}" for i, s in enumerate(states, start=1)}
    lines = ["stateDiagram-v2"]
    for s in states:
        lines.append(f'    state "{_label(s)}" as {ids[s]}')
    if wf.initial_state and wf.initial_state in ids:
        lines.append(f"    [*] --> {ids[wf.initial_state]}")
    seen: set[str] = set()
    for t in wf.transitions:
        label = _label(t.trigger) if t.trigger else ""
        if t.guard:
            label = f"{label} [{_label(t.guard)}]".strip()
        sources = states if t.from_state == "*" else [t.from_state]
        for src in sources:
            if src == t.to_state and t.from_state == "*":
                continue
            edge = f"    {ids[src]} --> {ids[t.to_state]}" + (
                f": {label}" if label else ""
            )
            if edge not in seen:
                seen.add(edge)
                lines.append(edge)
    return "\n".join(lines)


def _participant_ids(names: list[str]) -> dict[str, str]:
    return {n: f"P{i}" for i, n in enumerate(dict.fromkeys(names), start=1)}


def traced_sequence(surface: Surface) -> str | None:
    """Sequence diagram from an LLM ``traced_flow`` (hop list), if any."""
    flow = surface.enrichment.get("traced_flow") if surface.enrichment else None
    if not isinstance(flow, list) or len(flow) < 2:
        return None
    hops = [h for h in flow if isinstance(h, dict) and h.get("hop")]
    if len(hops) < 2:
        return None
    names = ["User", *(str(h["hop"]) for h in hops)]
    ids = _participant_ids(names)
    lines = ["sequenceDiagram", "    actor " + f"{ids['User']} as User"]
    for n, pid in ids.items():
        if n != "User":
            lines.append(f"    participant {pid} as {_label(n)}")
    prev = "User"
    for h in hops:
        note = _label(h.get("note") or "calls")
        lines.append(f"    {ids[prev]}->>{ids[str(h['hop'])]}: {note}")
        prev = str(h["hop"])
    return "\n".join(lines)


def structural_sequence(
    screen: ScreenSurface,
    api_by_ref: dict[str, ApiSurface],
    models_by_feature: dict[str, list[ModelSurface]],
) -> list[tuple[str, str]]:
    """(title, diagram) per screen action that resolves to a known API."""
    out: list[tuple[str, str]] = []
    for action in screen.actions:
        api = api_by_ref.get(action.api_ref)
        if api is None:
            continue
        screen_name = screen.screen_name or screen.name
        names = ["User", screen_name, api.name]
        models = models_by_feature.get(api.feature_id, [])
        if models:
            names.append(models[0].entity_name or models[0].name)
        ids = _participant_ids(names)
        lines = ["sequenceDiagram", f"    actor {ids['User']} as User"]
        for n, pid in ids.items():
            if n != "User":
                lines.append(f"    participant {pid} as {_label(n)}")
        lines.append(
            f"    {ids['User']}->>{ids[screen_name]}: {_label(action.trigger)}"
        )
        lines.append(f"    {ids[screen_name]}->>{ids[api.name]}: {_label(api.name)}")
        if models:
            model_name = models[0].entity_name or models[0].name
            lines.append(
                f"    {ids[api.name]}->>{ids[model_name]}: persists or reads (inferred)"
            )
            lines.append(f"    {ids[model_name]}-->>{ids[api.name]}: result")
        lines.append(f"    {ids[api.name]}-->>{ids[screen_name]}: response")
        if action.navigation_target:
            lines.append(
                f"    {ids[screen_name]}->>{ids['User']}: navigates to {_label(action.navigation_target)}"
            )
        out.append((f"{screen_name} {action.trigger}", "\n".join(lines)))
    return out


def generate_diagrams(surfaces: SurfaceCollection, output_dir: Path) -> list[Path]:
    """Write ``<output_dir>/diagrams/``; returns created files (empty if none)."""
    api_by_ref = {f"{a.method} {a.path}": a for a in surfaces.apis}
    models_by_feature: dict[str, list[ModelSurface]] = {}
    for m in surfaces.models:
        models_by_feature.setdefault(m.feature_id, []).append(m)

    state_docs = [
        (wf, state_diagram(wf)) for wf in surfaces.workflows if wf.transitions
    ]
    seq_docs: list[tuple[str, str]] = []
    for s in surfaces:
        traced = traced_sequence(s)
        if traced:
            seq_docs.append((f"{s.name} (traced)", traced))
    for screen in surfaces.screens:
        seq_docs.extend(structural_sequence(screen, api_by_ref, models_by_feature))
    if not state_docs and not seq_docs:
        return []

    root = output_dir / DIAGRAMS_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    for stale in root.glob("*.md"):
        stale.unlink()
    written: list[Path] = []
    index: list[str] = []
    used: set[str] = set()

    def _emit(prefix: str, title: str, diagram: str) -> None:
        slug = f"{prefix}-{_slug(title)}"
        base, n = slug, 2
        while slug in used:
            slug, n = f"{base}-{n}", n + 1
        used.add(slug)
        path = root / f"{slug}.md"
        path.write_text(f"# {title}\n\n```mermaid\n{diagram}\n```\n", encoding="utf-8")
        written.append(path)
        index.append(f"- [{title}]({slug}.md)")

    for wf, diagram in state_docs:
        _emit("state", wf.name, diagram)
    shown = seq_docs[:MAX_SEQUENCE_DIAGRAMS]
    for title, diagram in shown:
        _emit("sequence", title, diagram)
    skipped = len(seq_docs) - len(shown)

    readme = root / "README.md"
    readme.write_text(
        "# Diagrams\n\nRendered from surface data (never hand-authored). "
        "Mermaid sources are embedded in each file.\n\n"
        + "\n".join(index)
        + f"\n\n_Sequence diagrams shown: {len(shown)}; skipped (cap {MAX_SEQUENCE_DIAGRAMS}): {skipped}._\n",
        encoding="utf-8",
    )
    written.append(readme)
    logger.info(
        "diagrams_written", state=len(state_docs), sequence=len(shown), skipped=skipped
    )
    return written
