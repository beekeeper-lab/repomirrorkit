"""Capture-time passthrough for literal values (BEAN-082 marker).

Every exact literal an analyzer copies verbatim out of source — error
messages, column defaults, enum members, check-constraint expressions,
validation regexes — is routed through :func:`sanitize_captured_literal` at
capture time. It is intentionally an **identity** transform.

Secret / PII redaction does NOT happen here. It is performed authoritatively
by the :func:`repo_mirror_kit.harvester.redaction.redact_surfaces` post-pass,
which runs after enrichment and recursively scans every surface's serialized
strings — the only layer that has each surface's ``source_ref`` (for
``file:line`` in findings) and sees LLM-produced fields too. Redacting at this
per-value capture point instead would miss those and could not attribute
locations, so this function is deliberately left as a no-op marker of where a
literal enters a surface.
"""

from __future__ import annotations


def sanitize_captured_literal(value: str) -> str:
    """Return a captured source literal unchanged (identity).

    Redaction is handled by the ``redact_surfaces`` post-pass, not here —
    see the module docstring. Retained as an explicit, greppable marker of
    literal-capture sites.

    Args:
        value: The exact literal copied verbatim from source.

    Returns:
        The value, unchanged.
    """
    return value


__all__ = ["sanitize_captured_literal"]
