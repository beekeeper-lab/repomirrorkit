"""Unit tests for the sensitive-findings redaction post-pass (BEAN-083).

Security-critical: raw secret/PII values must never survive redaction into a
surface, and legitimate rule data must NOT be over-redacted.
"""

from __future__ import annotations

import structlog

from repo_mirror_kit.harvester.analyzers.surfaces import (
    ApiSurface,
    ConfigSurface,
    SeedDataSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.redaction import (
    redact_surfaces,
    redact_value,
)

# A fake AWS key that is NOT a real credential (AWS's documented example).
FAKE_AWS_KEY = "AKIAIOSFODNN7EXAMPLE"


# ---------------------------------------------------------------------------
# Detector unit tests (positive + negative)
# ---------------------------------------------------------------------------


def test_detects_email() -> None:
    redacted, dets = redact_value("contact alice@example.com now")
    assert redacted == "contact [REDACTED:email] now"
    assert [d.kind for d in dets] == ["email"]


def test_detects_aws_access_key() -> None:
    redacted, dets = redact_value(FAKE_AWS_KEY)
    assert redacted == "[REDACTED:aws-access-key]"
    assert [d.kind for d in dets] == ["aws-access-key"]


def test_detects_private_key_header() -> None:
    redacted, dets = redact_value("-----BEGIN RSA PRIVATE KEY-----\nMIIabc")
    assert "[REDACTED:private-key]" in redacted
    assert dets[0].kind == "private-key"


def test_detects_connection_string_with_credentials() -> None:
    redacted, dets = redact_value("postgres://user:s3cret@db:5432/app")
    assert redacted.startswith("[REDACTED:connection-string]")
    assert "s3cret" not in redacted
    assert dets[0].kind == "connection-string"


def test_detects_formatted_phone_paren() -> None:
    redacted, dets = redact_value("call (555) 123-4567")
    assert redacted == "call [REDACTED:phone]"
    assert dets[0].kind == "phone"


def test_detects_formatted_phone_dashed() -> None:
    redacted, dets = redact_value("555-123-4567")
    assert redacted == "[REDACTED:phone]"
    assert dets[0].kind == "phone"


def test_detects_high_entropy_secret() -> None:
    token = "wJalrXUtnFEMIbKdEXAMPLEKEYaws1234567890AB"
    redacted, dets = redact_value(token)
    assert redacted == "[REDACTED:high-entropy-secret]"
    assert dets[0].kind == "high-entropy-secret"


def test_multiple_matches_all_redacted() -> None:
    redacted, dets = redact_value(f"key {FAKE_AWS_KEY} email bob@test.io")
    assert "[REDACTED:aws-access-key]" in redacted
    assert "[REDACTED:email]" in redacted
    assert FAKE_AWS_KEY not in redacted
    assert "bob@test.io" not in redacted
    assert {d.kind for d in dets} == {"aws-access-key", "email"}


# --- Negative cases: legitimate BEAN-082 rule values must survive untouched ---


def test_enum_alternation_not_redacted() -> None:
    assert redact_value("admin|member|guest") == ("admin|member|guest", [])


def test_expression_rule_not_redacted() -> None:
    assert redact_value("length(name) > 0") == ("length(name) > 0", [])


def test_quoted_enum_member_not_redacted() -> None:
    assert redact_value('"member"') == ('"member"', [])


def test_short_numeric_literal_not_redacted() -> None:
    assert redact_value("18") == ("18", [])


def test_bare_digit_run_not_treated_as_phone() -> None:
    # 10 bare digits must not trip the phone detector.
    assert redact_value("5551234567") == ("5551234567", [])


def test_ordinary_identifier_not_high_entropy() -> None:
    # A long-but-low-entropy identifier stays put.
    value = "user_account_status_lookup_table_name"
    assert redact_value(value) == (value, [])


# ---------------------------------------------------------------------------
# redact_surfaces: the chokepoint over the collection
# ---------------------------------------------------------------------------


def _collection_with_planted_secrets() -> SurfaceCollection:
    api = ApiSurface(
        name="create_user",
        source_refs=[SourceRef(file_path="app/api.py", start_line=42)],
    )
    api.enrichment["exact_rules"] = [
        {
            "field": "token",
            "rule": "equals",
            "value": FAKE_AWS_KEY,
            "error_message": None,
        },
    ]
    api.enrichment["error_contract"] = [
        # The secret hides inside the condition descriptor (Tech-QA L1).
        {
            "condition": 'token == "AKIAIOSFODNN7EXAMPLE"',
            "status": 403,
            "response": "denied",
        },
    ]

    seed = SeedDataSurface(
        name="enum Contacts",
        dataset_name="Contacts",
        kind="enum",
        values=[{"name": "OWNER", "value": "alice@example.com"}],
        source_refs=[SourceRef(file_path="app/models.py", start_line=7)],
    )

    cfg = ConfigSurface(
        name="DATABASE_URL",
        env_var_name="DATABASE_URL",
        default_value="postgres://user:p4ss@db:5432/app",
        source_refs=[SourceRef(file_path="app/config.py", start_line=3)],
    )

    return SurfaceCollection(apis=[api], config=[cfg], seed_data=[seed])


def test_redact_surfaces_redacts_all_planted_values() -> None:
    surfaces = _collection_with_planted_secrets()
    findings = redact_surfaces(surfaces)

    # Every planted raw value is gone from the surfaces.
    blob = surfaces.to_json()
    assert FAKE_AWS_KEY not in blob
    assert "alice@example.com" not in blob
    assert "p4ss" not in blob

    kinds = {f.kind for f in findings}
    assert "aws-access-key" in kinds
    assert "email" in kinds
    assert "connection-string" in kinds


def test_redact_surfaces_records_file_line_and_surface() -> None:
    surfaces = _collection_with_planted_secrets()
    findings = redact_surfaces(surfaces)

    aws = next(f for f in findings if f.kind == "aws-access-key")
    assert aws.file == "app/api.py"
    assert aws.line == 42
    assert aws.surface_name == "create_user"
    assert aws.surface_type == "api"
    assert aws.placeholder == "[REDACTED:aws-access-key]"
    assert len(aws.hash_prefix) == 12

    email = next(f for f in findings if f.kind == "email")
    assert email.file == "app/models.py"
    assert email.line == 7
    assert email.surface_type == "seed_data"


def test_redact_surfaces_condition_descriptor_scanned() -> None:
    surfaces = _collection_with_planted_secrets()
    redact_surfaces(surfaces)
    condition = surfaces.apis[0].enrichment["error_contract"][0]["condition"]
    assert FAKE_AWS_KEY not in condition
    assert "[REDACTED:aws-access-key]" in condition


def test_redact_surfaces_no_findings_on_clean_collection() -> None:
    api = ApiSurface(name="ping")
    api.enrichment["exact_rules"] = [
        {
            "field": "role",
            "rule": "in",
            "value": "admin|member|guest",
            "error_message": "invalid role",
        },
    ]
    surfaces = SurfaceCollection(apis=[api])
    assert redact_surfaces(surfaces) == []
    # Legitimate value untouched.
    assert surfaces.apis[0].enrichment["exact_rules"][0]["value"] == (
        "admin|member|guest"
    )


def test_redact_surfaces_dedups_identical_findings() -> None:
    # Same secret at the same file:line/kind should collapse to one finding.
    api = ApiSurface(
        name="dup",
        source_refs=[SourceRef(file_path="a.py", start_line=1)],
    )
    api.enrichment["exact_rules"] = [
        {"field": "a", "rule": "eq", "value": FAKE_AWS_KEY, "error_message": None},
        {"field": "b", "rule": "eq", "value": FAKE_AWS_KEY, "error_message": None},
    ]
    findings = redact_surfaces(SurfaceCollection(apis=[api]))
    assert len(findings) == 1


# ---------------------------------------------------------------------------
# Chokepoint / coverage: every redactable field is actually visited
# ---------------------------------------------------------------------------


def test_every_redactable_field_is_visited() -> None:
    """Plant a distinct secret in each enumerated field; assert each redacted."""
    api = ApiSurface(
        name="cover",
        source_refs=[SourceRef(file_path="x.py", start_line=1)],
    )
    api.enrichment["exact_rules"] = [
        {
            "field": "f",
            "rule": "eq",
            "value": "a@ex1.com",
            "error_message": "b@ex2.com",
        },
    ]
    api.enrichment["error_contract"] = [
        {"condition": "c@ex3.com", "status": 400, "response": "d@ex4.com"},
    ]
    api.enrichment["token_session"] = "e@ex5.com"
    api.enrichment["behavioral_description"] = "f@ex6.com"
    api.enrichment["data_flow"] = "g@ex7.com"
    api.enrichment["inferred_intent"] = "h@ex8.com"

    seed = SeedDataSurface(
        name="s",
        values=[{"name": "N", "value": "i@ex9.com"}],
        source_refs=[SourceRef(file_path="x.py", start_line=1)],
    )
    cfg = ConfigSurface(name="C", default_value="j@ex10.com")

    surfaces = SurfaceCollection(apis=[api], config=[cfg], seed_data=[seed])
    findings = redact_surfaces(surfaces)

    # 10 distinct planted emails → 10 findings, and none survive.
    blob = surfaces.to_json()
    for i in range(1, 11):
        assert f"ex{i}.com" not in blob, f"field {i} leaked"
    assert len(findings) == 10


# ---------------------------------------------------------------------------
# Log-safety (cross-cutting rule 2)
# ---------------------------------------------------------------------------


def test_log_output_never_contains_raw_secret() -> None:
    import repo_mirror_kit.harvester.redaction as redaction_mod

    surfaces = _collection_with_planted_secrets()
    saved = redaction_mod.logger
    try:
        with structlog.testing.capture_logs() as logs:
            # Rebind a fresh logger under the capture config so the assertion
            # is deterministic regardless of prior structlog caching state
            # (configure_logging uses cache_logger_on_first_use=True).
            redaction_mod.logger = structlog.get_logger()
            redaction_mod.redact_surfaces(surfaces)
    finally:
        redaction_mod.logger = saved

    serialized = repr(logs)
    assert FAKE_AWS_KEY not in serialized
    assert "alice@example.com" not in serialized
    assert "p4ss" not in serialized
    # It DID log something (metadata rollup).
    assert any(e.get("event") == "sensitive_findings_redacted" for e in logs)


# ---------------------------------------------------------------------------
# Security-regression: whole-enrichment coverage (Security Engineer finding)
# ---------------------------------------------------------------------------


def _api_with_enrichment(enrichment: dict) -> ApiSurface:
    api = ApiSurface(
        name="ep", method="GET", path="/ep", source_refs=[SourceRef("app.py", 3)]
    )
    api.enrichment.update(enrichment)
    return api


def test_behavioral_signals_docstring_is_redacted() -> None:
    # HIGH regression: a secret in a BEAN-054 structural docstring must not
    # leak. It lives under enrichment["behavioral_signals"]["docstring"].
    api = _api_with_enrichment(
        {"behavioral_signals": {"docstring": f"root key {FAKE_AWS_KEY} do not ship"}}
    )
    findings = redact_surfaces(SurfaceCollection(apis=[api]))
    doc = api.enrichment["behavioral_signals"]["docstring"]
    assert FAKE_AWS_KEY not in doc
    assert "[REDACTED:aws-access-key]" in doc
    assert any(f.kind == "aws-access-key" for f in findings)


def test_given_when_then_text_is_redacted() -> None:
    api = _api_with_enrichment(
        {
            "given_when_then": [
                {"given": "user alice@example.com", "when": "x", "then": "y"}
            ]
        }
    )
    findings = redact_surfaces(SurfaceCollection(apis=[api]))
    gwt = api.enrichment["given_when_then"][0]
    assert "alice@example.com" not in gwt["given"]
    assert "[REDACTED:email]" in gwt["given"]
    assert any(f.kind == "email" for f in findings)


def test_deeply_nested_enrichment_string_redacted() -> None:
    # Any future/unknown enrichment key is covered by the recursive scan.
    api = _api_with_enrichment(
        {"some_future_key": {"nested": ["ok", {"deep": FAKE_AWS_KEY}]}}
    )
    redact_surfaces(SurfaceCollection(apis=[api]))
    assert api.enrichment["some_future_key"]["nested"][1]["deep"] == (
        "[REDACTED:aws-access-key]"
    )


def test_enrichment_dict_keys_are_not_redacted() -> None:
    # Keys are field names, not data — they must survive verbatim even if
    # they look secret-shaped.
    api = _api_with_enrichment({"exact_rules": [{"field": "email", "value": "18"}]})
    redact_surfaces(SurfaceCollection(apis=[api]))
    assert "field" in api.enrichment["exact_rules"][0]
    assert api.enrichment["exact_rules"][0]["field"] == "email"


def test_connection_string_labeled_not_email() -> None:
    # A credentialed URL with a dotted-TLD host must be reported as a
    # connection-string secret, not mislabeled PII email (Tech-QA finding).
    api = _api_with_enrichment(
        {
            "error_contract": [
                {
                    "condition": "c",
                    "response": "postgres://admin:hunter2pw@db.example.com:5432/prod",
                }
            ]
        }
    )
    findings = redact_surfaces(SurfaceCollection(apis=[api]))
    kinds = {f.kind for f in findings}
    assert "connection-string" in kinds
    assert "email" not in kinds
    resp = api.enrichment["error_contract"][0]["response"]
    assert "hunter2pw" not in resp
    assert "[REDACTED:connection-string]" in resp


def test_hash_prefix_is_salted_per_run() -> None:
    # The same raw value in two separate runs yields different hash prefixes,
    # so the prefix is not a cross-run guess-confirmation oracle for PII.
    def _run() -> str:
        api = _api_with_enrichment({"data_flow": "alice@example.com"})
        findings = redact_surfaces(SurfaceCollection(apis=[api]))
        return findings[0].hash_prefix

    assert _run() != _run()
