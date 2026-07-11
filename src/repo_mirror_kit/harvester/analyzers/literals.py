"""Single chokepoint for captured literal values (BEAN-082 / BEAN-083 seam).

Every exact literal an analyzer copies verbatim out of source — error
messages, column defaults, enum members, check-constraint expressions,
validation regexes — MUST pass through :func:`sanitize_captured_literal`
before it is stored on a surface's ``enrichment``. Today the function is an
identity transform; BEAN-083 will replace the body with the sensitive-value
filter (secret / PII redaction and reporting) so that one edit here protects
every captured literal without touching each call site.

Keeping this as the sole seam means the redaction pass has exactly one place
to plug in, and a test can assert the chokepoint is actually exercised by
monkeypatching it.
"""

from __future__ import annotations


def sanitize_captured_literal(value: str) -> str:
    """Return a captured source literal, ready to store on a surface.

    Identity for now (BEAN-082). BEAN-083 will wrap this to redact secrets
    and PII from the value and record what was redacted. Every analyzer that
    copies a literal out of source routes it through here first, so the
    redaction pass has a single chokepoint to own.

    Args:
        value: The exact literal copied verbatim from source.

    Returns:
        The value, sanitized. Currently unchanged.
    """
    return value


__all__ = ["sanitize_captured_literal"]
