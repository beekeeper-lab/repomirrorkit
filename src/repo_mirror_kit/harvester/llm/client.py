"""LLM client wrapper with rate limiting and token tracking."""

from __future__ import annotations

import time
from typing import Any

import structlog

logger = structlog.get_logger()

# Guarded import — anthropic is optional
try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    anthropic = None  # type: ignore[assignment]
    HAS_ANTHROPIC = False


class LLMClient:
    """Wrapper around the Anthropic SDK with rate limiting.

    Args:
        api_key: Anthropic API key. May be omitted when ``base_url`` points
            at a local endpoint (e.g. Ollama) that doesn't check the key.
        model: Model identifier.
        requests_per_minute: Max API calls per minute.
        base_url: Optional override for the Anthropic SDK's base URL. Set
            this to target a local, Anthropic-API-compatible endpoint such
            as Ollama (``http://localhost:11434``), which implements the
            Messages API natively as of Ollama >= 0.14. When set and no
            ``api_key`` is supplied, a dummy key of ``"ollama"`` is used
            since local endpoints typically don't validate it.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        requests_per_minute: int = 30,
        base_url: str | None = None,
    ) -> None:
        if not HAS_ANTHROPIC:
            msg = "anthropic package is not installed. Install with: pip install anthropic"
            raise ImportError(msg)
        if base_url:
            resolved_key = api_key or "ollama"
            self._client: Any = anthropic.Anthropic(
                api_key=resolved_key, base_url=base_url
            )
        else:
            self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._rpm = requests_per_minute
        self._min_interval = 60.0 / requests_per_minute
        self._last_request_time: float = 0.0
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._request_count: int = 0

    def complete(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 2048
    ) -> str:
        """Send a completion request with rate limiting.

        Args:
            system_prompt: System instruction.
            user_prompt: User message.
            max_tokens: Max response tokens.

        Returns:
            The text content of the model's response.
        """
        self._throttle()

        response: Any = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        self._request_count += 1
        self._total_input_tokens += response.usage.input_tokens
        self._total_output_tokens += response.usage.output_tokens

        logger.debug(
            "llm_request_complete",
            model=self._model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            request_number=self._request_count,
        )

        text_block = response.content[0]
        result: str = text_block.text
        return result

    @property
    def total_input_tokens(self) -> int:
        return self._total_input_tokens

    @property
    def total_output_tokens(self) -> int:
        return self._total_output_tokens

    @property
    def request_count(self) -> int:
        return self._request_count

    def _throttle(self) -> None:
        """Sleep if needed to respect rate limit."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            sleep_time = self._min_interval - elapsed
            logger.debug("llm_throttle", sleep_seconds=round(sleep_time, 2))
            time.sleep(sleep_time)
        self._last_request_time = time.monotonic()
