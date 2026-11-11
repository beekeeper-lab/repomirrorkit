"""Shared LLM-enrichment constants."""

from __future__ import annotations

# Surface types worth a model call. The rest (dependencies, config, build
# files, tests, seed data, mined rules) are fully described structurally and
# carry no behavioural placeholders for a model to fill.
ENRICH_TYPES = frozenset(
    {
        "api",
        "route",
        "screen",
        "component",
        "model",
        "auth",
        "workflow",
        "ui_flow",
        "integration",
        "middleware",
        "state_mgmt",
        "crosscutting",
        "general_logic",
    }
)
