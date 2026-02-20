"""Prompt templates for LLM-based surface enrichment."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are a senior software architect analyzing source code to extract behavioral requirements.
For each code surface provided, generate:
1. A behavioral description explaining what the code does from a user/system perspective
2. The inferred intent — why this code exists
3. Given/When/Then acceptance criteria (as a JSON array of objects with "given", "when", "then" keys)
4. Data flow description
5. Priority assessment (critical/high/medium/low)
6. Dependencies (list of other components/services this depends on)

Respond ONLY with valid JSON matching this schema:
{
  "behavioral_description": "string",
  "inferred_intent": "string",
  "given_when_then": [{"given": "string", "when": "string", "then": "string"}],
  "data_flow": "string",
  "priority": "critical|high|medium|low",
  "dependencies": ["string"]
}
"""


def build_enrichment_prompt(
    surface_type: str,
    surface_name: str,
    surface_data: dict[str, object],
    source_code: str,
) -> str:
    """Build a user prompt for enriching a specific surface.

    Args:
        surface_type: The type of surface (route, api, model, etc.).
        surface_name: The name of the surface.
        surface_data: Serialized surface data dict.
        source_code: The relevant source code snippet.

    Returns:
        The formatted user prompt string.
    """
    # Truncate very large source code to stay within context
    max_code_chars = 8000
    if len(source_code) > max_code_chars:
        source_code = source_code[:max_code_chars] + "\n... (truncated)"

    return f"""\
Analyze this {surface_type} surface named "{surface_name}".

Surface metadata:
{_format_surface_data(surface_data)}

Source code:
```
{source_code}
```

Generate behavioral requirements as specified in the system prompt.
"""


def _format_surface_data(data: dict[str, object]) -> str:
    """Format surface data as readable key-value pairs."""
    lines: list[str] = []
    for key, value in data.items():
        if key in ("source_refs", "enrichment"):
            continue
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
