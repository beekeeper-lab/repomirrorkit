"""Unit tests for the LLM enrichment orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from repo_mirror_kit.harvester.analyzers.surfaces import (
    RouteSurface,
    SourceRef,
    SurfaceCollection,
)
from repo_mirror_kit.harvester.config import HarvestConfig
from repo_mirror_kit.harvester.llm.enrichment import (
    _parse_enrichment_response,
    enrich_surfaces,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_ENRICHMENT_JSON: dict[str, Any] = {
    "behavioral_description": "Returns user profile data.",
    "inferred_intent": "Allows clients to fetch user info.",
    "given_when_then": [
        {
            "given": "an authenticated user",
            "when": "they call GET /user",
            "then": "they receive their profile",
        },
    ],
    "data_flow": "Request -> auth check -> DB query -> JSON response",
    "priority": "high",
    "dependencies": ["auth-service", "user-db"],
}


def _make_config(
    *,
    llm_enabled: bool = True,
    llm_api_key: str | None = "sk-test-key",
) -> HarvestConfig:
    """Build a HarvestConfig with LLM settings."""
    return HarvestConfig(
        repo="https://github.com/example/repo",
        llm_enabled=llm_enabled,
        llm_api_key=llm_api_key,
        llm_model="claude-test",
    )


def _make_surfaces(count: int = 2) -> SurfaceCollection:
    """Build a SurfaceCollection with ``count`` route surfaces."""
    routes = [
        RouteSurface(
            name=f"route_{i}",
            path=f"/route/{i}",
            method="GET",
            source_refs=[SourceRef(file_path=f"src/routes/r{i}.py", start_line=1, end_line=10)],
        )
        for i in range(count)
    ]
    return SurfaceCollection(routes=routes)


def _mock_llm_client_class(response_text: str | None = None) -> MagicMock:
    """Return a mock LLMClient class whose instances return ``response_text``."""
    if response_text is None:
        response_text = json.dumps(_ENRICHMENT_JSON)
    mock_cls = MagicMock()
    instance = mock_cls.return_value
    instance.complete.return_value = response_text
    instance.total_input_tokens = 100
    instance.total_output_tokens = 50
    return mock_cls


# ---------------------------------------------------------------------------
# Early-exit conditions (surfaces returned unchanged)
# ---------------------------------------------------------------------------


class TestEnrichSurfacesSkipConditions:
    def test_returns_unchanged_when_llm_not_enabled(self) -> None:
        config = HarvestConfig(
            repo="https://github.com/example/repo",
            llm_enabled=False,
        )
        surfaces = _make_surfaces()
        result = enrich_surfaces(surfaces, config, Path("/tmp"))

        assert result is surfaces
        for s in result:
            assert s.enrichment == {}

    def test_returns_unchanged_when_anthropic_not_installed(self) -> None:
        config = _make_config()
        surfaces = _make_surfaces()

        with patch(
            "repo_mirror_kit.harvester.llm.enrichment.HAS_ANTHROPIC", False,
        ):
            result = enrich_surfaces(surfaces, config, Path("/tmp"))

        assert result is surfaces
        for s in result:
            assert s.enrichment == {}

    def test_returns_unchanged_when_api_key_is_none(self) -> None:
        config = HarvestConfig(
            repo="https://github.com/example/repo",
            llm_enabled=True,
            llm_api_key="placeholder",
        )
        surfaces = _make_surfaces()

        # Patch the config's api_key check by patching the attribute read
        with patch(
            "repo_mirror_kit.harvester.llm.enrichment.HAS_ANTHROPIC", True,
        ), patch.object(
            type(config), "llm_api_key", new_callable=lambda: property(lambda self: None),
        ):
            result = enrich_surfaces(surfaces, config, Path("/tmp"))

        assert result is surfaces


# ---------------------------------------------------------------------------
# Enrichment with mocked LLMClient
# ---------------------------------------------------------------------------


class TestEnrichSurfacesWithMockedClient:
    def test_surfaces_get_enrichment_populated(self, tmp_path: Path) -> None:
        config = _make_config()
        surfaces = _make_surfaces(count=2)
        mock_cls = _mock_llm_client_class()

        with (
            patch("repo_mirror_kit.harvester.llm.enrichment.HAS_ANTHROPIC", True),
            patch("repo_mirror_kit.harvester.llm.client.LLMClient", mock_cls),
        ):
            result = enrich_surfaces(surfaces, config, tmp_path)

        for s in result:
            assert s.enrichment != {}
            assert "behavioral_description" in s.enrichment
            assert "given_when_then" in s.enrichment
            assert s.enrichment["priority"] == "high"
            assert "auth-service" in s.enrichment["dependencies"]

    def test_client_complete_called_for_each_surface(self, tmp_path: Path) -> None:
        config = _make_config()
        surfaces = _make_surfaces(count=3)
        mock_cls = _mock_llm_client_class()

        with (
            patch("repo_mirror_kit.harvester.llm.enrichment.HAS_ANTHROPIC", True),
            patch("repo_mirror_kit.harvester.llm.client.LLMClient", mock_cls),
        ):
            enrich_surfaces(surfaces, config, tmp_path)

        instance = mock_cls.return_value
        assert instance.complete.call_count == 3


# ---------------------------------------------------------------------------
# _parse_enrichment_response
# ---------------------------------------------------------------------------


class TestParseEnrichmentResponse:
    def test_parses_plain_json(self) -> None:
        raw = json.dumps(_ENRICHMENT_JSON)
        result = _parse_enrichment_response(raw)

        assert result["behavioral_description"] == "Returns user profile data."
        assert result["priority"] == "high"
        assert len(result["given_when_then"]) == 1
        assert result["dependencies"] == ["auth-service", "user-db"]

    def test_parses_json_wrapped_in_code_fence(self) -> None:
        fenced = "```json\n" + json.dumps(_ENRICHMENT_JSON) + "\n```"
        result = _parse_enrichment_response(fenced)

        assert result["behavioral_description"] == "Returns user profile data."
        assert result["inferred_intent"] == "Allows clients to fetch user info."

    def test_parses_json_wrapped_in_bare_code_fence(self) -> None:
        fenced = "```\n" + json.dumps(_ENRICHMENT_JSON) + "\n```"
        result = _parse_enrichment_response(fenced)

        assert result["priority"] == "high"

    def test_fills_defaults_for_missing_keys(self) -> None:
        partial = json.dumps({"behavioral_description": "Something"})
        result = _parse_enrichment_response(partial)

        assert result["behavioral_description"] == "Something"
        assert result["inferred_intent"] == ""
        assert result["given_when_then"] == []
        assert result["data_flow"] == ""
        assert result["priority"] == "medium"
        assert result["dependencies"] == []

    def test_fallback_on_invalid_json(self) -> None:
        result = _parse_enrichment_response("This is not JSON at all.")

        assert "This is not JSON at all." in result["behavioral_description"]
        assert result["inferred_intent"] == "Could not parse structured response"
        assert result["given_when_then"] == []
        assert result["priority"] == "medium"


# ---------------------------------------------------------------------------
# Error handling: enrichment errors do not crash the pipeline
# ---------------------------------------------------------------------------


class TestEnrichmentErrorHandling:
    def test_errors_are_caught_and_surfaces_returned(self, tmp_path: Path) -> None:
        config = _make_config()
        surfaces = _make_surfaces(count=2)

        mock_cls = MagicMock()
        instance = mock_cls.return_value
        instance.complete.side_effect = RuntimeError("LLM exploded")
        instance.total_input_tokens = 0
        instance.total_output_tokens = 0

        with (
            patch("repo_mirror_kit.harvester.llm.enrichment.HAS_ANTHROPIC", True),
            patch("repo_mirror_kit.harvester.llm.client.LLMClient", mock_cls),
        ):
            result = enrich_surfaces(surfaces, config, tmp_path)

        # Pipeline should survive; surfaces returned (unenriched)
        assert result is surfaces
        for s in result:
            assert s.enrichment == {}

    def test_partial_failure_enriches_surviving_surfaces(self, tmp_path: Path) -> None:
        config = _make_config()
        surfaces = _make_surfaces(count=3)

        mock_cls = MagicMock()
        instance = mock_cls.return_value
        # First call succeeds, second fails, third succeeds
        instance.complete.side_effect = [
            json.dumps(_ENRICHMENT_JSON),
            RuntimeError("temporary failure"),
            json.dumps(_ENRICHMENT_JSON),
        ]
        instance.total_input_tokens = 100
        instance.total_output_tokens = 50

        with (
            patch("repo_mirror_kit.harvester.llm.enrichment.HAS_ANTHROPIC", True),
            patch("repo_mirror_kit.harvester.llm.client.LLMClient", mock_cls),
        ):
            result = enrich_surfaces(surfaces, config, tmp_path)

        enriched = [s for s in result if s.enrichment]
        unenriched = [s for s in result if not s.enrichment]
        assert len(enriched) == 2
        assert len(unenriched) == 1
