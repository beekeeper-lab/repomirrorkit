"""Run generated Gherkin scenarios against a live app over HTTP (BEAN-074/078).

The harvester's generator (``generator/gherkin.py``) emits behaviour-only
steps. This runner binds the API-level phrasing it produces to generic HTTP
steps — it does not need (or contain) any application knowledge beyond the
OpenAPI contract that ships with the harvest:

- ``the client sends METHOD /path [with "a", "b" | without "x"]``
- ``the response status is N`` / ``the request is rejected with a client error``
  / ``the request is rejected as unauthorized``
- ``the body contains "a", "b"`` / ``each item contains "a"``
- ``the service is running [and the client is authenticated]`` /
  ``the client is not authenticated``

Scenarios built from other phrasings (rules, invariants, screens, lifecycles)
are reported as *unbound*, never silently counted as passes. Scenarios run in
file order against one live instance; ``{param}`` path segments take the most
recently created entity id.

Calibration: when the same suite is also run against the *original* app, the
rebuild is scored relative to the scenarios the original itself passes, so
scenarios the generator phrases ambiguously cannot unfairly sink a rebuild.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from repo_mirror_kit.harvester.parity.server import http_call

_TAG_RE = re.compile(r"@[\w-]+")
_SEND_RE = re.compile(
    r'^the client sends (?P<method>[A-Z]+) (?P<path>\S+)(?: (?P<mode>with|without) (?P<fields>"[^"]+"(?:, "[^"]+")*))?$'
)
_STATUS_RE = re.compile(r"^the response status is (?P<code>\d{3})$")
_CONTAINS_RE = re.compile(
    r'^(?:the body|each item) contains (?P<fields>"[^"]+"(?:, "[^"]+")*)$'
)
_FIELDS_RE = re.compile(r'"([^"]+)"')

_SAMPLES: dict[str, Any] = {
    "string": "sample value",
    "integer": 1,
    "number": 1.5,
    "boolean": True,
    "array": [],
    "object": {},
}


@dataclass
class Step:
    keyword: str
    text: str


@dataclass
class Scenario:
    feature: str
    name: str
    tags: list[str]
    steps: list[Step]
    outline: bool = False


@dataclass
class ScenarioResult:
    feature: str
    name: str
    status: str  # passed | failed | unbound
    detail: str = ""


def parse_feature(text: str, feature_file: str = "") -> list[Scenario]:
    """Parse the generator's ``.feature`` dialect (no external dependency)."""
    scenarios: list[Scenario] = []
    current: Scenario | None = None
    pending_tags: list[str] = []
    feature_name = feature_file
    in_examples = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            pending_tags = _TAG_RE.findall(line)
            continue
        if line.startswith("Feature:"):
            feature_name = line.split(":", 1)[1].strip()
            continue
        m = re.match(r"^(Scenario Outline|Scenario):\s*(.*)$", line)
        if m:
            current = Scenario(
                feature=feature_name,
                name=m.group(2),
                tags=pending_tags,
                steps=[],
                outline=m.group(1) == "Scenario Outline",
            )
            scenarios.append(current)
            pending_tags = []
            in_examples = False
            continue
        if line.startswith("Examples:"):
            in_examples = True
            continue
        if current is None or in_examples or line.startswith("|"):
            continue
        sm = re.match(r"^(Given|When|Then|And|But)\s+(.*)$", line)
        if sm:
            current.steps.append(Step(sm.group(1), sm.group(2).strip()))
    return scenarios


class _Contract:
    """OpenAPI lookups for request-body sampling."""

    def __init__(self, contract: dict[str, Any] | None) -> None:
        self._paths = (contract or {}).get("paths", {})

    def body_fields(self, method: str, path: str) -> dict[str, str]:
        op = self._op(method, path)
        if not op:
            return {}
        try:
            props = op["requestBody"]["content"]["application/json"]["schema"][
                "properties"
            ]
        except (KeyError, TypeError):
            return {}
        return {name: str(spec.get("type", "string")) for name, spec in props.items()}

    def _op(self, method: str, path: str) -> dict[str, Any] | None:
        norm = re.sub(r"\{[^}]+\}", "{}", path)
        for p, ops in self._paths.items():
            if re.sub(r"\{[^}]+\}", "{}", p) == norm:
                found = ops.get(method.lower())
                return found if isinstance(found, dict) else None
        return None


@dataclass
class _Context:
    base_url: str
    contract: _Contract
    auth_headers: dict[str, str]
    last_id: Any = 1
    authenticated: bool = True
    status: int | None = None
    body: Any = None
    steps_bound: int = 0
    failures: list[str] = field(default_factory=list)


def _bind_path(path: str, ctx: _Context) -> str:
    return re.sub(r"\{[^}]+\}", lambda _m: str(ctx.last_id), path)


