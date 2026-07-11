"""Sensitive-findings redaction post-pass (BEAN-083).

A single authoritative redaction pass over the ``SurfaceCollection``, run
after LLM enrichment (Stage C2) and before beans are written (Stage E), so
every bean, report, and generated artifact is produced already-redacted.

Security contract (cross-cutting rules 1-2):

- Raw secret/PII values are **never** written to any bean, log, report, or
  state file. This module replaces detected literals in-place with typed
  placeholders (e.g. ``[REDACTED:aws-access-key]``).
- Findings record only metadata: category, kind, ``file:line``, the surface
  they came from, the placeholder used, and a short SHA-256 *prefix* of the
  raw value (for dedup). The raw value itself is never retained.

Detectors are deliberately conservative: over-redaction corrupts legitimate
rule data (enum members, expressions, short constants), so each detector is
tuned for low false-positive rates. See :data:`_DETECTORS`.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import SurfaceCollection

logger = structlog.get_logger()

# Category constants.
CATEGORY_SECRET = "secret"  # noqa: S105 — category label, not a credential
CATEGORY_PII = "pii"


@dataclass(frozen=True)
class SensitiveFinding:
    """A single redacted sensitive value.

    Carries only metadata about the finding — never the raw value.

    Attributes:
        category: ``"secret"`` or ``"pii"``.
        kind: Detector slug, e.g. ``"aws-access-key"`` or ``"email"``.
        file: Source file path (from the surface's first ``source_ref``).
        line: Source line number (from the surface's first ``source_ref``).
        surface_name: Name of the surface the value came from.
        surface_type: Type discriminator of that surface.
        placeholder: The typed placeholder written in the value's place.
        hash_prefix: First 12 hex chars of ``sha256(raw_value)`` — for dedup
            only. Not reversible; the raw value is never stored.
    """

    category: str
    kind: str
    file: str | None
    line: int | None
    surface_name: str
    surface_type: str
    placeholder: str
    hash_prefix: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "category": self.category,
            "kind": self.kind,
            "file": self.file,
            "line": self.line,
            "surface_name": self.surface_name,
            "surface_type": self.surface_type,
            "placeholder": self.placeholder,
            "hash_prefix": self.hash_prefix,
        }


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------
#
# Each detector is (category, kind, compiled-regex, optional extra predicate).
# The predicate takes the matched substring and returns True only when the
# match is truly sensitive — used to guard the high-entropy detector against
# ordinary identifiers. Detectors are applied in list order; earlier, more
# specific patterns win before the broad high-entropy sweep runs.

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_AWS_ACCESS_KEY_RE = re.compile(r"AKIA[0-9A-Z]{16}")
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
# A URL with inline credentials: scheme://user:pass@host
_CONNECTION_STRING_RE = re.compile(r"[a-z][a-z0-9+.\-]*://[^/\s:@]+:[^/\s:@]+@")
# Formatted phone numbers only — never bare digit runs.
_PHONE_RE = re.compile(r"\(\d{3}\)\s?\d{3}-\d{4}|\d{3}-\d{3}-\d{4}")
# High-entropy token candidate (further gated by Shannon entropy below).
_HIGH_ENTROPY_RE = re.compile(r"[A-Za-z0-9+/=_-]{32,}")

# Shannon-entropy threshold (bits/char) above which a long token is treated
# as a probable secret. Normal identifiers, base-N enums, and repeated
# characters fall well below this.
_ENTROPY_THRESHOLD = 4.0


def _shannon_entropy(value: str) -> float:
    """Return the Shannon entropy of ``value`` in bits per character."""
    if not value:
        return 0.0
    counts: dict[str, int] = {}
    for char in value:
        counts[char] = counts.get(char, 0) + 1
    length = len(value)
    return -sum(
        (count / length) * math.log2(count / length) for count in counts.values()
    )


def _high_entropy_predicate(match: str) -> bool:
    """Guard: only treat a long token as a secret when its entropy is high.

    Prevents redaction of long-but-low-entropy strings (repeated chars,
    predictable identifiers) that happen to exceed the length floor.
    """
    return _shannon_entropy(match) > _ENTROPY_THRESHOLD


# (category, kind, regex, predicate|None)
_Predicate = Callable[[str], bool]
_DETECTORS: list[tuple[str, str, re.Pattern[str], _Predicate | None]] = [
    (CATEGORY_PII, "email", _EMAIL_RE, None),
    (CATEGORY_SECRET, "aws-access-key", _AWS_ACCESS_KEY_RE, None),
    (CATEGORY_SECRET, "private-key", _PRIVATE_KEY_RE, None),
    (CATEGORY_SECRET, "connection-string", _CONNECTION_STRING_RE, None),
    (CATEGORY_PII, "phone", _PHONE_RE, None),
    (CATEGORY_SECRET, "high-entropy-secret", _HIGH_ENTROPY_RE, _high_entropy_predicate),
]


@dataclass(frozen=True)
class _Detection:
    """An internal detection within a single string (pre-finding)."""

    category: str
    kind: str
    matched: str  # raw matched span — used ONLY to compute the hash prefix


def _placeholder_for(kind: str) -> str:
    return f"[REDACTED:{kind}]"


def redact_value(value: str) -> tuple[str, list[_Detection]]:
    """Redact all detected sensitive spans in ``value``.

    Replaces every detected match with ``[REDACTED:<kind>]``. Multiple
    different matches within one string are all redacted. Detectors run in
    priority order; spans already replaced by an earlier detector are not
    re-scanned by later, broader detectors (prevents the high-entropy sweep
    from touching an already-redacted AWS key).

    Args:
        value: The raw string to scan.

    Returns:
        A tuple of the redacted string and the list of detections. Each
        detection carries the matched span only so the caller can compute a
        hash prefix; the span is not persisted anywhere.
    """
    detections: list[_Detection] = []
    redacted = value
    for category, kind, pattern, predicate in _DETECTORS:
        placeholder = _placeholder_for(kind)

        def _replace(
            m: re.Match[str],
            *,
            category: str = category,
            kind: str = kind,
            predicate: _Predicate | None = predicate,
            placeholder: str = placeholder,
        ) -> str:
            span = m.group(0)
            if predicate is not None and not predicate(span):
                return span
            detections.append(_Detection(category=category, kind=kind, matched=span))
            return placeholder

        redacted = pattern.sub(_replace, redacted)
    return redacted, detections


def _hash_prefix(raw: str) -> str:
    """Return the first 12 hex chars of ``sha256(raw)`` (dedup key only)."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Surface post-pass
# ---------------------------------------------------------------------------


class _SurfaceRedactor:
    """Accumulates findings while redacting one surface's fields in place."""

    def __init__(self, file: str | None, line: int | None, name: str, stype: str):
        self.file = file
        self.line = line
        self.name = name
        self.stype = stype
        self.findings: list[SensitiveFinding] = []

    def scalar(self, value: Any) -> Any:
        """Redact a single value if it is a string; record findings."""
        if not isinstance(value, str) or not value:
            return value
        redacted, detections = redact_value(value)
        for det in detections:
            self.findings.append(
                SensitiveFinding(
                    category=det.category,
                    kind=det.kind,
                    file=self.file,
                    line=self.line,
                    surface_name=self.name,
                    surface_type=self.stype,
                    placeholder=_placeholder_for(det.kind),
                    hash_prefix=_hash_prefix(det.matched),
                )
            )
        return redacted

    def structure(self, value: Any) -> Any:
        """Recursively redact strings inside nested dict/list structures.

        Dict *keys* are never redacted (they are column/field names, not
        data); only values and list elements are scanned.
        """
        if isinstance(value, str):
            return self.scalar(value)
        if isinstance(value, dict):
            return {k: self.structure(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.structure(v) for v in value]
        return value


def _first_ref(surface: Any) -> tuple[str | None, int | None]:
    """Return (file, line) from a surface's first source_ref, if any."""
    refs = getattr(surface, "source_refs", None)
    if refs:
        ref = refs[0]
        return ref.file_path, ref.start_line
    return None, None


def redact_surfaces(surfaces: SurfaceCollection) -> list[SensitiveFinding]:
    """Redact sensitive literals across every surface, in place.

    Iterates every surface in the collection and scans the string-bearing
    fields that can carry captured literals (BEAN-082 exact rules and error
    contracts, BEAN-066 seed-data cells, config defaults, and LLM-produced
    behavioral text). Detected values are replaced with typed placeholders
    directly on the surfaces so all downstream artifacts are already-redacted.

    Args:
        surfaces: The surface collection to redact in place.

    Returns:
        A deduplicated list of findings (metadata only, no raw values).
    """
    all_findings: list[SensitiveFinding] = []

    for surface in surfaces:
        file, line = _first_ref(surface)
        r = _SurfaceRedactor(file, line, surface.name, surface.surface_type)
        enrichment = getattr(surface, "enrichment", None)

        if isinstance(enrichment, dict):
            _redact_enrichment(enrichment, r)

        # ConfigSurface.default_value (a plain str | None attribute).
        if hasattr(surface, "default_value"):
            surface.default_value = r.scalar(surface.default_value)

        # SeedDataSurface.values (BEAN-066): list of row/member dicts whose
        # cell values may carry planted secrets/PII.
        if hasattr(surface, "values"):
            surface.values = [r.structure(row) for row in surface.values]

        all_findings.extend(r.findings)

    findings = _dedup(all_findings)

    if findings:
        # Log metadata only — counts and kinds, never raw values.
        kinds: dict[str, int] = {}
        for f in findings:
            kinds[f.kind] = kinds.get(f.kind, 0) + 1
        logger.warning(
            "sensitive_findings_redacted",
            count=len(findings),
            kinds=kinds,
        )
    else:
        logger.info("sensitive_findings_none")

    return findings


def _redact_enrichment(enrichment: dict[str, Any], r: _SurfaceRedactor) -> None:
    """Redact the string-bearing enrichment fields in place."""
    # BEAN-082 exact_rules: value + error_message.
    rules = enrichment.get("exact_rules")
    if isinstance(rules, list):
        for rule in rules:
            if isinstance(rule, dict):
                if "value" in rule:
                    rule["value"] = r.scalar(rule["value"])
                if "error_message" in rule:
                    rule["error_message"] = r.scalar(rule["error_message"])

    # BEAN-082 error_contract: response + condition. The condition descriptor
    # comes from ``ast.unparse`` and would otherwise leak a literal inside an
    # ``if token == "abc123":`` guard (Tech-QA finding L1).
    errors = enrichment.get("error_contract")
    if isinstance(errors, list):
        for entry in errors:
            if isinstance(entry, dict):
                if "response" in entry:
                    entry["response"] = r.scalar(entry["response"])
                if "condition" in entry:
                    entry["condition"] = r.scalar(entry["condition"])

    # Free-text LLM-produced fields (may quote captured literals).
    for key in (
        "token_session",
        "behavioral_description",
        "data_flow",
        "inferred_intent",
    ):
        if key in enrichment:
            enrichment[key] = r.scalar(enrichment[key])


def _dedup(findings: list[SensitiveFinding]) -> list[SensitiveFinding]:
    """Drop duplicate (kind, hash_prefix, file, line) findings, order-stable."""
    seen: set[tuple[str, str, str | None, int | None]] = set()
    unique: list[SensitiveFinding] = []
    for f in findings:
        key = (f.kind, f.hash_prefix, f.file, f.line)
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)
    return unique


def _iter_findings_sorted(
    findings: list[SensitiveFinding],
) -> Iterator[SensitiveFinding]:
    """Yield findings in a stable, human-friendly order for reports."""
    yield from sorted(
        findings,
        key=lambda f: (f.category, f.kind, f.file or "", f.line or 0),
    )
