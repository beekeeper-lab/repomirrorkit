"""Tool-use enrichment loop (BEAN-068).

Runs one surface through a bounded read-only investigation: the model may call
``read_file`` / ``grep`` / ``list_dir`` (see :mod:`tools`) up to ``max_turns``
times, then must answer with the enrichment JSON. On turn exhaustion a final
tool-less turn forces an answer so work already paid for is never discarded.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import structlog

from repo_mirror_kit.harvester.llm.prompts import AGENT_SYSTEM_PROMPT
from repo_mirror_kit.harvester.llm.tools import TOOL_SPECS, RepoTools

logger = structlog.get_logger()

_MAX_TOOL_RESULT_CHARS = 30_000


class _Response(Protocol):
    content: list[dict[str, Any]]
    stop_reason: str
    input_tokens: int
    output_tokens: int


class ToolClient(Protocol):
    """What the loop needs from an LLM client (satisfied by ``LLMClient``)."""

    def create_message(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = ...,
        max_tokens: int = ...,
    ) -> _Response: ...


@dataclass
class AgentResult:
    """Outcome of one surface's agentic run."""

    final_text: str = ""
    turns: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    status: str = "ok"  # ok | turn_limit | failed
    tools_used: list[str] = field(default_factory=list)


def _text_of(blocks: list[dict[str, Any]]) -> str:
    return "\n".join(b["text"] for b in blocks if b.get("type") == "text").strip()


def run_agent(
    client: ToolClient,
    user_prompt: str,
    tools: RepoTools,
    max_turns: int,
) -> AgentResult:
    """Drive the tool loop for one surface and return the final text."""
    result = AgentResult()
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_prompt}]

    for _ in range(max_turns):
        response = client.create_message(AGENT_SYSTEM_PROMPT, messages, TOOL_SPECS)
        result.turns += 1
        result.input_tokens += response.input_tokens
        result.output_tokens += response.output_tokens
        calls = [b for b in response.content if b.get("type") == "tool_use"]
        if not calls:
            result.final_text = _text_of(response.content)
            return result
        messages.append({"role": "assistant", "content": response.content})
        tool_results: list[dict[str, Any]] = []
        for call in calls:
            output = tools.execute(str(call["name"]), dict(call.get("input") or {}))
            result.tool_calls += 1
            result.tools_used.append(str(call["name"]))
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": call["id"],
                    "content": output[:_MAX_TOOL_RESULT_CHARS],
                }
            )
        messages.append({"role": "user", "content": tool_results})

    # Turn budget spent: force a final answer without tools.
    messages.append(
        {
            "role": "user",
            "content": (
                "Turn limit reached. Reply NOW with only the JSON object, "
                'listing in "gaps" what you could not verify.'
            ),
        }
    )
    response = client.create_message(AGENT_SYSTEM_PROMPT, messages, None)
    result.turns += 1
    result.input_tokens += response.input_tokens
    result.output_tokens += response.output_tokens
    result.final_text = _text_of(response.content)
    result.status = "turn_limit"
    return result


def parse_agent_json(text: str) -> dict[str, Any] | None:
    """Extract the JSON object from a model reply (fenced or bare)."""
    body = text.strip()
    if body.startswith("```"):
        lines = body.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        body = "\n".join(lines)
    start, end = body.find("{"), body.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(body[start : end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