def _run_scenario(sc: Scenario, ctx: _Context) -> ScenarioResult:
    if sc.outline:
        return ScenarioResult(sc.feature, sc.name, "unbound", "scenario outline")
    ctx.status = None
    ctx.body = None
    ctx.authenticated = True
    saw_send = False
    pending_checks: list[tuple[str, Any]] = []
    for step in sc.steps:
        text = step.text
        if text.startswith("the service is running"):
            ctx.authenticated = "client is authenticated" in text or True
            continue
        if text == "the client is not authenticated":
            ctx.authenticated = False
            continue
        send = _SEND_RE.match(text)
        if send:
            if "in a way the service rejects" in text:
                return ScenarioResult(
                    sc.feature, sc.name, "unbound", "needs a failing input"
                )
            method, path = send.group("method"), send.group("path")
            declared = ctx.contract.body_fields(method, path)
            mode = send.group("mode")
            named = _FIELDS_RE.findall(send.group("fields") or "")
            body: dict[str, Any] | None = None
            if method in ("POST", "PUT", "PATCH"):
                if mode == "without":
                    body = {
                        f: _SAMPLES.get(t, "x")
                        for f, t in declared.items()
                        if f not in named
                    }
                elif named:
                    body = {
                        f: _SAMPLES.get(declared.get(f, "string"), "x") for f in named
                    }
                else:
                    body = {}
            headers = dict(ctx.auth_headers) if ctx.authenticated else {}
            status, parsed, _raw = http_call(
                ctx.base_url, method, _bind_path(path, ctx), headers, body
            )
            ctx.status, ctx.body = status, parsed
            saw_send = True
            if 200 <= status < 300 and isinstance(parsed, dict) and "id" in parsed:
                ctx.last_id = parsed["id"]
            continue
        code = _STATUS_RE.match(text)
        if code:
            pending_checks.append(("status", int(code.group("code"))))
            continue
        if text == "the request is rejected with a client error":
            pending_checks.append(("4xx", None))
            continue
        if text == "the request is rejected as unauthorized":
            pending_checks.append(("auth", None))
            continue
        contains = _CONTAINS_RE.match(text)
        if contains:
            pending_checks.append(
                ("contains", _FIELDS_RE.findall(contains.group("fields")))
            )
            continue
        return ScenarioResult(
            sc.feature, sc.name, "unbound", f"unrecognised step: {text[:60]}"
        )
    if not saw_send:
        return ScenarioResult(sc.feature, sc.name, "unbound", "no HTTP action")
    for kind, arg in pending_checks:
        status = ctx.status or 0
        if kind == "status" and status != arg:
            return ScenarioResult(
                sc.feature, sc.name, "failed", f"status {status} != {arg}"
            )
        if kind == "4xx" and not 400 <= status < 500:
            return ScenarioResult(
                sc.feature, sc.name, "failed", f"status {status} is not 4xx"
            )
        if kind == "auth" and status not in (401, 403):
            return ScenarioResult(
                sc.feature, sc.name, "failed", f"status {status} is not 401/403"
            )
        if kind == "contains":
            item = ctx.body[0] if isinstance(ctx.body, list) and ctx.body else ctx.body
            if not isinstance(item, dict) or any(f not in item for f in arg):
                return ScenarioResult(
                    sc.feature, sc.name, "failed", f"body lacks {arg}"
                )
    return ScenarioResult(sc.feature, sc.name, "passed")


@dataclass
class GherkinRun:
    results: list[ScenarioResult]

    @property
    def bound(self) -> int:
        return sum(1 for r in self.results if r.status != "unbound")

    @property
    def passed_names(self) -> set[tuple[str, str]]:
        return {(r.feature, r.name) for r in self.results if r.status == "passed"}

    @property
    def pass_rate(self) -> float | None:
        return len(self.passed_names) / self.bound if self.bound else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenarios": len(self.results),
            "bound": self.bound,
            "unbound": len(self.results) - self.bound,
            "passed": len(self.passed_names),
            "pass_rate": self.pass_rate,
            "failures": [
                {"feature": r.feature, "scenario": r.name, "detail": r.detail}
                for r in self.results
                if r.status == "failed"
            ][:25],
        }


def load_scenarios(gherkin_dir: Path) -> list[Scenario]:
    out: list[Scenario] = []
    for path in sorted(gherkin_dir.glob("*.feature")):
        out.extend(parse_feature(path.read_text(encoding="utf-8"), path.name))
    return out


def run_scenarios(
    base_url: str,
    scenarios: list[Scenario],
    contract: dict[str, Any] | None,
    auth_headers: dict[str, str],
) -> GherkinRun:
    ctx = _Context(
        base_url=base_url, contract=_Contract(contract), auth_headers=auth_headers
    )
    return GherkinRun([_run_scenario(sc, ctx) for sc in scenarios])


def load_contract(harvest_dir: Path) -> dict[str, Any] | None:
    path = harvest_dir / "api-contract.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None
