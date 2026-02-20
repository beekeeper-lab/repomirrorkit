"""Unit tests for the LLM client wrapper."""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# HAS_ANTHROPIC flag
# ---------------------------------------------------------------------------


class TestHasAnthropicFlag:
    def test_has_anthropic_is_bool(self) -> None:
        from repo_mirror_kit.harvester.llm.client import HAS_ANTHROPIC

        assert isinstance(HAS_ANTHROPIC, bool)


# ---------------------------------------------------------------------------
# Helpers: mock Anthropic SDK objects
# ---------------------------------------------------------------------------


def _mock_anthropic_module() -> MagicMock:
    """Return a mock that acts like the ``anthropic`` package."""
    mod = MagicMock()
    # anthropic.Anthropic(...) returns a client instance
    mod.Anthropic.return_value = _mock_client_instance()
    return mod


def _mock_client_instance() -> MagicMock:
    """Return a mock Anthropic client with a ``messages.create`` method."""
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        text="Hello from the LLM",
        input_tokens=42,
        output_tokens=17,
    )
    return client


def _mock_response(
    text: str = "ok",
    input_tokens: int = 10,
    output_tokens: int = 5,
) -> SimpleNamespace:
    """Build a fake Anthropic ``Message`` response."""
    content_block = SimpleNamespace(text=text)
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(content=[content_block], usage=usage)


# ---------------------------------------------------------------------------
# Client initialisation
# ---------------------------------------------------------------------------


class TestLLMClientInit:
    def test_init_stores_model_and_rpm(self) -> None:
        mock_mod = _mock_anthropic_module()
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            # Re-import so the guarded import picks up our mock
            from importlib import reload

            import repo_mirror_kit.harvester.llm.client as client_mod

            reload(client_mod)

            client = client_mod.LLMClient(api_key="sk-test", model="claude-test", requests_per_minute=60)

            assert client._model == "claude-test"
            assert client._rpm == 60
            assert client._min_interval == pytest.approx(1.0)
            mock_mod.Anthropic.assert_called_once_with(api_key="sk-test")

    def test_init_default_model(self) -> None:
        mock_mod = _mock_anthropic_module()
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            from importlib import reload

            import repo_mirror_kit.harvester.llm.client as client_mod

            reload(client_mod)

            client = client_mod.LLMClient(api_key="sk-test")

            assert client._model == "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# complete() method
# ---------------------------------------------------------------------------


class TestLLMClientComplete:
    def test_complete_returns_text(self) -> None:
        mock_mod = _mock_anthropic_module()
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            from importlib import reload

            import repo_mirror_kit.harvester.llm.client as client_mod

            reload(client_mod)

            client = client_mod.LLMClient(api_key="sk-test")
            result = client.complete("system prompt", "user prompt")

            assert result == "Hello from the LLM"

    def test_complete_passes_correct_args_to_sdk(self) -> None:
        mock_mod = _mock_anthropic_module()
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            from importlib import reload

            import repo_mirror_kit.harvester.llm.client as client_mod

            reload(client_mod)

            client = client_mod.LLMClient(api_key="sk-test", model="claude-test")
            client.complete("sys", "usr", max_tokens=512)

            inner_client = mock_mod.Anthropic.return_value
            inner_client.messages.create.assert_called_once_with(
                model="claude-test",
                max_tokens=512,
                system="sys",
                messages=[{"role": "user", "content": "usr"}],
            )


# ---------------------------------------------------------------------------
# Token tracking
# ---------------------------------------------------------------------------


class TestTokenTracking:
    def test_tokens_accumulate_across_calls(self) -> None:
        mock_mod = _mock_anthropic_module()
        inner_client = mock_mod.Anthropic.return_value
        # Two calls with different token counts
        inner_client.messages.create.side_effect = [
            _mock_response(text="r1", input_tokens=10, output_tokens=5),
            _mock_response(text="r2", input_tokens=20, output_tokens=15),
        ]
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            from importlib import reload

            import repo_mirror_kit.harvester.llm.client as client_mod

            reload(client_mod)

            client = client_mod.LLMClient(api_key="sk-test", requests_per_minute=9999)
            client.complete("s", "u1")
            client.complete("s", "u2")

            assert client.total_input_tokens == 30
            assert client.total_output_tokens == 20
            assert client.request_count == 2

    def test_initial_counters_are_zero(self) -> None:
        mock_mod = _mock_anthropic_module()
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            from importlib import reload

            import repo_mirror_kit.harvester.llm.client as client_mod

            reload(client_mod)

            client = client_mod.LLMClient(api_key="sk-test")

            assert client.total_input_tokens == 0
            assert client.total_output_tokens == 0
            assert client.request_count == 0


# ---------------------------------------------------------------------------
# Rate limiting / throttle
# ---------------------------------------------------------------------------


class TestRateLimiting:
    def test_throttle_sleeps_when_calls_are_too_fast(self) -> None:
        mock_mod = _mock_anthropic_module()
        inner_client = mock_mod.Anthropic.return_value
        inner_client.messages.create.side_effect = [
            _mock_response(text="r1"),
            _mock_response(text="r2"),
        ]
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            from importlib import reload

            import repo_mirror_kit.harvester.llm.client as client_mod

            reload(client_mod)

            # 30 rpm => 2s interval
            client = client_mod.LLMClient(
                api_key="sk-test",
                requests_per_minute=30,
            )

            with patch.object(client_mod.time, "sleep") as mock_sleep:
                # First call sets _last_request_time; second triggers throttle
                client.complete("s", "u1")
                client.complete("s", "u2")

                # time.sleep should have been called at least once for the second request
                assert mock_sleep.call_count >= 1

    def test_high_rpm_allows_rapid_calls(self) -> None:
        mock_mod = _mock_anthropic_module()
        inner_client = mock_mod.Anthropic.return_value
        inner_client.messages.create.side_effect = [
            _mock_response(text="r1"),
            _mock_response(text="r2"),
        ]
        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            from importlib import reload

            import repo_mirror_kit.harvester.llm.client as client_mod

            reload(client_mod)

            # Very high RPM means near-zero interval
            client = client_mod.LLMClient(
                api_key="sk-test",
                requests_per_minute=999_999,
            )

            start = time.monotonic()
            client.complete("s", "u1")
            client.complete("s", "u2")
            elapsed = time.monotonic() - start

            # Should complete in well under a second
            assert elapsed < 1.0


# ---------------------------------------------------------------------------
# Graceful degradation when anthropic is not installed
# ---------------------------------------------------------------------------


class TestAnthropicNotInstalled:
    def test_raises_import_error_when_anthropic_missing(self) -> None:
        with patch.dict("sys.modules", {"anthropic": None}):
            from importlib import reload

            import repo_mirror_kit.harvester.llm.client as client_mod

            # Force HAS_ANTHROPIC to False to simulate missing package
            original = client_mod.HAS_ANTHROPIC
            client_mod.HAS_ANTHROPIC = False
            try:
                with pytest.raises(ImportError, match="anthropic package is not installed"):
                    client_mod.LLMClient(api_key="sk-test")
            finally:
                client_mod.HAS_ANTHROPIC = original
