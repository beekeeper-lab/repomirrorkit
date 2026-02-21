"""LLM enrichment orchestrator for surfaces."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import Surface, SurfaceCollection
from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.llm.prompts import SYSTEM_PROMPT, build_enrichment_prompt

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

    if not config.llm_api_key:
        logger.warning("llm_enrichment_skipped", reason="no_api_key")
        return surfaces

    from repo_mirror_kit.harvester.llm.client import LLMClient

    client = LLMClient(
        api_key=config.llm_api_key,
        model=config.llm_model,
    )

    total = len(surfaces)
    enriched_count = 0
    error_count = 0

    for i, surface in enumerate(surfaces):
        try:
            _enrich_single_surface(surface, client, workdir)
            enriched_count += 1
        except Exception:
            logger.warning(
                "llm_enrichment_failed",
                surface_name=surface.name,
                surface_type=surface.surface_type,
                exc_info=True,
            )
            error_count += 1

        if callback is not None and (i + 1) % 5 == 0:
            from repo_mirror_kit.harvester.pipeline import (
                PipelineEvent,
                PipelineEventType,
            )
            callback(PipelineEvent(
                event_type=PipelineEventType.PROGRESS_UPDATE,
                stage="C2",
                message=f"Enriched {i + 1}/{total} surfaces",
            ))

    logger.info(
        "llm_enrichment_complete",
        total=total,
        enriched=enriched_count,
        errors=error_count,
        input_tokens=client.total_input_tokens,
        output_tokens=client.total_output_tokens,
    )

    return surfaces


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
