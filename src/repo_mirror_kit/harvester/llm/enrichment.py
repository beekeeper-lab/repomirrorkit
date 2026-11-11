"""LLM enrichment orchestrator for surfaces."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    Surface,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.llm.agent import parse_agent_json, run_agent
from repo_mirror_kit.harvester.llm.prompts import (
    SYSTEM_PROMPT,
    build_agent_prompt,
    build_enrichment_prompt,
)
from repo_mirror_kit.harvester.llm.tools import RepoTools

logger = structlog.get_logger()

# Re-export availability check
try:
    from repo_mirror_kit.harvester.llm.client import HAS_ANTHROPIC
except ImportError:
    HAS_ANTHROPIC = False


def enrich_surfaces(
    surfaces: SurfaceCollection,
    config: HarvestConfig,
    workdir: Path,
    callback: Callable[..., Any] | None = None,
) -> SurfaceCollection:
    """Enrich all surfaces with LLM-generated behavioral descriptions.

    If LLM is not enabled or anthropic is not installed, returns surfaces unchanged.

    Args:
        surfaces: The surface collection to enrich.
        config: Harvest configuration with LLM settings.
        workdir: Repository working directory for reading source files.
        callback: Optional progress callback.

    Returns:
        The same SurfaceCollection with enrichment dicts populated.
    """
    if not config.llm_enabled:
        logger.info("llm_enrichment_skipped", reason="llm_not_enabled")
        return surfaces

    if not HAS_ANTHROPIC:
        logger.warning("llm_enrichment_skipped", reason="anthropic_not_installed")
        return surfaces

    if not config.llm_api_key and not config.llm_base_url:
        logger.warning("llm_enrichment_skipped", reason="no_api_key")
        return surfaces

    from repo_mirror_kit.harvester.llm.client import LLMClient

    client = LLMClient(
        api_key=config.llm_api_key,
        model=config.llm_model,
        base_url=config.llm_base_url,
    )
    return enrich_with_client(surfaces, config, workdir, client, callback)


def enrich_with_client(
    surfaces: SurfaceCollection,
    config: HarvestConfig,
    workdir: Path,
    client: Any,
    callback: Callable[..., Any] | None = None,
) -> SurfaceCollection:
    """Enrichment loop over an already-built client (injectable for tests)."""
    all_surfaces = list(surfaces)
    total = len(all_surfaces)
    telemetry = _Telemetry(model=getattr(client, "model", config.llm_model))
    price = _price_for(client, config)
    tools = RepoTools(workdir)
    agentic = config.llm_agentic and hasattr(client, "create_message")
    neighbors = _neighbor_index(all_surfaces) if agentic else {}
    spent = 0.0

    for i, surface in enumerate(all_surfaces):
        record = telemetry.start(surface)
        if config.llm_budget_usd > 0 and spent >= config.llm_budget_usd:
            record["status"] = "skipped_budget"
            telemetry.add(record)
            continue
        before_in, before_out = client.total_input_tokens, client.total_output_tokens
        try:
            if agentic:
                try:
                    _enrich_agentic(
                        surface, client, workdir, tools, neighbors, config, record
                    )
                except Exception:
                    logger.warning(
                        "llm_agentic_failed_falling_back",
                        surface_name=surface.name,
                        exc_info=True,
                    )
                    record["fallback"] = "single_shot"
                    _enrich_single_surface(surface, client, workdir)
                    record["status"] = "ok_single_shot"
            else:
                _enrich_single_surface(surface, client, workdir)
                record["status"] = "ok_single_shot"
        except Exception:
            logger.warning(
                "llm_enrichment_failed",
                surface_name=surface.name,
                surface_type=surface.surface_type,
                exc_info=True,
            )
            record["status"] = "failed"
        used_in = client.total_input_tokens - before_in
        used_out = client.total_output_tokens - before_out
        record["input_tokens"] = used_in
        record["output_tokens"] = used_out
        record["est_cost_usd"] = round(
            (used_in * price[0] + used_out * price[1]) / 1_000_000, 6
        )
        spent += float(record["est_cost_usd"])
        telemetry.add(record)

        if callback is not None and (i + 1) % 5 == 0:
            from repo_mirror_kit.harvester.pipeline import (
                PipelineEvent,
                PipelineEventType,
            )

            callback(
                PipelineEvent(
                    event_type=PipelineEventType.PROGRESS_UPDATE,
                    stage="C2",
                    message=f"Enriched {i + 1}/{total} surfaces",
                )
            )

    summary = telemetry.summary(spent, config.llm_budget_usd, price)
    logger.info("llm_enrichment_complete", **summary)
    # Pipeline layout is <out>/repo (the clone) beside <out>/reports.
    if workdir.name == "repo":
        telemetry.write(workdir.parent / "reports", summary)
    return surfaces


# Estimated $/MTok (input, output) for budgeting only — assumptions, not a
# billing source of truth. Local endpoints cost nothing.
_ASSUMED_PRICE_PER_MTOK = (3.0, 15.0)


def _price_for(client: Any, config: HarvestConfig) -> tuple[float, float]:
    if getattr(client, "is_local", False) or config.llm_base_url:
        return (0.0, 0.0)
    return _ASSUMED_PRICE_PER_MTOK


class _Telemetry:
    """Per-surface and per-run enrichment telemetry (reports/enrichment-telemetry.json)."""

    def __init__(self, model: str) -> None:
        self.model = model
        self.records: list[dict[str, Any]] = []

    def start(self, surface: Surface) -> dict[str, Any]:
        return {
            "surface": surface.name,
            "type": surface.surface_type,
            "status": "pending",
            "turns": 0,
            "tool_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "est_cost_usd": 0.0,
        }

    def add(self, record: dict[str, Any]) -> None:
        self.records.append(record)

    def summary(
        self, spent: float, budget: float, price: tuple[float, float]
    ) -> dict[str, Any]:
        statuses: dict[str, int] = {}
        for r in self.records:
            statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        return {
            "model": self.model,
            "surfaces": len(self.records),
            "statuses": statuses,
            "input_tokens": sum(r["input_tokens"] for r in self.records),
            "output_tokens": sum(r["output_tokens"] for r in self.records),
            "tool_calls": sum(r["tool_calls"] for r in self.records),
            "est_cost_usd": round(spent, 6),
            "budget_usd": budget,
            "budget_exhausted": budget > 0 and spent >= budget,
            "pricing_assumption_usd_per_mtok": {"input": price[0], "output": price[1]},
        }

    def write(self, reports_dir: Path, summary: dict[str, Any]) -> None:
        try:
            reports_dir.mkdir(parents=True, exist_ok=True)
            (reports_dir / "enrichment-telemetry.json").write_text(
                json.dumps({"summary": summary, "surfaces": self.records}, indent=2)
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            logger.warning("enrichment_telemetry_write_failed", exc_info=True)


def _neighbor_index(all_surfaces: list[Surface]) -> dict[int, str]:
    """Compact "same resource" neighbor summaries keyed by surface identity."""
    from repo_mirror_kit.harvester.features import resource_key

    by_key: dict[str, list[Surface]] = {}
    keyed: dict[int, str] = {}
    for s in all_surfaces:
        if s.surface_type in ("dependency", "config", "build_deploy", "test_pattern"):
            continue
        name = getattr(s, "entity_name", "") or getattr(s, "screen_name", "") or s.name
        path = getattr(s, "path", "")
        key = resource_key(
            path.strip("/").split("/")[-1]
            if path and s.surface_type == "route"
            else name
        )
        if s.surface_type == "api" and path:
            segs = [
                p
                for p in path.split("/")
                if p and p != "api" and not p.startswith((":", "{", "<"))
            ]
            key = resource_key(segs[0]) if segs else key
        keyed[id(s)] = key
        by_key.setdefault(key, []).append(s)
    out: dict[int, str] = {}
    for s in all_surfaces:
        found = keyed.get(id(s))
        if not found:
            continue
        key = found
        peers = [p for p in by_key.get(key, []) if p is not s][:12]
        out[id(s)] = "\n".join(
            f"- [{p.surface_type}] {p.name}"
            + (f" ({p.source_refs[0].file_path})" if p.source_refs else "")
            for p in peers
        )
    return out


def _enrich_agentic(
    surface: Surface,
    client: Any,
    workdir: Path,
    tools: RepoTools,
    neighbors: dict[int, str],
    config: HarvestConfig,
    record: dict[str, Any],
) -> None:
    """Agentic enrichment of one surface; fills *record* telemetry."""
    prompt = build_agent_prompt(
        surface_type=surface.surface_type,
        surface_name=surface.name,
        surface_data=surface.to_dict(),
        source_code=_read_source_for_surface(surface, workdir),
        neighbors=neighbors.get(id(surface), "") or "(none found)",
    )
    result = run_agent(client, prompt, tools, config.llm_max_turns)
    record.update(
        turns=result.turns,
        tool_calls=result.tool_calls,
        tools_used=sorted(set(result.tools_used)),
    )
    data = parse_agent_json(result.final_text)
    if data is None:
        raise ValueError("agent reply was not valid JSON")
    enrichment = _parse_enrichment_response(json.dumps(data))
    enrichment["confidence"] = str(data.get("confidence", "medium"))
    enrichment["gaps"] = [str(g) for g in data.get("gaps", []) if g]
    enrichment["traced_flow"] = _clean_flow(data.get("traced_flow"))
    fill = data.get("contract_fill")
    if isinstance(fill, dict):
        enrichment["contract_fill"] = fill
    if result.status == "turn_limit":
        enrichment["gaps"].append(
            "Agent hit the turn limit before finishing its trace."
        )
    surface.enrichment = enrichment
    apply_contract_fill(surface)
    record["status"] = "turn_limit" if result.status == "turn_limit" else "ok"


def _clean_flow(raw: Any) -> list[dict[str, Any]]:
    flow: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for hop in raw[:20]:
            if isinstance(hop, dict):
                flow.append(
                    {
                        "hop": str(hop.get("hop", ""))[:200],
                        "file": str(hop.get("file", ""))[:300],
                        "line": hop.get("line")
                        if isinstance(hop.get("line"), int)
                        else None,
                        "note": str(hop.get("note", ""))[:300],
                    }
                )
    return flow


def apply_contract_fill(surface: Surface) -> None:
    """Merge LLM contract guesses into an API surface — never over static results.

    Static extraction (``declared``/``inferred``) always wins; the LLM only
    fills schemas that are missing or marked ``{"unknown": True}``, and what it
    writes is stamped ``confidence: "llm"``.
    """
    if not isinstance(surface, ApiSurface):
        return
    fill = surface.enrichment.get("contract_fill")
    if not isinstance(fill, dict):
        return

    def _fields(raw: Any, source: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for f in raw if isinstance(raw, list) else []:
            if isinstance(f, dict) and f.get("name"):
                out.append(
                    {
                        "name": str(f["name"]),
                        "type": str(f.get("type", "unknown")),
                        "required": bool(f.get("required", False)),
                        "source": source,
                    }
                )
        return out

    def _is_open(schema: dict[str, Any]) -> bool:
        return not schema or schema.get("unknown") is True

    req = _fields(fill.get("request_fields"), "body")
    if req and _is_open(surface.request_schema or {}):
        surface.request_schema = {"fields": req, "confidence": "llm"}
    resp = _fields(fill.get("response_fields"), "body")
    errors = [
        {"status": int(c)}
        for c in fill.get("error_statuses", [])
        if isinstance(c, int) and 400 <= c < 600
    ]
    if resp and _is_open(surface.response_schema or {}):
        schema: dict[str, Any] = {"fields": resp, "confidence": "llm"}
        if errors:
            schema["errors"] = errors
        surface.response_schema = schema


def _enrich_single_surface(
    surface: Surface,
    client: Any,
    workdir: Path,
) -> None:
    """Enrich a single surface with LLM output."""
    source_code = _read_source_for_surface(surface, workdir)
    surface_data = surface.to_dict()

    prompt = build_enrichment_prompt(
        surface_type=surface.surface_type,
        surface_name=surface.name,
        surface_data=surface_data,
        source_code=source_code,
    )

    response = client.complete(SYSTEM_PROMPT, prompt)

    enrichment = _parse_enrichment_response(response)
    surface.enrichment = enrichment


def _read_source_for_surface(surface: Surface, workdir: Path) -> str:
    """Read source code referenced by a surface."""
    if not surface.source_refs:
        return "(no source references)"

    parts: list[str] = []
    for ref in surface.source_refs[:3]:  # Limit to first 3 refs
        file_path = workdir / ref.file_path
        try:
            content = file_path.read_text(encoding="utf-8")
            if ref.start_line is not None and ref.end_line is not None:
                lines = content.splitlines()
                start = max(0, ref.start_line - 1)
                end = min(len(lines), ref.end_line)
                content = "\n".join(lines[start:end])
            elif ref.start_line is not None:
                lines = content.splitlines()
                start = max(0, ref.start_line - 1)
                end = min(len(lines), start + 50)
                content = "\n".join(lines[start:end])
            # Truncate individual files
            if len(content) > 4000:
                content = content[:4000] + "\n... (truncated)"
            parts.append(f"// File: {ref.file_path}\n{content}")
        except OSError:
            parts.append(f"// File: {ref.file_path} (could not read)")

    return "\n\n".join(parts)


def _parse_enrichment_response(response: str) -> dict[str, Any]:
    """Parse LLM response into enrichment dict."""
    # Try to extract JSON from response (may be wrapped in markdown code blocks)
    text = response.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last lines (code fence)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        data: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("llm_response_parse_failed", response_preview=text[:200])
        return {
            "behavioral_description": text[:500],
            "inferred_intent": "Could not parse structured response",
            "given_when_then": [],
            "data_flow": "",
            "priority": "medium",
            "dependencies": [],
        }

    # Validate expected keys, fill missing with defaults
    result: dict[str, Any] = {
        "behavioral_description": data.get("behavioral_description", ""),
        "inferred_intent": data.get("inferred_intent", ""),
        "given_when_then": data.get("given_when_then", []),
        "data_flow": data.get("data_flow", ""),
        "priority": data.get("priority", "medium"),
        "dependencies": data.get("dependencies", []),
    }
    return result
